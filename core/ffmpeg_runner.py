import sys
import os
import subprocess
import re
import psutil
from PyQt6.QtCore import QThread, pyqtSignal

class FFmpegRunner(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int, float)  # current_index, total_files, percentage (0-100)
    finished_signal = pyqtSignal(int)  # Exit code
    error_signal = pyqtSignal(str)

    def __init__(self, ffmpeg_path, commands):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.commands = commands # List of lists of arguments
        self.process = None
        self._is_running = False
        self._is_paused = False
        self.current_output_file = None

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

    def _time_str_to_seconds(self, time_str):
        # Format: HH:MM:SS.mm
        try:
            h, m, s = time_str.split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
        except ValueError:
            return 0.0

    def run(self):
        self._is_running = True
        total_exit_code = 0
        total_files = len(self.commands)
        
        # Regex patterns
        duration_pattern = re.compile(r"Duration:\s+(\d{2}:\d{2}:\d{2}\.\d{2})")
        time_pattern = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")

        for i, args in enumerate(self.commands):
            if not self._is_running:
                break
            
            self.current_output_file = None # Reset before processing new file
            
            # Emit initial progress for this file (0%)
            self.progress_signal.emit(i + 1, total_files, 0.0)

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
                     
                     # Track current output file for cleanup on stop
                     self.current_output_file = final_args[output_idx]

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
                
                duration_sec = 0.0

                # FFmpeg usually outputs to stderr
                while True:
                    line = self.process.stderr.readline()
                    if not line and self.process.poll() is not None:
                        break
                    
                    if line:
                        self.log_signal.emit(line.strip())
                        
                        # Parse Duration
                        if "Duration:" in line and duration_sec == 0.0:
                            match = duration_pattern.search(line)
                            if match:
                                duration_sec = self._time_str_to_seconds(match.group(1))

                        # Parse Time (Progress)
                        if "time=" in line and duration_sec > 0:
                            match = time_pattern.search(line)
                            if match:
                                current_sec = self._time_str_to_seconds(match.group(1))
                                percent = (current_sec / duration_sec) * 100
                                percent = min(max(percent, 0.0), 100.0)
                                self.progress_signal.emit(i + 1, total_files, percent)

                exit_code = self.process.poll()
                
                # Reset current output file if successful (so we don't delete valid files)
                # If exit_code != 0, we might want to keep it if it's not a stop request? 
                # But here we only delete in stop().
                if exit_code == 0:
                     self.current_output_file = None
                     # Ensure 100% is emitted on success
                     self.progress_signal.emit(i + 1, total_files, 100.0)
                else:
                    # If failed (and not stopped), we usually leave the partial file for inspection, 
                    # OR we could clean it up. The user specifically asked for "manual stop" cleanup.
                    # So we leave self.current_output_file set, but only stop() uses it.
                    # However, to be safe, if we move to next file, we must reset it.
                    # We do reset at top of loop.
                    
                    total_exit_code = exit_code
                    if self._is_running:
                        self.error_signal.emit(f"Command failed with exit code {exit_code}")
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
        # self.current_output_file = None # REMOVED: Do not reset here, so stop() can see it
        self.finished_signal.emit(total_exit_code)

    def pause(self):
        if self.process and self._is_running and not self._is_paused:
            try:
                p = psutil.Process(self.process.pid)
                p.suspend()
                self._is_paused = True
                self.log_signal.emit("[PAUSED] 任务已暂停")
            except Exception as e:
                self.error_signal.emit(f"Failed to pause: {e}")

    def resume(self):
        if self.process and self._is_running and self._is_paused:
            try:
                p = psutil.Process(self.process.pid)
                p.resume()
                self._is_paused = False
                self.log_signal.emit("[RESUMED] 任务继续执行")
            except Exception as e:
                self.error_signal.emit(f"Failed to resume: {e}")

    def stop(self):
        self._is_running = False
        if self.process:
            try:
                # If paused, must resume before terminating to avoid zombie processes or hanging
                if self._is_paused:
                    self.resume()
                
                self.process.terminate()
                self.wait() # Wait for thread to finish (and process to die)
                
                # Cleanup partial file
                if self.current_output_file and os.path.exists(self.current_output_file):
                    try:
                        # Add a small retry mechanism or delay as filesystem might lock briefly
                        os.remove(self.current_output_file)
                        self.log_signal.emit(f"\n[CLEANUP] 已自动清理未完成的文件: {os.path.basename(self.current_output_file)}")
                    except OSError as e:
                        self.log_signal.emit(f"\n[CLEANUP ERROR] 无法清理文件: {e}")

            except Exception as e:
                self.error_signal.emit(f"Error stopping process: {e}")
