#include <stdio.h>
#include "fpioa.h"
#include "sysctl.h"
#include "dmac.h"
#include "fpioa.h"
#include "plic.h"
#include "uarths.h"
#include "bsp.h"
#include "fpga_spi.h"
#include "gpiohs.h"
#include "gpio.h"
#include "main.h"
#include "w25qxx.h"
#define INCBIN_STYLE INCBIN_STYLE_SNAKE
#define INCBIN_PREFIX
#include "incbin.h"
#include "kpu.h"
#include "region_layer.h"

#if PROG_FPGA
  #include "fpga_prog.h"
#endif

#if LOAD_KMODEL_FROM_FLASH
    #define KMODEL_SIZE (4928 * 1024)
    uint8_t model_data[KMODEL_SIZE];
#else
    INCBIN(model, "detect.kmodel");
#endif

kpu_model_context_t task;
static region_layer_t detect_rl;


corelock_t lock;

volatile uint8_t g_start_spi_flag = 0;
volatile uint8_t g_ai_done_flag = 0;
volatile uint32_t g_returnbox_done_flag = 0;
volatile uint32_t g_returnbox_num_flag = 0;

static void ai_done(void *ctx) { g_ai_done_flag= 1; }


uint8_t g_ai_buf0[320 * 224 *3] __attribute__((aligned(128)));
uint8_t g_ai_buf1[320 * 224 *3] __attribute__((aligned(128)));

//uint32_t g_box_result[6*128];
result_box_t g_box_result[128];

#define ANCHOR_NUM 5


#if CLASS_NUMBER == 20 
//VOC
    float g_anchor[ANCHOR_NUM * 2]= {
        0.69738163, 0.79621842, 0.51716131, 0.38546754, 0.29342869,
        0.67185739, 0.17332458, 0.33237338, 0.07665034, 0.14115778,
    };

#elif CLASS_NUMBER == 1 
//Wideface
    float g_anchor[ANCHOR_NUM * 2]= {
        1.241550, 0.773463, 1.414109, 1.405454, 1.734359,
        2.235745, 2.941098, 2.801502, 4.661444, 4.165160
    };
#endif

volatile uint8_t g_dvp_finish_flag= 0;
volatile uint8_t g_ramwr_mux= 0;
volatile uint8_t g_ramrd_mux= 0;




void io_mux_init(void)
{

    
    //SPI0 (Master) : Programming of Lattice FPGA

    fpioa_set_function(22, FUNC_SPI0_SCLK);
    fpioa_set_function(24, FUNC_SPI0_D0);
    fpioa_set_function(21, FUNC_SPI0_D1);

	fpioa_set_function(23, FUNC_GPIOHS0); //CS
    fpioa_set_function(17, FUNC_GPIO0); //ICE_CDONE

    #if REV2
      fpioa_set_function(20, FUNC_GPIO1); //ICE_RESET_B
    #else
      fpioa_set_function(6, FUNC_GPIO1); //ICE_RESET_B
    #endif

    fpioa_set_function(44, FUNC_SPI0_SS3);




    //SPI1 (Master) : Main data path to FPGA
    fpioa_set_function(30, FUNC_SPI1_SCLK);
    fpioa_set_function(32, FUNC_SPI1_D0);
    fpioa_set_function(31, FUNC_SPI1_D1);
	fpioa_set_function(29, FUNC_GPIOHS1); //CS
    fpioa_set_function(25, FUNC_GPIOHS2); //RDY
    fpioa_set_function(45, FUNC_SPI1_SS3);




#if PROG_FPGA

#else
	gpio_set_drive_mode(1, GPIO_DM_OUTPUT); //CRESETB
	gpio_set_pin(1, GPIO_PV_LOW);
	gpio_set_drive_mode(0, GPIO_DM_INPUT_PULL_UP); //CDONE
#endif
 
}

static void io_set_power(void) {
    /* Set dvp and spi pin to 1.8V */
    sysctl_set_power_mode(SYSCTL_POWER_BANK6, SYSCTL_POWER_V18);
    sysctl_set_power_mode(SYSCTL_POWER_BANK7, SYSCTL_POWER_V18);
}



static void returnboxes(uint32_t num) {
 #if DEBUG
    printf("core0 : returnboxes called\n");
#endif

    g_returnbox_num_flag = num;


    fpga_spi_send_img((uint8_t*)&g_returnbox_num_flag,4); 
    if (g_returnbox_num_flag != 0){
        fpga_spi_send_img((uint8_t*)&g_box_result,g_returnbox_num_flag<<4); 
    }
     g_returnbox_done_flag = 1;



}



static void get_img(void) {

    if (g_ramwr_mux == 0){
        fpga_spi_get_img(g_ai_buf0,215040); //Get a full 224x320x3 image from FPGA.
    } else {
        fpga_spi_get_img(g_ai_buf1,215040); //Get a full 224x320x3 image from FPGA.
    }
    g_ramwr_mux^= 0x01;
       
     
}


int main(void)
{


    sysctl_pll_set_freq(SYSCTL_PLL0, PLL0_OUTPUT_FREQ);
    sysctl_pll_set_freq(SYSCTL_PLL1, PLL1_OUTPUT_FREQ);
    uarths_init();
    
    usleep(1000);
    printf("IO Init\n");
    io_mux_init();
    printf("IO Power Set\n");
    io_set_power();
    printf("DMA Init\n");
    dmac_init();
    printf("Interrupt Init\n");
    plic_init();
    printf("System Enable Init\n");
    sysctl_enable_irq();

    
    #if REV2
        printf("REV2 Board\n");
    #else
        printf("REV1 Board\n");
    #endif


    #if PROG_FPGA
        fpga_prog_init();
        fpga_prog_start();
    #else
        gpio_set_pin(1, GPIO_PV_LOW); //Assert CRESETB
        usleep(1000);
        gpio_set_pin(1, GPIO_PV_HIGH); //Release CRESETB
        usleep(1000);
        printf("FPGA Reset Done. Boot from NVCM\n");
    #endif



    w25qxx_init(3, 0);
    w25qxx_enable_quad_mode();
    w25qxx_read_data(0xA00000, model_data, KMODEL_SIZE, W25QXX_QUAD_FAST);
    printf("KPU model loaded from flash\n");


    //Initialize FPGA SPI port
    fpga_spi_init();



     /* init kpu */
    if (kpu_load_kmodel(&task, model_data) != 0) {
        printf("\nmodel init error\n");
        while (1) {};
    }

    printf("KPU model initialized OK\n");


    detect_rl.anchor_number= ANCHOR_NUM;
    detect_rl.anchor= g_anchor;
    detect_rl.threshold= 0.7;
    detect_rl.nms_value= 0.3;
    region_layer_init(&detect_rl, 10, 7, ((CLASS_NUMBER+5)*5), 320, 224);

    dmac_init();

    g_ai_done_flag = 0;
    printf("Region initialized.\n");
    
    get_img(); //Pre-fetch first image

    #if DEBUG
        printf("Initiated to fetch 1 image\n");
    #endif

    
    printf("Running.....\n");

    while (1) {

    
        

    #if 1
        if (g_ramrd_mux == 0){
            kpu_run_kmodel(&task, g_ai_buf0, DMAC_CHANNEL5, ai_done, NULL);
        } else {
            kpu_run_kmodel(&task, g_ai_buf1, DMAC_CHANNEL5, ai_done, NULL);
        }
        
        while (!g_ai_done_flag){
            continue;
        }; //Wait for KPU done

        g_ai_done_flag= 0;
        g_ramrd_mux^= 0x01;
         #if DEBUG
            printf ("Kmodel done\n");
         #endif

        float *output;
        size_t output_size;
        kpu_get_output(&task, 0, (uint8_t **)&output, &output_size);
        detect_rl.input= output;

        /* start region layer */
        region_layer_run(&detect_rl, NULL);

        /* draw boxs */
        region_layer_return_boxes(&detect_rl, g_box_result, returnboxes);

    #endif


        get_img(); //Fetch subsequent image


        while (g_returnbox_done_flag == 0){
            continue;
        };

        g_returnbox_done_flag = 0;
         #if DEBUG
            printf ("Return box main done\n");
        #endif

    }
    



    return 0;
}
