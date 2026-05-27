import os
import cv2
from torch.utils.data import Dataset
from torchvision import transforms

default_image_size = (128, 128)


class Nahida_Dataset(Dataset):
    def __init__(self, image_dir, image_size=default_image_size):
        self.samples = []
        # 预处理 最后转成tensor向量 并归一化
        trans_rules = transforms.Compose([
            transforms.Resize(()),
            transforms.ToTensor()
        ])

        for label in ['0', '1']:
            label_dir = os.path.join(image_dir, label)
            for file in os.listdir(label_dir):
                self.samples.append(
                    (os.path.join(label_dir, file), int(label))
                )

        self.transform = trans_rules

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):  # 第二个参数是索引
        img_path, label = self.samples[idx]
        img = cv2.cvtColor(cv2.imread(img_path), cv2.COLOR_BGR2RGB)
        img = self.transform(img)  # 最后用转换规则 处理成tensor向量
        return img, label


import torch.nn as nn


class Nahida_CNN(nn.Module):
    def __init__(self):
        super().__init__()  # 调用父类 nn.Module 的 __init__
        #                   顺序容器
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),  # R G B -> 16特征 , 卷积核大小, 填充数
            nn.ReLU(),  # 加非线性
            nn.MaxPool2d(2),  # 128x128 -> 64x64

            nn.Conv2d(16, 32, 3, padding=1),  # 第二层卷积 16->32
            nn.ReLU(),
            nn.MaxPool2d(2),  # 64 -> 32
        )

        self.classifier = nn.Sequential(  # 分类器
            nn.Linear(32 * 32 * 32, 64),
            nn.ReLU(),
            nn.Linear(64, 2)  # 二分类
        )
