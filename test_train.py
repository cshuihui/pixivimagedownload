"""测试 model.train 包（从项目根目录调用）"""
from model_script.train import cnn_train

if __name__ == "__main__":
    cnn_train('./datasets/pic_datasets', './models', epochs=20, model_save_name="nahida_cnn_1.1")
