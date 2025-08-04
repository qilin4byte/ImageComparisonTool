import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from app_gui import AppGui
import qdarktheme


class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Image comparator")
        self.setMinimumSize(600, 400)
        self.app_gui = AppGui(self)

        central_widget = QWidget()
        central_widget.setLayout(self.app_gui)

        self.setCentralWidget(central_widget)

    def load_images(self, items, text_color):
        self.app_gui.load_images(items, text_color)


def main():
    app = QApplication()
    qdarktheme.setup_theme()
    window = MyApp()

    default_items = {
        "Input": {
            "path": "/Users/bytedance/Desktop/test/input/0002_0000.png",
            "color": "#6E2C00",
        },
        "Output": {
            # "path": "/Users/bytedance/Documents/Data/NafNet_analysis/RealMCDataset/Fused-width64-LPIPS-L1-FixData/visualization/img_sorted/0000.png",
            "path":"/Users/bytedance/Desktop/0002_0000.png",
            "color": "#004D40",
        },
        "GT": {
            "path": "/Users/bytedance/Documents/Data/NafNet_analysis/RealMCDataset/Fused-width64-LPIPS-L1-FixData/visualization/gt/0002_0000_gt.png",
            "color": "#512E5F",
        },

    }
    text_color = "#f9f9f9"
    window.load_images(default_items, text_color)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
