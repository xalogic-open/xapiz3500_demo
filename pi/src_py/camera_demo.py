import numpy as np
import os
import cv2
from picamera import PiCamera
from picamera.array import PiRGBArray
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

def main(model_def):

  camera = PiCamera()
  camera.resolution = (640, 480)
  camera.framerate = 60
  rawCapture = PiRGBArray(camera, size=(640, 480))

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


  #xapispi = xapi_spi.Xapi_spi(0,0,60000000)
  xapispi = xapi_spi.Xapi_spi(0,0,60000000)
  xapispi.init()

  boxstruct = namedtuple('boxstruct',['x1','y1','x2','y2','boxclass','prob'])



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
  for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # grab the raw NumPy array representing the image, then initialize the timestamp
    # and occupied/unoccupied text

    img = frame.array
    img = image_resize(img, width=320, height = 224)
    rawCapture.truncate(0)
  
    xapispi.spi_send_img(img)
    boxes = xapispi.spi_getbox()
  
    fps += 1 
  
    if len(boxes) > 0:
      for box in boxes:
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
 
  # Closes all the frames
  cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_def', type=str, help='Model definition.', choices=['face', 'voc'], default='voc')

    args = parser.parse_args(sys.argv[1:])

    main(args.model_def)

