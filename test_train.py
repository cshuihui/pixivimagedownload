"""测试 model.train 包（从项目根目录调用）"""
from model.train import cnn_train

if __name__ == "__main__":
    cnn_train('./datasets/pic_datasets', '.', epochs=2)
