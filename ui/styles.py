from utils.helpers import resource_path
import os

# Get resource paths and convert backslashes to forward slashes for Qt Style Sheets
ARROW_DOWN = resource_path(os.path.join("assets", "arrow_down.svg")).replace("\\", "/")
ARROW_DOWN_ACTIVE = resource_path(os.path.join("assets", "arrow_down_active.svg")).replace("\\", "/")

# Color Palette
COLORS = {
    "background": "#1e1e2e",       # Deep dark blue/gray
    "surface": "#2a2b3d",          # Slightly lighter for cards (increased contrast)
    "surface_hover": "#3a3c55",    # Hover state for surface
    "primary": "#7aa2f7",          # Bright Blue
    "primary_hover": "#8ab0ff",    # Lighter Blue
    "secondary": "#bb9af7",        # Purple accent
    "text_main": "#c0caf5",        # Light gray/blue text
    "text_dim": "#787c99",         # Dimmed text
    "border": "#3b3b50",           # Border color
    "success": "#9ece6a",          # Green
    "error": "#f7768e",            # Red
    "warning": "#e0af68",          # Orange/Yellow
    "input_bg": "#181825"          # Darker for inputs
}

APP_STYLE = f"""
/* Global Reset */
QWidget {{
    color: {COLORS['text_main']};
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
}}

/* Main Window & Dialog Backgrounds */
QMainWindow, QDialog {{
    background-color: {COLORS['background']};
}}

/* Make Labels Transparent (Fixes 'Shadow' artifact) */
QLabel {{
    background-color: transparent;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: {COLORS['background']};
    width: 8px;
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['primary']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Tooltips */
QToolTip {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_main']};
    border: 1px solid {COLORS['border']};
    padding: 5px;
}}

/* Generic QFrame as Card */
QFrame.CardFrame {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}

/* Buttons */
QPushButton {{
    background-color: #3b3d5c; /* Lighter background for better visibility */
    border: 1px solid #565f89; /* More visible border */
    color: {COLORS['text_main']};
    padding: 0px 16px;
    min-height: 36px;
    border-radius: 8px;
    font-weight: 600;
    text-align: center;
    outline: none;
}}
QPushButton:hover {{
    background-color: #444b6a;
    border-color: {COLORS['primary']};
}}
QPushButton:pressed {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
}}
QPushButton:disabled {{
    background-color: {COLORS['background']};
    color: {COLORS['text_dim']};
    border-color: {COLORS['border']};
}}

/* Primary Action Button */
QPushButton.PrimaryButton {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
    border: none;
    padding: 0px 20px;
    min-height: 36px;
}}
QPushButton.PrimaryButton:hover {{
    background-color: {COLORS['primary_hover']};
}}

/* Outline Button (Secondary) */
QPushButton.OutlineButton {{
    background-color: transparent;
    border: 1px solid {COLORS['primary']};
    color: {COLORS['primary']};
    padding: 0px 16px;
}}
QPushButton.OutlineButton:hover {{
    background-color: rgba(122, 162, 247, 0.1);
    border-color: {COLORS['primary_hover']};
}}
QPushButton.OutlineButton:pressed {{
    background-color: rgba(122, 162, 247, 0.2);
}}
/* Inputs */
QLineEdit, QTextEdit {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 10px;
    color: {COLORS['text_main']};
    selection-background-color: {COLORS['primary']};
    selection-color: {COLORS['background']};
}}
QLineEdit:focus, QTextEdit:focus {{
    border: 1px solid {COLORS['primary']};
}}

/* Progress Bar */
QProgressBar {{
    background-color: {COLORS['input_bg']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 4px;
}}

/* Labels */
QLabel.Header {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['text_main']};
}}
QLabel.SubHeader {{
    font-size: 16px;
    font-weight: 700;
    color: {COLORS['text_main']};
}}

/* Custom Title Bar */
QFrame#TitleBar {{
    background-color: {COLORS['background']};
    border-bottom: 1px solid {COLORS['border']};
}}
QPushButton.TitleBarButton {{
    background-color: transparent;
    border: none;
    border-radius: 0;
    padding: 5px;
}}
QPushButton.TitleBarButton:hover {{
    background-color: {COLORS['surface']};
}}
QPushButton#CloseButton:hover {{
    background-color: {COLORS['error']};
    color: white;
}}

/* Sidebar */
QFrame#Sidebar {{
    background-color: {COLORS['input_bg']};
    border-right: 1px solid {COLORS['border']};
}}

QPushButton.SidebarButton {{
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-radius: 0px;
    background-color: transparent;
    color: {COLORS['text_dim']};
    font-size: 15px;
}}
QPushButton.SidebarButton:hover {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_main']};
}}
QPushButton.SidebarButton:checked {{
    background-color: {COLORS['surface']};
    color: {COLORS['primary']};
    border-left: 3px solid {COLORS['primary']};
    font-weight: bold;
}}

/* List Widget */
QListWidget {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 5px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px;
    border-radius: 6px;
    color: {COLORS['text_main']};
}}
QListWidget::item:selected {{
    background-color: {COLORS['surface_hover']};
    color: {COLORS['primary']};
    border: 1px solid {COLORS['primary']};
}}
QListWidget::item:hover {{
    background-color: {COLORS['surface']};
}}

/* ComboBox */
QComboBox {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    min-width: 80px;
    color: {COLORS['text_main']};
    /* Fix for popup covering the box and styling issues */
    combobox-popup: 0; 
}}

QComboBox:hover {{
    border-color: {COLORS['primary']};
    background-color: {COLORS['surface']};
}}

QComboBox:on {{ /* When popup is open */
    border-color: {COLORS['primary']};
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left: 1px solid {COLORS['border']}; /* Separator line */
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: transparent;
}}

QComboBox::down-arrow {{
    image: url({ARROW_DOWN});
    width: 14px;
    height: 14px;
    margin-right: 8px;
}}

QComboBox::down-arrow:hover, QComboBox::down-arrow:on {{
    image: url({ARROW_DOWN_ACTIVE});
}}

/* The Popup List */
QComboBox QAbstractItemView {{
    background-color: {COLORS['input_bg']};
    border: 1px solid {COLORS['border']};
    border-top: none;
    selection-background-color: {COLORS['surface_hover']};
    selection-color: {COLORS['text_main']};
    outline: 0;
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
    padding: 4px;
}}

QComboBox QAbstractItemView::item {{
    min-height: 25px;
    padding: 4px 8px;
    border-radius: 4px;
    color: {COLORS['text_main']};
}}

QComboBox QAbstractItemView::item:hover {{
    background-color: {COLORS['surface_hover']};
    color: {COLORS['primary']};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {COLORS['primary']};
    color: {COLORS['background']};
}}

/* Splitter */
QSplitter::handle {{
    background-color: {COLORS['border']};
}}
QSplitter::handle:hover {{
    background-color: {COLORS['primary']};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}
"""
