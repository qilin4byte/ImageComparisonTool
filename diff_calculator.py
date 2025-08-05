import numpy as np
from PIL import Image
import math


class ImageDiffCalculator:
    """
    Simple image difference calculator using basic subtraction and hot colormap.
    """
    
    def __init__(self):
        self.threshold = 10  # Simple pixel difference threshold (0-255)
        
    def calculate_diff(self, img1_path, img2_path, options=None):
        """
        Calculate pixel differences between two images using simple subtraction.
        Returns a PIL Image with hot colormap visualization.
        """
        if options:
            self.threshold = options.get('threshold', self.threshold)
        
        try:
            # Load images and convert to RGB
            img1 = Image.open(img1_path).convert('RGB')
            img2 = Image.open(img2_path).convert('RGB')
            
            # Resize images to match if they're different sizes
            if img1.size != img2.size:
                # Use the larger size to avoid data loss
                max_width = max(img1.width, img2.width)
                max_height = max(img1.height, img2.height)
                
                if img1.size != (max_width, max_height):
                    img1 = img1.resize((max_width, max_height), Image.Resampling.LANCZOS)
                if img2.size != (max_width, max_height):
                    img2 = img2.resize((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Convert to numpy arrays
            arr1 = np.array(img1, dtype=np.float32)
            arr2 = np.array(img2, dtype=np.float32)
            
            # Calculate absolute difference
            diff = np.abs(arr1 - arr2)
            
            # Convert to grayscale difference (average across RGB channels)
            diff_gray = np.mean(diff, axis=2)
            
            # Apply threshold to reduce noise
            diff_gray[diff_gray < self.threshold] = 0
            
            # Normalize to 0-255 range
            if diff_gray.max() > 0:
                diff_gray = (diff_gray / diff_gray.max() * 255).astype(np.uint8)
            else:
                diff_gray = diff_gray.astype(np.uint8)
            
            # Apply hot colormap
            diff_colored = self._apply_hot_colormap(diff_gray)
            
            # Convert back to PIL Image
            diff_pil = Image.fromarray(diff_colored.astype(np.uint8))
            return diff_pil
            
        except Exception as e:
            print(f"Error calculating image difference: {e}")
            return None
    
    def _apply_hot_colormap(self, gray_array):
        """
        Apply a hot colormap to grayscale difference array.
        Black = no difference, Red->Yellow->White = increasing difference
        """
        height, width = gray_array.shape
        colored = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Normalize input to 0-1 range
        normalized = gray_array.astype(np.float32) / 255.0
        
        # Hot colormap implementation
        # 0.0 -> (0, 0, 0) black
        # 0.33 -> (255, 0, 0) red  
        # 0.66 -> (255, 255, 0) yellow
        # 1.0 -> (255, 255, 255) white
        
        # Red channel: starts at 0.33
        red_mask = normalized >= 0.33
        colored[red_mask, 0] = 255
        early_red_mask = (normalized > 0) & (normalized < 0.33)
        colored[early_red_mask, 0] = (normalized[early_red_mask] / 0.33 * 255).astype(np.uint8)
        
        # Green channel: starts at 0.66
        green_mask = normalized >= 0.66  
        colored[green_mask, 1] = 255
        early_green_mask = (normalized > 0.33) & (normalized < 0.66)
        colored[early_green_mask, 1] = ((normalized[early_green_mask] - 0.33) / 0.33 * 255).astype(np.uint8)
        
        # Blue channel: starts at 0.8 (for white highlights)
        blue_mask = normalized >= 0.8
        colored[blue_mask, 2] = ((normalized[blue_mask] - 0.8) / 0.2 * 255).astype(np.uint8)
        
        return colored
    
    def calculate_diff_stats(self, img1_path, img2_path):
        """
        Calculate simple difference statistics.
        Returns dict with pixel counts and percentages.
        """
        try:
            img1 = Image.open(img1_path).convert('RGB')
            img2 = Image.open(img2_path).convert('RGB')
            
            # Handle size differences
            if img1.size != img2.size:
                max_width = max(img1.width, img2.width)
                max_height = max(img1.height, img2.height)
                
                if img1.size != (max_width, max_height):
                    img1 = img1.resize((max_width, max_height), Image.Resampling.LANCZOS)
                if img2.size != (max_width, max_height):
                    img2 = img2.resize((max_width, max_height), Image.Resampling.LANCZOS)
            
            arr1 = np.array(img1, dtype=np.float32)
            arr2 = np.array(img2, dtype=np.float32)
            
            # Calculate differences
            diff = np.abs(arr1 - arr2)
            diff_gray = np.mean(diff, axis=2)
            
            total_pixels = arr1.shape[0] * arr1.shape[1]
            diff_pixels = np.sum(diff_gray > self.threshold)
            
            return {
                'total_pixels': total_pixels,
                'diff_pixels': int(diff_pixels),
                'diff_percentage': (diff_pixels / total_pixels) * 100,
                'similarity_percentage': ((total_pixels - diff_pixels) / total_pixels) * 100
            }
            
        except Exception as e:
            print(f"Error calculating diff stats: {e}")
            return None 