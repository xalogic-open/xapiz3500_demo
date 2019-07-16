import spidev
import numpy as np
import struct
from collections import namedtuple 



class Xapi_spi:
  def __init__(self, bus, device, speed):
    self.bus = bus
    self.device = device
    self.speed = speed

################################################
# Initialize SPI
################################################
  def init(self):
    self.spi = spidev.SpiDev()
    self.spi.open(self.bus, self.device)
    self.spi.max_speed_hz = self.speed

################################################
# Takes a full image (BGR) from application 
# and send it as R - G - B
################################################
  def spi_send_img(self, img, blocksize):
    tmpbuf = []
    _b, _g, _r    = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    #Create a 1D view of the Channels
    b = _b.ravel()
    g = _g.ravel()
    r = _r.ravel()

    #Send image over SPI, in R->G->B

    #totalsize  = len(r) + len(g) + len(b)
    #print (totalsize)
    #tmpbuf.append(0xaa)
    #tmpbuf.append(0x55)
    #tmpbuf.append(0xaa)
    #tmpbuf.append(0x55)
    #tmpbuf.append(0x10)
    #tmpbuf.append(totalsize & 0xff)
    #tmpbuf.append(totalsize>>8 & 0xff)
    #tmpbuf.append(totalsize>>16 & 0xff)
    ##print (tmpbuf)
    #self.spi_tx(tmpbuf)
    self.spi_wr_img(r,blocksize)
    self.spi_wr_img(g,blocksize)
    self.spi_wr_img(b,blocksize)


################################################
# Write data to FIFO while breaking it down 
# into blocks.
################################################
  def spi_wr_img(self, img, blocksize):
    xfersize = len(img)
    xferindex = 0

    while xfersize != 0:
      if xfersize >= blocksize:
        #Ensure FPGA buffer is sufficient
        while self.spi_wrspace() < blocksize:
          pass

        wrbuf = img[xferindex:xferindex+blocksize]
        #self.spi_tx(wrbuf)
        self.spi_tx(img[xferindex:xferindex+blocksize])


        xfersize = xfersize - blocksize
        xferindex = xferindex + blocksize

      else:
        #Ensure FPGA buffer is sufficient
        while self.spi_wrspace() < xfersize:
          pass

        wrbuf = img[xferindex:]
        self.spi_tx(wrbuf)
        xfersize = 0
        xferindex = 0


################################################
# Get bounding box.
# If towait=True, will wait until box available
################################################
  def spi_getbox(self, towait=True):

    boxstruct = namedtuple('boxstruct',['x1','y1','x2','y2','boxclass','prob'])
    boxes=[]

    if towait:
      while self.spi_rdavail() < 4: 
        pass
    else:
      if self.spi_rdavail() < 4: 
        boxes.append("na")
        return boxes
    
    txbuf = np.zeros((4),dtype=int)
    rxbuf = self.spi_rx(txbuf)
    numbox = rxbuf[0]

    if numbox == 0:
      return boxes
    else:
      xfercnt = numbox * 16

      while self.spi_rdavail() < xfercnt: 
        pass
    
      txbuf = np.zeros((xfercnt),dtype=int)
      rxbuf = self.spi_rx(txbuf)

      for i in range(numbox):
        onebox = rxbuf[(i*16):(i*16)+16]
        #print(onebox)
        _x1 = onebox[0:2]
        _y1 = onebox[2:4]
        _x2 = onebox[4:6]
        _y2 = onebox[6:8]
        _boxclass = onebox[8:12]
        _prob = onebox[12:16]

        x1 = struct.unpack('<h',bytes(_x1))
        y1 = struct.unpack('<h',bytes(_y1))
        x2 = struct.unpack('<h',bytes(_x2))
        y2 = struct.unpack('<h',bytes(_y2))
        boxclass = struct.unpack('<l',bytes(_boxclass))
        prob = struct.unpack('<f',bytes(_prob))
        x1 = int(x1[0])
        x2 = int(x2[0])
        y1 = int(y1[0])
        y2 = int(y2[0])

        b = boxstruct(x1,y1,x2,y2,boxclass,prob)
        boxes.append(b)

    return boxes


################################################
# SPI read from FIFO
# The address is 0xA0.
# For read, a dummy byte is needed, 
#   so we simply send the address twice.
# Because of the 2 cycle, we need to delete
#   2 bytes from the received data.
################################################
  def spi_rx(self,txdata):
    txdata = txdata.tolist()
    txdata.insert(0,0xA0)
    txdata.insert(0,0xA0) #Dummy cycle
    #rxdata = self.spi.xfer2(txdata)
    rxdata = self.spi.xfer2(txdata,self.speed,0)
    del rxdata[0] #Not real data
    del rxdata[0] #Not real data
    return rxdata

    
################################################
# SPI write to FIFO
# The address is 0x10, followed by data.
################################################
  def spi_tx(self,txdata):
    txdata = np.insert(txdata,0,0x10,axis=0)
    self.spi.writebytes2(txdata)
    return


################################################
# SPI read from FIFO
# The address is 0xA0.
# For read, a dummy byte is needed, 
#   so we simply send the address twice.
# Because of the 2 cycle, we need to delete
#   2 bytes from the received data.
################################################
  def spi_rx(self,txdata):
    txdata = txdata.tolist()
    txdata.insert(0,0xA0)
    txdata.insert(0,0xA0) #Dummy cycle
    #print(np.shape(txdata))
    #print(txdata)
    #txdata = np.insert(txdata,0,0xA0,axis=0)
    #txdata = np.insert(txdata,0,0xA0,axis=0)
    #print(np.shape(txdata))
    #print(txdata)
    rxdata = self.spi.xfer2(txdata)
    #rxdata = self.spi.xfer3(txdata,self.speed,0)
    #rxdata = self.spi.xfer3(txdata)
    del rxdata[0] #Not real data
    del rxdata[0] #Not real data
    return rxdata

    
################################################
# Check the amount of space avaialable in FIFO
# Address 0x88 : wr_space[7:0]
# Address 0x89 : wr_space[15:8]
################################################
  def spi_wrspace(self):
    cmd = []
    cmd.append(0x88) #Address 
    cmd.append(0x00) #Dummy cycle
    cmd.append(0x00) #Read data
    rddata = self.spi.xfer2(cmd)
    wr_space = rddata[2]

    cmd = []
    cmd.append(0x89) #Address
    cmd.append(0x00) #Dummy cycle
    cmd.append(0x00) #Read data
    rddata = self.spi.xfer2(cmd)
    wr_space = rddata[2]*256 + wr_space #Pack it to 16 bits

    return wr_space

################################################
# Check the amount of data in FIFO to be read
# Address 0x8A : rd_avail[7:0]
# Address 0x8B : rd_avail[15:8]
################################################
  def spi_rdavail(self):
    cmd = []
    cmd.append(0x8A) #Address
    cmd.append(0x00) #Dummy cycle
    cmd.append(0x00) #Read data
    rddata = self.spi.xfer2(cmd)
    rd_avail = rddata[2]

    cmd = []
    cmd.append(0x8B) #Address
    cmd.append(0x00) #Dummy cycle
    cmd.append(0x00) #Read data
    rddata = self.spi.xfer2(cmd)
    rd_avail = rddata[2]*256 + rd_avail #Pack it to 16 bits
    return rd_avail


    

################################################
# Read Version of Board
# When reading a register, bit[7] is always "1"
#   and a dummy cycle is always needed.
################################################
  def spi_rd_boardver(self):
    msg = [0x80] 	#Address
    msg.append(0x00)	#Dummy cycle
    msg.append(0x00)	#Data
    version = self.spi.xfer2(msg)
    return version[2]

################################################
# Read Version of FPGA
# When reading a register, bit[7] is always "1"
#   and a dummy cycle is always needed.
################################################
  def spi_rd_fpgaver(self):
    msg = [0x81]        #Address
    msg.append(0x00)    #Dummy cycle
    msg.append(0x00)    #Data
    version = self.spi.xfer2(msg)
    return version[2]
