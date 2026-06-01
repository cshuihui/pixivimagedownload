import torch
from param import image_process, NahidaCNN

default_image_size = (128, 128)

def predict(model_dir, img_dir, image_size=default_image_size):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    model = NahidaCNN(image_size=image_size).to(device)
    model.load_state_dict(torch.load(model_dir, map_location=device))
    img = image_process(img_dir, image_size).unsqueeze(0).to(device)

    model.eval()

    with torch.no_grad():
        outputs = model(img)
        result = outputs.argmax(dim=1)  # dim=1 参数指定了沿着哪个维度寻找最大值索引

    return result.item()


if __name__ == '__main__':
    model_dir = './nahida_cnn_best.pth'
    img_dir = './139301594_p0.png'
    print(predict(model_dir, img_dir, image_size=default_image_size))