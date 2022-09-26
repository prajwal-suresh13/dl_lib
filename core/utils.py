
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: core/utils.ipynb
import torch
from torch import nn
from torch import tensor
import torch.nn.functional as F
from torch.utils.data import DataLoader, SequentialSampler, RandomSampler
import pdb





import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from functools import partial
from typing import Iterable
from collections import OrderedDict
import random
import operator
import os
import shutil


from pathlib import Path
import PIL,os,mimetypes
from fastdownload import FastDownload
import math
import re
import time
import cv2


import urllib
from urllib.request import urlretrieve
import zipfile

def video2frame(video_path, dest,no_of_images,start_time_secs=None,crop=None):
    start_frame=0
    if not os.path.exists(dest):
        os.mkdir(dest)

    if os.path.exists(video_path):
        video = cv2.VideoCapture(video_path)
    else:
        print('Video not found')
        return
    if start_time_secs is not None:
        fps=video.get(cv2.CAP_PROP_FPS)
        print(fps)
        start_frame = int(start_time_secs*fps)

    count=0
    frame=0
    run=True
    while run:
        try:
            ret,image=video.read()
            if not ret:run=False
            if ret:
                frame+=1
                if frame>=start_frame and frame%3==0:
                    if crop is not None:
                        x,w,y,h = crop
                        image=image[x:w,y:h]
                    count+=1
                    img = cv2.resize(image,(512,512),interpolation=cv2.INTER_AREA)
                    cv2.imwrite(f'{dest}/{count}.jpg',img,[int(cv2.IMWRITE_JPEG_QUALITY),100])
                    print(f"{count}.jpg saved successfully")
                if count==no_of_images:run=False
        except Exception as e:pass


def move_no_files(source,dest,num_files):
    if not os.path.exists(source): print('Source path not valid');return

    if not os.path.exists(dest):
        os.mkdir(dest)

    all_files = os.listdir(source)
    total_files=len(all_files)

    np.random.shuffle(all_files)
    move_files=all_files[:num_files]
    move_files = [source+'/'+ name for name in move_files]
    print(len(move_files))

    for name in move_files:
        shutil.move(name, dest)
    print(f'Moved {len(move_files)} files to "{dest}" folder ')

def convert_rgb2bw_save(path,save_path):
    save_path = Path(save_path)
    il = get_files(path ,extensions = image_extensions)
    for i,img in enumerate(il):
        PIL.Image.open(img).convert('L').save(f'{save_path}/{img.stem}.jpg')

import torchvision


def save_predicted_images(input_image_path, model_path, save_path, tfms=None):
    model = resnet_generator(3,3).cuda()
    state = torch.load(model_path)
    model.load_state_dict(state['model'])
    model.eval()

    il = ImageList.from_folder(input_image_path, tfms=tfms)
    count =0
    for  i in range(0,len(il),4):
        pred = model(torch.stack(il[i:i+4]).cuda())
        pred = pred.detach().cpu()/2 +0.5
        for j in range(pred.size(0)):
            torchvision.utils.save_image(pred[j, :, :, :], f'{save_path}/{count}.jpg')
            count+=1


def show(im, ax=None, figsize=None, title=None,**kwargs):
    if figsize is None: figsize = (6,6)
    if ax is None: _,ax = plt.subplots(figsize=figsize)
    if title is not None:ax.set_title(title)
    ax.axis('off')
    try:
        if hasattr(im,'data') and hasattr(im,'cpu') and hasattr(im,'permute'):
        # im = im.flip(0).mul(255).data.cpu().type(torch.uint8)
            im = im.data.cpu()

        # im = im.data.cpu()
            im = im.permute(1,2,0)
            ax.imshow(im,**kwargs)
    except Exception as e:
            ax.imshow(im,alpha=1,cmap='tab20', interpolation='nearest', **kwargs)

    return ax

from torch import Tensor
Tensor.show = show # to display tensor in mbar

Path.ls = lambda x:list(x.iterdir())
torch.Tensor.ndim = property(lambda x:len(x.shape))

def normalize_channel(x,mean=None,std=None):
    assert (mean is not None) and (std is not None),'Mean/Std is not defined'
    return (x-mean[...,None,None])/std[...,None,None]

def show_image(im, ax=None,figsize=(64,64), title=None, **kwargs):
  if ax is None: _,ax = plt.subplots(1,1, figsize=figsize)
  ax.axis('off')
  if len(im.shape)==2: ax.imshow(im,alpha=1,cmap='tab20', interpolation='nearest', **kwargs)
  else:ax.imshow(im.permute(1,2,0), **kwargs)
  if title is not None: ax.set_title(title)

def compose(x, funcs, *args, order_key='_order',**kwargs):
  key = lambda a : getattr(a,order_key,0)
  for f in sorted(listify(funcs),key = key):x = f(x,*args,**kwargs)
  return x

def setify(o):return o if isinstance(o,set) else set(listify(o))

def listify(o):
  if o is None: return []
  if isinstance(o,list):return o
  if isinstance(o,str): return [o]
  if isinstance(o,Iterable): return list(o)
  return [o]

class ListContainer():
  def __init__(self,items):self.items = listify(items)

  def __getitem__(self,idx):
    if isinstance(idx,(int,slice)):return self.items[idx]
    if isinstance(idx[0],bool):
      assert len(idx)==len(self)
      return [o for b,o in zip(idx,self.items) if b]
    return [self.items[i] for i in idx]

  def __len__(self): return len(self.items)
  def __iter__(self): return iter(self.items)
  def __delitem__(self,idx): del(self.items[idx])
  def __setitem__(self,idx,ob):self.items[idx]=ob
  def __repr__(self):
    res = f'{self.__class__.__name__} ({len(self)} items) \n{self.items[:10]}'
    if len(self)>10:res=res[:-1]+'...]'
    return res

def lin_comb(beta,x1,x2):
  return beta*x1 + (1-beta)*x2

def uniqueify(x, sort=False):
  res = list(OrderedDict.fromkeys(x).keys())
  if sort: res.sort()
  return res

def show_batch(dataloader, no_of_batches=1,**kwargs):
    total = int(dataloader.batch_size*no_of_batches)
    columns=3
    rows = int(math.ceil(total/columns))
    fig,axes = plt.subplots(rows, columns,figsize=(columns*10,rows*10))
    i=0
    for xb,yb in dataloader:
        for x,y in zip(xb,yb):
            show_image(x, axes.flat[i],figsize=(16,16), title = dataloader.dataset.proc_y.vocab[y], **kwargs)
            i+=1
            if i==total:return

def show_img2img_batch(dataloader, no_of_batches=1, **kwargs):
    total = int(dataloader.batch_size*no_of_batches*2)
    columns=2
    rows = int(math.ceil(total/columns))
    fig,axes = plt.subplots(rows, columns,figsize=(columns*10,rows*10))
    i=0
    for xb,yb in dataloader:
        for x,y in zip(xb,yb):
            show_image(x, axes.flat[i],figsize=(32,32),**kwargs)
            i+=1
            if i==total:return
            show_image(y,axes.flat[i],figsize=(32,32),**kwargs)
            i+=1
            if i==total:return

ifnone=lambda a,b:b if a is None else a

def _one_hot(x, classes, axis=1):
    "Target mask to one hot"
    return torch.stack([torch.where(x==c, 1,0) for c in range(classes)], axis=axis)