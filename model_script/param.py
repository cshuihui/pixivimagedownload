import os

from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms



def image_process(dir, image_size):
    img = Image.open(dir).convert('RGB')  # 直接用PIL，不用cv2
    img = transform_rules(image_size)(img)
    return img

def transform_rules(image_size):
    trans_rules = transforms.Compose([
        #  transform期望PIL图片 之后最好用PIL
        transforms.Resize((image_size[0], image_size[1])),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])  # 归一化
    ])
    return trans_rules

class NahidaDataset(Dataset):
    def __init__(self, image_dir, image_size):
        self.samples = []
        self.image_size = image_size  # 保存到self后续可以引用
        # 预处理 最后转成tensor向量 并归一化


        for label in ['0', '1']:
            label_dir = os.path.join(image_dir, label)
            for file in os.listdir(label_dir):
                self.samples.append(
                    (os.path.join(label_dir, file), int(label))
                )

        self.transform = transform_rules(image_size)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):  # 第二个参数是索引
        img, label = self.samples[idx]
        img = image_process(img, self.image_size)
        return img, label


import torch.nn as nn


class NahidaCNN(nn.Module):
    def __init__(self, image_size):
        super().__init__()  # 调用父类 nn.Module 的 __init__
        #                   顺序容器
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),  # R G B -> 16特征 , 卷积核大小, 填充数
            nn.BatchNorm2d(32),  # pytorch 需要将bn加在激活函数前 参数为通道数
            nn.ReLU(),  # 加非线性
            nn.Dropout2d(0.1),  #  卷积层用dropout2d 全连接层用dropout
            nn.MaxPool2d(2),  #  缩小图片尺寸2倍

            nn.Conv2d(32, 64, 3, padding=1),  # 第二层卷积 32->64
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Dropout2d(0.1),
            nn.MaxPool2d(2),  #

            nn.Conv2d(64, 128, 3, padding=1),  # 第二层卷积 64->128
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.Dropout2d(0.1),
            nn.MaxPool2d(2),  #

        )

        feature_size = (image_size[0] // (2 ** 3), image_size[1] // (2 ** 3))  # 3次池化

        self.classifier = nn.Sequential(  # 分类器 全连接层
            nn.Linear(128 * feature_size[0] * feature_size[1], 256),  # 通道数 × 图片宽 × 图片高
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 2)  # 二分类
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)  # 展平 x.size(0)是 batch_size  有多少张图片
        #   -1 = “你帮我算剩下的长度”
        x = self.classifier(x)
        return x
