import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtCore import Qt

from app_gui import AppGui
import qdarktheme

# Default configuration
default_items = {
    "Input": {
        "path": None,  # Set to None to start without default images
        "color": "#6E2C00",
    },
    "Output": {
        "path": None,  # Set to None to start without default images
        "color": "#004D40",
    },
    "GT": {
        "path": None,  # Set to None to start without default images
        "color": "#512E5F",
    },
}
text_color = "#f9f9f9"

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Image Comparator - Enhanced Multi-Image Viewer')
        self.setGeometry(100, 100, 1400, 800)
        
        # Enable keyboard focus
        self.setFocusPolicy(Qt.StrongFocus)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.app_gui = AppGui(main_window=self)
        central_widget.setLayout(self.app_gui)
        
        # Load default images
        if default_items:
            # Filter out items with None paths
            valid_items = {k: v for k, v in default_items.items() if v.get("path") is not None}
            if valid_items:
                self.app_gui.load_images(valid_items, text_color)
    
    def keyPressEvent(self, event):
        """Forward keyboard events to the app GUI."""
        self.app_gui.keyPressEvent(event)
        super().keyPressEvent(event)


def main():
    app = QApplication()
    qdarktheme.setup_theme()
    window = MyApp()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
