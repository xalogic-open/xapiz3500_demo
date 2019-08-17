import numpy as np
import os
import cv2
import picamera
import time
import xapi_spi
import random
import datetime
import struct
import argparse
import sys
from gpiozero import LED


from collections import namedtuple

#VOC Class name
classname = ["aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]


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


def main(imgsrc):
    k210_reset = LED(27)


    k210_reset.off()
    time.sleep(0.5)
    k210_reset.on()
    time.sleep(0.5)


    #xapispi = xapi_spi.Xapi_spi(0,0,4000000)
    xapispi = xapi_spi.Xapi_spi(0,0,60000000)
    xapispi.init()



    boxstruct = namedtuple('boxstruct',['x1','y1','x2','y2','boxclass','prob'])



    font                   = cv2.FONT_HERSHEY_PLAIN
    TopLeftCornerOfText = (10,11)
    bottomLeftCornerOfText = (10,238)
    fontScale              = 1
    fontColor              = (165,26,26)
    lineType               = 1

    boxes = []

    boardver = xapispi.spi_rd_boardver()
    print("Board Version : "+ str(boardver))
    fpgaver = xapispi.spi_rd_fpgaver()
    print("FPGA Version : "+ str(fpgaver) )
 
    #img = cv2.imread('data/dog.jpg')
    img = cv2.imread(imgsrc)
    print("Original image size : "+str(np.shape(img)))
    img_small = image_resize(img, width=320, height = 224)
    img_large = image_resize(img, width=1280, height = 896)
    print("Small image size : "+str(np.shape(img_small)))
    print("Large image size : "+str(np.shape(img_large)))

    #Send the small image to K210
    xapispi.spi_send_img(img_small)

    boxes = xapispi.spi_getbox()

    if len(boxes) > 0 and boxes[0] != "na":
        for box in boxes:
            x1 = box.x1
            x2 = box.x2
            y1 = box.y1
            y2 = box.y2
            boxclass = box.boxclass
            prob = box.prob
            #cv2.rectangle(img_small, (x1*4, y1*4), (x2*4, y2*4), (255,0,0), 2)
            text = "{} : {:.2f}".format(classname[boxclass[0]],prob[0])

            if prob[0] > 0.6:
                cv2.putText(img_small, text, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX,0.5,fontColor, 1)
                cv2.rectangle(img_small, (x1, y1), (x2, y2), (255,0,0), 1)

                cv2.putText(img_large, text, (x1*4, y1*4-5), cv2.FONT_HERSHEY_SIMPLEX,0.5,fontColor, 1)
                cv2.rectangle(img_large, (x1*4, y1*4), (x2*4, y2*4), (255,0,0), 1)


    cv2.imshow('Detection : large',img_large)
    cv2.imshow('Detection : small',img_small)
    cv2.waitKey(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--imgsrc', type=str, help='Model definition.', default='data/dog.jpg')

    args = parser.parse_args(sys.argv[1:])

    main(args.imgsrc)

