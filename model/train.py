import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from param import *
import os


default_image_size = (128, 128)

def cnn_train(datasets_dir, save_dir, epochs=20, lr=0.001, train_size_rate=0.8, batch_size=32, image_size=default_image_size):
    # 1. 加载你的数据集
    print('loading datasets...')
    dataset = NahidaDataset(image_dir=datasets_dir, image_size=image_size)
    print('done.')

    # 2. 自动分割 80%训练 20%验证
    train_size = int(train_size_rate * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # 3. 初始化模型
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print('device:', device)
    model = NahidaCNN(image_size=image_size).to(device)

    # 4. 损失函数和优化器
    criterion = nn.CrossEntropyLoss()  # 交叉熵损失函数
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    print('training...')
    # 5. 训练循环
    best_acc = 0

    for epoch in range(epochs):
        model.train()
        train_loss = 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()  # 将损失loss 向输入侧进行反向传播，同时对于需要进行梯度计算的所有变量 并将其累积到梯度
            optimizer.step()  # 是优化器对 权重 的值进行更新

            train_loss += loss.item()  # 累加损失，最后求平均

        model.eval()
        val_loss = 0
        correct = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                val_loss += criterion(outputs, labels).item()
                correct += (outputs.argmax(1) == labels).sum().item()  # argmax(1) 取最大值的索引

        acc = correct / val_size
        print(f"Epoch {epoch+1}/{epochs} | 训练损失: {train_loss/len(train_loader):.4f} | 验证损失: {val_loss/len(val_loader):.4f} | 验证准确率: {acc:.4f}")
        if acc > best_acc:
            best_acc = acc
            torch.save(model.state_dict(), os.path.join(save_dir, "nahida_cnn_best.pth"))
            print(f"  → 保存最优模型，准确率: {best_acc:.4f}")

    # 6. 保存模型
    torch.save(model.state_dict(), os.path.join(save_dir, "nahida_cnn.pth"))
    #               仅保存权重
    print("模型已保存")

if __name__ == "__main__":
    cnn_train('../datasets/pic_datasets', '.')