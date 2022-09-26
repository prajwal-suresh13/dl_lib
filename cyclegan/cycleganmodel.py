
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: image_colorization/cyclegan/cycleganmodel.ipynb
__all__ ='convT_norm_relu pad_conv_norm_relu resnet_generator conv_norm_leaky discriminator CycleGAN'.split(" ")

from dl_lib.core.all import *

def convT_norm_relu(ch_in, ch_out, norm_layer, kernel_size=3, stride=2, bias=True, init=nn.init.kaiming_normal_):
    convT = nn.ConvTranspose2d(ch_in, ch_out, kernel_size=kernel_size, stride=stride, padding=1, output_padding=1, bias=bias)
    if init:
        init(convT.weight)
        if hasattr(convT, 'bias') and hasattr(convT.bias,'data'): convT.bias.data.fill_(0.)
    layers = [convT, norm_layer(ch_out), nn.ReLU(inplace=True)]
    return layers

def pad_conv_norm_relu(ch_in, ch_out, pad_mode, norm_layer, kernel_size=3, bias=True, pad=1, stride=1, activ=True, init=nn.init.kaiming_normal_):
    layers = []
    if pad_mode == 'reflection': layers.append(nn.ReflectionPad2d(pad))
    elif pad_mode == 'border':   layers.append(nn.ReplicationPad2d(pad))
    p= pad if pad_mode =='zeros' else 0
    conv = nn.Conv2d(ch_in, ch_out, kernel_size=kernel_size, padding=p, stride=stride, bias=bias)
    if init:
        init(conv.weight)
        if hasattr(conv, 'bias') and hasattr(conv.bias,'data'): conv.bias.data.fill_(0.)
    layers += [conv, norm_layer(ch_out)]
    if activ: layers.append(nn.ReLU(inplace=True))
    return layers

class ResnetBlock(nn.Module):
    def __init__(self, dim, pad_mode='reflection', norm_layer=None, dropout=0., bias=True):
        super().__init__()
        assert pad_mode in ['zeros','reflection','border'], f'padding {pad_mode} not implemented'
        norm_layer = (nn.InstanceNorm2d if norm_layer is None else norm_layer)
        layers = pad_conv_norm_relu(dim, dim, pad_mode, norm_layer, bias=bias)
        if dropout!=0: layers.append(nn.Dropout(dropout))
        layers += pad_conv_norm_relu(dim, dim, pad_mode, norm_layer, bias=bias, activ=False)
        self.conv_block = nn.Sequential(*layers)

    def forward(self, x):return x + self.conv_block(x)

def resnet_generator(ch_in, ch_out, n_filters=64, norm_layer=None, dropout=0, n_blocks=9, pad_mode='reflection'):
    norm_layer = (nn.InstanceNorm2d if norm_layer is None else norm_layer)
    bias = (norm_layer == nn.InstanceNorm2d)
    layers = pad_conv_norm_relu(ch_in, n_filters, 'reflection', norm_layer, kernel_size=7, pad=3, bias=bias)
    for i in range(2):
        layers += pad_conv_norm_relu(n_filters, n_filters*2, 'zeros', norm_layer, stride=2, bias=bias)
        n_filters *= 2
    layers += [ResnetBlock(n_filters, pad_mode, norm_layer, dropout, bias) for _ in range(n_blocks)]
    for i in range(2):
        layers += convT_norm_relu(n_filters, n_filters//2, norm_layer, bias=bias)
        n_filters//=2
    layers += [nn.ReflectionPad2d(3), nn.Conv2d(n_filters, ch_out, kernel_size=7, padding=0), nn.Tanh()]
    return nn.Sequential(*layers)

def conv_norm_leaky(ch_in, ch_out, norm_layer=None, kernel_size=3, bias=True, pad=1, stride=1, activ=True, slope=0.2, init=nn.init.kaiming_normal_):
    conv = nn.Conv2d(ch_in, ch_out, kernel_size=kernel_size, padding=pad, stride=stride, bias=bias)
    if init:
        init(conv.weight)
        if hasattr(conv, 'bias') and hasattr(conv.bias, 'data'): conv.bias.data.fill_(0)
    layers = [conv]
    if norm_layer is not None: layers.append(norm_layer(ch_out))
    if activ: layers.append(nn.LeakyReLU(slope,inplace=True))
    return layers

def discriminator(ch_in, n_filters=64, n_layers=3, norm_layer=None, sigmoid=False):
    norm_layer = (nn.InstanceNorm2d if norm_layer is None else norm_layer)
    bias = (norm_layer == nn.InstanceNorm2d)
    layers = conv_norm_leaky(ch_in, n_filters, kernel_size=4, stride=2, pad=1)
    for i in range(n_layers-1):
        new_filters = 2*n_filters if i<=3 else n_filters
        layers += conv_norm_leaky(n_filters, new_filters, norm_layer, kernel_size=4, stride=2, pad=1, bias=bias)
        n_filters = new_filters
    new_filters = 2*n_filters if n_layers <=3 else n_filters
    layers += conv_norm_leaky(n_filters, new_filters, norm_layer, kernel_size=4, stride=1, pad=1, bias=bias)
    layers.append(nn.Conv2d(new_filters, 1, kernel_size=4, stride=1, padding=1))
    if sigmoid: layers.append(nn.Sigmoid())
    return nn.Sequential(*layers)

class CycleGAN(nn.Module):

    def __init__(self, ch_in, ch_out, n_features=64, disc_layers=3, gen_blocks=9, lsgan=True, drop=0., norm_layer=None):
        super().__init__()
        self.D_A = discriminator(ch_in, n_features, disc_layers, norm_layer, sigmoid = not lsgan)
        self.D_B = discriminator(ch_in, n_features, disc_layers, norm_layer, sigmoid = not lsgan)
        self.G_A = resnet_generator(ch_in, ch_out, n_features, norm_layer, drop, gen_blocks)
        self.G_B = resnet_generator(ch_in, ch_out, n_features, norm_layer, drop, gen_blocks)

    def forward(self, input):
        real_A, real_B = input
        fake_A, fake_B = self.G_A(real_B), self.G_B(real_A)
        cyc_A , cyc_B = self.G_A(fake_B), self.G_B(fake_A)
        idt_A, idt_B = self.G_A(real_A), self.G_B(real_B)
        return [fake_A, fake_B, cyc_A, cyc_B, idt_A, idt_B]