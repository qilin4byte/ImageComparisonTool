import random

from PySide6.QtGui import QFont, Qt
from PySide6.QtWidgets import QVBoxLayout, QLineEdit, QGraphicsDropShadowEffect

from image_view import ImageView


class GraphicsView(QVBoxLayout):
    def __init__(self, color=None, name="", text_color="white"):
        super().__init__()
        self.text_view = QLineEdit()
        self.text_view.setText(name)
        if color is None:
            color = random.choice(
                [
                    "#6E2C00",  # roasted sienna → for Input
                    "#004D40",  # forest cyan → for Output
                    "#512E5F",  # plum → for GT
                    "#2C3E50",  # dark slate blue
                    "#00695C",  # deep teal
                    "#6A1B9A",  # rich purple
                    "#BF360C",  # burnt orange
                    "#37474F",  # dark grey blue
                    "#4E342E",  # deep chocolate
                    "#1A237E",  # indigo night
                    "#3E2723",  # espresso brown
                    "#5D4037",  # warm brown
                    "#264653",  # dark ocean blue
                    "#3D405B",  # stormy navy
                    "#1C2833",  # blackened steel
                    "#2E4053",  # twilight grey blue
                    "#3B3B58",  # gothic indigo
                    "#4A148C",  # dark royal violet
                    "#0D47A1",  # navy cobalt
                    "#1B5E20",  # deep forest green
                    "#311B92",  # deep indigo
                    "#263238",  # charcoal black
                    "#3F3F3F",  # neutral gunmetal
                    "#1C1C1C",  # almost black
                    "#7B241C",  # rich red brown (NEW — matches red detail in image)
                    "#512D38",  # muted wine (NEW — elegant reddish tone)
                ]
            )
        font = QFont("Arial")  # Use a more commonly available font
        font.setBold(True)
        font.setPointSize(16)  # Slightly larger font size for better readability
        self.text_view.setFont(font)
        self.text_view.setStyleSheet(
            f"background-color: {color}; color: {text_color};"
            "padding: 10px;"  # Add padding around text
            "border-top: 1px solid rgba(255, 255, 255, 0.2);"  # Add highlight line
        )
        self.text_view.setAlignment(Qt.AlignCenter)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(Qt.black)
        self.text_view.setGraphicsEffect(shadow)

        self.image_view = ImageView()
        self.addWidget(self.image_view)
        self.addWidget(self.text_view)
        self.setSpacing(0)
