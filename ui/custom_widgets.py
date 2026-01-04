from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QHBoxLayout, 
                             QFrame, QVBoxLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent, QMouseEvent, QPixmap

class CardFrame(QFrame):
    """A container with a background, border, and optional shadow."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "CardFrame") # For QSS styling
        
        # Optional: Add shadow
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(15)
        # shadow.setXOffset(0)
        # shadow.setYOffset(4)
        # shadow.setColor(QColor(0, 0, 0, 80))
        # self.setGraphicsEffect(shadow)

class ModernButton(QPushButton):
    """A styled button."""
    def __init__(self, text, parent=None, is_primary=False):
        super().__init__(text, parent)
        if is_primary:
            self.setProperty("class", "PrimaryButton")

class CustomTitleBar(QFrame):
    """Custom title bar for frameless window."""
    settingsClicked = pyqtSignal()

    def __init__(self, parent=None, title="AI-Commander"):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(40)
        self._parent = parent
        self._start_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 0, 0)
        layout.setSpacing(10)

        # Icon
        self.icon_label = QLabel()
        pixmap = QPixmap("assets/icon.png")
        if not pixmap.isNull():
             self.icon_label.setPixmap(pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.icon_label)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; color: #c0caf5; font-size: 14px;")
        layout.addWidget(self.title_label)
        
        layout.addStretch()

        # Settings Button
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setToolTip("设置")
        self.btn_settings.setProperty("class", "TitleBarButton")
        self.btn_settings.setFixedSize(45, 40)
        self.btn_settings.clicked.connect(self.settingsClicked.emit)
        layout.addWidget(self.btn_settings)

        # Window Controls
        self.btn_min = QPushButton("—")
        self.btn_min.setObjectName("MinButton")
        self.btn_min.setProperty("class", "TitleBarButton")
        self.btn_min.setFixedSize(45, 40)
        self.btn_min.clicked.connect(self.minimize_window)
        
        self.btn_max = QPushButton("□") 
        self.btn_max.setObjectName("MaxButton")
        self.btn_max.setProperty("class", "TitleBarButton")
        self.btn_max.setFixedSize(45, 40)
        self.btn_max.clicked.connect(self.maximize_window)

        self.btn_close = QPushButton("×")
        self.btn_close.setObjectName("CloseButton")
        self.btn_close.setProperty("class", "TitleBarButton")
        self.btn_close.setFixedSize(45, 40)
        self.btn_close.clicked.connect(self.close_window)

        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._start_pos and self._parent:
            delta = event.globalPosition().toPoint() - self._start_pos
            self._parent.move(self._parent.pos() + delta)
            self._start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._start_pos = None

    def minimize_window(self):
        if self._parent:
            self._parent.showMinimized()

    def maximize_window(self):
        if self._parent:
            if self._parent.isMaximized():
                self._parent.showNormal()
            else:
                self._parent.showMaximized()

    def close_window(self):
        if self._parent:
            self._parent.close()

class DropLabel(QLabel):
    fileDropped = pyqtSignal(list)
    clicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        # Initial Style
        self.default_style = """
            QLabel {
                border: 2px dashed #3b3b50;
                border-radius: 12px;
                background-color: #252535;
                color: #787c99;
                font-weight: bold;
                font-size: 16px;
            }
            QLabel:hover {
                border-color: #7aa2f7;
                background-color: #2f2f45;
                color: #c0caf5;
            }
        """
        self.active_style = """
            QLabel {
                border: 2px solid #7aa2f7;
                border-radius: 12px;
                background-color: #2f2f45;
                color: #c0caf5;
                font-weight: bold;
                font-size: 16px;
            }
        """
        self.setStyleSheet(self.default_style)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(self.active_style)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.default_style)

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.fileDropped.emit(files)
            self.setStyleSheet(self.active_style)
        else:
            self.setStyleSheet(self.default_style)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
