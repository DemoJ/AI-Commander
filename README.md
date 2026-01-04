# AI-Commander (AI 指挥官)

**AI-Commander** 开启了媒体处理的新纪元。这是一个现代化的桌面应用程序，充当您与 FFmpeg 之间的智能桥梁。无需记忆复杂的命令行参数，只需用平常的语言（中文或英文）描述您的需求，让 AI 为您处理一切。

![Icon](assets/icon.png)

## ✨ 核心特性

-   **自然语言处理**: 基于 OpenAI 兼容的各种大语言模型，将“转换为 mp4 并剪掉前 10 秒”等指令精准翻译为 FFmpeg 命令。
-   **批量处理**: 支持拖拽多个文件或整个文件夹，一次性完成所有任务。
-   **安全可控**: 在执行之前可以预览和修改 AI 生成的命令。您始终拥有最终决定权。
-   **实时日志**: 在程序内实时查看 FFmpeg 的运行输出和进度。
-   **现代化 UI**: 使用 PyQt6 构建的深色模式界面，简约而不简单。

## 🛠️ 安装指南

### 前置要求

1.  **Python 3.8+**: 确保您的系统中已安装 Python。
2.  **FFmpeg**: 您需要在系统中安装 `ffmpeg` 执行文件，或在程序设置中指定其路径。

### 环境搭建

1.  克隆仓库：
    ```bash
    git clone https://github.com/your-username/AI-Commander.git
    cd AI-Commander
    ```

2.  创建并激活虚拟环境（建议）：
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```

3.  安装依赖库：
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 使用说明

1.  **启动程序**:
    ```bash
    python main.py
    ```

2.  **配置参数** (首次运行):
    -   点击右上角的 **设置 (⚙)** 图标。
    -   输入您的 **OpenAI API Key** (或 DeepSeek, Moonshot 等兼容接口的 Key)。
    -   如果使用非 OpenAI 官方接口，请设置 **Base URL**。
    -   指定 **Model Name** (例如：`gpt-3.5-turbo`, `deepseek-chat`)。
    -   设置 **FFmpeg 执行文件** 的完整路径。

3.  **操作流程**:
    -   **第一步：导入素材** - 拖拽视频/音频文件到窗口中。
    -   **第二步：定义任务** - 输入您的处理需求（例如：“提取 mp3 音频”，“缩放至 1080p 并降低码率”），点击“生成处理方案”。
    -   **第三步：执行预览** - 检查生成的 JSON 命令，点击“开始执行处理”。

## 📂 项目结构

-   `core/`: 处理 AI 交互与 FFmpeg 执行的核心逻辑。
-   `ui/`: 基于 PyQt6 的用户界面组件。
-   `utils/`: 配置管理与工具函数。
-   `assets/`: 图标及资源文件。

## 📝 开源协议

本项目采用 MIT 协议开源。