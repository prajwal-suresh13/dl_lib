
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/optimizers.ipynb
__all__='maybe_update get_defaults Optimizer StatefulOptimizer Stat AverageGrad AverageSqrGrad StepCount sgd_step weight_decay l2_reg momentum_step debias adam_step lamb_step sgd_opt sgd_mom_opt adam_opt lamb_opt'.split(" ")

from dl_lib.core.utils import *

def maybe_update(os, dest, func):
    for o in os:
        for k, v in func(o).items():
            if k not in dest: dest[k]=v

def get_defaults(d): return getattr(d,'_defaults',{})

class Optimizer():
    def __init__(self, params, steppers, **hyper):
        self.param_groups = list(params)
        if not isinstance(self.param_groups[0], list):self.param_groups = [self.param_groups]

        self.steppers = listify(steppers)
        maybe_update(self.steppers, hyper, get_defaults)

        self.hypers = [{**hyper} for _ in self.param_groups]

    def grad_params(self):
        return [(p,hyper) for pg,hyper in zip(self.param_groups, self.hypers)
                        for p in pg if p.grad is not None]

    def zero_grad(self):
        for p,hyper in self.grad_params():
            p.grad.detach_()
            p.grad.zero_()

    def step(self):
        for p, hyper in self.grad_params(): compose(p, self.steppers, **hyper)

    def state_dict(self):
        return {'hypers':self.hypers}

    def load_state_dict(self,sd):
        assert len(sd["hypers"])==len(self.param_groups)
        self.hypers = sd["hypers"]



class StatefulOptimizer(Optimizer):
    def __init__(self, params, steppers, stats=None, **hyper):
        self.stats = listify(stats)
        maybe_update(self.stats, hyper, get_defaults)
        super().__init__(params, steppers, **hyper)
        self.state={}

    def step(self):
        for p, hyper in self.grad_params():
            if p not in self.state:
                self.state[p] = {}
                maybe_update(self.stats, self.state[p], lambda o : o.init_state(p))
            state = self.state[p]
            for stat in self.stats: state = stat.update(p, state, **hyper)
            compose(p, self.steppers, **state, **hyper)
            self.state[p] = state

    def state_dict(self):
        state = [self.state[p] for p,hyper in self.grad_params()]
        return {'state':state,'hypers':self.hypers}

    def load_state_dict(self, sd):
        assert len(sd["hypers"])==len(self.param_groups)
        #   assert len(sd["state"]) == sum([len(pg) for pg in self.param_groups])
        self.hypers = sd['hypers']
        self.state = {p:s for p,s in zip([p for p,hyper in self.grad_params()],sd['state'])}



class Stat():
    _defaults = {}

    def init_state(self, p): raise NotImplementedError
    def update(self,p, state, **kwargs): raise NotImplementedError

class AverageGrad(Stat):
    _defaults=dict(mom=0.9)

    def __init__(self, dampening = True): self.dampening = dampening

    def init_state(self, p ): return {'grad_avg': torch.zeros_like(p.grad.data)}

    def update(self, p, state, mom,**kwargs):
        state['mom_damp'] =1-mom if self.dampening else 1.
        state['grad_avg'].mul_(mom).add_(p.grad.data, alpha=state['mom_damp'])
        return state

class AverageSqrGrad(Stat):
    _defaults = dict(sqr_mom=0.99)

    def __init__(self, dampening=True): self.dampening = dampening

    def init_state(self,p): return {'sqr_grad_avg': torch.zeros_like(p.grad.data)}

    def update(self,p, state, sqr_mom, **kwargs):
        state['sqr_mom_damp'] = 1-sqr_mom if self.dampening else 1.
        state['sqr_grad_avg'].mul_(sqr_mom).addcmul_(state['sqr_mom_damp'], p.grad.data, p.grad.data)
        return state


class StepCount(Stat):
    def init_state(self,p): return {'step':0}
    def update(self, p, state, **kwargs):
        state['step']+=1
        return state


def sgd_step(p, lr, **kwargs):
    p.data.add_(-lr, p.grad.data)
    return p

def weight_decay(p, lr, wd, **kwargs):
    p.data.mul_(1 - lr*wd)
    return p

weight_decay._defaults=dict(wd=0.)

def l2_reg(p, lr, wd, **kwargs):
    p.grad.data.add_(wd, p.data)
    return p

l2_reg._defaults=dict(wd=0.)

def momentum_step(p, lr, grad_avg, **kwargs):
    p.data.add_(-lr, grad_avg)

def debias(mom, damp, step): return damp * (1 - mom**step)/(1-mom)

def adam_step(p, lr, mom, mom_damp, grad_avg, sqr_mom, sqr_mom_damp, sqr_grad_avg, step, eps, **kwargs):
    debias1 = debias(mom, mom_damp, step)
    debias2 = debias(sqr_mom, sqr_mom_damp, step)

    p.data.addcdiv_(grad_avg, (sqr_grad_avg/debias2) + eps, value = -lr/debias1)
    return p

adam_step._defaults = dict(eps=1e-5)

def lamb_step(p, lr, mom, mom_damp, grad_avg, sqr_mom, sqr_mom_damp, sqr_grad_avg, step, eps, wd ,**kwargs):
    debias1 = debias(mom, mom_damp, step)
    debias2 = debias(sqr_mom, sqr_mom_damp, step)
    r1 = p.data.pow(2).mean().sqrt()
    step = (grad_avg/debias1) / ((sqr_grad_avg/debias2).sqrt() +eps) + wd*p.data
    r2 = step.pow(2).mean().sqrt()
    q=1 if r1==0 or r2==0 else min(r1/r2, 10)
    p.data.add_(step, alpha =-lr*q)
    return p

lamb_step._defaults = dict(eps = 1e-6, wd=0.)


sgd_opt = partial(Optimizer, steppers=[weight_decay, sgd_step])

sgd_mom_opt = partial(StatefulOptimizer, steppers = [momentum_step, weight_decay], stats = AverageGrad(), wd = 0.01)

def adam_opt(extra_step=None, **kwargs):
    return partial(StatefulOptimizer, steppers = [adam_step, weight_decay] + listify(extra_step),
                 stats = [AverageGrad(), AverageSqrGrad(), StepCount()], **kwargs)

def lamb_opt(extra_step=None, **kwargs):
    return partial(StatefulOptimizer, steppers = [lamb_step] + listify(extra_step), stats = [AverageGrad(dampening=True), AverageSqrGrad(), StepCount()], **kwargs)
