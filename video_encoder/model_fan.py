#!/usr/bin/env python
import torch
import torch.nn as nn
import torch.nn.functional as F
from .models.emonet_split import ConvBlock


nn.InstanceNorm2d = nn.BatchNorm2d

import sys

def get_emonet():

    net = torch.load("video_encoder/models/model_8.pth")
    return net

class AttentionPool2d(nn.Module):
    def __init__(self, spacial_dim: int, embed_dim: int, num_heads: int, output_dim: int = None):
        super().__init__()
        self.positional_embedding = nn.Parameter(torch.randn(spacial_dim ** 2 + 1, embed_dim) / embed_dim ** 0.5)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.c_proj = nn.Linear(embed_dim, output_dim or embed_dim)
        self.num_heads = num_heads

    def forward(self, x):
        x = x.flatten(start_dim=2).permute(2, 0, 1)  # NCHW -> (HW)NC
        x = torch.cat([x.mean(dim=0, keepdim=True), x], dim=0)  # (HW+1)NC
        x = x + self.positional_embedding[:, None, :].to(x.dtype)  # (HW+1)NC
        x, _ = F.multi_head_attention_forward(
            query=x[:1], key=x, value=x,
            embed_dim_to_check=x.shape[-1],
            num_heads=self.num_heads,
            q_proj_weight=self.q_proj.weight,
            k_proj_weight=self.k_proj.weight,
            v_proj_weight=self.v_proj.weight,
            in_proj_weight=None,
            in_proj_bias=torch.cat([self.q_proj.bias, self.k_proj.bias, self.v_proj.bias]),
            bias_k=None,
            bias_v=None,
            add_zero_attn=False,
            dropout_p=0,
            out_proj_weight=self.c_proj.weight,
            out_proj_bias=self.c_proj.bias,
            use_separate_proj_weight=True,
            training=self.training,
            need_weights=False
        )
        return x.squeeze(0)

class Model_fan(nn.Module):
    def __init__(self,embedding_dim):
        super(Model_fan, self).__init__()
        self.emonet = get_emonet()

        self.emonet.module.feature.fan.conv1 =ConvBlock(3, 64, stride=1)

        self.emonet.module.predictor.emo_fc_2=nn.Sequential()
        self.emonet.module.predictor.attenpool2 = nn.Sequential()
    def forward(self, imgs):
        out = self.emonet(imgs)

        return out

device = torch.device('cuda')
if __name__ == '__main__':
    model = Model_fan(50).to(device)
    imgs = torch.rand(2, 3, 256, 256).to(device)
    logits = model(imgs)
    print(logits.shape)
