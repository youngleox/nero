import math
import torch
from torch.optim.optimizer import Optimizer, required

import numpy as np

def neuron_norm(x):
    if x.dim() > 1:
        view_shape = [x.shape[0]] + [1]*(x.dim()-1)
        x = x.view(x.shape[0],-1)
        return x.norm(dim=1).view(*view_shape)
    else:
        return x.abs()

def neuron_mean(x):
    if x.dim() > 1:
        view_shape = [x.shape[0]] + [1]*(x.dim()-1)
        x = x.view(x.shape[0],-1)
        return x.mean(dim=1).view(*view_shape)
    else:
        raise Exception("neuron_mean not defined on 1D tensors.")

class MadamCS(Optimizer):

    def __init__(self, params, lr=0.01, p_scale=3.0, g_bound=10.0, constraints=False):
        self.constraints = constraints
        self.p_scale = p_scale
        self.g_bound = g_bound
        defaults = dict(lr=lr)
        super(MadamCS, self).__init__(params, defaults)

    def step(self, closure=None):
        """Performs a single optimization step.
        Arguments:
            closure (callable, optional): A closure that reevaluates the model
                and returns the loss.
        """
        loss = None
        if closure is not None:
            loss = closure()

        for group in self.param_groups:
            for p in group['params']:
                if p.grad is None:
                    continue

                state = self.state[p]
                if len(state) == 0:
                    state['max'] = self.p_scale*(p*p).mean().sqrt().item()
                    state['step'] = 0
                    state['exp_avg_sq'] = torch.zeros_like(p)

                state['step'] += 1
                bias_correction = 1 - 0.999 ** state['step']
                state['exp_avg_sq'] = 0.999 * state['exp_avg_sq'] + 0.001 * p.grad.data**2
                
                g_normed = p.grad.data / (state['exp_avg_sq']/bias_correction).sqrt()
                g_normed[torch.isnan(g_normed)] = 0
                g_normed.clamp_(-self.g_bound, self.g_bound)
                
                p.data *= torch.exp( -group['lr']*g_normed*torch.sign(p.data) )
                p.data.clamp_(-state['max'], state['max'])

                if self.constraints and p.dim() > 1:
                    p.data -= neuron_mean(p)
                    p.data /= neuron_norm(p)
        return loss
