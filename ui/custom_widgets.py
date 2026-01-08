from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QHBoxLayout, 
                             QFrame, QVBoxLayout, QGraphicsDropShadowEffect, QProgressBar, QStackedWidget,
                             QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QAbstractAnimation
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent, QMouseEvent, QPixmap
from utils.helpers import resource_path

class CardFrame(QFrame):
    """A container with a background, border, and optional shadow."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "CardFrame") # For QSS styling
        
        # Shadow effect removed to prevent QPainter conflicts with AnimatedStackedWidget
        # shadow = QGraphicsDropShadowEffect(self)
        # ...

class AnimatedStackedWidget(QStackedWidget):
    """A QStackedWidget with fade transition animation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fade_duration = 300
        self.fade_curve = QEasingCurve.Type.OutCubic
        self._is_animating = False

    def setCurrentIndex(self, index):
        if index == self.currentIndex() or self._is_animating:
            return

        current_widget = self.currentWidget()
        next_widget = self.widget(index)
        
        if not current_widget:
            super().setCurrentIndex(index)
            return

        self._is_animating = True
        
        # Prepare next widget
        next_widget.setVisible(True)
        next_widget.raise_()
        # Set geometry to cover the area (in case it wasn't)
        next_widget.setGeometry(self.rect())

        # Effects
        self.effect_out = QGraphicsOpacityEffect(current_widget)
        self.effect_in = QGraphicsOpacityEffect(next_widget)
        current_widget.setGraphicsEffect(self.effect_out)
        next_widget.setGraphicsEffect(self.effect_in)
        
        self.effect_out.setOpacity(1.0)
        self.effect_in.setOpacity(0.0)

        # Animations
        self.anim_out = QPropertyAnimation(self.effect_out, b"opacity")
        self.anim_out.setDuration(self.fade_duration)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(self.fade_curve)

        self.anim_in = QPropertyAnimation(self.effect_in, b"opacity")
        self.anim_in.setDuration(self.fade_duration)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(self.fade_curve)

        # Group
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.anim_out)
        self.anim_group.addAnimation(self.anim_in)
        
        def on_finished():
            current_widget.setGraphicsEffect(None)
            next_widget.setGraphicsEffect(None)
            current_widget.hide()
            super(AnimatedStackedWidget, self).setCurrentIndex(index)
            self._is_animating = False
            # Clean up references to avoid GC issues during callback
            self.anim_group = None
            self.anim_out = None
            self.anim_in = None
            self.effect_out = None
            self.effect_in = None

        self.anim_group.finished.connect(on_finished)
        self.anim_group.start()

class ModernButton(QPushButton):
    """A styled button."""
    def __init__(self, text, parent=None, is_primary=False):
        super().__init__(text, parent)
        if is_primary:
            self.setProperty("class", "PrimaryButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

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
        pixmap = QPixmap(resource_path("assets/icon.png"))
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

class TaskItemWidget(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Top row: Title and Status
        top_row = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #c0caf5; font-weight: bold;")
        top_row.addWidget(self.title_label)
        
        top_row.addStretch()
        
        self.status_label = QLabel("等待中")
        self.status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        top_row.addWidget(self.status_label)
        
        layout.addLayout(top_row)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #1a1b26;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #7aa2f7;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

    def set_progress(self, value):
        self.progress_bar.setValue(int(value))

    def set_status(self, status, color="#565f89"):
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    def set_active(self, active=True):
        if active:
            self.setStyleSheet("background-color: #2f2f45; border-radius: 6px;")
        else:
            self.setStyleSheet("background-color: transparent;")