# Image Comparator

An advanced image comparison tool with metric calculation capabilities. This application enables you to compare multiple images side by side with synchronized scrolling, zooming, and optional quantitative analysis using PSNR, SSIM, and LPIPS metrics.

![screenshot.jpg](screenshot.png)

## Features

- **Multi-Image Comparison:** View and compare multiple images simultaneously with customizable layouts
- **Flexible Panel Layouts:** Dynamic grid arrangements (1×N, 2×2, 2×3, 3×2, etc.) for any number of images
- **Synchronized Navigation:** Scroll and zoom across all images simultaneously for precise comparison
- **Configurable Interface:** Customize image names, background colors, and text colors
- **Metric Calculation:** Optional PSNR, SSIM, and LPIPS metric calculation against ground truth
- **Easy Configuration:** Simple dictionary-based setup for default images and settings

## Getting Started

### Prerequisites

Make sure you have the following prerequisites installed:

- Python 3.7+
- Required packages (see installation section)

### Installation

1. Clone or download this repository:

   ```shell
   git clone https://code.byted.org/qilin.deng/ImageComparator.git
   cd image_comparator
   ```

2. Install the required dependencies:

   ```shell
   pip install -r requirements.txt
   ```

   Or install packages individually:
   ```shell
   pip install PySide6 pyqtdarktheme Pillow scikit-image torch lpips
   ```

### Configuration

Edit the `main.py` file to configure your default images. The configuration uses a simple dictionary format:

```python
default_items = {
    "Input": {
        "path": "/path/to/your/input/image.png",
        "color": "#6E2C00",  # Optional: roasted sienna (recommended)
    },
    "Output": {
        "path": "/path/to/your/output/image.png", 
        "color": "#004D40",  # Optional: forest cyan (recommended)
    },
    "GT": {
        "path": "/path/to/your/ground_truth/image.png",
        "color": "#512E5F",  # Optional: plum (recommended)
    },
    "Method 4": {
        "path": "/path/to/another/image.png",
        # No color specified - will use random expert-curated color
    },
}
text_color = "#f9f9f9"  # Text color for all labels
```

**Note:** 
- The `color` field is optional. If not specified, the application will automatically select from a professionally curated color palette.
- **You can drag and drop images based on the UI.**

### Running the Application

```shell
python main.py
```

## Usage

### Basic Navigation
- **Mouse Wheel:** Zoom in/out on images
- **Click and Drag:** Pan around images
- **Synchronized Movement:** All image views move together for easy comparison

### Controls
- **Resolution Dropdown:** Change the display resolution of images
- **Layout Dropdown:** Switch between available grid arrangements (1×N, 2×2, etc.)
- **Antialiasing Checkbox:** Toggle smooth image rendering (unchecked by default for better performance)
- **Calculate Metrics Checkbox:** Enable/disable metric calculations (unchecked by default for faster loading)


#### Sample Terminal Output:
When you check the "Calculate Metrics" box, you'll see output like this in your terminal:

```
Starting metrics calculation in background...

--- Metrics Calculation ---
Ground Truth: GT
========================================
Metrics for Input:
  PSNR: 22.11 dB
  SSIM: 0.6433
  LPIPS: 0.3732
------------------------------
Metrics for Output:
  PSNR: 23.54 dB
  SSIM: 0.7222
  LPIPS: 0.1128
------------------------------
Metrics calculation completed!
```

#### Supported Metrics:
- **PSNR (Peak Signal-to-Noise Ratio):** Measures image quality in decibels (dB)
- **SSIM (Structural Similarity Index):** Measures structural similarity (0-1, higher is better)
- **LPIPS (Learned Perceptual Image Patch Similarity):** Perceptual similarity using deep learning (lower is better)

### Loading New Images
- **Drag and Drop:** Drop image files directly onto any view
- **Multiple Files:** Drop multiple files to load them into separate views
- **Panel Integration:** Dropped images automatically integrate with the current layout system

## Customization

### Colors
You can use any valid CSS color format:
- Hex with transparency: `"#2c3e50cc"`
- Hex without transparency: `"#2c3e50"`
- Color names: `"red"`, `"blue"`, etc.
- If no color is specified, a professional color will be automatically selected

### Adding More Images
Simply add more entries to the `default_items` dictionary:

```python
default_items = {
    "Input": {"path": "/path/to/input.png", "color": "#6E2C00"},
    "Method A": {"path": "/path/to/methodA.png", "color": "#004D40"},
    "Method B": {"path": "/path/to/methodB.png"},  # Auto color selection
    "Method C": {"path": "/path/to/methodC.png", "color": "#512E5F"},
    "Ground Truth": {"path": "/path/to/gt.png", "color": "#BF360C"},
}
```

## File Structure

```
image_comparator/
├── main.py              # Main application entry point and configuration
├── app_gui.py           # Main GUI layout and logic
├── graphics_view.py     # Individual image view components
├── image_view.py        # Image display and interaction handling
├── metrics.py           # PSNR, SSIM, and LPIPS calculation
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── screenshot.png      # Application screenshot
```


## Tips

1. **Performance:** Disable "Calculate Metrics" when you don't need quantitative analysis for faster loading
2. **Large Images:** The application supports high-resolution images with smooth zooming and panning
3. **Batch Comparison:** Use the configuration dictionary to quickly switch between different image sets
4. **Ground Truth:** Always place your ground truth/reference image last in the configuration for proper metric calculation
5. **Progress Monitoring:** Watch the terminal to see metrics being calculated progressively for each image

## Troubleshooting

### LPIPS Model Download
The first time you use LPIPS metrics, the model will be downloaded automatically. This may take a few minutes but only happens once.

## License

This project is open source. Please refer to the license file for more information.

