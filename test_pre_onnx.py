"""测试 ONNX 模型推理"""
from model_script.function import predict_onnx

# 配置
ONNX_PATH = r"models/nahida_cnn_1.1_best.onnx"
TEST_IMG = r"143035291_p0.jpg"

def main():
    print(f"模型: {ONNX_PATH}")
    print(f"图片: {TEST_IMG}")

    result = predict_onnx(ONNX_PATH, TEST_IMG)
    print(f"预测结果: {result}")
    print("纳西妲" if result == 1 else "其他")

if __name__ == '__main__':
    main()
