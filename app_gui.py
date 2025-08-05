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
    QMainWindow,
    QGridLayout,
    QLineEdit,
)
from PySide6.QtCore import QThread, Signal
from image_view import ImageView
from graphics_view import GraphicsView
from curtain_view import CurtainComparisonWidget
from metrics import ImageMetrics
import math
import os
import glob
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtGui import QPixmap
from diff_calculator import ImageDiffCalculator


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

        # Curtain comparison mode
        self.curtain_widget = None
        self.is_curtain_mode = False
        
        # Folder comparison mode
        self.is_folder_mode = False
        self.folder_left_path = None
        self.folder_right_path = None
        self.folder_image_list = []  # List of (left_image, right_image) tuples
        self.current_folder_index = 0
        
        # Flag to temporarily disable curtain availability updates during loading
        self.loading_images = False

        # Top bar
        self.top_settings_layout = QHBoxLayout()
        
        # Folder comparison controls (will be added to bottom layout later)
        self.folder_mode_checkbox = QCheckBox("Folder Compare Mode")
        self.folder_mode_checkbox.setChecked(False)
        self.folder_mode_checkbox.stateChanged.connect(self.toggle_folder_mode)
        
        self.select_folder_left_button = QPushButton("Select Left Folder")
        self.select_folder_left_button.clicked.connect(self.select_left_folder)
        self.select_folder_left_button.setEnabled(False)
        
        self.select_folder_right_button = QPushButton("Select Right Folder")
        self.select_folder_right_button.clicked.connect(self.select_right_folder)
        self.select_folder_right_button.setEnabled(False)
        
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self.navigate_previous)
        self.prev_button.setEnabled(False)
        
        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self.navigate_next)
        self.next_button.setEnabled(False)
        
        self.image_counter_label = QLabel("0 / 0")

        # Change resolution based on selected images
        self.resolution_label = QLabel("Resolution")
        self.resolution_combo = QComboBox()
        self.resolution_combo.setFixedWidth(100)
        self.resolution_combo.currentTextChanged.connect(self.set_resolution)

        # Panel Layout Selection
        self.layout_label = QLabel("Layout")
        self.layout_combo = QComboBox()
        self.layout_combo.setFixedWidth(80)
        self.layout_combo.currentTextChanged.connect(self.change_panel_layout)
        
        # Curtain comparison toggle
        self.curtain_checkbox = QCheckBox("Curtain Mode")
        self.curtain_checkbox.setChecked(False)
        self.curtain_checkbox.stateChanged.connect(self.toggle_curtain_mode)
        
        # Diff mode toggle (only available in curtain mode)
        self.diff_checkbox = QCheckBox("Show Differences")
        self.diff_checkbox.setChecked(False)
        self.diff_checkbox.setEnabled(False)  # Will be enabled when exactly 2 images
        self.diff_checkbox.stateChanged.connect(self.toggle_diff_panel)

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
        self.top_settings_layout.addWidget(self.layout_label)
        self.top_settings_layout.addWidget(self.layout_combo)
        self.top_settings_layout.addWidget(self.curtain_checkbox)
        self.top_settings_layout.addWidget(self.diff_checkbox)
        self.top_settings_layout.addWidget(self.antialiasing_checkbox)
        self.top_settings_layout.addWidget(self.calculate_metrics_checkbox)
        self.top_settings_layout.addStretch()

        # Images comparison
        self.images_widget = QWidget()

        # Use QGridLayout for flexible panel arrangement
        self.image_views_layout = QGridLayout()
        self.image_views_layout.setSpacing(0)
        self.images_widget.setLayout(self.image_views_layout)

        # Keep track of the original images widget for restoration
        self.original_images_widget = self.images_widget

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

        self.addLayout(self.top_settings_layout)

        # Image viewing area
        self.addWidget(self.images_widget)
        
        # Bottom bar with folder controls and add/remove buttons
        self.bottom_controls_layout = QHBoxLayout()
        
        # Add folder controls to bottom bar
        self.bottom_controls_layout.addWidget(self.folder_mode_checkbox)
        self.bottom_controls_layout.addWidget(self.select_folder_left_button)
        self.bottom_controls_layout.addWidget(self.select_folder_right_button)
        self.bottom_controls_layout.addWidget(self.prev_button)
        self.bottom_controls_layout.addWidget(self.image_counter_label)
        self.bottom_controls_layout.addWidget(self.next_button)
        
        # Add some space before the +/- buttons
        self.bottom_controls_layout.addStretch()
        
        # Add a label to make the +/- buttons more obvious
        add_remove_label = QLabel("Add/Remove:")
        self.bottom_controls_layout.addWidget(add_remove_label)
        
        # Add the +/- buttons with some spacing
        self.bottom_controls_layout.addWidget(self.remove_button)
        self.bottom_controls_layout.addWidget(self.add_button)
        
        # Add final stretch to balance the layout
        self.bottom_controls_layout.addStretch()
        
        self.addLayout(self.bottom_controls_layout)

        # Add reference to diff panel
        self.diff_panel = None
        self.is_showing_diff_panel = False

    def calculate_layout_options(self, num_panels):
        """Calculate possible grid arrangements for given number of panels"""
        if num_panels <= 0:
            return []
        
        options = []
        
        # Find all divisor pairs
        for rows in range(1, num_panels + 1):
            if num_panels % rows == 0:
                cols = num_panels // rows
                options.append((rows, cols))
        
        # For non-perfect divisions (like 5 panels), add practical arrangements
        if len(options) == 2:  # Only 1xN and Nx1 (prime numbers)
            # Add some practical arrangements for prime numbers
            sqrt_n = int(math.sqrt(num_panels))
            for rows in range(sqrt_n, sqrt_n + 2):
                cols = math.ceil(num_panels / rows)
                if rows * cols >= num_panels and (rows, cols) not in options:
                    options.append((rows, cols))
        
        # Sort by aspect ratio preference (closer to square first)
        options.sort(key=lambda x: abs(x[0] - x[1]))
        
        return options

    def update_layout_combo(self):
        """Update layout dropdown based on current number of panels"""
        num_panels = len(self.image_views)
        self.layout_combo.clear()
        
        if num_panels == 0:
            return
        
        options = self.calculate_layout_options(num_panels)
        
        # Find the 1×n (horizontal) option index
        horizontal_index = 0
        for i, (rows, cols) in enumerate(options):
            if rows == 1:
                label = f"1×{cols} (Horizontal)"
                horizontal_index = i
            elif cols == 1:
                label = f"{rows}×1 (Vertical)"
            else:
                label = f"{rows}×{cols} (Grid)"
            
            self.layout_combo.addItem(label, (rows, cols))
        
        # Set default to horizontal layout (1×n)
        if options:
            self.layout_combo.setCurrentIndex(horizontal_index)

    def change_panel_layout(self):
        """Change the panel layout based on selected option"""
        if not self.layout_combo.currentData():
            return
        
        rows, cols = self.layout_combo.currentData()
        self.arrange_panels_in_grid(rows, cols)

    def arrange_panels_in_grid(self, rows, cols):
        """Arrange panels in specified grid layout"""
        # Remove all widgets from layout
        while self.image_views_layout.count():
            child = self.image_views_layout.takeAt(0)
            if child.layout():
                child.layout().setParent(None)
        
        # Reset stretch factors
        for i in range(self.image_views_layout.columnCount()):
            self.image_views_layout.setColumnStretch(i, 0)
        for i in range(self.image_views_layout.rowCount()):
            self.image_views_layout.setRowStretch(i, 0)
        
        # Add panels to grid layout
        for i, view in enumerate(self.image_views):
            row = i // cols
            col = i % cols
            self.image_views_layout.addLayout(view, row, col)
        
        # Set equal stretch factors for all used columns and rows
        for col in range(cols):
            self.image_views_layout.setColumnStretch(col, 1)
        for row in range(rows):
            self.image_views_layout.setRowStretch(row, 1)

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

        # Insert at the beginning instead of appending at the end
        self.image_views.insert(0, graphics_view)
        
        # Update layout options and curtain availability
        self.update_layout_combo()
        self.update_curtain_availability()
        
        # Rearrange in current layout (only if not in curtain mode)
        if not self.is_curtain_mode and self.layout_combo.currentData():
            rows, cols = self.layout_combo.currentData()
            self.arrange_panels_in_grid(rows, cols)

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

    def load_images(self, items, text_color):
        # Clear existing image views
        while self.image_views:
            view_to_remove = self.image_views.pop()
            self.image_views_layout.removeItem(view_to_remove)
            view_to_remove.image_view.deleteLater()
            view_to_remove.text_view.deleteLater()
            view_to_remove.deleteLater()

        image_paths = [item["path"] for item in items.values()]
        
        # Process items in reverse order since add_image_view inserts at beginning
        items_list = list(items.items())
        for name, details in reversed(items_list):
            color = details.get("color", None)  # Use None if color not specified
            self.add_image_view(
                color=color, name=name, text_color=text_color
            )
            # Since add_image_view inserts at beginning, load image into first panel
            self.image_views[0].image_view.loadImage(details["path"])
            
            # Apply current antialiasing state to the newly loaded image
            antialiasing_enabled = self.antialiasing_checkbox.isChecked()
            self.image_views[0].image_view.set_antialiasing(antialiasing_enabled)

        # Update layout and curtain availability after loading all images
        self.update_layout_combo()
        self.update_curtain_availability()  # This will call update_diff_availability()
        
        # Arrange in grid layout (only if not in curtain mode)
        if not self.is_curtain_mode and self.layout_combo.currentData():
            rows, cols = self.layout_combo.currentData()
            self.arrange_panels_in_grid(rows, cols)

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
        if len(self.image_views) > 0:
            # Don't allow removing the diff panel directly with - button
            if len(self.image_views) == 1 and self.is_showing_diff_panel:
                QMessageBox.information(self.main_window, "Cannot Remove", 
                                      "Cannot remove the last image. Uncheck 'Show Differences' first to remove the difference panel.")
                return
                
            # If removing would leave only the diff panel, remove diff panel first
            non_diff_panels = [view for view in self.image_views if view != self.diff_panel]
            if len(non_diff_panels) == 1 and self.is_showing_diff_panel:
                self.diff_checkbox.blockSignals(True)
                self.diff_checkbox.setChecked(False)
                self.diff_checkbox.blockSignals(False)
                self.remove_diff_panel()
                return
            
            # Remove the first non-diff panel
            for view in self.image_views:
                if view != self.diff_panel:
                    # Remove from layout
                    self.image_views_layout.removeItem(view)
                    view.image_view.deleteLater()
                    view.text_view.deleteLater()
                    view.deleteLater()
                    self.image_views.remove(view)
                    break
            
            self.update_layout_combo()
            if not self.is_curtain_mode and self.layout_combo.currentData():
                rows, cols = self.layout_combo.currentData()
                self.arrange_panels_in_grid(rows, cols)
            
            self.update_curtain_availability()  # This will call update_diff_availability()

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

    def toggle_curtain_mode(self, state):
        """Toggle between curtain comparison mode and grid mode."""
        should_enable_curtain = state == 2  # Qt.Checked
        
        if should_enable_curtain:
            if len(self.image_views) == 2:
                self.switch_to_curtain_mode()
            else:
                # Disable checkbox if not exactly 2 images
                self.curtain_checkbox.blockSignals(True)
                self.curtain_checkbox.setChecked(False)
                self.curtain_checkbox.blockSignals(False)
                QMessageBox.information(
                    self.main_window, 
                    "Curtain Mode", 
                    "Curtain mode requires exactly 2 images.\nPlease add or remove images to have exactly 2 images."
                )
        else:
            self.switch_to_grid_mode()
    
    def toggle_diff_panel(self, state):
        """Toggle the difference panel in grid layout (not curtain mode)."""
        should_show_diff = state == 2
        
        if should_show_diff:
            if len(self.image_views) == 2:
                self.add_diff_panel()
            else:
                # This shouldn't happen as checkbox should be disabled, but just in case
                self.diff_checkbox.blockSignals(True)
                self.diff_checkbox.setChecked(False)
                self.diff_checkbox.blockSignals(False)
                QMessageBox.information(self.main_window, "Show Differences", "Difference panel requires exactly 2 images.")
        else:
            self.remove_diff_panel()

    def add_diff_panel(self):
        """Add a difference panel showing the computed difference between the two images."""
        if self.is_showing_diff_panel or len(self.image_views) != 2:
            return
        
        try:
            # Get paths of the two images
            img1_path = self.image_views[0].image_view.url
            img2_path = self.image_views[1].image_view.url
            
            if not img1_path or not img2_path:
                QMessageBox.warning(self.main_window, "Error", "Both images must be loaded before showing differences.")
                self.diff_checkbox.blockSignals(True)
                self.diff_checkbox.setChecked(False)
                self.diff_checkbox.blockSignals(False)
                return
            
            print("Calculating difference image for grid panel...")
            
            # Calculate difference using our diff calculator
            diff_calc = ImageDiffCalculator()
            diff_pil_image = diff_calc.calculate_diff(img1_path, img2_path)
            
            if diff_pil_image is None:
                QMessageBox.critical(self.main_window, "Error", "Failed to calculate image difference.")
                self.diff_checkbox.blockSignals(True)
                self.diff_checkbox.setChecked(False)
                self.diff_checkbox.blockSignals(False)
                return
            
            # Convert PIL Image to QPixmap
            diff_qt_image = ImageQt(diff_pil_image)
            diff_pixmap = QPixmap.fromImage(diff_qt_image)
            
            # Create a new graphics view for the difference
            self.diff_panel = GraphicsView(color="#e74c3c", name="Differences", text_color="#f9f9f9")
            
            # Set the difference image by directly adding to scene
            if self.diff_panel.image_view.scene().items():
                self.diff_panel.image_view.scene().removeItem(self.diff_panel.image_view.scene().items()[0])
            
            self.diff_panel.image_view.original_image = diff_pixmap
            pixmap_item = self.diff_panel.image_view.scene().addPixmap(diff_pixmap)
            pixmap_item.setTransformationMode(Qt.SmoothTransformation)
            self.diff_panel.image_view.url = f"diff_{len(self.image_views)}"  # Pseudo URL for tracking
            
            # Apply current antialiasing setting
            if hasattr(self, 'antialiasing_checkbox') and self.antialiasing_checkbox:
                self.diff_panel.image_view.set_antialiasing(self.antialiasing_checkbox.isChecked())
            
            # Connect diff panel to scroll synchronization (like other image views)
            self.diff_panel.image_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.diff_panel.image_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.diff_panel.image_view.horizontalScrollBar().valueChanged.connect(
                partial(self.slider_sync, "horizontal")
            )
            self.diff_panel.image_view.verticalScrollBar().valueChanged.connect(
                partial(self.slider_sync, "vertical")
            )
            self.diff_panel.image_view.tranformChanged.connect(self.set_transform)
            
            # Add to image views list and mark as showing
            self.image_views.append(self.diff_panel)
            self.is_showing_diff_panel = True
            
            # Update layout to accommodate 3 panels
            self.update_layout_combo()
            
            # Arrange panels - prefer 1x3 layout for 3 images
            if self.layout_combo.count() > 0:
                # Look for 1x3 layout in combo box
                for i in range(self.layout_combo.count()):
                    data = self.layout_combo.itemData(i)
                    if data and data == (1, 3):
                        self.layout_combo.setCurrentIndex(i)
                        self.arrange_panels_in_grid(1, 3)
                        break
                else:
                    # If no 1x3 found, use the first available layout
                    if self.layout_combo.count() > 0:
                        data = self.layout_combo.itemData(0)
                        if data:
                            rows, cols = data
                            self.arrange_panels_in_grid(rows, cols)
            
            print("Difference panel added successfully")
            
        except Exception as e:
            print(f"Error adding difference panel: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Failed to add difference panel: {str(e)}")
            self.diff_checkbox.blockSignals(True)
            self.diff_checkbox.setChecked(False)
            self.diff_checkbox.blockSignals(False)

    def remove_diff_panel(self):
        """Remove the difference panel from the grid layout."""
        if not self.is_showing_diff_panel or self.diff_panel is None:
            return
        
        try:
            # Find and remove the diff panel
            if self.diff_panel in self.image_views:
                # Disconnect signals to avoid issues
                try:
                    self.diff_panel.image_view.horizontalScrollBar().valueChanged.disconnect()
                    self.diff_panel.image_view.verticalScrollBar().valueChanged.disconnect()
                    self.diff_panel.image_view.tranformChanged.disconnect()
                except Exception:
                    pass  # Ignore disconnection errors
                
                # Clear the scene
                if self.diff_panel.image_view.scene().items():
                    self.diff_panel.image_view.scene().clear()
                
                # Remove from image_views list
                self.image_views.remove(self.diff_panel)
                
                # Clean up the graphics view and text view
                self.diff_panel.image_view.deleteLater()
                self.diff_panel.text_view.deleteLater()
                
                # Clean up
                self.diff_panel = None
                self.is_showing_diff_panel = False
                
                # Update layout for remaining panels
                self.update_layout_combo()
                
                # Re-arrange remaining panels
                if len(self.image_views) > 0 and self.layout_combo.count() > 0:
                    data = self.layout_combo.itemData(0)  # Use first available layout
                    if data:
                        rows, cols = data
                        self.arrange_panels_in_grid(rows, cols)
                
                print("Difference panel removed successfully")
                
        except Exception as e:
            print(f"Error removing difference panel: {e}")

    def switch_to_curtain_mode(self):
        # First remove diff panel if it's showing, since curtain mode has its own diff
        if self.is_showing_diff_panel:
            self.diff_checkbox.blockSignals(True)
            self.diff_checkbox.setChecked(False)
            self.diff_checkbox.blockSignals(False)
            self.remove_diff_panel()
        
        if len(self.image_views) != 2: 
            return
            
        self.is_curtain_mode = True
        if self.curtain_widget: 
            self.curtain_widget.deleteLater()
        
        self.curtain_widget = CurtainComparisonWidget()
        if (len(self.image_views) >= 2 and 
            self.image_views[0].image_view.url and 
            self.image_views[1].image_view.url):
            before_path = self.image_views[0].image_view.url
            after_path = self.image_views[1].image_view.url
            before_name = self.image_views[0].text_view.text()
            after_name = self.image_views[1].text_view.text()
            self.curtain_widget.set_images(before_path, after_path, before_name, after_name)
        
        self.removeWidget(self.images_widget)
        self.images_widget.setParent(None)
        self.insertWidget(1, self.curtain_widget)
        
        # In curtain mode, disable the diff checkbox completely
        self.diff_checkbox.setEnabled(False)
        self.diff_checkbox.setChecked(False)
        
        self.layout_combo.setEnabled(False)
        self.add_button.setEnabled(False)
        self.remove_button.setEnabled(False)

    def switch_to_grid_mode(self):
        self.is_curtain_mode = False
        if self.curtain_widget:
            self.removeWidget(self.curtain_widget)
            self.curtain_widget.deleteLater()
            self.curtain_widget = None
        
        self.insertWidget(1, self.original_images_widget)
        self.images_widget = self.original_images_widget
        
        # Re-arrange in current layout
        if self.layout_combo.currentData():
            rows, cols = self.layout_combo.currentData()
            self.arrange_panels_in_grid(rows, cols)
        
        # In grid mode, restore the diff checkbox functionality
        self.diff_checkbox.setChecked(False)  # Reset state
        
        self.layout_combo.setEnabled(True)
        self.add_button.setEnabled(True)
        self.remove_button.setEnabled(True)
        
        # Update diff checkbox availability
        self.update_diff_availability()

    def update_curtain_availability(self):
        """Update availability of curtain mode and diff panel based on number of images."""
        # Skip updates during image loading to prevent interference with mode restoration
        if self.loading_images:
            return
            
        # Only count non-diff panels for curtain mode availability
        non_diff_panels = [view for view in self.image_views if view != self.diff_panel]
        has_exactly_two = len(non_diff_panels) == 2
        
        self.curtain_checkbox.setEnabled(has_exactly_two)
        
        if not has_exactly_two and self.is_curtain_mode:
            self.curtain_checkbox.blockSignals(True)
            self.curtain_checkbox.setChecked(False)
            self.curtain_checkbox.blockSignals(False)
            self.switch_to_grid_mode()
        elif has_exactly_two and self.curtain_checkbox.isChecked():
            self.switch_to_curtain_mode()
        
        # Update diff availability
        self.update_diff_availability()

    def update_diff_availability(self):
        """Update availability of diff panel based on number of images and mode."""
        if self.is_curtain_mode:
            # In curtain mode, diff is disabled
            self.diff_checkbox.setEnabled(False)
        else:
            # In grid mode, diff is available when exactly 2 non-diff images
            non_diff_panels = [view for view in self.image_views if view != self.diff_panel]
            has_exactly_two = len(non_diff_panels) == 2
            self.diff_checkbox.setEnabled(has_exactly_two)
            
            # If we don't have exactly 2 images, remove diff panel if showing
            if not has_exactly_two and self.is_showing_diff_panel:
                self.diff_checkbox.blockSignals(True)
                self.diff_checkbox.setChecked(False)
                self.diff_checkbox.blockSignals(False)
                self.remove_diff_panel()

    # Folder comparison methods
    def toggle_folder_mode(self, state):
        """Toggle folder comparison mode."""
        self.is_folder_mode = state == Qt.Checked.value
        
        if self.is_folder_mode:
            # Enable folder selection buttons
            self.select_folder_left_button.setEnabled(True)
            self.select_folder_right_button.setEnabled(True)
            
            # Disable other modes
            self.curtain_checkbox.setEnabled(False)
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.layout_combo.setEnabled(False)
            
            # Clear existing images
            self.clear_all_images()
        else:
            # Disable folder controls
            self.select_folder_left_button.setEnabled(False)
            self.select_folder_right_button.setEnabled(False)
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            
            # Re-enable other controls
            self.add_button.setEnabled(True)
            self.remove_button.setEnabled(True)
            self.layout_combo.setEnabled(True)
            
            # Clear folder data
            self.folder_left_path = None
            self.folder_right_path = None
            self.folder_image_list = []
            self.current_folder_index = 0
            self.update_image_counter()
            
            # Update other mode availability
            self.update_curtain_availability()
    
    def select_left_folder(self):
        """Select the left folder for comparison."""
        folder_path = QFileDialog.getExistingDirectory(
            None, "Select Left Folder", 
            self.folder_left_path or os.path.expanduser("~")
        )
        if folder_path:
            self.folder_left_path = folder_path
            self.select_folder_left_button.setText(f"Left: {os.path.basename(folder_path)}")
            self.check_folders_and_load()
    
    def select_right_folder(self):
        """Select the right folder for comparison."""
        folder_path = QFileDialog.getExistingDirectory(
            None, "Select Right Folder",
            self.folder_right_path or os.path.expanduser("~")
        )
        if folder_path:
            self.folder_right_path = folder_path
            self.select_folder_right_button.setText(f"Right: {os.path.basename(folder_path)}")
            self.check_folders_and_load()
    
    def check_folders_and_load(self):
        """Check if both folders are selected and load matching images."""
        if not self.folder_left_path or not self.folder_right_path:
            return
        
        # Get image files from both folders
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif', '*.gif']
        
        left_images = []
        right_images = []
        
        for ext in image_extensions:
            left_images.extend(glob.glob(os.path.join(self.folder_left_path, ext)))
            left_images.extend(glob.glob(os.path.join(self.folder_left_path, ext.upper())))
            right_images.extend(glob.glob(os.path.join(self.folder_right_path, ext)))
            right_images.extend(glob.glob(os.path.join(self.folder_right_path, ext.upper())))
        
        # Sort by filename for consistent ordering
        left_images.sort(key=lambda x: os.path.basename(x).lower())
        right_images.sort(key=lambda x: os.path.basename(x).lower())
        
        if not left_images or not right_images:
            QMessageBox.warning(None, "No Images Found", 
                              "No compatible images found in one or both folders.")
            return
        
        # Create matched pairs (by filename or index)
        self.folder_image_list = self.match_images(left_images, right_images)
        
        if not self.folder_image_list:
            QMessageBox.warning(None, "No Matching Images", 
                              "No matching image pairs found between folders.")
            return
        
        self.current_folder_index = 0
        self.load_current_folder_images()
        self.update_navigation_buttons()
        self.update_image_counter()
    
    def match_images(self, left_images, right_images):
        """Match images from both folders by filename or index."""
        matched_pairs = []
        
        # First try to match by filename (without extension)
        left_basenames = {os.path.splitext(os.path.basename(img))[0]: img for img in left_images}
        right_basenames = {os.path.splitext(os.path.basename(img))[0]: img for img in right_images}
        
        # Find common basenames
        common_names = set(left_basenames.keys()) & set(right_basenames.keys())
        
        if common_names:
            # Match by filename
            for name in sorted(common_names):
                matched_pairs.append((left_basenames[name], right_basenames[name]))
        else:
            # Match by index if no common names
            min_count = min(len(left_images), len(right_images))
            for i in range(min_count):
                matched_pairs.append((left_images[i], right_images[i]))
        
        return matched_pairs
    
    def load_current_folder_images(self):
        """Load the current pair of images from folders."""
        if not self.folder_image_list or self.current_folder_index >= len(self.folder_image_list):
            return
        
        left_path, right_path = self.folder_image_list[self.current_folder_index]
        
        # Remember current curtain mode state before clearing images
        was_in_curtain_mode = self.is_curtain_mode
        
        # Set loading flag to prevent curtain availability updates during loading
        self.loading_images = True
        
        # Clear existing images
        self.clear_all_images()
        
        # Create exactly 2 image views for folder comparison
        left_name = os.path.splitext(os.path.basename(left_path))[0]
        right_name = os.path.splitext(os.path.basename(right_path))[0]
        
        # Use the existing add_image_view method to ensure proper setup
        self.add_image_view(color="#2C3E50", name=f"Left: {left_name}", text_color="#f9f9f9")
        self.add_image_view(color="#00695C", name=f"Right: {right_name}", text_color="#f9f9f9")
        
        # Load the images into the views
        if len(self.image_views) >= 2:
            self.image_views[0].image_view.loadImage(left_path)
            self.image_views[1].image_view.loadImage(right_path)
            
            # Apply current antialiasing setting
            self.image_views[0].image_view.set_antialiasing(self.antialiasing_checkbox.isChecked())
            self.image_views[1].image_view.set_antialiasing(self.antialiasing_checkbox.isChecked())
        
        # Clear loading flag now that we're done loading
        self.loading_images = False
        
        # Enable curtain mode for folder comparison
        self.curtain_checkbox.setEnabled(True)
        
        # If we were in curtain mode before, restore curtain mode with new images
        if was_in_curtain_mode:
            # Make sure the checkbox reflects the curtain mode state
            self.curtain_checkbox.blockSignals(True)
            self.curtain_checkbox.setChecked(True)
            self.curtain_checkbox.blockSignals(False)
            
            # Switch to curtain mode with the new images
            self.switch_to_curtain_mode()
        else:
            # Arrange in 1x2 layout only if not switching to curtain mode
            self.arrange_panels_in_grid(1, 2)
        
        # Note: slider_sync will be handled automatically by the image views
    
    def update_curtain_widget_images(self, left_path, right_path, left_name, right_name):
        """Update the curtain widget with new image paths."""
        if self.curtain_widget:
            self.curtain_widget.set_images(left_path, right_path, f"Left: {left_name}", f"Right: {right_name}")
    
    def navigate_previous(self):
        """Navigate to the previous image pair."""
        if self.current_folder_index > 0:
            self.current_folder_index -= 1
            self.load_current_folder_images()
            self.update_navigation_buttons()
            self.update_image_counter()
    
    def navigate_next(self):
        """Navigate to the next image pair."""
        if self.current_folder_index < len(self.folder_image_list) - 1:
            self.current_folder_index += 1
            self.load_current_folder_images()
            self.update_navigation_buttons()
            self.update_image_counter()
    
    def update_navigation_buttons(self):
        """Update the state of navigation buttons."""
        has_images = len(self.folder_image_list) > 0
        can_go_prev = has_images and self.current_folder_index > 0
        can_go_next = has_images and self.current_folder_index < len(self.folder_image_list) - 1
        
        self.prev_button.setEnabled(can_go_prev)
        self.next_button.setEnabled(can_go_next)
    
    def update_image_counter(self):
        """Update the image counter display."""
        if self.folder_image_list:
            current = self.current_folder_index + 1
            total = len(self.folder_image_list)
            self.image_counter_label.setText(f"{current} / {total}")
        else:
            self.image_counter_label.setText("0 / 0")
    
    def clear_all_images(self):
        """Clear all current image views."""
        # Remove all items from the grid layout
        while self.image_views_layout.count():
            child = self.image_views_layout.takeAt(0)
            if child.layout():
                # If it's a layout, delete it
                self.delete_layout(child.layout())
            elif child.widget():
                # If it's a widget, delete it
                child.widget().deleteLater()
        
        # Clear the image views list
        self.image_views.clear()
        self.is_showing_diff_panel = False
        self.diff_panel = None
    
    def delete_layout(self, layout):
        """Recursively delete a layout and all its children."""
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.layout():
                    self.delete_layout(child.layout())
                elif child.widget():
                    child.widget().deleteLater()
            layout.deleteLater()

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

    def keyPressEvent(self, event):
        """Handle keyboard events for folder navigation."""
        if self.is_folder_mode and self.folder_image_list:
            if event.key() == Qt.Key_Left or event.key() == Qt.Key_A:
                self.navigate_previous()
            elif event.key() == Qt.Key_Right or event.key() == Qt.Key_D:
                self.navigate_next()
            elif event.key() == Qt.Key_Home:
                self.current_folder_index = 0
                self.load_current_folder_images()
                self.update_navigation_buttons()
                self.update_image_counter()
            elif event.key() == Qt.Key_End:
                self.current_folder_index = len(self.folder_image_list) - 1
                self.load_current_folder_images()
                self.update_navigation_buttons()
                self.update_image_counter()
