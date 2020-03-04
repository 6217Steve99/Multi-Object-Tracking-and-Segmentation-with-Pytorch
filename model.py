
import datetime
import math
import os
import random
import re

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.utils.data
import cv2
import matplotlib.pyplot as plt
import torchvision
from roi_align import RoIAlign
from roi_align import CropAndResize

class SamePad2d(nn.Module):
    """Mimics tensorflow's 'SAME' padding.
    """

    def __init__(self, kernel_size, stride):
        super(SamePad2d, self).__init__()
        self.kernel_size = torch.nn.modules.utils._pair(kernel_size)
        self.stride = torch.nn.modules.utils._pair(stride)

    def forward(self, input):
        in_width = input.size()[2]
        in_height = input.size()[3]
        out_width = math.ceil(float(in_width) / float(self.stride[0]))
        out_height = math.ceil(float(in_height) / float(self.stride[1]))
        pad_along_width = ((out_width - 1) * self.stride[0] +
                           self.kernel_size[0] - in_width)
        pad_along_height = ((out_height - 1) * self.stride[1] +
                            self.kernel_size[1] - in_height)
        pad_left = math.floor(pad_along_width / 2)
        pad_top = math.floor(pad_along_height / 2)
        pad_right = pad_along_width - pad_left
        pad_bottom = pad_along_height - pad_top
        return F.pad(input, (pad_left, pad_right, pad_top, pad_bottom), 'constant', 0)

    def __repr__(self):
        return self.__class__.__name__

class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, stride=stride)
        self.bn1 = nn.BatchNorm2d(planes, eps=0.001, momentum=0.01)
        self.padding2 = SamePad2d(kernel_size=3, stride=1)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3)
        self.bn2 = nn.BatchNorm2d(planes, eps=0.001, momentum=0.01)
        self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1)
        self.bn3 = nn.BatchNorm2d(planes * 4, eps=0.001, momentum=0.01)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.padding2(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out

class ResNet(nn.Module):

    def __init__(self, architecture, stage5=False):
        super(ResNet, self).__init__()
        assert architecture in ["resnet50", "resnet101"]
        self.inplanes = 64
        self.layers = [3, 4, {"resnet50": 6, "resnet101": 23}[architecture], 3]
        self.block = Bottleneck
        self.stage5 = stage5

        self.C1 = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm2d(64, eps=0.001, momentum=0.01),
            nn.ReLU(inplace=True),
            SamePad2d(kernel_size=3, stride=2),
            nn.MaxPool2d(kernel_size=3, stride=2),
        )
        self.C2 = self.make_layer(self.block, 64, self.layers[0])
        self.C3 = self.make_layer(self.block, 128, self.layers[1], stride=2)
        self.C4 = self.make_layer(self.block, 256, self.layers[2], stride=2)
        if self.stage5:
            self.C5 = self.make_layer(self.block, 512, self.layers[3], stride=2)
        else:
            self.C5 = None

    def forward(self, x):
        x = self.C1(x)
        x = self.C2(x)
        x = self.C3(x)
        x = self.C4(x)
        x = self.C5(x)
        return x


    def stages(self):
        return [self.C1, self.C2, self.C3, self.C4, self.C5]

    def make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride),
                nn.BatchNorm2d(planes * block.expansion, eps=0.001, momentum=0.01),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

if __name__=='__main__':
    device = torch.device("cuda:"+str(0) if torch.cuda.is_available() else "cpu")
    resnet = ResNet("resnet101", stage5=True)
    C1, C2, C3, C4, C5 = resnet.stages()
    img = cv2.imread('000001.jpg')
    print(img.shape)
    img = img[:,:,:].transpose(2, 0, 1)
    img = np.ascontiguousarray(img, dtype=np.float32)
    img /= 255.0
    img = img[None]
    print(img.shape)
    torchimg = torch.from_numpy(img)

    resnet = resnet.cuda()
    torchimg=torchimg.cuda()
    out = C1(torchimg)
    print(out.shape)
    out = C2(out)
    print(out.shape)
    out = C3(out)
    print(out.shape)
    out = C4(out)
    print(out.shape)
    data=out.cpu().detach()

    # for example, we have two bboxes with coords xyxy (first with batch_id=0, second with batch_id=1).
    boxes = torch.Tensor([[10/1080*34, 20/1920*60, 540/1080*34, 640/1920*60]]).cuda()
    #做好坐标比例变化


    box_index = torch.tensor([0, 1], dtype=torch.int).cuda()  # index of bbox in batch

    # RoIAlign layer with crop sizes:
    crop_height = 28
    crop_width = 14
    roi_align = RoIAlign(crop_height, crop_width,0.25)

    # make crops:
    crops = roi_align(out.cuda(), boxes, box_index) #输入必须是tensor，不能是numpy
    print(type(crops))
    net = torch.nn.ConvTranspose2d(1024, 256, (2, 2), stride=2, padding=2).cuda()
    net1 = torch.nn.ConvTranspose2d(256, 64, (2, 2), stride=2, padding=2).cuda()
    net2 = torch.nn.ConvTranspose2d(64, 16, (2, 2), stride=2, padding=2).cuda()
    net3 = torch.nn.ConvTranspose2d(16, 1, (2, 2), stride=2, padding=2).cuda()
    crops = net(crops)
    crops = net1(crops)
    crops = net2(crops)
    crops = net3(crops)

    # plt.imshow(img[0][0])
    # plt.show()
    print(crops.shape)
    crops=crops.cpu().detach().numpy()
    plt.imshow(crops[0][0])
    plt.show()

    # ConvTranspose2d(256, 256, kernel_size=(2, 2), stride=(2, 2)
