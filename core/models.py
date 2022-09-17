
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: core/models.ipynb
__all__ ='noop Flatten conv act_fn conv_layer kaiming_init_cnn ResBlock XResnet xresnet18 xresnet34 xresnet50 xresnet101 xresnet152 AdaptiveConcatPool2d'.split(" ")

from dl_lib.core.utils import *

def noop(x): return x

class Flatten(nn.Module):
  def forward(self,x): return x.view(x.size(0), -1)

def conv(ni, nf, ks=3, stride=1, bias = False):
  return nn.Conv2d(ni, nf, kernel_size=ks, stride=stride, padding=ks//2, bias=bias)

act_fn = nn.ReLU(inplace=True)

def conv_layer(ni, nf, ks=3, stride=1, zero_bn = False, act = True):
  bn = nn.BatchNorm2d(nf)
  nn.init.constant_(bn.weight, 0. if zero_bn else 1.)
  layers = [conv(ni, nf, ks=ks, stride=stride), bn]
  if act:layers.append(act_fn)
  return nn.Sequential(*layers)


def kaiming_init_cnn(m, uniform=False):
  if getattr(m,'bias', None) is not None: nn.init.constant_(m.bias, 0)
  if isinstance(m, (nn.Linear, nn.Conv2d)): nn.init.kaiming_normal_(m.weight) if uniform==False else nn.init.kaiming_uniform_(m.weight)
  for l in m.children():kaiming_init_cnn(l, uniform=uniform)

class ResBlock(nn.Module):
  def __init__(self,expansion, ni, nh, stride=1):
    super().__init__()
    ni, nf = ni*expansion, nh*expansion
    layers = [conv_layer(ni,nh, 3, stride=stride),
              conv_layer(nh, nf, 3, zero_bn=True, act=False)
            ] if expansion==1 else [
                conv_layer(ni,nh, 1),
                conv_layer(nh,nh,3, stride=stride),
                conv_layer(nh, nf, 1, zero_bn=True, act=False)
            ]

    self.convs = nn.Sequential(*layers)
    self.idconv = noop if ni==nf else conv_layer(ni, nf, 1, act=False)
    self.pool  = noop if stride==1 else nn.AvgPool2d(2, ceil_mode=True)

  def forward(self, x): return act_fn(self.convs(x) + self.idconv(self.pool(x)))



class XResnet(nn.Sequential):
  @classmethod
  def create(cls, expansion, layers, c_in=3, c_out=1000):
    nfs = [c_in,(c_in+1)*8, 64,64]
    stem = [conv_layer(nfs[i], nfs[i+1], ks =3, stride=2 if i==0 else 1) for i in range(3)]

    nfs=[64//expansion, 64, 128, 256, 512]
    res_layers =[cls._make_layer(expansion, nfs[i], nfs[i+1], n_blocks=l, stride =1 if i==0 else 2)
                for i,l in enumerate(layers)]

    res = cls(*stem,
              nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
              *res_layers,
              nn.AdaptiveAvgPool2d(1),
              Flatten(),
              nn.Linear(nfs[-1]*expansion, c_out)
              )

    kaiming_init_cnn(res)
    return res

  @staticmethod
  def _make_layer( expansion, ni, nf, n_blocks, stride):
    return nn.Sequential(
        *[ResBlock(expansion, ni if i==0 else nf, nf, stride if i==0 else 1)
                          for i in range(n_blocks)])

def xresnet18(**kwargs): return XResnet.create(1, [2,2,2,2], **kwargs)
def xresnet34(**kwargs): return XResnet.create(1,[3,4,6,3], **kwargs)
def xresnet50(**kwargs): return XResnet.create(4, [3,4,6,3], **kwargs)
def xresnet101(**kwargs): return XResnet.create(4, [3,4,23,3], **kwargs)
def xresnet152(**kwargs): return XResnet.create(4, [ 3,8,36,3], **kwargs)

class AdaptiveConcatPool2d(nn.Module):
  def __init__(self, sz=1):
    super().__init__()
    self.output_size = sz
    self.ap = nn.AdaptiveAvgPool2d(sz)
    self.mp = nn.AdaptiveMaxPool2d(sz)

  def forward(self, x): return torch.cat([self.mp(x), self.ap(x)],1)