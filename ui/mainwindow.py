import sys
import os
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTextEdit, QLineEdit, 
                             QFileDialog, QProgressBar, QMessageBox, QFrame,
                             QSizeGrip, QListWidget, QStackedWidget, QListWidgetItem,
                             QMenu, QButtonGroup, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QIcon, QDragEnterEvent, QDropEvent, QMouseEvent, QAction, QCursor

from ui.settings_dialog import SettingsDialog
from utils.config import ConfigManager
from utils.helpers import resource_path
from core.ai_service import AIService
from core.ffmpeg_runner import FFmpegRunner

# Import Custom Components
from ui.custom_widgets import CustomTitleBar, CardFrame, ModernButton, DropLabel
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
        
        self.content_stack = QStackedWidget()
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
        btn_add_files.clicked.connect(self.browse_files)
        btn_add_folder = ModernButton("📂 添加文件夹")
        btn_add_folder.clicked.connect(self.browse_folder)
        btn_clear = ModernButton("🗑 清空列表")
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
        layout.setSpacing(15)

        card = CardFrame()
        card_layout = QVBoxLayout(card)
        
        lbl = QLabel("请输入自然语言指令 (例如：'转为mp4格式，分辨率720p，去掉前10秒')")
        lbl.setProperty("class", "SubHeader")
        card_layout.addWidget(lbl)

        self.requirement_text = QTextEdit()
        self.requirement_text.setPlaceholderText("在这里输入您的需求...")
        self.requirement_text.setFixedHeight(200)
        self.requirement_text.textChanged.connect(self.on_requirement_changed)
        card_layout.addWidget(self.requirement_text)
        
        layout.addWidget(card)

        self.task_status_label = QLabel("")
        self.task_status_label.setStyleSheet("color: #e0af68; font-size: 14px;")
        layout.addWidget(self.task_status_label)

        layout.addStretch()

        nav_layout = QHBoxLayout()
        prev_btn = ModernButton("← 返回")
        prev_btn.clicked.connect(lambda: self.switch_page(0))
        
        self.generate_btn = ModernButton("✨ 生成处理方案", is_primary=True)
        self.generate_btn.clicked.connect(self.generate_command)
        self.generate_btn.setFixedWidth(200)
        
        nav_layout.addWidget(prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.generate_btn)
        layout.addLayout(nav_layout)

        return page

    def init_page_exec(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        card = CardFrame()
        card_layout = QVBoxLayout(card)
        
        # Use QSplitter for resizable areas
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top: Command Preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(QLabel("生成的命令 (可手动微调):", objectName="SubHeader"))
        self.command_preview = QTextEdit()
        preview_layout.addWidget(self.command_preview)
        
        # Bottom: Logs
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.addWidget(QLabel("执行日志:", objectName="SubHeader"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("logOutput")
        log_layout.addWidget(self.log_output)
        
        splitter.addWidget(preview_widget)
        splitter.addWidget(log_widget)
        
        # Set initial sizes: Preview larger (factor 2), Logs smaller (factor 1)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        card_layout.addWidget(splitter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        card_layout.addWidget(self.progress_bar)

        layout.addWidget(card)

        nav_layout = QHBoxLayout()
        self.btn_exec_prev = ModernButton("← 返回修改指令")
        self.btn_exec_prev.clicked.connect(lambda: self.switch_page(1))
        
        self.execute_btn = ModernButton("🚀 开始执行处理", is_primary=True)
        self.execute_btn.clicked.connect(self.execute_command)

        self.btn_new_task = ModernButton("🔄 开始新任务")
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
        self.task_status_label.setText("方案已生成！请在下一步预览并执行。" )
        
        # Unlock and move to step 3
        self.unlocked_step = 2
        self.switch_page(2)
        
        self.execute_btn.setEnabled(True)
        self.execute_btn.show()
        self.btn_new_task.hide()
        self.log_output.clear()

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
        
        self.execute_btn.setEnabled(False)
        self.btn_exec_prev.setEnabled(False)
        self.log_output.clear()
        self.progress_bar.show()
        
        self.ffmpeg_runner = FFmpegRunner(ffmpeg_path, commands)
        self.ffmpeg_runner.log_signal.connect(self.append_log)
        self.ffmpeg_runner.finished_signal.connect(self.on_execution_finished)
        self.ffmpeg_runner.error_signal.connect(self.append_log)
        self.ffmpeg_runner.start()

    def append_log(self, text):
        self.log_output.append(text)
        cursor = self.log_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_output.setTextCursor(cursor)

    def on_execution_finished(self, exit_code):
        self.progress_bar.hide()
        self.btn_exec_prev.setEnabled(True)
        
        if exit_code == 0:
            self.execute_btn.hide()
            self.btn_new_task.show()
            QMessageBox.information(self, "成功", "所有任务处理完成！")
            self.append_log("\n[SUCCESS] 全部任务已完成")
        else:
            self.execute_btn.setEnabled(True)
            QMessageBox.warning(self, "失败", f"处理过程中断，退出代码 {exit_code}")
            self.append_log(f"\n[FAILED] 错误代码 {exit_code}")

    def reset_task(self):
        self.clear_files()
        self.requirement_text.clear()
        self.task_status_label.setText("")
        self.generate_btn.setText("✨ 生成处理方案") # Reset button text
        self.command_preview.clear()
        self.log_output.clear()
        self.execute_btn.show()
        self.execute_btn.setEnabled(False)
        self.btn_new_task.hide()
        
        self.unlocked_step = 0
        self.switch_page(0)

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.exec()