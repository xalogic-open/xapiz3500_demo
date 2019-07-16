#ifndef _FPGS_SPI_H
#define _FPGS_SPI_H

#ifdef __cplusplus
 extern "C" {
#endif

#include "stdint.h"

//#define FPGA_SPI_BLK_SIZE 2048
#define FPGA_SPI_BLK_SIZE 512


uint8_t spi_get_rdy(void);
uint32_t spi_rd_avail(void);
uint32_t spi_wr_space(void);
void spi_write_data(uint8_t *data_buff, uint32_t length);
void spi_read_data(uint8_t *data_buff, uint32_t length);

void spi_write_data_dma(uint8_t *data_buff, uint32_t length);
void spi_read_data_dma(uint8_t *data_buff, uint32_t length);

void spi_fifo_read(uint8_t *data_buff, uint32_t length);
void spi_fifo_read_dma(uint8_t *data_buff, uint32_t length);
void spi_fifo_write(uint8_t *data_buff, uint32_t length);


void fpga_spi_init(void);
void fpga_spi_test(void);
void fpga_spi_get_img(uint8_t *data_buf, uint32_t length);
void fpga_spi_send_img(uint8_t *data_buf, uint32_t length);

uint8_t spi_reg_rd(uint8_t address);
void spi_reg_wr(uint8_t data, uint8_t address);







#ifdef __cplusplus
}
#endif

#endif
