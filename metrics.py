import torch
import lpips
import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

def _prepare_image_for_lpips(image_path):
    img = Image.open(image_path).convert("RGB")
    img_tensor = (
        torch.tensor(np.array(img)).permute(2, 0, 1).unsqueeze(0) / 255.0
    )  # HWC to CHW -> NCHW and scale to [0, 1]
    return (img_tensor * 2) - 1  # scale to [-1, 1]


class ImageMetrics:
    def __init__(self):
        self.lpips_model = lpips.LPIPS(net="alex")

    def calculate_psnr(self, img1_path, img2_path):
        img1 = np.array(Image.open(img1_path))
        img2 = np.array(Image.open(img2_path))
        
        # Ensure both images have the same size
        if img1.shape != img2.shape:
            # Resize img2 to match img1's size
            img2_pil = Image.fromarray(img2)
            img2_pil = img2_pil.resize((img1.shape[1], img1.shape[0]), Image.Resampling.LANCZOS)
            img2 = np.array(img2_pil)
        
        return psnr(img1, img2, data_range=img1.max() - img1.min())

    def calculate_ssim(self, img1_path, img2_path):
        img1 = np.array(Image.open(img1_path))
        img2 = np.array(Image.open(img2_path))
        
        # Ensure both images have the same size
        if img1.shape != img2.shape:
            # Resize img2 to match img1's size
            img2_pil = Image.fromarray(img2)
            img2_pil = img2_pil.resize((img1.shape[1], img1.shape[0]), Image.Resampling.LANCZOS)
            img2 = np.array(img2_pil)
        
        return ssim(img1, img2, data_range=img1.max() - img1.min(), channel_axis=2)

    def calculate_lpips(self, img1_path, img2_path):
        img1_tensor = _prepare_image_for_lpips(img1_path)
        img2_tensor = _prepare_image_for_lpips(img2_path)
        with torch.no_grad():
            distance = self.lpips_model.forward(img1_tensor, img2_tensor)
        return distance.item() 