import cv2
from torch.utils.data import Dataset
import torch
import os
from roi_align import RoIAlign
import matplotlib.pyplot as plt

import numpy as np

def format_bbox(box,width,height,sequence):
    if sequence==5 or sequence==6 :
        x = int(box[0] / 810 * width)
        y = int(box[1] / 608 * height)
        w = int(box[2] / 810 * width)
        h = int(box[3] / 608 * height)
    else:
        x = int(box[0]/1080*width)
        y = int(box[1]/608*height)
        w = int(box[2]/1080*width)
        h = int(box[3]/608*height)
    if x+w>width:
        w=width-x
    if y+h>height:
        h=height-y
    if x<0:
        w=w+x
        x=0
    if y<0:
        h=h+y
        y=0
    return [x,y,w,h]

def format_box(bbox):
    return torch.Tensor([[bbox[0], bbox[1], bbox[0]+ bbox[2], bbox[1] + bbox[3]]])

def pass_box(bbox):
    return torch.Tensor([bbox[0], bbox[1], bbox[2], bbox[3]])

def load_MOT_txt(path,width,height,sequence):
    instance_per_frame = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            fields = line.split(",")
            if int(fields[0]) not in instance_per_frame.keys():
                instance_per_frame[int(fields[0])]=[]

            instance_per_frame[int(fields[0])].append({
                "track_id":int(fields[1]),
                "bbox":format_bbox([float(fields[2]),float(fields[3]),float(fields[4]),float(fields[5])],width,height,sequence)
            })
    return instance_per_frame


class MOTTrackDataset(Dataset):
    def __init__(self, inputRes=None,
                 seqs_list_file=r'E:\Challenge\Multi-Object-Tracking-and-Segmentation-with-Pytorch\results',
                 # seqs_list_file='/home/zuochenyu/codes/Multi-Object-Tracking-and-Segmentation-with-Pytorch/results',
                 transform=None,
                 sequence=2,
                 random_rev_thred=0.4):

        self.imgPath = r'E:\Challenge\MOTSChallenge\train\images'
        # self.imgPath = '/home/zuochenyu/datasets/MOTSChallenge/train/images'
        self.imgPath = os.path.join(self.imgPath,"{:04}".format(sequence))
        self.width = 1920
        self.height = 1080
        if sequence==6 or sequence==5:
            self.width=640
            self.height=480
        filename = os.path.join(seqs_list_file, "{:04}.txt".format(sequence))
        # self.instance = load_MOT_txt(filename,self.width,self.height)
        self.instance = load_MOT_txt(filename, 2048, 1024,sequence)
        self.inputRes = inputRes
        self.random_rev_thred = random_rev_thred
        self.roi_align = RoIAlign(56, 56, 0.25)

    def __len__(self):
        return len(self.instance)

    def __getitem__(self, idx):
        frame = idx + 1
        bbox_list = []
        track_list = []
        img = os.path.join(self.imgPath, "{:06}.jpg".format(frame))
        img = cv2.imread(img)
        img = cv2.resize(img, (2048, 1024))
        img = img[:, :, :].transpose(2, 0, 1)
        img = np.ascontiguousarray(img, dtype=np.float32)
        img /= 255.0
        mask = torch.from_numpy(img)
        mask = mask[None]
        box_index = torch.tensor([0], dtype=torch.int)
        if frame in self.instance.keys():
            for obj in self.instance[frame]:
                bbox = pass_box(obj["bbox"])
                boxes = format_box(bbox)
                # print(obj["track_id"])
                crops = self.roi_align(mask, boxes, box_index)
                crops = crops.squeeze()
                # plt.imshow(crops[0])
                # plt.show()
                bbox_list.append(bbox)
                track_list.append(obj["track_id"])

        return  {"img":img,"bbox":bbox_list,"track":track_list}