
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: image_colorization/cyclegan/callbacks.ipynb
from dl_lib.core.all import *
from dl_lib.cyclegan.cycleganloss import *
from dl_lib.cyclegan.datadl import *
from dl_lib.cyclegan.cycleganmodel import *

__all__ = 'SmoothenValue CycleGANTrainer ShowCycleGANImgsCallback BatchTransformXTupleCallback BatchTransformXYCallback LoadPretrainedModelCallback SaveCycleGANModelCallback LoadCycleGANModelCallback cyclegan_learner pretrain_cyclegan_generator'.split(" ")

class SmoothenValue():
    def __init__(self, beta):
        self.beta, self.n, self.mov_avg = beta,0,0.


    def add_value(self,val):
        self.n += 1
        self.mov_avg = lin_comb(self.beta, self.mov_avg, val)
        self.smooth = self.mov_avg/(1-self.beta**self.n)

class CycleGANTrainer(Callback):
    _order = -20

    def _set_trainable(self, D_A=False, D_B = False):
        gen = (not D_A) and (not D_B)

        def set_requires_grad(m,req):
            for p in m.parameters(): p.requires_grad_(req)

        set_requires_grad(self.learner.model.G_A, gen)
        set_requires_grad(self.learner.model.G_B, gen)
        set_requires_grad(self.learner.model.D_A, D_A)
        set_requires_grad(self.learner.model.D_B, D_B)

        if not gen:
            self.opt_D_A.hypers = self.opt.hypers
            self.opt_D_B.hypers = self.opt.hypers

    def before_fit(self):
        self.G_A, self.G_B = self.learner.model.G_A, self.learner.model.G_B
        self.D_A, self.D_B = self.learner.model.D_A, self.learner.model.D_B
        self.crit = self.learner.loss_func.crit

        if not getattr(self,'opt_G',None):
            self.opt_G = self.learner.opt_func(self.learner.splitter(nn.Sequential(*flatten_model(self.G_A),*flatten_model(self.G_B))), lr=self.learner.lr)

        else:
            self.opt_G.hypers = self.learner.opt.hypers

        if not getattr(self, 'opt_D_A',None):
            self.opt_D_A = self.learner.opt_func(self.learner.splitter(nn.Sequential(*flatten_model(self.D_A))), lr=self.learner.lr)
        else:
            self.opt_D_A.hypers = self.learner.opt.hypers

        if not getattr(self,'opt_D_B',None):
            self.opt_D_B = self.learner.opt_func(self.learner.splitter(nn.Sequential(*flatten_model(self.D_B))), lr=self.learner.lr)
        else:
            self.opt_D_B.hypers = self.learner.opt.hypers

        self.learner.opt = self.opt_G

        if getattr(self,'id_smter',None) is None:
            self.learner.id_smter, self.learner.gen_smter, self.learner.cyc_smter = SmoothenValue(0.98), SmoothenValue(0.98), SmoothenValue(0.98)
            if self.learner.loss_func.perceptual_loss:self.learner.perc_smter=SmoothenValue(0.98)
            self.learner.da_smter, self.learner.db_smter = SmoothenValue(0.98), SmoothenValue(0.98)



    def before_batch(self):
        self._set_trainable()
        self.learner.loss_func.set_input(self.learner.xb, self.learner.yb)
        self.learner.xb = self.learner.xb, self.learner.yb


    def after_loss(self):
        self.learner.id_smter.add_value(self.loss_func.id_loss.detach().cpu())
        self.learner.gen_smter.add_value(self.loss_func.gen_loss.detach().cpu())
        self.learner.cyc_smter.add_value(self.loss_func.cyc_loss.detach().cpu())
        if self.learner.loss_func.perceptual_loss:self.learner.perc_smter.add_value(self.loss_func.perc_loss.detach().cpu())

    def after_step(self):
        self.opt_D_A.hypers = self.learner.opt.hypers
        self.opt_D_B.hypers = self.learner.opt.hypers

    def after_batch(self):
        fake_A, fake_B = self.learner.pred[0].detach(), self.learner.pred[1].detach()
        real_A, real_B = self.learner.xb

        self._set_trainable(D_A=True)
        self.opt_D_A.zero_grad()
        loss_D_A = 0.5 * (self.crit(self.D_A(real_A),True) + self.crit(self.D_A(fake_A),False))
        loss_D_A.backward()
        self.learner.loss_func.D_A_loss = loss_D_A.detach().cpu()
        self.learner.da_smter.add_value(self.learner.loss_func.D_A_loss)
        self.opt_D_A.step()

        self._set_trainable(D_B=True)
        self.opt_D_B.zero_grad()
        loss_D_B = 0.5 * (self.crit(self.D_B(real_B),True) + self.crit(self.D_B(fake_B),False))
        loss_D_B.backward()
        self.learner.loss_func.D_B_loss = loss_D_B.detach().cpu()
        self.learner.db_smter.add_value(self.learner.loss_func.D_B_loss)
        self.opt_D_B.step()

        self._set_trainable()





class ShowCycleGANImgsCallback(Callback):

    def __init__(self, show_img_interval=1):
        self.show_img_interval = show_img_interval
        assert show_img_interval, "Non_zero allowed"

    def before_fit(self):
        self.imgs=[]
        self.titles = []
        assert hasattr(self.learner, 'progressbar')

    def after_epoch(self):
        if (self.learner.epoch+1) % self.show_img_interval == 0:
            self.imgA_result = torch.cat((self.learner.xb[0][0].detach()/2 + 0.5,self.learner.pred[1][0].detach()/2 +0.5),dim=-1)
            self.imgB_result = torch.cat((self.learner.xb[1][0].detach()/2 + 0.5,self.learner.pred[0][0].detach()/2 +0.5),dim=-1)
            self.last_gen = torch.cat((self.imgA_result,self.imgB_result),dim=-2)
            self.imgs.append(self.last_gen)
            self.titles.append(f'Epoch {self.learner.epoch}')
            self.progressbar.mbar.show_imgs(self.imgs, self.titles, imgsize=10)

class BatchTransformXTupleCallback(Callback):
  _order =-2
  def __init__(self,tfm):self.tfm=tfm
  def before_batch(self):self.learner.xb = self.tfm(self.xb[0]),self.tfm(self.xb[1])

class BatchTransformXYCallback(Callback):
  _order =-2
  def __init__(self,tfm):self.tfm=tfm
  def before_batch(self):self.learner.xb = self.tfm(self.xb); self.learner.yb=self.tfm(self.yb)

class LoadPretrainedModelCallback(Callback):
    _order=-50
    def __init__(self,ga,gb,da,db):
        self.ga_state = torch.load(ga)
        self.gb_state = torch.load(gb)
        self.da_state = torch.load(da)
        self.db_state = torch.load(db)



    def before_fit(self):
        self.learner.model.G_A.load_state_dict(self.ga_state['model'])
        self.learner.model.G_B.load_state_dict(self.gb_state['model'])
        self.learner.model.D_A.load_state_dict(self.da_state['model'])
        self.learner.model.D_B.load_state_dict(self.db_state['model'])


class SaveCycleGANModelCallback(Callback):
    _order=100
    def __init__(self, model_path, interval=1):
        self.model_path = model_path
        self.interval=interval

        if not os.path.exists(self.model_path):
            os.mkdir(self.model_path)

    def after_epoch(self):
        if (self.learner.epoch+1) % self.interval==0:
            state = {
                'epoch':self.learner.epoch,
                'G_A':self.learner.model.G_A.state_dict(),
                'G_B':self.learner.model.G_B.state_dict(),
                'D_A':self.learner.model.D_A.state_dict(),
                'D_B':self.learner.model.D_B.state_dict(),
                'opt_G':self.learner.opt.state_dict(),
                 'id_smter':self.learner.id_smter,
                 'gen_smter':self.learner.gen_smter,
                 'cyc_smter': self.learner.cyc_smter,
                 'da_smter':self.learner.da_smter,
                 'db_smter':self.learner.db_smter,

            }
            if self.learner.loss_func.perceptual_loss:state['perc_smter']=self.learner.perc_smter
            torch.save(state,f'{self.model_path}/{self.epoch}.pth')

class LoadCycleGANModelCallback(Callback):
    _order = -50
    def __init__(self, model_path, from_start=False, with_opt=True):
        self.model_path = model_path
        self.from_start = from_start
        self.with_opt = with_opt
        if not os.path.exists(self.model_path):
            print('Invalid model Path')
            return
        self.state = torch.load(self.model_path)

    def before_fit(self):
        self.learner.model.G_A.load_state_dict(self.state['G_A'])
        self.learner.model.G_B.load_state_dict(self.state['G_B'])
        self.learner.model.D_A.load_state_dict(self.state['D_A'])
        self.learner.model.D_B.load_state_dict(self.state['D_B'])
        if self.with_opt:
            self.learner.opt.load_state_dict(self.state['opt_G'])
            self.learner.id_smter = self.state['id_smter']
            self.learner.gen_smter = self.state['gen_smter']
            self.learner.cyc_smter = self.state['cyc_smter']
            if 'perc_smter' in self.state.keys():self.learner.perc_smter = self.state['perc_smter']
            self.learner.da_smter = self.state['da_smter']
            self.learner.db_smter = self.state['db_smter']

    def before_epoch(self):
        if self.from_start:return
        self.learner.epoch = self.state['epoch'] +self.learner.epoch +1
        if self.learner.epoch == self.learner.epochs:raise CancelTrainException()


def cyclegan_learner(data, opt_func=lamb_opt(mom=0.5), extra_cbs=None, gen_blocks=9, lr = 1e-2, avg_stats_metrics=None, valid_stats=False, norm=None, lr_find=False, show_imgs=True, plot_hypers=['mom','lr'], lambda_perc=5, perceptual_loss=True, perc_layer_weights=[5,12,2], perc_scale=0.1, display_metrics={},**kwargs):
    cyclegan = CycleGAN(3,3, gen_blocks=gen_blocks)
    metrics={'Id_Loss':'id_smter.smooth','Gen_Loss':'gen_smter.smooth','Cyc_Loss':'cyc_smter.smooth','DA_Loss':'da_smter.smooth','DB_Loss':'db_smter.smooth'}
    if perceptual_loss: metrics['Perc_loss'] = 'perc_smter.smooth'
    for k,v in display_metrics.items():metrics[k] = v
    cbfs = [Recorder, CudaCallback, ProgressbarCallback, CycleGANTrainer]
    if norm: cbfs.append(partial(BatchTransformXTupleCallback, norm))
    if lr_find:
        cbfs.append(LR_Find)
    else:
        if show_imgs:cbfs.append(ShowCycleGANImgsCallback)
        if extra_cbs: cbfs += listify(extra_cbs)
        cbfs.append(partial(AvgStatsCallback,avg_stats_metrics,valid_stats=valid_stats))

    return Learner(cyclegan, data,
                   CycleGanLossFunc(cyclegan, perceptual_loss = perceptual_loss, lambda_perc=lambda_perc,
                                    perc_layer_weights=perc_layer_weights, perc_scale=perc_scale),
                   opt_func = opt_func,cbfuncs = cbfs,lr=lr, metrics=metrics,plot_hypers=plot_hypers, **kwargs)



def pretrain_cyclegan_generator(data, opt_func=lamb_opt(mom=0.5), extra_cbs=None, n_blocks = 9, lr = 1e-2, avg_stats_metrics=None, valid_stats=False, norm=None, lr_find=False, show_imgs=True, plot_hypers=['mom','lr'], perc_layer_weights=[5,12,2], perc_scale=1., display_metrics={},**kwargs):
    model = resnet_generator(3,3, n_blocks=n_blocks)

    from torchvision.models import vgg16_bn
    vgg_m = vgg16_bn(True).features.cuda().eval()
    for p in vgg_m.parameters():p.requires_grad_(False)
    blocks = [i-1 for i,o in enumerate(list(vgg_m.children())) if isinstance(o,nn.MaxPool2d)]
    perc_loss = PerceptualLoss(vgg_m, blocks[2:5],perc_layer_weights, scale=perc_scale)
    metrics = {'Perc_loss':'feat_losses'}

    for k,v in display_metrics.items():metrics[k] = v
    cbfs = [Recorder, CudaCallback, ProgressbarCallback]
    if norm: cbfs.append(partial(BatchTransformXYCallback, norm))
    if lr_find:
        cbfs.append(LR_Find)
    else:
        if show_imgs:cbfs.append(ShowImgsCallback)
        if extra_cbs: cbfs += listify(extra_cbs)
        cbfs.append(partial(AvgStatsCallback,avg_stats_metrics,valid_stats=valid_stats))

    return Learner(model, data, perc_loss, opt_func=opt_func, cbfuncs = cbfs, metrics=metrics, plot_hypers = plot_hypers, **kwargs)