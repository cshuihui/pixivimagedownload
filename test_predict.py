"""测试 model.predict 包（从项目根目录调用）"""
import time
_start = time.time()

from model_script.predict import predict

if __name__ == "__main__":
    t1 = time.time()
    print(f"导入耗时: {t1 - _start:.3f}s")

    model_dir = './models/nahida_cnn_1.1_best.pth'

    # 测试两张图：一张在 models/ 下，一张在项目根目录
    test_images = [
        './datasets/pic_datasets/0/145517948_p2.jpg',  # 在 models/ 下
    ]

    for i, img in enumerate(test_images):
        result = predict(model_dir, img)
        elapsed = time.time() - _start
        print(f"第{i+1}张 ({img}) → 预测结果: {result}  (启动后 {elapsed:.3f}s)")

