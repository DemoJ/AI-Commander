from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QHBoxLayout, QFileDialog)
from utils.config import ConfigManager
from ui.styles import APP_STYLE
from ui.custom_widgets import ModernButton

class SettingsDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.config = config_manager
        self.resize(500, 350)
        self.init_ui()
        self.setStyleSheet(APP_STYLE)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Base URL
        layout.addWidget(QLabel("Base URL (API 地址):"))
        self.base_url_input = QLineEdit(self.config.get("base_url"))
        layout.addWidget(self.base_url_input)

        # API Key
        layout.addWidget(QLabel("API Key (密钥):"))
        self.api_key_input = QLineEdit(self.config.get("api_key"))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.api_key_input)

        # Model Name
        layout.addWidget(QLabel("模型名称:"))
        self.model_input = QLineEdit(self.config.get("model_name"))
        layout.addWidget(self.model_input)

        # FFmpeg Path
        layout.addWidget(QLabel("FFmpeg 路径:"))
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_input = QLineEdit(self.config.get("ffmpeg_path"))
        ffmpeg_layout.addWidget(self.ffmpeg_input)
        
        self.browse_btn = ModernButton("📂 浏览")
        self.browse_btn.clicked.connect(self.browse_ffmpeg)
        self.browse_btn.setFixedWidth(80)
        ffmpeg_layout.addWidget(self.browse_btn)
        
        layout.addLayout(ffmpeg_layout)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = ModernButton("💾 保存", is_primary=True)
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = ModernButton("❌ 取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 FFmpeg 可执行文件", "", "可执行文件 (*.exe);;所有文件 (*)")
        if path:
            self.ffmpeg_input.setText(path)

    def save_settings(self):
        new_config = {
            "base_url": self.base_url_input.text().strip(),
            "api_key": self.api_key_input.text().strip(),
            "model_name": self.model_input.text().strip(),
            "ffmpeg_path": self.ffmpeg_input.text().strip()
        }
        self.config.save_config(new_config)
        self.accept()