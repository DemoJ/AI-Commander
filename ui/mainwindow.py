import sys
import os
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTextEdit, QLineEdit, 
                             QFileDialog, QProgressBar, QMessageBox, QFrame,
                             QSizeGrip, QListWidget, QStackedWidget, QListWidgetItem,
                             QMenu, QButtonGroup, QSplitter, QComboBox, QTabWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QIcon, QDragEnterEvent, QDropEvent, QMouseEvent, QAction, QCursor

from ui.settings_dialog import SettingsDialog
from utils.config import ConfigManager
from utils.helpers import resource_path
from core.ai_service import AIService
from core.ffmpeg_runner import FFmpegRunner

# Import Custom Components
from ui.custom_widgets import CustomTitleBar, CardFrame, ModernButton, DropLabel, TaskItemWidget, AnimatedStackedWidget
from ui.styles import APP_STYLE

class AIWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, ai_service, input_files, requirement):
        super().__init__()
        self.ai_service = ai_service
        self.input_files = input_files
        self.requirement = requirement

    def run(self):
        try:
            # Returns a list of lists of args
            commands = self.ai_service.generate_commands(self.input_files, self.requirement)
            self.finished.emit(commands)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(900, 700) 
        self.setWindowIcon(QIcon(resource_path("assets/icon.png")))
        
        self.config = ConfigManager()
        self.ai_service = AIService(self.config)
        self.ffmpeg_runner = None
        self.generated_commands = []
        self.input_files = [] 
        
        # State tracking
        self.unlocked_step = 0 # 0: Files, 1: Task, 2: Exec

        self.init_ui()
        self.setStyleSheet(APP_STYLE)

    def init_ui(self):
        # Root Widget & Layout
        self.root_widget = QWidget()
        self.setCentralWidget(self.root_widget)
        self.root_layout = QVBoxLayout(self.root_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # 1. Custom Title Bar
        self.title_bar = CustomTitleBar(self, "AI-Commander")
        self.title_bar.settingsClicked.connect(self.open_settings)
        self.root_layout.addWidget(self.title_bar)

        # 2. Step Indicator (Interactive)
        self.step_container = QWidget()
        self.step_container.setFixedHeight(60)
        step_layout = QHBoxLayout(self.step_container)
        step_layout.setContentsMargins(40, 0, 40, 0)
        step_layout.setSpacing(10)
        
        self.step_buttons = []
        steps = ["1. 导入素材", "2. 定义任务", "3. 执行预览"]
        for i, text in enumerate(steps):
            btn = QPushButton(text)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("text-align: left; padding: 5px; font-weight: bold; font-size: 16px;")
            # Use lambda with default arg to capture 'i' correctly
            btn.clicked.connect(lambda checked, idx=i: self.on_step_clicked(idx))
            
            step_layout.addWidget(btn)
            self.step_buttons.append(btn)

            if i < len(steps) - 1:
                arrow = QLabel(">")
                arrow.setStyleSheet("color: #3b3b50; font-size: 16px; margin: 0 5px;")
                step_layout.addWidget(arrow)
            
        step_layout.addStretch()
        self.root_layout.addWidget(self.step_container)

        # 3. Content Area (Stacked)
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(20, 0, 20, 20)
        
        self.content_stack = AnimatedStackedWidget()
        content_layout.addWidget(self.content_stack)
        self.root_layout.addWidget(content_area)

        # Page 1: Files
        self.page_files = self.init_page_files()
        self.content_stack.addWidget(self.page_files)

        # Page 2: Task
        self.page_task = self.init_page_task()
        self.content_stack.addWidget(self.page_task)

        # Page 3: Execution
        self.page_exec = self.init_page_exec()
        self.content_stack.addWidget(self.page_exec)

        # Initial State
        self.update_step_indicator()
        self.content_stack.setCurrentIndex(0)

    # --- Navigation Logic ---

    def on_step_clicked(self, index):
        # Only allow navigation if the step is unlocked
        if index <= self.unlocked_step:
            self.switch_page(index)

    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        self.update_step_indicator()

    def update_step_indicator(self):
        current = self.content_stack.currentIndex()
        
        colors = {
            "active": "#7aa2f7",    # Blue
            "completed": "#9ece6a", # Green
            "locked": "#565f89"     # Dim
        }

        for i, btn in enumerate(self.step_buttons):
            # Determine state
            if i == current:
                color = colors["active"]
            elif i < current:
                color = colors["completed"]
            else:
                # If it's a future step, check if it's unlocked
                if i <= self.unlocked_step:
                     color = colors["completed"] # Unlocked but not active (viewing previous)
                else:
                    color = colors["locked"]
            
            # Apply style
            # Locked steps shouldn't look clickable
            if i > self.unlocked_step:
                btn.setCursor(Qt.CursorShape.ForbiddenCursor)
            else:
                btn.setCursor(Qt.CursorShape.PointingHandCursor)

            btn.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 16px; border: none; text-align: left;")

    def invalidate_steps_from(self, step_index):
        """
        Invalidates steps starting from step_index.
        Example: invalidate_steps_from(1) means Step 1 (Task) is now the limit. Step 2 (Exec) is locked.
        """
        if self.unlocked_step > step_index:
            self.unlocked_step = step_index
            self.update_step_indicator()
            
        # If we invalidate Step 1 (or before), it means we need to re-generate, so reset the button text.
        if step_index <= 1:
            self.generate_btn.setText("✨ 生成处理方案")
            self.task_status_label.setText("")

    # --- Pages Initialization ---

    def init_page_files(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        card = CardFrame()
        card_layout = QVBoxLayout(card)

        toolbar = QHBoxLayout()
        btn_add_files = ModernButton("📄 添加文件")
        btn_add_files.setFixedHeight(36)
        btn_add_files.clicked.connect(self.browse_files)
        btn_add_folder = ModernButton("📂 添加文件夹")
        btn_add_folder.setFixedHeight(36)
        btn_add_folder.clicked.connect(self.browse_folder)
        btn_clear = ModernButton("🗑 清空列表")
        btn_clear.setFixedHeight(36)
        btn_clear.clicked.connect(self.clear_files)
        
        toolbar.addWidget(btn_add_files)
        toolbar.addWidget(btn_add_folder)
        toolbar.addStretch()
        toolbar.addWidget(btn_clear)
        card_layout.addLayout(toolbar)

        self.file_drop_area = DropLabel("点击添加或拖拽文件到此处", self)
        self.file_drop_area.setFixedHeight(120)
        self.file_drop_area.fileDropped.connect(self.add_files)
        self.file_drop_area.clicked.connect(self.browse_files)
        card_layout.addWidget(self.file_drop_area)

        self.file_list_widget = QListWidget()
        self.file_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list_widget.customContextMenuRequested.connect(self.show_file_context_menu)
        card_layout.addWidget(self.file_list_widget)

        layout.addWidget(card)

        nav_layout = QHBoxLayout()
        nav_layout.addStretch()
        next_btn = ModernButton("下一步: 定义任务 →", is_primary=True)
        next_btn.clicked.connect(self.go_to_task)
        next_btn.setFixedSize(200, 45)
        nav_layout.addWidget(next_btn)
        layout.addLayout(nav_layout)
        
        return page

    def go_to_task(self):
        # Unlock step 1 if not already
        if self.unlocked_step < 1:
            self.unlocked_step = 1
        self.switch_page(1)

    def init_page_task(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(30)

        # --- Card 1: Quick Format Conversion ---
        quick_card = CardFrame()
        quick_layout = QVBoxLayout(quick_card)
        quick_layout.setContentsMargins(25, 25, 25, 25)
        quick_layout.setSpacing(15)

        lbl_quick = QLabel("⚡ 快速格式转换 (不使用 AI)")
        lbl_quick.setProperty("class", "SubHeader")
        quick_layout.addWidget(lbl_quick)

        # Content: Single Toolbar Row
        quick_toolbar = QHBoxLayout()
        quick_toolbar.setSpacing(10) # Tighter spacing for cohesive look
        
        quick_toolbar.addWidget(QLabel("目标格式:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mp3", "mkv", "mov", "wav", "flac", "avi", "webm", "自定义"])
        self.format_combo.setEditable(False)
        self.format_combo.setFixedSize(120, 36)
        self.format_combo.currentTextChanged.connect(self.on_format_combo_changed)
        quick_toolbar.addWidget(self.format_combo)
        
        self.custom_format_input = QLineEdit()
        self.custom_format_input.setPlaceholderText("输入格式")
        self.custom_format_input.setFixedSize(100, 36)
        self.custom_format_input.hide() 
        self.custom_format_input.textChanged.connect(self.on_requirement_changed)
        quick_toolbar.addWidget(self.custom_format_input)
        
        # Button: Inline, compact, matching height
        btn_quick_exec = ModernButton("⚡生成", is_primary=True)
        btn_quick_exec.setFixedSize(90, 36)
        btn_quick_exec.clicked.connect(self.on_quick_convert_clicked)
        quick_toolbar.addWidget(btn_quick_exec)
        
        quick_toolbar.addStretch() # Push everything to left
        
        quick_layout.addLayout(quick_toolbar)
        layout.addWidget(quick_card)

        # --- Card 2: AI Generation ---
        ai_card = CardFrame()
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(25, 25, 25, 25)
        ai_layout.setSpacing(20)

        lbl_ai = QLabel("🤖 复杂需求 (AI 智能生成)")
        lbl_ai.setProperty("class", "SubHeader")
        ai_layout.addWidget(lbl_ai)

        lbl_hint = QLabel("请输入自然语言指令，例如：'转为mp4格式，分辨率720p，去掉前10秒'...")
        lbl_hint.setStyleSheet("color: #787c99; font-size: 13px; margin-bottom: 5px;")
        ai_layout.addWidget(lbl_hint)

        self.requirement_text = QTextEdit()
        self.requirement_text.setPlaceholderText("在这里输入您的详细需求...")
        self.requirement_text.setFixedHeight(100)
        self.requirement_text.textChanged.connect(self.on_requirement_changed)
        ai_layout.addWidget(self.requirement_text)
        
        # AI Action Row
        ai_action_layout = QHBoxLayout()
        
        self.task_status_label = QLabel("")
        self.task_status_label.setStyleSheet("color: #e0af68; font-size: 13px;")
        ai_action_layout.addWidget(self.task_status_label)
        
        ai_action_layout.addStretch()
        
        self.generate_btn = ModernButton("✨生成 AI 方案", is_primary=True)
        self.generate_btn.setFixedSize(150, 40)
        self.generate_btn.clicked.connect(self.generate_command)
        ai_action_layout.addWidget(self.generate_btn)
        
        ai_layout.addLayout(ai_action_layout)
        layout.addWidget(ai_card)

        layout.addStretch()

        # --- Bottom Nav ---
        nav_layout = QHBoxLayout()
        prev_btn = ModernButton("← 返回文件列表")
        prev_btn.setFixedSize(150, 42)
        prev_btn.clicked.connect(lambda: self.switch_page(0))
        nav_layout.addWidget(prev_btn)
        nav_layout.addStretch()
        
        layout.addLayout(nav_layout)

        return page

    def on_format_combo_changed(self, text):
        if text == "自定义":
            self.custom_format_input.show()
            self.custom_format_input.setFocus()
        else:
            self.custom_format_input.hide()
            self.custom_format_input.clear()
        
        self.on_requirement_changed()

    def on_quick_convert_clicked(self):
        selection = self.format_combo.currentText()
        if selection == "自定义":
            target_ext = self.custom_format_input.text().strip().lower().replace(".", "")
        else:
            target_ext = selection.strip().lower().replace(".", "")
            
        if not target_ext:
            QMessageBox.warning(self, "警告", "请输入或选择目标格式。")
            return
        self.quick_convert(target_ext)

    def quick_convert(self, ext):
        if not self.input_files:
            QMessageBox.warning(self, "警告", "请先在第一步中添加视频文件。")
            self.switch_page(0)
            return

        commands = []
        audio_formats = ["mp3", "wav", "flac", "m4a", "ogg", "aac"]
        
        for input_file in self.input_files:
            base, _ = os.path.splitext(input_file)
            output_file = f"{base}.{ext}"
            
            # Simple unique naming if needed (handled by FFmpegRunner anyway, but let's be clean)
            cmd = ["-i", input_file]
            
            if ext in audio_formats:
                # Audio extraction: Remove video, use decent bitrate
                cmd.extend(["-vn"])
                if ext == "mp3":
                    cmd.extend(["-c:a", "libmp3lame", "-q:a", "2"])
                elif ext == "wav":
                    cmd.extend(["-c:a", "pcm_s16le"])
                # For others, let ffmpeg choose default encoder
            else:
                # Video conversion: Use copy if possible or default to h264 for better compatibility
                # Here we use a safe default: h264 + aac
                cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac"])
            
            cmd.append(output_file)
            commands.append(cmd)

        self.generated_commands = commands
        self.command_preview.setText(json.dumps(commands, indent=2))
        self.task_status_label.setText(f"快速转换方案 ({ext}) 已生成！")
        
        self.unlocked_step = 2
        self.switch_page(2)
        self.execute_btn.setEnabled(True)
        self.execute_btn.show()
        self.btn_new_task.hide()
        self.log_output.clear()
        
        # Reset UI for new execution
        self.task_list_widget.clear()
        self.status_header.setText("准备就绪")
        self.btn_pause.hide()
        self.btn_stop.hide()
        self.exec_tabs.setCurrentIndex(0)

    def init_page_exec(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        card = CardFrame()
        card_layout = QVBoxLayout(card)
        
        # --- Control Area ---
        control_layout = QHBoxLayout()
        
        self.status_header = QLabel("准备就绪")
        self.status_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #7aa2f7;")
        control_layout.addWidget(self.status_header)
        
        control_layout.addStretch()
        
        self.btn_pause = QPushButton("⏸ 暂停")
        self.btn_pause.setCheckable(True)
        self.btn_pause.setFixedSize(110, 42)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setStyleSheet("""
            QPushButton {
                background-color: #e0af68; 
                color: #15161e; 
                font-weight: bold; 
                border-radius: 8px;
                font-size: 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ffc777;
            }
            QPushButton:checked {
                background-color: #7aa2f7;
                color: #15161e;
            }
        """)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_pause.hide() # Initially hidden
        control_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ 停止")
        self.btn_stop.setFixedSize(110, 42)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #f7768e; 
                color: white; 
                font-weight: bold; 
                border-radius: 8px;
                font-size: 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ff9eaf;
            }
        """)
        self.btn_stop.clicked.connect(self.stop_execution)
        self.btn_stop.hide() # Initially hidden
        control_layout.addWidget(self.btn_stop)

        card_layout.addLayout(control_layout)
        
        # --- Main Content Splitter ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Task List
        task_container = QWidget()
        task_layout = QVBoxLayout(task_container)
        task_layout.setContentsMargins(0, 0, 0, 0)
        task_layout.addWidget(QLabel("任务队列:", objectName="SubHeader"))
        
        self.task_list_widget = QListWidget()
        self.task_list_widget.setStyleSheet("QListWidget { background-color: #16161e; border: 1px solid #414868; border-radius: 6px; }")
        task_layout.addWidget(self.task_list_widget)
        
        splitter.addWidget(task_container)
        
        # Right: Tabs (Preview & Logs)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.exec_tabs = QTabWidget()
        self.exec_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #414868; background: #16161e; border-radius: 6px; }
            QTabBar::tab { background: #1a1b26; color: #787c99; padding: 8px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #24283b; color: #c0caf5; font-weight: bold; }
        """)
        
        # Tab 1: Command Preview
        self.command_preview = QTextEdit()
        self.command_preview.setStyleSheet("border: none;")
        self.exec_tabs.addTab(self.command_preview, "🔧 命令详情")
        
        # Tab 2: Logs
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("border: none; font-family: Consolas, monospace; font-size: 12px;")
        self.exec_tabs.addTab(self.log_output, "📜 执行日志")
        
        right_layout.addWidget(self.exec_tabs)
        splitter.addWidget(right_container)
        
        # Set initial sizes
        splitter.setStretchFactor(0, 1) # Tasks
        splitter.setStretchFactor(1, 1) # Details
        
        card_layout.addWidget(splitter, 1) # Add stretch factor 1 for internal content expansion
        layout.addWidget(card, 1) # Add stretch factor 1 to fill vertical space

        nav_layout = QHBoxLayout()
        self.btn_exec_prev = ModernButton("← 返回修改指令")
        self.btn_exec_prev.setFixedSize(160, 42)
        self.btn_exec_prev.clicked.connect(lambda: self.switch_page(1))
        
        self.execute_btn = ModernButton("🚀 开始执行处理", is_primary=True)
        self.execute_btn.setFixedSize(180, 42)
        self.execute_btn.clicked.connect(self.execute_command)

        self.btn_new_task = ModernButton("🔄 开始新任务")
        self.btn_new_task.setFixedSize(180, 42)
        self.btn_new_task.clicked.connect(self.reset_task)
        self.btn_new_task.hide()

        nav_layout.addWidget(self.btn_exec_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.execute_btn)
        nav_layout.addWidget(self.btn_new_task)
        layout.addLayout(nav_layout)

        return page

    # --- File Logic ---

    def browse_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "选择视频文件")
        if file_paths:
            self.add_files(file_paths)

    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm')
            found_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(video_extensions):
                        found_files.append(os.path.join(root, file))
            if found_files:
                self.add_files(found_files)
            else:
                QMessageBox.information(self, "提示", "在该文件夹中未找到视频文件。" )

    def add_files(self, file_paths):
        if isinstance(file_paths, str):
            file_paths = [file_paths]
            
        added_count = 0
        for path in file_paths:
            path = os.path.normpath(path)
            if path not in self.input_files:
                self.input_files.append(path)
                self.file_list_widget.addItem(path)
                added_count += 1
        
        if added_count > 0:
            self.file_drop_area.setText(f"已添加 {added_count} 个新文件 (共 {len(self.input_files)} 个)")
            # Invalidate future steps because input changed
            self.invalidate_steps_from(0)
        
        self.task_status_label.setText("") 

    def clear_files(self):
        self.input_files.clear()
        self.file_list_widget.clear()
        self.file_drop_area.setText("点击添加或拖拽文件到此处")
        self.invalidate_steps_from(0)

    def show_file_context_menu(self, position):
        menu = QMenu()
        remove_action = QAction("移除选中", self)
        remove_action.triggered.connect(self.remove_selected_file)
        menu.addAction(remove_action)
        menu.exec(self.file_list_widget.mapToGlobal(position))

    def remove_selected_file(self):
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            path = item.text()
            if path in self.input_files:
                self.input_files.remove(path)
            self.file_list_widget.takeItem(self.file_list_widget.row(item))
        
        self.file_drop_area.setText(f"剩余 {len(self.input_files)} 个文件")
        self.invalidate_steps_from(0)

    # --- AI Logic ---

    def on_requirement_changed(self):
        # Invalidate Execution step if requirement changes
        self.invalidate_steps_from(1)

    def generate_command(self):
        if not self.input_files:
            QMessageBox.warning(self, "警告", "请先在第一步中添加视频文件。" )
            self.switch_page(0)
            return

        # Check FFmpeg path before generating
        ffmpeg_path = self.config.get("ffmpeg_path")
        if not ffmpeg_path or not os.path.exists(ffmpeg_path):
            QMessageBox.warning(
                self, 
                "未找到 FFmpeg", 
                f"在以下路径未找到 FFmpeg 执行文件：\n{ffmpeg_path}\n\n请点击右上角设置图标 (⚙) 配置正确的路径。"
            )
            return

        requirement = self.requirement_text.toPlainText().strip()
        if not requirement:
            QMessageBox.warning(self, "警告", "请输入您的处理指令。" )
            return

        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("✨ AI 思考中...")
        self.task_status_label.setText("正在分析需求并生成 FFmpeg 命令...")
        
        self.ai_worker = AIWorker(self.ai_service, self.input_files, requirement)
        self.ai_worker.finished.connect(self.on_ai_finished)
        self.ai_worker.error.connect(self.on_ai_error)
        self.ai_worker.start()

    def on_ai_finished(self, commands):
        self.generated_commands = commands
        self.command_preview.setText(json.dumps(commands, indent=2))
        
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("✨ 重新生成")
        
        self.unlocked_step = 2
        self.switch_page(2)
        
        self.execute_btn.setEnabled(True)
        self.execute_btn.show()
        self.btn_new_task.hide()
        self.log_output.clear()
        
        # Reset UI for new execution
        self.task_list_widget.clear()
        self.status_header.setText("准备就绪")
        self.btn_pause.hide()
        self.btn_stop.hide()
        self.exec_tabs.setCurrentIndex(0)

    def on_ai_error(self, error_msg):
        QMessageBox.critical(self, "AI 错误", f"生成命令失败:\n{error_msg}")
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("✨ 生成处理方案")
        self.task_status_label.setText("生成失败，请重试。" )

    # --- Execution Logic ---

    def execute_command(self):
        try:
            content = self.command_preview.toPlainText()
            commands = json.loads(content)
            if not isinstance(commands, list):
                raise ValueError("Format error: Must be a list of lists.")
            if commands and isinstance(commands[0], str):
                commands = [commands] 
        except Exception as e:
            QMessageBox.critical(self, "错误", f"命令格式无效: {e}")
            return

        ffmpeg_path = self.config.get("ffmpeg_path")
        
        # UI Setup for Execution
        self.execute_btn.hide()
        self.btn_exec_prev.setEnabled(False)
        self.log_output.clear()
        self.task_list_widget.clear()
        self.task_items = []
        
        # Populate Task List
        for i, cmd in enumerate(commands):
            # Try to guess output filename for display
            display_name = f"任务 {i+1}"
            try:
                # Simple heuristic: Last argument is usually output
                last_arg = cmd[-1]
                if not last_arg.startswith("-"):
                     display_name = os.path.basename(last_arg)
            except:
                pass
            
            item_widget = TaskItemWidget(display_name)
            list_item = QListWidgetItem(self.task_list_widget)
            # Explicitly set height to ensure content fits (approx 55px)
            list_item.setSizeHint(QSize(item_widget.sizeHint().width(), 55))
            self.task_list_widget.addItem(list_item)
            self.task_list_widget.setItemWidget(list_item, item_widget)
            self.task_items.append(item_widget)

        self.btn_pause.show()
        self.btn_pause.setChecked(False)
        self.btn_pause.setText("⏸ 暂停")
        self.btn_stop.show()
        self.status_header.setText("🚀正在处理中...")
        self.exec_tabs.setCurrentIndex(1) # Switch to Logs

        self.ffmpeg_runner = FFmpegRunner(ffmpeg_path, commands)
        self.ffmpeg_runner.log_signal.connect(self.append_log)
        self.ffmpeg_runner.progress_signal.connect(self.on_progress_update)
        self.ffmpeg_runner.finished_signal.connect(self.on_execution_finished)
        self.ffmpeg_runner.error_signal.connect(self.append_log)
        self.ffmpeg_runner.start()

    def on_progress_update(self, current_idx, total, percent):
        # current_idx is 1-based
        idx = current_idx - 1
        if 0 <= idx < len(self.task_items):
            widget = self.task_items[idx]
            widget.set_progress(percent)
            widget.set_active(True)
            
            if percent >= 100:
                widget.set_status("完成", "#9ece6a") # Green
            else:
                widget.set_status(f"处理中 {percent:.1f}%", "#7aa2f7") # Blue
            
            # Mark previous tasks as completed (just in case)
            for prev_idx in range(idx):
                self.task_items[prev_idx].set_status("完成", "#9ece6a")
                self.task_items[prev_idx].set_progress(100)
                self.task_items[prev_idx].set_active(False)

            # Scroll to current item
            self.task_list_widget.scrollToItem(self.task_list_widget.item(idx))

    def toggle_pause(self):
        if self.btn_pause.isChecked():
            self.ffmpeg_runner.pause()
            self.btn_pause.setText("▶ 继续")
            self.status_header.setText("⏸ 任务已暂停")
            # Set current task status
            # We need to track current index, but simplified:
            self.append_log("[UI] 请求暂停...")
        else:
            self.ffmpeg_runner.resume()
            self.btn_pause.setText("⏸ 暂停")
            self.status_header.setText("🚀 正在处理中...")
            self.append_log("[UI] 请求继续...")

    def stop_execution(self):
        reply = QMessageBox.question(self, '确认停止', '确定要停止当前所有任务吗？', 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.ffmpeg_runner.stop()
            self.status_header.setText("⏹ 任务已停止")
            self.append_log("[UI] 正在停止任务...")

    def append_log(self, text):
        self.log_output.append(text)
        cursor = self.log_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_output.setTextCursor(cursor)

    def on_execution_finished(self, exit_code):
        self.btn_pause.hide()
        self.btn_stop.hide()
        self.btn_exec_prev.setEnabled(True)
        
        if exit_code == 0:
            self.status_header.setText("✅ 所有任务已完成")
            self.execute_btn.hide()
            self.btn_new_task.show()
            QMessageBox.information(self, "成功", "所有任务处理完成！")
            self.append_log("\n[SUCCESS] 全部任务已完成")
            
            # Ensure all marked as done
            for widget in self.task_items:
                if widget.status_label.text() != "完成":
                    widget.set_status("完成", "#9ece6a")
                    widget.set_progress(100)
                    widget.set_active(False)

        else:
            self.status_header.setText(f"❌ 任务中断 (代码 {exit_code})")
            self.execute_btn.setEnabled(True)
            self.execute_btn.show()
            QMessageBox.warning(self, "提示", f"处理过程已结束或中断。")
            self.append_log(f"\n[FAILED/STOPPED] 退出代码 {exit_code}")

    def reset_task(self):
        self.clear_files()
        self.requirement_text.clear()
        self.task_status_label.setText("")
        self.generate_btn.setText("✨ 生成处理方案") # Reset button text
        self.command_preview.clear()
        self.log_output.clear()
        
        # Reset Execution Page State
        self.task_list_widget.clear()
        self.status_header.setText("准备就绪")
        self.btn_pause.hide()
        self.btn_stop.hide()
        self.exec_tabs.setCurrentIndex(0) # Switch back to Preview tab
        
        self.execute_btn.show()
        self.execute_btn.setEnabled(False)
        self.btn_new_task.hide()
        
        self.unlocked_step = 0
        self.switch_page(0)

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.exec()