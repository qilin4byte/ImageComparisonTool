from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtWidgets import QWidget, QLabel, QSlider
from PySide6.QtGui import QPixmap, QPainter, QFont, QPen, QBrush
from PySide6.QtCore import Qt, Signal, QRect
import math


class CurtainComparisonWidget(QWidget):
    """
    A widget that provides before/after comparison with a draggable curtain slider.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.before_image = None
        self.after_image = None
        self.before_name = "Before"
        self.after_name = "After"
        self.text_color = "white"
        
        # Slider position (0.0 to 1.0, where 0.5 is center)
        self.slider_position = 0.5
        self.dragging_slider = False
        
        # View transformation (similar to QGraphicsView)
        self.view_scale = 1.0  # This is the zoom level
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.dragging_image = False
        self.last_mouse_pos = None
        
        self.setMinimumSize(400, 300)
        
        # Set black background to ensure no grid shows through
        self.setStyleSheet("CurtainComparisonWidget { background-color: black; }")
        self.setAutoFillBackground(True)
        
        # Ensure widget expands to fill available space
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Enable mouse tracking for better interaction
        self.setMouseTracking(True)
        
        # Enable keyboard focus for shortcuts
        self.setFocusPolicy(Qt.StrongFocus)
    
    def set_images(self, before_path, after_path, before_name="Before", after_name="After"):
        """Load the before and after images."""
        try:
            # Load before image
            before_img = Image.open(before_path)
            before_qt = ImageQt(before_img)
            self.before_image = QPixmap.fromImage(before_qt)
            
            # Load after image
            after_img = Image.open(after_path)
            after_qt = ImageQt(after_img)
            self.after_image = QPixmap.fromImage(after_qt)
            
            self.before_name = before_name
            self.after_name = after_name
            
            self.update()
            
        except Exception as e:
            print(f"Error loading images for curtain comparison: {e}")
    
    def set_text_color(self, color):
        """Set the color for the labels."""
        self.text_color = color
        self.update()
    
    def paintEvent(self, event):
        """Paint the curtain comparison with pixel-perfect zoom."""
        painter = QPainter(self)
        
        # Set rendering hints based on zoom level for pixel-perfect display
        if self.view_scale > 1.0:
            # When zoomed in, disable smooth scaling to show individual pixels
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        else:
            # When zoomed out, use smooth scaling for better appearance
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        widget_rect = self.rect()
        
        # Fill the entire background with black to hide any grid background
        painter.fillRect(widget_rect, QBrush(Qt.black))
        
        if not self.before_image or not self.after_image:
            # Draw placeholder text if no images loaded
            painter.setPen(QPen(Qt.white, 1))
            font = QFont("Arial", 16)
            painter.setFont(font)
            painter.drawText(widget_rect, Qt.AlignCenter, "Load exactly 2 images to use Curtain Mode")
            return
            
        # Get original image sizes
        before_size = self.before_image.size()
        after_size = self.after_image.size()
        
        # Use the larger dimensions for consistent display
        max_width = max(before_size.width(), after_size.width())
        max_height = max(before_size.height(), after_size.height())
        
        # Calculate base fit-to-screen scale (this is just for initial positioning)
        base_scale_x = widget_rect.width() / max_width
        base_scale_y = widget_rect.height() / max_height
        base_scale = min(base_scale_x, base_scale_y)
        
        # Calculate the "virtual" image dimensions (what would fit on screen at 1x zoom)
        virtual_width = max_width * base_scale
        virtual_height = max_height * base_scale
        
        # Calculate actual display size with zoom applied
        display_width = virtual_width * self.view_scale
        display_height = virtual_height * self.view_scale
        
        # Calculate position with centering and pan offset
        x_offset = (widget_rect.width() - display_width) / 2 + self.view_offset_x
        y_offset = (widget_rect.height() - display_height) / 2 + self.view_offset_y
        
        # Create the destination rectangle
        dest_rect = QRect(int(x_offset), int(y_offset), int(display_width), int(display_height))
        
        # Draw the after image (background) - use original pixmap with pixel-perfect scaling
        painter.drawPixmap(dest_rect, self.after_image)
        
        # Calculate curtain position
        curtain_x = x_offset + display_width * self.slider_position
        
        # Draw the before image (clipped by curtain) - use original pixmap with pixel-perfect scaling
        if self.slider_position > 0 and curtain_x > x_offset:
            # Create clipped destination rectangle for before image
            before_dest_width = curtain_x - x_offset
            before_dest_rect = QRect(int(x_offset), int(y_offset), int(before_dest_width), int(display_height))
            
            # Create corresponding source rectangle from the original image
            # This maintains pixel accuracy by taking the exact pixel slice
            source_width_ratio = self.slider_position
            before_source_rect = QRect(0, 0, int(self.before_image.width() * source_width_ratio), self.before_image.height())
            
            # Draw the clipped before image with pixel-perfect scaling
            painter.drawPixmap(before_dest_rect, self.before_image, before_source_rect)
        
        # Reset rendering hints for UI elements (always use smooth rendering for UI)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # Only draw curtain line and handle if images are visible in the current view
        if (x_offset < widget_rect.width() and y_offset < widget_rect.height() and 
            x_offset + display_width > 0 and y_offset + display_height > 0):
            
            # Draw the curtain line
            painter.setPen(QPen(Qt.white, 3))
            curtain_top = max(y_offset, 0)
            curtain_bottom = min(y_offset + display_height, widget_rect.height())
            painter.drawLine(int(curtain_x), int(curtain_top), int(curtain_x), int(curtain_bottom))
            
            # Draw the slider handle (circle) - only if curtain line is visible
            if (curtain_x >= 0 and curtain_x <= widget_rect.width()):
                handle_radius = 20
                handle_center_y = y_offset + display_height / 2
                
                # Clamp handle to visible area
                handle_center_y = max(handle_radius, min(handle_center_y, widget_rect.height() - handle_radius))
                
                # Handle background
                painter.setBrush(QBrush(Qt.white))
                painter.setPen(QPen(Qt.black, 2))
                painter.drawEllipse(int(curtain_x - handle_radius), int(handle_center_y - handle_radius), 
                                  handle_radius * 2, handle_radius * 2)
                
                # Handle arrows
                painter.setPen(QPen(Qt.black, 2))
                # Left arrow
                painter.drawLine(int(curtain_x - 8), int(handle_center_y), int(curtain_x - 3), int(handle_center_y - 5))
                painter.drawLine(int(curtain_x - 8), int(handle_center_y), int(curtain_x - 3), int(handle_center_y + 5))
                # Right arrow  
                painter.drawLine(int(curtain_x + 8), int(handle_center_y), int(curtain_x + 3), int(handle_center_y - 5))
                painter.drawLine(int(curtain_x + 8), int(handle_center_y), int(curtain_x + 3), int(handle_center_y + 5))
        
        # Draw labels with better visibility (only if images are in view)
        if (x_offset < widget_rect.width() and y_offset < widget_rect.height() and 
            x_offset + display_width > 0 and y_offset + display_height > 0):
            
            font = QFont("Arial", 14, QFont.Bold)
            painter.setFont(font)
            
            # Before label (top-left)
            if self.slider_position > 0.15:  # Only show if there's enough space
                label_x = max(x_offset + 10, 10)
                label_y = max(y_offset + 10, 10)
                before_rect = QRect(int(label_x), int(label_y), 100, 30)
                painter.fillRect(before_rect, QBrush(Qt.black))
                painter.setPen(QPen(Qt.white, 1))
                painter.drawText(before_rect, Qt.AlignCenter, self.before_name)
            
            # After label (top-right)
            if self.slider_position < 0.85:  # Only show if there's enough space
                label_x = min(x_offset + display_width - 110, widget_rect.width() - 110)
                label_y = max(y_offset + 10, 10)
                after_rect = QRect(int(label_x), int(label_y), 100, 30)
                painter.fillRect(after_rect, QBrush(Qt.black))
                painter.setPen(QPen(Qt.white, 1))
                painter.drawText(after_rect, Qt.AlignCenter, self.after_name)
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        if not self.before_image or not self.after_image:
            return
            
        # Get mouse position for zoom center
        mouse_pos = event.position()
        
        # Calculate zoom factor
        zoom_delta = event.angleDelta().y() / 120.0  # Standard wheel delta
        zoom_factor_change = 1.1 if zoom_delta > 0 else 1.0 / 1.1
        
        old_zoom = self.view_scale
        self.view_scale *= zoom_factor_change
        
        # Limit zoom range
        self.view_scale = max(0.1, min(self.view_scale, 10.0))
        
        # Adjust pan to zoom towards mouse position
        if old_zoom != self.view_scale:
            widget_rect = self.rect()
            center_x = widget_rect.width() / 2
            center_y = widget_rect.height() / 2
            
            # Calculate offset from center
            offset_x = mouse_pos.x() - center_x
            offset_y = mouse_pos.y() - center_y
            
            # Adjust pan to keep mouse position stable during zoom
            zoom_ratio = self.view_scale / old_zoom - 1
            self.view_offset_x -= offset_x * zoom_ratio
            self.view_offset_y -= offset_y * zoom_ratio
        
        self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging slider or panning image."""
        if event.button() == Qt.LeftButton:
            mouse_x = event.position().x()
            
            # Check if we're clicking on the slider handle
            if self.is_on_slider_handle(mouse_x, event.position().y()):
                self.dragging_slider = True
                self.update_slider_position(mouse_x)
            else:
                # Start image panning
                self.dragging_image = True
                self.last_mouse_pos = event.position()
        elif event.button() == Qt.RightButton:
            # Right click to reset zoom and pan
            self.view_scale = 1.0
            self.view_offset_x = 0
            self.view_offset_y = 0
            self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging slider or panning image."""
        if self.dragging_slider:
            self.update_slider_position(event.position().x())
        elif self.dragging_image and self.last_mouse_pos:
            # Pan the image
            delta_x = event.position().x() - self.last_mouse_pos.x()
            delta_y = event.position().y() - self.last_mouse_pos.y()
            
            self.view_offset_x += delta_x
            self.view_offset_y += delta_y
            
            self.last_mouse_pos = event.position()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self.dragging_slider = False
            self.dragging_image = False
            self.last_mouse_pos = None
    
    def is_on_slider_handle(self, mouse_x, mouse_y):
        """Check if mouse position is on the slider handle."""
        if not self.before_image or not self.after_image:
            return False
            
        widget_rect = self.rect()
        
        # Calculate image dimensions and position (same logic as paintEvent)
        before_size = self.before_image.size()
        after_size = self.after_image.size()
        max_width = max(before_size.width(), after_size.width())
        max_height = max(before_size.height(), after_size.height())
        
        # Calculate base fit-to-screen scale
        base_scale_x = widget_rect.width() / max_width
        base_scale_y = widget_rect.height() / max_height
        base_scale = min(base_scale_x, base_scale_y)
        
        # Calculate virtual and display dimensions
        virtual_width = max_width * base_scale
        virtual_height = max_height * base_scale
        display_width = virtual_width * self.view_scale
        display_height = virtual_height * self.view_scale
        
        # Calculate position
        x_offset = (widget_rect.width() - display_width) / 2 + self.view_offset_x
        y_offset = (widget_rect.height() - display_height) / 2 + self.view_offset_y
        
        # Calculate curtain and handle position
        curtain_x = x_offset + display_width * self.slider_position
        handle_center_y = y_offset + display_height / 2
        handle_center_y = max(20, min(handle_center_y, widget_rect.height() - 20))
        
        # Check if mouse is within handle area (20px radius)
        handle_radius = 20
        distance = ((mouse_x - curtain_x) ** 2 + (mouse_y - handle_center_y) ** 2) ** 0.5
        return distance <= handle_radius
    
    def update_slider_position(self, x):
        """Update slider position based on mouse x coordinate."""
        if not self.before_image or not self.after_image:
            return
            
        widget_rect = self.rect()
        
        # Calculate image area (same logic as paintEvent)
        before_size = self.before_image.size()
        after_size = self.after_image.size()
        max_width = max(before_size.width(), after_size.width())
        max_height = max(before_size.height(), after_size.height())
        
        # Calculate base fit-to-screen scale
        base_scale_x = widget_rect.width() / max_width
        base_scale_y = widget_rect.height() / max_height
        base_scale = min(base_scale_x, base_scale_y)
        
        # Calculate virtual and display dimensions
        virtual_width = max_width * base_scale
        display_width = virtual_width * self.view_scale
        
        # Calculate position
        x_offset = (widget_rect.width() - display_width) / 2 + self.view_offset_x
        
        # Convert x coordinate to slider position
        relative_x = x - x_offset
        self.slider_position = max(0.0, min(1.0, relative_x / display_width))
        
        self.update()
    
    def reset_view(self):
        """Reset zoom and pan to default values."""
        self.view_scale = 1.0
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.update()
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_R or (event.key() == Qt.Key_0 and event.modifiers() & Qt.ControlModifier):
            # R key or Ctrl+0 to reset view
            self.reset_view()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            # Plus key to zoom in
            self.view_scale *= 1.2
            self.view_scale = min(self.view_scale, 10.0)
            self.update()
        elif event.key() == Qt.Key_Minus:
            # Minus key to zoom out
            self.view_scale /= 1.2
            self.view_scale = max(self.view_scale, 0.1)
            self.update()
        else:
            super().keyPressEvent(event) 