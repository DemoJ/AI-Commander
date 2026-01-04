import sys
import os
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

class FFmpegRunner(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)  # Exit code
    error_signal = pyqtSignal(str)

    def __init__(self, ffmpeg_path, commands):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.commands = commands # List of lists of arguments
        self.process = None
        self._is_running = False

    def _get_unique_filename(self, path):
        if not os.path.exists(path):
            return path
        
        base, ext = os.path.splitext(path)
        counter = 1
        while True:
            new_path = f"{base}_{counter}{ext}"
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    def run(self):
        self._is_running = True
        total_exit_code = 0

        for i, args in enumerate(self.commands):
            if not self._is_running:
                break
            
            # Smart Output Collision Handling
            # Heuristic: Scan args backwards for the first non-flag argument that isn't an input file
            final_args = list(args)
            output_idx = -1
            
            for idx in range(len(final_args) - 1, -1, -1):
                arg = final_args[idx]
                # Skip flags (starting with -)
                if arg.startswith('-'):
                    continue
                # Skip input files (preceded by -i)
                if idx > 0 and final_args[idx-1] == '-i':
                    continue
                
                # Found potential output file
                output_idx = idx
                break
            
            if output_idx != -1:
                original_path = final_args[output_idx]
                # Ignore special outputs like pipe or null
                if original_path != "-" and not original_path.startswith("pipe:") and not original_path.startswith("udp:"):
                     new_path = self._get_unique_filename(original_path)
                     if new_path != original_path:
                         final_args[output_idx] = new_path
                         self.log_signal.emit(f"Notice: Output file exists. Renaming to '{os.path.basename(new_path)}' to avoid overwrite.\n")

            command = [self.ffmpeg_path] + final_args
            
            # Join command for display purposes
            cmd_str = " ".join(f'"{c}"' if " " in c else c for c in command)
            self.log_signal.emit(f"Executing ({i+1}/{len(self.commands)}): {cmd_str}\n")

            try:
                # We need to capture stderr because FFmpeg prints progress info to stderr
                # startupinfo to hide console window on Windows
                startupinfo = None
                if sys.platform == 'win32':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                self.process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL, # Ensure we never hang on input
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1, # Line buffered
                    startupinfo=startupinfo
                )

                # FFmpeg usually outputs to stderr
                while True:
                    line = self.process.stderr.readline()
                    if not line and self.process.poll() is not None:
                        break
                    if line:
                        self.log_signal.emit(line.strip())

                exit_code = self.process.poll()
                if exit_code != 0:
                    total_exit_code = exit_code
                    self.error_signal.emit(f"Command failed with exit code {exit_code}")
                    # Decide whether to continue or stop. Usually stop on error.
                    break 

            except FileNotFoundError:
                self.error_signal.emit(f"Error: FFmpeg executable not found at '{self.ffmpeg_path}'")
                total_exit_code = -1
                break
            except Exception as e:
                self.error_signal.emit(f"Error executing FFmpeg: {str(e)}")
                total_exit_code = -1
                break
        
        self._is_running = False
        self.finished_signal.emit(total_exit_code)

    def stop(self):
        self._is_running = False
        if self.process:
            self.process.terminate()
            self.wait()
