"""测试将 .pth 模型转换为 .onnx 格式"""
from model_script.function import to_onnx

PTH_PATH = r"models/nahida_cnn_1.1_best.pth"
ONNX_PATH = r"models/nahida_cnn_1.1_best.onnx"

def main():
    print(f"输入: {PTH_PATH}")
    print(f"输出: {ONNX_PATH}")
    to_onnx(PTH_PATH, ONNX_PATH)

if __name__ == '__main__':
    main()
