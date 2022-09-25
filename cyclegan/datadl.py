
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/datadl.ipynb
__all__ ='ImageToImageList get_dataloader'.split(" ")

from dl_lib.core.all import *

class ImageToImageList():
    def __init__(self, imagesA, imagesB, lenA, lenB):
        self.imagesA, self.imagesB = imagesA, imagesB
        self.lenA, self.lenB = lenA, lenB

    @classmethod
    def from_folders(cls, pathA, pathB, extensions=None, recurse=False,include=None, tfms=None):
        imagesA = ImageList.from_folder(pathA, extensions=extensions, recurse=recurse, include=include, tfms=tfms)
        imagesB = ImageList.from_folder(pathB, extensions=extensions, recurse=recurse, include=include, tfms=tfms)
        lenA,lenB =len(imagesA), len(imagesB)
        return cls(imagesA,imagesB,lenA, lenB)

    def __getitem__(self,idx):
        if isinstance(idx, slice):
            indexes =list(range(ifnone(idx.start, 0),idx.stop,ifnone(idx.step,1)))
            imgsA = [self.imagesA[i%self.lenA] for i in indexes]
            imgsB = [self.imagesB[random.randint(0,self.lenB-1)] for i in indexes]
        elif isinstance(idx,int):
            imgsA = self.imagesA[idx%self.lenA]
            imgsB = self.imagesB[random.randint(0,self.lenB-1)]
        else:
            imgsA=[self.imagesA[i%self.lenA] for i in idx]
            imgsB=[self.imagesB[random.randint(0,self.lenB-1)] for _ in idx]
        return imgsA, imgsB

    def __repr__(self):
        return f'{self.__class__.__name__}\nImagesA\n: {self.imagesA}\nImagesB\n: {self.imagesB}\n'

    def __len__(self):
        return max(self.lenA, self.lenB)



def get_dataloader(pathA, pathB, extensions=None, recurse=False, include=None,tfms=None, image_size=128, batch_size=1, shuffle=True,num_workers=2,pin_memory=True,**kwargs):
    stfms=[MakeRGB(), ResizeFixed(image_size), to_byte_tensor, to_float_tensor]
    if tfms is not None: stfms += tfms
    il = ImageToImageList.from_folders(pathA, pathB, extensions=extensions, recurse=recurse, include=include, tfms=stfms)
    return DataLoader(il, batch_size=batch_size, shuffle=shuffle,num_workers=num_workers,pin_memory=pin_memory,**kwargs)

def show_img2img_batch(dataloader, no_of_batches=1):
    total = dataloader.batch_size*no_of_batches
    columns=3
    rows = int(math.ceil(total/columns))
    fig,axes = plt.subplots(rows, columns,figsize=(columns*10,rows*10))
    i=0
    for xb,yb in dataloader:
        for x,y in zip(xb,yb):
            img=torch.cat((x,y),dim=-1)
            show_image(img, axes.flat[i],figsize=(32,32))
            i+=1
        if i==total:break