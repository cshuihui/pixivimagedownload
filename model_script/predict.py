import torch
from .param import image_process, NahidaCNN

default_image_size = (128, 128)

# 模型缓存（避免重复加载）
_model_cache = None
_model_path_cache = ""
_device = None


def predict(model_dir, img_dir, image_size=default_image_size):
    global _model_cache, _model_path_cache, _device

    if _device is None:
        _device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # 只有首次调用或模型路径变更时才加载
    if _model_cache is None or _model_path_cache != model_dir:
        model = NahidaCNN(image_size=image_size).to(_device)
        model.load_state_dict(torch.load(model_dir, map_location=_device))
        model.eval()
        _model_cache = model
        _model_path_cache = model_dir

    img = image_process(img_dir, image_size).unsqueeze(0).to(_device)

    with torch.no_grad():
        outputs = _model_cache(img)
        result = outputs.argmax(dim=1)

    return result.item()


if __name__ == '__main__':
    model_dir = './nahida_cnn_best.pth'
    img_dir = './139301594_p0.png'
    print(predict(model_dir, img_dir, image_size=default_image_size))
