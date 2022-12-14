
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: image_colorization/cyclegan/cycleganloss.ipynb
__all__ = "AdaptiveLoss CycleGanLossFunc".split(" ")

from dl_lib.core.all import *
from dl_lib.cyclegan.cycleganmodel import *
from dl_lib.cyclegan.datadl import*

class AdaptiveLoss(nn.Module):
    def __init__(self, crit):
        super().__init__()
        self.crit = crit

    def forward(self, output, target, **kwargs):
        targ = output.new_ones(*output.size()) if target else output.new_zeros(*output.size())
        return self.crit(output,targ, **kwargs)

class CycleGanLossFunc(nn.Module):

    def __init__(self, cyclegan, lambda_A=10, lambda_B=10, lambda_idt=0.5,lambda_perc=5, lsgan=True,perceptual_loss=True,perc_layer_weights=[5,12,2],perc_scale=1.):
        super().__init__()
        self.cyclegan ,self.l_A, self.l_B, self.l_idt, self.l_perc = cyclegan, lambda_A, lambda_B, lambda_idt, lambda_perc
        self.perceptual_loss,self.perc_layer_weights,self.perc_scale = perceptual_loss, perc_layer_weights,perc_scale
        self.crit = AdaptiveLoss(F.mse_loss if lsgan else F.binary_cross_entropy)
        if self.perceptual_loss:
            from torchvision.models import vgg16_bn
            vgg_m = vgg16_bn(True).features.cuda().eval()
            for p in vgg_m.parameters():p.requires_grad_(False)
            blocks = [i-1 for i,o in enumerate(list(vgg_m.children())) if isinstance(o,nn.MaxPool2d)]
            self.perceptual = PerceptualLoss(vgg_m, blocks[2:5], self.perc_layer_weights,scale=self.perc_scale)


    def set_input(self, real_A, real_B):
        self.real_A, self.real_B = real_A, real_B

    def forward(self, output, target):
        fake_A, fake_B,cyc_A, cyc_B, idt_A, idt_B = output

        #Identity loss
        self.id_loss = self.l_idt * (self.l_A * F.l1_loss(idt_A, self.real_A) + self.l_B * F.l1_loss(idt_B, self.real_B))

        #Generator loss
        self.gen_loss = self.crit(self.cyclegan.D_A(fake_A), True) + self.crit(self.cyclegan.D_B(fake_B), True)

        #Cyclic loss
        self.cyc_loss  = self.l_A * F.l1_loss(cyc_A, self.real_A)
        self.cyc_loss += self.l_B * F.l1_loss(cyc_B, self.real_B)

        #Perceptual Loss
        if self.perceptual_loss:
            self.perc_lossA = self.perceptual(self.real_A, cyc_A)
            self.perc_lossB = self.perceptual(self.real_B, cyc_B)
            self.perc_loss = (self.perc_lossA +self.perc_lossB) *self.l_perc

        total_loss = self.id_loss +self.gen_loss +self.cyc_loss

        return total_loss + self.perc_loss if self.perceptual_loss else total_loss