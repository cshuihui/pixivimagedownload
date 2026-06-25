import os
import torch
import torch.nn as nn

from PIL import Image
from torch.utils.data import Dataset, DataLoader

from torchvision import transforms
from torchvision.models import (
    mobilenet_v3_small,
    MobileNet_V3_Small_Weights
)


# =====================
# Dataset
# =====================

class NahidaDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.samples = []
        self.transform = transform

        for label in ['0', '1']:
            label_dir = os.path.join(root_dir, label)

            for file in os.listdir(label_dir):
                self.samples.append(
                    (
                        os.path.join(label_dir, file),
                        int(label)
                    )
                )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]

        image = Image.open(img_path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        return image, label


# =====================
# Config
# =====================

IMAGE_SIZE = 224
BATCH_SIZE = 8
EPOCHS = 20
LR = 1e-3

DEVICE = (
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

print("Device:", DEVICE)


# =====================
# Transform
# =====================

train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),

    transforms.RandomHorizontalFlip(),

    transforms.RandomRotation(15),

    transforms.ColorJitter(
        brightness=0.2,
        contrast=0.2,
        saturation=0.2
    ),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

val_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# =====================
# Dataset
# =====================

train_dataset = NahidaDataset(
    "dataset/train",
    train_transform
)

val_dataset = NahidaDataset(
    "dataset/val",
    val_transform
)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False
)

print("Train:", len(train_dataset))
print("Val:", len(val_dataset))


# =====================
# Model
# =====================

model = mobilenet_v3_small(
    weights=MobileNet_V3_Small_Weights.DEFAULT
)

# 冻结特征提取层
for param in model.features.parameters():
    param.requires_grad = False

# 修改最后输出层
in_features = model.classifier[3].in_features

model.classifier[3] = nn.Linear(
    in_features,
    2
)

model = model.to(DEVICE)

print(model)


# =====================
# Loss & Optimizer
# =====================

criterion = nn.CrossEntropyLoss()

optimizer = torch.optim.Adam(
    filter(
        lambda p: p.requires_grad,
        model.parameters()
    ),
    lr=LR
)


# =====================
# Train
# =====================

best_acc = 0.0

for epoch in range(EPOCHS):

    # -----------------
    # Train
    # -----------------

    model.train()

    train_loss = 0
    train_correct = 0
    train_total = 0

    for images, labels in train_loader:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(
            outputs,
            labels
        )

        loss.backward()
        optimizer.step()

        train_loss += loss.item()

        preds = outputs.argmax(dim=1)

        train_correct += (
            preds == labels
        ).sum().item()

        train_total += labels.size(0)

    train_acc = (
        train_correct / train_total
    )

    # -----------------
    # Validation
    # -----------------

    model.eval()

    val_loss = 0
    val_correct = 0
    val_total = 0

    with torch.no_grad():

        for images, labels in val_loader:

            images = images.to(DEVICE)
            labels = labels.to(DEVICE)

            outputs = model(images)

            loss = criterion(
                outputs,
                labels
            )

            val_loss += loss.item()

            preds = outputs.argmax(dim=1)

            val_correct += (
                preds == labels
            ).sum().item()

            val_total += labels.size(0)

    val_acc = (
        val_correct / val_total
    )

    print(
        f"Epoch [{epoch+1}/{EPOCHS}] "
        f"Train Loss: {train_loss:.4f} "
        f"Train Acc: {train_acc:.4f} "
        f"Val Loss: {val_loss:.4f} "
        f"Val Acc: {val_acc:.4f}"
    )

    # 保存最佳模型
    if val_acc > best_acc:

        best_acc = val_acc

        torch.save(
            model.state_dict(),
            "best_nahida_mobilenetv3.pth"
        )

        print(
            f"Best model saved! "
            f"Acc={best_acc:.4f}"
        )

print("Training Finished.")