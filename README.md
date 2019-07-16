# XAPIZ3500

There are 2 sets of code, the Raspberry PI side and the K210 side.
 - pi/
 - k210/

## Raspberry PI Setup
In the Preferences -> Raspberry PI Configuration - Interface
 - SPI (enable)
 - Serial Port (enable)
 - Serial Console (disable)

## Interface Description
There are 2 SPI interface in XAPIZ3500. One is connected to PI while the other is connected to K210.

| Port | SPI Mode | Speed |
|------|----------|-------|
| PI   | Mode 0   | 40Mhz |
| K210 | Mode 0   | 40Mhz |


### Rev1 and Rev2 Pinout

| Port | SCLK | MOSI | MISO | CS  | RDY |
|------|------|------|------|-----|-----|
| PI   |23|19|21|24|22|
| K210 |IO30|IO32|IO31|IO29|IO33|

RDY when "1" indicates there is data in buffer to be read. Can be used to trigger interrupt.
