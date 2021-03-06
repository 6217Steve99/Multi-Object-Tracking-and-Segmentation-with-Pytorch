import matplotlib.pyplot as plt
import matplotlib.pylab as pylab

import requests
from io import BytesIO
from PIL import Image
import numpy as np
from maskrcnn_benchmark.config import cfg
from mypredictor import COCODemo
import os
import cv2

import sys

def load(url):
    """
    Given an url of an image, downloads the image and
    returns a PIL image
    """
    #response = requests.get(url)
    #pil_image = Image.open(BytesIO(response.content)).convert("RGB")
    pil_image = Image.open(url).convert("RGB")
    # convert to BGR format
    image = np.array(pil_image)[:, :, [2, 1, 0]]
    return image

def imshow(img):
    plt.imshow(img[:, :, [2, 1, 0]])
    plt.axis("off")
    plt.show()

sys.path.append(r"E:\Challenge\MaskR-CNN")

# this makes our figures bigger
# pylab.rcParams['figure.figsize'] = 20, 12

config_file = "./configs/my_test_e2e_mask_rcnn_R_50_FPN_1x.yaml"

# update the config options with the config file
cfg.merge_from_file(config_file)
# manual override some options
cfg.merge_from_list(["MODEL.DEVICE", "cpu"])

coco_demo = COCODemo(
    cfg,
    # min_image_size=300,
    confidence_threshold=0.7,
)

instance = 9

imgPath = os.path.join(r"E:\Challenge\KITTI_MOTS\training\image_02","{:04}".format(instance))

imgDir = os.listdir(imgPath)


for frame in range(len(imgDir)):
    img = os.path.join(imgPath, "{:06}.png".format(frame))
    image = load(img)

    # compute predictions
    predictions = coco_demo.run_on_opencv_image(image)
    savePath = os.path.join(r'E:\Challenge\MaskR-CNN\demo',"predictions{:06}.png".format(frame))
    cv2.imwrite(savePath,predictions)
    print(frame)