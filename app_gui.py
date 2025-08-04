from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QWidget,
    QFileDialog,
    QStatusBar,
    QMessageBox,
    QCheckBox,
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QCheckBox,
    QMessageBox,
)
from PySide6.QtCore import QThread, Signal
from image_view import ImageView
from graphics_view import GraphicsView
from metrics import ImageMetrics


class MetricsCalculationThread(QThread):
    """Thread for calculating metrics without blocking the UI"""
    metrics_calculated = Signal(str, str, float, float, float)  # name, gt_name, psnr, ssim, lpips
    calculation_started = Signal(str)  # gt_name
    calculation_finished = Signal()
    error_occurred = Signal(str, str)  # name, error_message

    def __init__(self, metrics_calculator, image_views):
        super().__init__()
        self.metrics_calculator = metrics_calculator
        self.image_views = image_views

    def run(self):
        """Calculate metrics in background thread"""
        if len(self.image_views) < 2:
            self.error_occurred.emit("General", "Need at least 2 images to calculate metrics")
            return
            
        # Use the last image as ground truth
        gt_view = self.image_views[-1]
        gt_image_path = gt_view.image_view.url
        
        if not gt_image_path:
            self.error_occurred.emit("General", "Ground truth image not loaded")
            return
            
        self.calculation_started.emit(gt_view.text_view.text())
        
        for i, view in enumerate(self.image_views[:-1]):
            img_path = view.image_view.url
            if not img_path:
                self.error_occurred.emit(f"Image {i+1}", "Image not loaded, skipping...")
                continue
                
            try:
                psnr = self.metrics_calculator.calculate_psnr(img_path, gt_image_path)
                ssim = self.metrics_calculator.calculate_ssim(img_path, gt_image_path)
                lpips_val = self.metrics_calculator.calculate_lpips(img_path, gt_image_path)
                
                self.metrics_calculated.emit(
                    view.text_view.text(), 
                    gt_view.text_view.text(),
                    psnr, ssim, lpips_val
                )
            except Exception as e:
                self.error_occurred.emit(view.text_view.text(), str(e))
        
        self.calculation_finished.emit()


class AppGui(QVBoxLayout):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.metrics_calculator = ImageMetrics()
        self.metrics_thread = None

        self.image_views = []

        # Top bar
        self.top_settings_layout = QHBoxLayout()

        # Change resolution based on selected images
        self.resolution_label = QLabel("Resolution")
        self.resolution_combo = QComboBox()
        self.resolution_combo.setFixedWidth(100)
        self.resolution_combo.currentTextChanged.connect(self.set_resolution)

        # Antialiasing checkbox
        self.antialiasing_checkbox = QCheckBox("Antialiasing")
        self.antialiasing_checkbox.setChecked(False)  # Set default to unchecked
        self.antialiasing_checkbox.stateChanged.connect(self.toggle_antialiasing)

        self.calculate_metrics_checkbox = QCheckBox("Calculate Metrics")
        self.calculate_metrics_checkbox.setChecked(False)
        self.calculate_metrics_checkbox.stateChanged.connect(self.toggle_metrics)

        self.top_settings_layout.addStretch()
        self.top_settings_layout.addWidget(self.resolution_label)
        self.top_settings_layout.addWidget(self.resolution_combo)
        self.top_settings_layout.addWidget(self.antialiasing_checkbox)
        self.top_settings_layout.addWidget(self.calculate_metrics_checkbox)
        self.top_settings_layout.addStretch()

        # Images comparison
        self.images_widget = QWidget()

        self.image_views_layout = QHBoxLayout()
        self.image_views_layout.setSpacing(0)

        # Layout with remove and add button
        self.add_remove_image_layout = QHBoxLayout()
        self.remove_button = QPushButton()
        self.remove_button.setText("-")
        self.remove_button.setFixedSize(30, 30)
        self.remove_button.pressed.connect(self.remove_image_view)
        self.add_button = QPushButton()
        self.add_button.setText("+")
        self.add_button.setFixedSize(30, 30)
        self.add_button.pressed.connect(self.add_image_view)

        self.add_remove_image_layout.addStretch()
        self.add_remove_image_layout.addWidget(self.remove_button)
        self.add_remove_image_layout.addWidget(self.add_button)
        self.add_remove_image_layout.addStretch()

        # Bottom bar
        self.bottom_settings_layout = QHBoxLayout()

        self.save_comparison_button = QPushButton()
        self.save_comparison_button.setText("Save comparison")
        self.save_comparison_button.setFixedWidth(200)
        self.save_comparison_button.pressed.connect(self.save_comparison)

        self.bottom_settings_layout.addWidget(self.save_comparison_button)

        self.images_widget.setLayout(self.image_views_layout)

        self.status_bar = QStatusBar()
        self.version = QLabel("Image Comparer v0.5")
        self.resolution_status = QLabel("None")
        self.status_bar.addWidget(self.version)
        self.status_bar.addWidget(self.resolution_status)

        self.main_window.setStatusBar(self.status_bar)

        self.addLayout(self.top_settings_layout)
        self.addWidget(self.images_widget)
        self.addLayout(self.add_remove_image_layout)
        self.addLayout(self.bottom_settings_layout)

    def toggle_metrics(self):
        """Calculate and display metrics when checkbox is checked"""
        if self.calculate_metrics_checkbox.isChecked():
            # Checkbox was just checked - calculate metrics in background
            if len(self.image_views) > 1:
                self.start_metrics_calculation()
            else:
                print("Need at least 2 images to calculate metrics")
        # If unchecked, do nothing - just keep the unchecked state

    def start_metrics_calculation(self):
        """Start metrics calculation in background thread"""
        if self.metrics_thread and self.metrics_thread.isRunning():
            return  # Already calculating
            
        print("Starting metrics calculation in background...")
        self.metrics_thread = MetricsCalculationThread(self.metrics_calculator, self.image_views)
        
        # Connect signals
        self.metrics_thread.calculation_started.connect(self.on_calculation_started)
        self.metrics_thread.metrics_calculated.connect(self.on_metrics_calculated)
        self.metrics_thread.calculation_finished.connect(self.on_calculation_finished)
        self.metrics_thread.error_occurred.connect(self.on_metrics_error)
        
        # Start the thread
        self.metrics_thread.start()

    def on_calculation_started(self, gt_name):
        """Called when metrics calculation starts"""
        print(f"\n--- Metrics Calculation ---")
        print(f"Ground Truth: {gt_name}")
        print("=" * 40)

    def on_metrics_calculated(self, name, gt_name, psnr, ssim, lpips_val):
        """Called when metrics for one image are calculated"""
        print(f"Metrics for {name}:")
        print(f"  PSNR: {psnr:.2f} dB")
        print(f"  SSIM: {ssim:.4f}")
        print(f"  LPIPS: {lpips_val:.4f}")
        print("-" * 30)

    def on_calculation_finished(self):
        """Called when all metrics calculations are finished"""
        print("Metrics calculation completed!")

    def on_metrics_error(self, name, error_message):
        """Called when an error occurs during metrics calculation"""
        print(f"Error calculating metrics for {name}: {error_message}")

    def calculate_metrics(self):
        """Legacy method - now redirects to threaded calculation"""
        self.start_metrics_calculation()

    def add_image_view(self, color=None, name="", text_color="white"):
        graphics_view = GraphicsView(color, name=name, text_color=text_color)
        graphics_view.image_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        graphics_view.image_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        graphics_view.image_view.horizontalScrollBar().valueChanged.connect(
            partial(self.slider_sync, "horizontal")
        )
        graphics_view.image_view.verticalScrollBar().valueChanged.connect(
            partial(self.slider_sync, "vertical")
        )
        graphics_view.image_view.photoAdded.connect(self.add_resolution)
        graphics_view.image_view.tranformChanged.connect(self.set_transform)
        graphics_view.image_view.multipleUrls.connect(self.load_multiple_images)

        self.image_views_layout.addLayout(graphics_view)
        self.image_views.append(graphics_view)

    def load_images(self, items, text_color):
        # Clear existing image views
        while self.image_views:
            view_to_remove = self.image_views.pop()
            self.image_views_layout.removeItem(view_to_remove)
            view_to_remove.image_view.deleteLater()
            view_to_remove.text_view.deleteLater()
            view_to_remove.deleteLater()

        image_paths = [item["path"] for item in items.values()]
        for name, details in items.items():
            color = details.get("color", None)  # Use None if color not specified
            self.add_image_view(
                color=color, name=name, text_color=text_color
            )
            self.image_views[-1].image_view.loadImage(details["path"])

        if self.calculate_metrics_checkbox.isChecked():
            gt_image_path = image_paths[-1]

            for i, view in enumerate(self.image_views[:-1]):
                img_path = image_paths[i]
                psnr = self.metrics_calculator.calculate_psnr(img_path, gt_image_path)
                ssim = self.metrics_calculator.calculate_ssim(img_path, gt_image_path)
                lpips_val = self.metrics_calculator.calculate_lpips(
                    img_path, gt_image_path
                )
                print(f"Metrics for {view.text_view.text()}:")
                print(f"  PSNR: {psnr:.2f}")
                print(f"  SSIM: {ssim:.4f}")
                print(f"  LPIPS: {lpips_val:.4f}")

    def load_multiple_images(self, urls):
        dialog = QMessageBox()
        dialog.setWindowTitle("Multiple files")
        dialog.setText("Do you want to load multiple files?")
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = dialog.exec_()
        urls = urls

        if result == QMessageBox.Yes:
            for item in self.image_views:
                if not item.image_view.url:
                    item.image_view.url = urls[0]
                    urls.remove(urls[0])

            for item in self.image_views:
                item.image_view.loadImage(item.image_view.url.toLocalFile())

        elif result == QMessageBox.No:
            return

    def remove_image_view(self):
        if len(self.image_views) > 2:
            self.image_views_layout.removeItem(self.image_views[-1])
            self.image_views[-1].deleteLater()
            self.image_views[-1].image_view.deleteLater()
            self.image_views[-1].text_view.deleteLater()
            self.image_views.remove(self.image_views[-1])

    def set_transform(self, *args):
        for item in self.image_views:
            item.image_view.set_transform(*args)

    def slider_sync(
        self,
        orientation,
        value,
    ):
        for item in self.image_views:
            if orientation == "horizontal":
                item.image_view.horizontalScrollBar().setValue(value)
            else:
                item.image_view.verticalScrollBar().setValue(value)

    def set_resolution(self, resolution):
        resolution = resolution.split("x")
        for item in self.image_views:
            if item.image_view.scene().items():
                item.image_view.scene().items()[0].setPixmap(
                    item.image_view.original_image.scaled(
                        int(resolution[0]), int(resolution[1])
                    )
                )
            item.image_view.setSceneRect(0, 0, int(resolution[0]), int(resolution[1]))
            item.image_view.setSceneRect(0, 0, int(resolution[0]), int(resolution[1]))
            self.resolution_status.setText("x".join(resolution))
            self.resolution_status.setStyleSheet("color: lime")

    def add_resolution(self, width, height):
        resolution = f"{width}x{height}"
        if resolution not in [
            self.resolution_combo.itemText(i)
            for i in range(self.resolution_combo.count())
        ]:
            self.resolution_combo.addItem(resolution)

        if self.resolution_combo.currentText():
            self.set_resolution(self.resolution_combo.currentText())

    def toggle_antialiasing(self, state):
        enabled = state == 2  # Qt.Checked
        for item in self.image_views:
            item.image_view.set_antialiasing(enabled)

    def save_comparison(self):
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("JPEG Image Files (*.jpg)")

        file_path, _ = file_dialog.getSaveFileName(
            None, "Save Comparison Screenshot", "", "JPEG Image Files (*.jpg)"
        )

        if file_path:
            screenshot = self.images_widget.grab()
            screenshot.save(file_path, "jpg")
            print(f"Saved screenshot as {file_path}")
