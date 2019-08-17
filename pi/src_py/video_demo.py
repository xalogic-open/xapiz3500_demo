import numpy as np
import os
import cv2
import picamera
import time
import xapi_spi
import random
import datetime
import struct
from collections import namedtuple
import argparse
import sys
from gpiozero import LED


def image_resize(image, width = None, height = None, inter = cv2.INTER_NEAREST):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    new_ratio = float(width / height)
    old_ratio = float(w / h)

    if old_ratio > new_ratio:
        r = width / float(w)
        dim = (width, int(h * r))
    elif old_ratio < new_ratio:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        dim = (width, height)

    # resize the image
    resized = cv2.resize(image, dim, interpolation = inter)

    old_size = resized.shape[:2] # old_size is in (height, width) format

    delta_w = width - old_size[1]
    delta_h = height - old_size[0]
    top, bottom = delta_h//2, delta_h-(delta_h//2)
    left, right = delta_w//2, delta_w-(delta_w//2)

    #color = [0, 0, 0]
    color = [255, 255, 255]
    resized = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)

    # return the resized image
    return resized

def main(model_def,vidsrc):
  print("Reset K210")
  k210_reset = LED(27)

  k210_reset.off()
  time.sleep(0.5)
  k210_reset.on()
  time.sleep(0.5)
  print("Reset K210 .... Done")


  #VOC
  classname = ["aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

  fps = 0
  fps_store = 0


  xapispi = xapi_spi.Xapi_spi(0,0,60000000)
  xapispi.init()

  boxstruct = namedtuple('boxstruct',['x1','y1','x2','y2','boxclass','prob'])



  cap = cv2.VideoCapture(vidsrc)
  print (cap.get(cv2.CAP_PROP_FPS))

  # Check if camera opened successfully
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")

  #Send a dummy image over
  img = np.empty((224, 320, 3), dtype=np.uint8)
  xapispi.spi_send_img(img)


  font                   = cv2.FONT_HERSHEY_PLAIN
  TopLeftCornerOfText = (10,11)
  fontScale              = 1
  fontColor              = (165,26,26)
  lineType               = 1

  pending_box = False
  boxes = []
  boxesold = []
 
  # Read until video is completed

  starttime = datetime.datetime.now()
  while(cap.isOpened()):

    # Capture frame-by-frame
    ret, frame = cap.read()
    if ret == True:
      img = image_resize(frame, width=320, height = 224)
  
  
      if not pending_box:
        pending_box = True
        xapispi.spi_send_img(img)
  
      boxes = xapispi.spi_getbox(False) #Non-blocking
  
      if (len(boxes) > 0):
        #print (boxes)
        if boxes[0] != "na":
          #print("box update")
          boxesold = boxes
          pending_box = False
          fps += 1 
        else:
          print("Box not ready")
      else:
        #print ("No Boxes detected")
        pending_box = False
        boxesold = boxes
        fps += 1 
  
      if len(boxesold) > 0 and boxes[0] != "na":
        for box in boxesold:
          x1 = box.x1
          x2 = box.x2
          y1 = box.y1
          y2 = box.y2
          boxclass = box.boxclass
          prob = box.prob
          if model_def == 'voc':
            text = "{} : {:.2f}".format(classname[boxclass[0]],prob[0])
          else:
            text = "{:.2f}".format(prob[0])
          if prob[0] > 0.7:
            cv2.putText(img, text, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX,0.5,fontColor, 1)
            cv2.rectangle(img, (x1, y1), (x2, y2), fontColor, 1)

      endtime = datetime.datetime.now()

      difftime = endtime-starttime
      if difftime.total_seconds() > 10.0:
        fps_store = fps
        fps=0
        starttime = datetime.datetime.now()
        print("FPS : "+str(fps_store/10))


      cv2.imshow('XaLogic XAPIZ3500 Demo',img)
      endtime = datetime.datetime.now()
 
      # Press Q on keyboard to  exit
      if cv2.waitKey(1) & 0xFF == ord('q'):
        break
 
    # Break the loop
    else: 
      break
 
  # When everything done, release the video capture object
  cap.release()
 
  # Closes all the frames
  cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--vidsrc', type=str, help='Video file path.', default='data/traffic.mp4')
    parser.add_argument('--model_def', type=str, help='Model definition.', choices=['face', 'voc'], default='voc')

    args = parser.parse_args(sys.argv[1:])

    main(args.model_def, args.vidsrc)

