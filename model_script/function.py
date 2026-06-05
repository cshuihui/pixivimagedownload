import os
import numpy as np
from PIL import Image


def to_onnx(pth_path, onnx_path=None, image_size=(128, 128)):
    """将 .pth 模型转换为 .onnx 格式

    Args:
        pth_path: 输入的 .pth 模型路径
        onnx_path: 输出的 .onnx 路径（默认同目录同名）
        image_size: 模型输入的图片尺寸
    """
    import torch
    from .param import NahidaCNN

    if onnx_path is None:
        onnx_path = pth_path.replace('.pth', '.onnx')

    device = 'cpu'
    model = NahidaCNN(image_size=image_size).to(device)
    model.load_state_dict(torch.load(pth_path, map_location=device))
    model.eval()

    dummy = torch.randn(1, 3, image_size[0], image_size[1])
    torch.onnx.export(
        model, dummy, onnx_path,
        input_names=['input'], output_names=['output'],
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}},
        opset_version=17,
    )

    # 将权重嵌入 .onnx 文件，删除外部 .onnx.data
    import onnx

    onnx_model = onnx.load(onnx_path)
    onnx.save_model(
        onnx_model,
        onnx_path,
        save_as_external_data=False
    )

    data_path = onnx_path + '.data'
    if os.path.exists(data_path):
        os.remove(data_path)
    print(f"ONNX 已保存（单文件）: {onnx_path}")


def predict_onnx(onnx_path, img_path, image_size=(128, 128)):
    """使用 ONNX 模型推理图片

    Args:
        onnx_path: .onnx 模型路径
        img_path: 要预测的图片路径
        image_size: 模型输入的图片尺寸

    Returns:
        预测类别 (0 或 1)
    """
    import onnxruntime

    # 图片预处理（等效于原 torchvision 流程）
    img = Image.open(img_path).convert('RGB')
    img = img.resize((image_size[0], image_size[1]), Image.BILINEAR)
    # (H, W, C) -> (C, H, W)，归一化到 [-1, 1]
    arr = np.array(img, dtype=np.float32) / 127.5 - 1.0
    arr = np.transpose(arr, (2, 0, 1))
    arr = np.expand_dims(arr, axis=0)  # NCHW

    # 加载模型（带缓存）
    session = onnxruntime.InferenceSession(
        onnx_path, providers=['CPUExecutionProvider']
    )
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: arr})
    result = np.argmax(outputs[0], axis=1)

    return int(result[0])
