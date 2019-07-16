#include "fpga_spi.h"
#include "sysctl.h"
#include "gpiohs.h"
#include "fpioa.h"
#include "dmac.h"
#include "spi.h"
#include <stdio.h>
#include "gpiohs.h"
#include "gpio.h"
#include "unistd.h"


void fpga_spi_init(void)
{
	gpiohs_set_drive_mode(1, GPIO_DM_OUTPUT); //SPI_CS
	gpiohs_set_pin(1, GPIO_PV_HIGH);


	gpiohs_set_drive_mode(2, GPIO_DM_INPUT); //SPI_RDY


	spi_set_clk_rate(SPI_DEVICE_1, 40000000);     /*set clk rate*/
    //spi_set_clk_rate(SPI_DEVICE_1, 10000000);     /*set clk rate*/
	spi_init(SPI_DEVICE_1, SPI_WORK_MODE_0, SPI_FF_STANDARD, 8, 0);

}


void fpga_spi_get_img(uint8_t *data_buf, uint32_t length)
{
	uint32_t xfercnt = 0;
	uint32_t rd_avail_cnt;
	uint32_t xfer_length = length;


	while (xfercnt != length){

		if (xfer_length >= FPGA_SPI_BLK_SIZE){

			rd_avail_cnt = spi_rd_avail();
			
			while (rd_avail_cnt < FPGA_SPI_BLK_SIZE) {

				rd_avail_cnt = spi_rd_avail();
			}

			spi_fifo_read(data_buf+xfercnt,FPGA_SPI_BLK_SIZE);

			xfercnt += FPGA_SPI_BLK_SIZE;
			xfer_length -= FPGA_SPI_BLK_SIZE;
	

		} else { //Last transfer odd block

			rd_avail_cnt = spi_rd_avail();
			while (rd_avail_cnt < xfer_length) {
				rd_avail_cnt = spi_rd_avail();
			}
			printf("Avail cnt : %d",rd_avail_cnt);

			spi_fifo_read(data_buf+xfercnt,xfer_length);

			xfercnt += xfer_length;
			xfer_length = 0;

			
		}
	}

}


void fpga_spi_send_img(uint8_t *data_buf, uint32_t length)
{
	uint32_t xfercnt = 0;
	uint32_t wr_space_cnt;
	uint32_t xfer_length = length;


	while (xfercnt != length){

		if (xfer_length >= FPGA_SPI_BLK_SIZE){

			wr_space_cnt = spi_wr_space();
			while (wr_space_cnt < FPGA_SPI_BLK_SIZE) {
				wr_space_cnt = spi_wr_space();
			}

			spi_fifo_write(data_buf+xfercnt,FPGA_SPI_BLK_SIZE);
			xfercnt += FPGA_SPI_BLK_SIZE;
			xfer_length -= FPGA_SPI_BLK_SIZE;

		} else { //Last transfer odd block

			wr_space_cnt = spi_wr_space();
			while (wr_space_cnt < xfer_length) {
				wr_space_cnt = spi_wr_space();
			}

			spi_fifo_write(data_buf+xfercnt,xfer_length);
			xfercnt += xfer_length;
			xfer_length = 0;
			
		}
	}

}






void spi_reg_wr(uint8_t data, uint8_t address)
{

    gpiohs_set_pin(1, GPIO_PV_LOW); //Assert CS
	spi_write_data(&address, 1); //Address
	spi_write_data(&data, 1); //Data
	gpiohs_set_pin(1, GPIO_PV_HIGH); //De-Assert CS


}


uint8_t spi_reg_rd(uint8_t address)
{
	uint8_t rddata;
	address = address | 0x80;

    gpiohs_set_pin(1, GPIO_PV_LOW); //Assert CS
	spi_write_data(&address, 1); //Address
	spi_write_data(&address, 1); //Dummy cycle
	spi_read_data(&rddata, 1);
	gpiohs_set_pin(1, GPIO_PV_HIGH); //De-Assert CS
	return rddata;
}

uint8_t spi_get_rdy(void){
	return gpiohs_get_pin(2);
}

uint32_t spi_rd_avail(void){

	uint32_t count;
	uint8_t rddata;

	rddata = spi_reg_rd(0x0A);
	count = rddata;
	rddata = spi_reg_rd(0x0B);
	count = rddata*256 + count;
	return count;
}

uint32_t spi_wr_space(void){

	uint32_t count;
	uint8_t rddata;

	rddata = spi_reg_rd(0x08);
	count = rddata;
	rddata = spi_reg_rd(0x09);
	count = rddata*256 + count;
	return count;
}


void spi_fifo_read(uint8_t *data_buff, uint32_t length)
{
	uint8_t address[2];
	address[0] = 0xA0; //Actual address is 0x20. Set bit[7] to "1" for READ operation
	address[1] = 0xA0;

	gpiohs_set_pin(1, GPIO_PV_LOW); //Assert CS
	spi_write_data(&address, 2); //Address
	spi_read_data(data_buff, length);

	gpiohs_set_pin(1, GPIO_PV_HIGH); //De-Assert CS

}

void spi_fifo_read_dma(uint8_t *data_buff, uint32_t length)
{
	uint8_t address;
	address = 0xA0; //Actual address is 0x20. Set bit[7] to "1" for READ operation

	gpiohs_set_pin(1, GPIO_PV_LOW); //Assert CS
	spi_write_data(&address, 1); //Address
	spi_write_data(&address, 1); //Dummy cycle
	//spi_read_data(data_buff, length);
	spi_read_data_dma(data_buff, length);
	gpiohs_set_pin(1, GPIO_PV_HIGH); //De-Assert CS

}

void spi_fifo_write(uint8_t *data_buff, uint32_t length)
{
	uint8_t address;
	address = 0x10; //Actual address is 0x10. Set bit[7] to "0" for WRITE operation

	gpiohs_set_pin(1, GPIO_PV_LOW); //Assert CS
	spi_write_data(&address, 1); //Address
	spi_write_data(data_buff, length);
	gpiohs_set_pin(1, GPIO_PV_HIGH); //De-Assert CS

}



void spi_write_data(uint8_t *data_buff, uint32_t length)
{
    
	spi_send_data_normal(SPI_DEVICE_1, SPI_CHIP_SELECT_3, data_buff, length);
}

void spi_read_data(uint8_t *data_buff, uint32_t length)
{

   
    spi_receive_data_standard(SPI_DEVICE_1, SPI_CHIP_SELECT_3, NULL, 0, data_buff, length);

}


void spi_write_data_dma(uint8_t *data_buff, uint32_t length)
{
    
    spi_send_data_standard_dma(DMAC_CHANNEL2, SPI_DEVICE_1, SPI_CHIP_SELECT_3, NULL, 0, data_buff, length);
}

void spi_read_data_dma(uint8_t *data_buff, uint32_t length)
{
    spi_init(SPI_DEVICE_1, SPI_WORK_MODE_0, SPI_FF_STANDARD, 8, 0);
    spi_receive_data_standard_dma(-1, DMAC_CHANNEL0, SPI_DEVICE_1, SPI_CHIP_SELECT_3, NULL, 0, data_buff, length);

}



