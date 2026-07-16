from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QElapsedTimer, QProcess
from PySide6.QtGui import QPainter, QColor, QBrush, QPixmap, QFont, QPen, QLinearGradient, QPainterPath
import ctypes
from ctypes import wintypes
import os
import psutil


class PerformanceMonitorWidget(QWidget):
    """悬浮窗性能监控面板 - 专业级系统指标显示"""
    
    _elapsed = QElapsedTimer()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        # 曲线图显示开关
        self._show_charts = True
        self.setFixedHeight(self.widget_height())
        
        # 性能指标存储
        self.metrics = {
            "FPS": ("0", QColor(80, 220, 120), "FPS"),
            "GPU": ("--", QColor(80, 200, 240), "GPU"),
            "CPU": ("0%", QColor(240, 200, 80), "CPU"),
            "MEM": ("0%", QColor(240, 140, 80), "MEM"),
            "UP": ("00:00:00", QColor(200, 200, 220), "UPTIME"),
            "THR": ("0", QColor(180, 160, 220), "THREADS"),
        }
        
        # 曲线图历史数据缓冲区（最多120个采样点 = 60秒）
        self._history_len = 120
        self._history = {
            "FPS": [0] * self._history_len,
            "CPU": [0.0] * self._history_len,
            "MEM": [0.0] * self._history_len,
            "GPU": [0.0] * self._history_len,
        }
        self._hist_idx = 0
        
        # 缓存的最新性能值
        self._last_cpu_val = 0.0
        self._last_cpu_str = "0%"
        self._last_gpu_val = 0.0
        self._last_gpu_str = "--"
        self._ps_process = None  # 持久 QProcess（GPU）
        self._ps_buffer = ""     # 行缓冲
        
        # FPS 相关
        self._fps_value = 0           # 当前 FPS
        self._fps_frame_count = 0     # 本秒累计帧数
        self._game_pid = None         # 游戏进程 PID
        self._fps_process = None      # PresentMon QProcess
        self._fps_buffer = ""         # PresentMon 行缓冲
        self._fps_header_skipped = False  # CSV表头是否已跳过
        
        # CPU 预热：psutil 第一次调用返回 0，预热后后续调用才准确
        psutil.cpu_percent(interval=0)
        
        # 启动性能定时器（1秒更新UI）
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(1000)
        self._update_timer.timeout.connect(self._collect_metrics)
        self._update_timer.start()
        
        # FPS 计算定时器（每秒统计一次帧数）
        self._fps_calc_timer = QTimer(self)
        self._fps_calc_timer.setInterval(1000)
        self._fps_calc_timer.timeout.connect(self._calc_fps)
        self._fps_calc_timer.start()
        
        # 游戏进程检测定时器（每3秒检查一次）
        self._game_check_timer = QTimer(self)
        self._game_check_timer.setInterval(3000)
        self._game_check_timer.timeout.connect(self._check_game_pid)
        self._game_check_timer.start()
        
        self._elapsed.start()
        
        self._process = psutil.Process()
        self._start_time = self._process.create_time()
        
        # 立即检查一次游戏进程
        self._check_game_pid()
        
        # 启动持久 PowerShell 进程（后台持续采集 GPU 数据）
        self._start_ps_poll()
    
    def widget_height(self):
        """返回当前需要的面板高度（数据+曲线图）"""
        base = 100  # 数据区高度
        if self._show_charts:
            return base + 115  # 数据 + 曲线图
        return base
    
    def set_charts_visible(self, visible):
        """显示/隐藏曲线图"""
        self._show_charts = visible
        self.setFixedHeight(self.widget_height())
        # 触发父窗口重新调整高度
        parent = self.parent()
        if parent and hasattr(parent, 'performance_monitor'):
            parent._resize_for_perf_monitor()
        self.update()
    
    def _collect_metrics(self):
        """采集各项性能指标并采样到历史缓冲区"""
        try:
            # CPU - 使用 psutil（快速，每秒更新，与任务管理器 CPU Time 一致）
            cpu_val = psutil.cpu_percent(interval=0)
            self._last_cpu_val = cpu_val
            self._last_cpu_str = f"{cpu_val:.0f}%"
            self.metrics["CPU"] = (self._last_cpu_str, QColor(240, 200, 80), "CPU")
            
            # 内存 - 系统总内存使用率（与任务管理器一致）
            try:
                sys_mem = psutil.virtual_memory()
                mem_str = f"{sys_mem.percent:.0f}%"
            except Exception:
                mem_str = "--"
            self.metrics["MEM"] = (mem_str, QColor(240, 140, 80), "MEM")
            
            # 运行时长
            uptime_sec = self._elapsed.elapsed() / 1000
            h = int(uptime_sec // 3600)
            m = int((uptime_sec % 3600) // 60)
            s = int(uptime_sec % 60)
            uptime_str = f"{h:02d}:{m:02d}:{s:02d}"
            self.metrics["UP"] = (uptime_str, QColor(200, 200, 220), "UPTIME")
            
            # 线程数
            thr_str = str(self._process.num_threads())
            self.metrics["THR"] = (thr_str, QColor(180, 160, 220), "THREADS")
            
            # GPU 使用率（由持久 PowerShell 后台实时更新）
            self.metrics["GPU"] = (self._last_gpu_str, QColor(80, 200, 240), "GPU")
            
            # FPS - 由 PresentMon 采集的真实游戏帧率（无游戏时为0）
            fps_str = str(self._fps_value) if self._fps_value > 0 else "0"
            self.metrics["FPS"] = (fps_str, QColor(80, 220, 120), "FPS")
            
            # 写入历史缓冲区
            idx = self._hist_idx % self._history_len
            self._history["FPS"][idx] = self._fps_value
            self._history["CPU"][idx] = cpu_val
            self._history["MEM"][idx] = sys_mem.percent
            self._history["GPU"][idx] = self._last_gpu_val
            self._hist_idx += 1
                
        except Exception:
            pass
        
        self.update()
    
    def _start_ps_poll(self):
        """启动持久 QProcess 后台持续采集 GPU 数据"""
        if self._ps_process is not None:
            return
        
        # 持久循环：每轮采集一次 GPU 3D 引擎利用率的最高值
        ps_cmd = (
            "while ($true) { "
            "$gpus = (Get-Counter "
            "'\\GPU Engine(*)\\Utilization Percentage' "
            "-MaxSamples 1 -ErrorAction SilentlyContinue).CounterSamples | "
            "Where-Object { $_.Status -eq 0 -and $_.InstanceName -like '*engtype_3d*' }; "
            "$gpuMax = ($gpus | Measure-Object CookedValue -Maximum).Maximum; "
            "if ($gpuMax -eq $null) { $gpuMax = 0 }; "
            "Write-Host $([Math]::Round($gpuMax,1)) "
            "}"
        )
        
        self._ps_process = QProcess(self)
        self._ps_process.setProcessChannelMode(QProcess.SeparateChannels)
        self._ps_process.readyReadStandardOutput.connect(self._on_ps_output)
        self._ps_process.start('powershell', ['-NoProfile', '-Command', ps_cmd])
    
    def _stop_ps_poll(self):
        """停止持久 PowerShell 进程"""
        if self._ps_process is not None:
            # 先断开信号连接
            try:
                self._ps_process.readyReadStandardOutput.disconnect()
            except Exception:
                pass
            # 尝试优雅停止
            self._ps_process.terminate()
            if not self._ps_process.waitForFinished(3000):
                print("[FPS] PowerShell 进程未优雅退出，强制杀死")
                self._ps_process.kill()
                self._ps_process.waitForFinished(1000)
            self._ps_process = None
        self._ps_buffer = ""
        self._gpu_usage = 0.0
        self._gpu_display = "--"
    
    def restart_all_perf(self):
        """异常重启时调用：停止所有持久进程并重新启动"""
        self._stop_ps_poll()
        self._stop_fps_monitor()
        self._game_pid = None
        self._start_ps_poll()
        self._check_game_pid()
    
    def _on_ps_output(self):
        """处理持久 PowerShell 的 GPU 数据输出（每行一个值）"""
        data = bytes(self._ps_process.readAllStandardOutput()).decode('utf-8', errors='ignore')
        self._ps_buffer += data
        while '\n' in self._ps_buffer:
            line, self._ps_buffer = self._ps_buffer.split('\n', 1)
            line = line.strip()
            if line:
                try:
                    gpu_v = float(line)
                    self._last_gpu_val = gpu_v
                    self._last_gpu_str = f"{gpu_v:.0f}%"
                except ValueError:
                    pass
    
    def _check_game_pid(self):
        """定时检查游戏进程是否存在，自动启停 FPS 监控"""
        GAME_PROCESS = 'NRC-Win64-Shipping.exe'
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == GAME_PROCESS:
                    new_pid = proc.info['pid']
                    if new_pid != self._game_pid:
                        print(f"[FPS] 检测到游戏进程 PID={new_pid}")
                        self._start_fps_monitor(new_pid)
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        # 游戏进程不存在
        if self._game_pid is not None:
            print(f"[FPS] 游戏进程已退出")
            self._stop_fps_monitor()
    
    def _start_fps_monitor(self, pid):
        """启动 PresentMon 监控游戏 FPS"""
        if pid == self._game_pid and self._fps_process is not None:
            return
        
        # 停止旧的
        self._stop_fps_monitor()
        self._game_pid = pid
        
        presentmon_dir = os.path.join(os.path.dirname(__file__), '..', 'tools', 'PresentMon')
        presentmon_exe = os.path.join(presentmon_dir, 'PresentMon.exe')
        
        if not os.path.exists(presentmon_exe):
            # PresentMon 未安装，FPS 保持为 0
            return
        
        self._fps_process = QProcess(self)
        self._fps_process.setProcessChannelMode(QProcess.SeparateChannels)
        self._fps_process.readyReadStandardOutput.connect(self._on_fps_output)
        self._fps_process.readyReadStandardError.connect(self._on_fps_error)
        self._fps_process.finished.connect(self._on_fps_finished)
        self._fps_process.setWorkingDirectory(presentmon_dir)
        self._fps_process.start(presentmon_exe, [
            '-process_id', str(pid),
            '-output_stdout',
            '-no_console_stats',
            '-stop_existing_session',
            '-terminate_on_proc_exit'
        ])
        self._fps_frame_count = 0
        self._fps_buffer = ""
        self._fps_header_skipped = False
        print(f"[FPS] PresentMon 已启动，监控 PID={pid}")
    
    def _stop_fps_monitor(self):
        """停止 FPS 监控"""
        if self._fps_process is not None:
            # 先断开信号连接
            try:
                self._fps_process.readyReadStandardOutput.disconnect()
            except Exception:
                pass
            try:
                self._fps_process.readyReadStandardError.disconnect()
            except Exception:
                pass
            try:
                self._fps_process.finished.disconnect()
            except Exception:
                pass
            # 尝试优雅停止
            self._fps_process.terminate()
            if not self._fps_process.waitForFinished(3000):
                print("[FPS] PresentMon 进程未优雅退出，强制杀死")
                self._fps_process.kill()
                self._fps_process.waitForFinished(1000)
            self._fps_process = None
        self._game_pid = None
        self._fps_value = 0
        self._fps_frame_count = 0
        self._fps_buffer = ""
        self._fps_header_skipped = False
    
    def _on_fps_output(self):
        """处理 PresentMon 输出（CSV格式：第一行是表头，之后每行是一帧）"""
        data = bytes(self._fps_process.readAllStandardOutput()).decode('utf-8', errors='ignore')
        self._fps_buffer += data
        while '\n' in self._fps_buffer:
            line, self._fps_buffer = self._fps_buffer.split('\n', 1)
            line = line.strip()
            if not line:
                continue
            # 第一行是 CSV 表头（Application,ProcessID,SwapChainAddress...），跳过
            if not self._fps_header_skipped:
                self._fps_header_skipped = True
                continue
            # 之后的每一行代表一帧
            self._fps_frame_count += 1
    
    def _on_fps_finished(self):
        """PresentMon 进程退出"""
        if self._fps_process is not None:
            exit_code = self._fps_process.exitCode()
            print(f"[FPS] PresentMon 退出, exit_code={exit_code}")
        self._fps_process = None
        self._fps_value = 0
        self._fps_frame_count = 0
    
    def _on_fps_error(self):
        """处理 PresentMon stderr 输出"""
        data = bytes(self._fps_process.readAllStandardError()).decode('utf-8', errors='ignore')
        if data.strip():
            print(f"[FPS] PresentMon stderr: {data.strip()}")
    
    def _calc_fps(self):
        """每秒计算一次 FPS（由定时器触发）"""
        self._fps_value = self._fps_frame_count
        self._fps_frame_count = 0
    
    def _draw_chart(self, p, x, y, chart_w, chart_h, data, color, label, unit=""):
        """绘制一条迷你曲线图"""
        if chart_w <= 0 or chart_h <= 0:
            return
        
        valid = [v for v in data if v > 0]
        if not valid:
            return
        max_val = max(valid) * 1.2
        min_val = 0
        if max_val <= 0:
            max_val = 100
        
        # 图表边框
        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.drawRect(x, y, chart_w, chart_h)
        
        # 标签 + 最大值（清晰可见）
        label_font = QFont("Consolas", 7)
        label_font.setBold(True)
        p.setFont(label_font)
        p.setPen(QColor(color))
        p.drawText(x + 4, y + 11, label)
        
        p.setPen(QColor(200, 200, 220, 80))
        p.drawText(x + chart_w - 4, y + 11, f"{max_val:.0f}{unit}")
        
        # 水平网格线
        grid_pen = QPen(QColor(255, 255, 255, 10), 1)
        grid_pen.setStyle(Qt.DashLine)
        p.setPen(grid_pen)
        grid_y = y + chart_h // 2
        p.drawLine(x + 1, grid_y, x + chart_w - 1, grid_y)
        
        # 曲线
        pen = QPen(color, 1.2)
        pen.setStyle(Qt.SolidLine)
        p.setPen(pen)
        
        path = QPainterPath()
        first_point = True
        for i in range(self._history_len):
            val = data[(self._hist_idx + i) % self._history_len]
            if val <= 0 and first_point:
                continue
            px = x + (i / (self._history_len - 1)) * (chart_w - 2) + 1
            py = y + chart_h - 2 - ((val - min_val) / (max_val - min_val)) * (chart_h - 4)
            py = max(y + 1, min(y + chart_h - 2, py))
            
            if first_point:
                path.moveTo(px, py)
                first_point = False
            else:
                path.lineTo(px, py)
        
        if not first_point:
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
            
            # 渐变填充区域
            fill_path = QPainterPath(path)
            last_px = x + ((self._history_len - 1) / (self._history_len - 1)) * (chart_w - 2) + 1
            fill_path.lineTo(last_px, y + chart_h - 2)
            fill_path.lineTo(x + 1, y + chart_h - 2)
            fill_path.closeSubpath()
            
            grad = QLinearGradient(0, y, 0, y + chart_h)
            base_color = QColor(color)
            base_color.setAlpha(30)
            grad.setColorAt(0.0, base_color)
            base_color.setAlpha(4)
            grad.setColorAt(1.0, base_color)
            p.fillPath(fill_path, grad)
    
    def paintEvent(self, event):
        if not self.isVisible():
            return
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        # === 背景 ===
        bg_path = QPainterPath()
        bg_path.addRoundedRect(0, 0, w, h, 8, 8)
        p.fillPath(bg_path, QColor(8, 4, 20, 230))
        
        # 顶部高光线
        p.setPen(QPen(QColor(157, 78, 221, 60), 1))
        p.drawLine(12, 0, w - 12, 0)
        
        # === 数据面板 ===
        # 标题
        font = QFont("Consolas", 7)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(157, 78, 221, 180))
        p.drawText(10, 14, "PERFORMANCE MONITOR")
        if not self._show_charts:
            p.drawText(w - 60, 14, "[仅数据]")
        
        # 分隔线
        p.setPen(QPen(QColor(157, 78, 221, 40), 1))
        p.drawLine(10, 20, w - 10, 20)
        
        # 两行四列布局（恢复原有风格）
        metrics_order = [
            ("FPS", "FPS", 0, 0),
            ("GPU", "GPU", 0, 1),
            ("CPU", "CPU", 0, 2),
            ("MEM", "MEM", 0, 3),
            ("UP", "UPTIME", 1, 0),
            ("THR", "THREADS", 1, 1),
        ]
        
        col_widths = [0, 0, 0, 0]
        for _, _, row, col in metrics_order:
            if col == 0:
                col_widths[0] = w // 4
            elif col == 1:
                col_widths[1] = w // 4
            elif col == 2:
                col_widths[2] = w // 4
            elif col == 3:
                col_widths[3] = w - col_widths[0] - col_widths[1] - col_widths[2]
        
        x_positions = [12]
        for i in range(1, 4):
            x_positions.append(x_positions[i-1] + col_widths[i-1])
        
        start_y = 26
        
        # 第一行：数值（大号）+ 小标签在上方
        value_font = QFont("Consolas", 11)
        value_font.setBold(True)
        label_font = QFont("Consolas", 6)
        label_font.setBold(True)
        
        for key, label_text, row, col in metrics_order:
            if row == 0:
                value, val_color, _ = self.metrics.get(key, ("--", QColor(200, 200, 220), ""))
                x = x_positions[col]
                
                # 小标签（清楚标注这是什么指标）
                p.setFont(label_font)
                p.setPen(QColor(180, 180, 200, 200))
                p.drawText(x, start_y + 10, label_text)
                
                # 大数值
                p.setFont(value_font)
                p.setPen(QColor(val_color))
                p.drawText(x, start_y + 22, value)
        
        # 第二行：标签（小号）+ 数值
        p.setFont(label_font)
        
        for key, label_text, row, col in metrics_order:
            if row == 1:
                value, val_color, _ = self.metrics.get(key, ("--", QColor(200, 200, 220), ""))
                x = x_positions[col]
                
                # 标签
                p.setPen(QColor(180, 180, 200, 220))
                p.drawText(x, start_y + 46, label_text)
                
                # 值
                val_font2 = QFont("Consolas", 10)
                val_font2.setBold(True)
                p.setFont(val_font2)
                p.setPen(QColor(val_color))
                p.drawText(x, start_y + 66, value)
        
        # === 曲线图区域 ===
        if self._show_charts:
            chart_top = 100
            chart_spacing = 6
            chart_w = max(1, (w - 12 - chart_spacing) // 2)
            chart_h = max(1, (h - chart_top - 6 - chart_spacing) // 2)
            
            # 在图表区上方画分隔线
            p.setPen(QPen(QColor(157, 78, 221, 30), 1))
            p.drawLine(10, chart_top - 4, w - 10, chart_top - 4)
            
            charts_config = [
                (self._history["FPS"], QColor(80, 220, 120), "FPS", ""),
                (self._history["CPU"], QColor(240, 200, 80), "CPU", "%"),
                (self._history["GPU"], QColor(80, 200, 240), "GPU", "%"),
                (self._history["MEM"], QColor(240, 140, 80), "MEM", "MB"),
            ]
            
            positions = [
                (6, chart_top + 4),
                (6 + chart_w + chart_spacing, chart_top + 4),
                (6, chart_top + chart_h + chart_spacing + 4),
                (6 + chart_w + chart_spacing, chart_top + chart_h + chart_spacing + 4),
            ]
            
            for (data, color, label_txt, unit), (cx, cy) in zip(charts_config, positions):
                self._draw_chart(p, cx, cy, chart_w, chart_h, data, color, label_txt, unit)
        
        # 底部装饰线
        p.setPen(QPen(QColor(157, 78, 221, 30), 1))
        p.drawLine(10, h - 1, w - 10, h - 1)
        
        p.end()

    def closeEvent(self, event):
        """关闭时确保清理所有 QProcess"""
        self._stop_ps_poll()
        self._stop_fps_monitor()
        if hasattr(self, '_update_timer'):
            self._update_timer.stop()
        if hasattr(self, '_fps_calc_timer'):
            self._fps_calc_timer.stop()
        if hasattr(self, '_game_check_timer'):
            self._game_check_timer.stop()
        super().closeEvent(event)


class FloatingWindow(QWidget):
    """悬浮窗 - 模仿HTML的半透明毛玻璃效果"""
    
    # 信号：当计数变化时通知主窗口
    count_changed = Signal(int)
    nightmare_count_changed = Signal(int)  # 童话事件提示计数变化
    breakthrough_count_changed = Signal(int)  # 童话事件计数变化
    counter_navigate = Signal(int)  # 快捷计数器导航：-1=上一个, +1=下一个
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 拖拽相关
        self.drag_pos = None
        self.is_locked = False  # 是否锁定位置
        
        # 交互模式控制
        self.interactive_mode = False  # 是否处于交互模式
        self.mouse_enabled = True  # 鼠标是否可选中
        self.normal_opacity = 0.7  # 默认透明度（由设置控制）
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(2000)  # 悬停2秒后激活
        self.hover_timer.timeout.connect(self._activate_interactive_mode)
        
        # 童话事件提示计数（本地缓存）
        self.current_nightmare_count = 0
        
        # 童话事件计数（本地缓存）
        self.current_breakthrough_count = 0
        
        # 注册全局快捷键 Ctrl+N
        self._register_hotkey()
        
        # 悬浮窗尺寸配置
        self.size_configs = {
            "small": {"size": (260, 150), "margins": (12, 12, 12, 12), "spacing": 8},
            "medium": {"size": (320, 180), "margins": (16, 16, 16, 16), "spacing": 10},
            "large": {"size": (400, 220), "margins": (20, 20, 20, 20), "spacing": 12}
        }
        self.current_size = "medium"
        
        # 初始化UI
        self._init_ui()
        
        # 设置初始状态为穿透模式
        self._set_transparent_mode()

    def closeEvent(self, event):
        """关闭前清理 QProcess，避免 'Destroyed while process is still running' 警告"""
        self.performance_monitor._stop_ps_poll()
        self.performance_monitor._stop_fps_monitor()
        super().closeEvent(event)
        
    def _init_ui(self):
        """初始化悬浮窗UI"""
        # 根据当前尺寸配置设置窗口
        config = self.size_configs[self.current_size]
        width, height = config["size"]
        margins = config["margins"]
        spacing = config["spacing"]
        
        self.resize(width, height)
        self._base_height = height  # 保存基础高度，用于性能监控面板展开
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*margins)
        main_layout.setSpacing(spacing)
        
        # 性能监控面板（默认隐藏）
        self.performance_monitor = PerformanceMonitorWidget(self)
        self.performance_monitor.setVisible(False)
        main_layout.addWidget(self.performance_monitor)
        
        # 顶部栏
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        
        # 精灵名称
        name_section = QHBoxLayout()
        name_section.setSpacing(6)
        name_section.setContentsMargins(0, 8, 0, 0)  # 增加顶部留白
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent;")
        name_section.addWidget(self.icon_label)
        
        self.poke_name_label = QLabel("异色帕尔")
        self.poke_name_label.setStyleSheet("color: #f8f0ff; font-weight: bold; font-size: 14px;")
        name_section.addWidget(self.poke_name_label)
        name_section.addStretch()
        
        top_bar.addLayout(name_section)
        
        # 展开按钮（返回主窗口）
        btn_expand = QPushButton("↗")
        btn_expand.setFixedSize(30, 30)
        btn_expand.setToolTip("返回主窗口")
        btn_expand.setStyleSheet("""
            QPushButton {
                color: #c77dff;
                background: rgba(139, 92, 246, 0.08);
                border: 1px solid rgba(139, 92, 246, 0.25);
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                color: #c4b5fd;
                background: rgba(139, 92, 246, 0.2);
                border-color: #a78bfa;
            }
            QPushButton:pressed {
                background: rgba(139, 92, 246, 0.3);
                border-color: #c4b5fd;
            }
        """)
        btn_expand.clicked.connect(self.expand_to_main)
        top_bar.addWidget(btn_expand)
        
        # 固定按钮（图钉图标）
        self.btn_lock = QPushButton("📍")
        self.btn_lock.setFixedSize(32, 32)
        self.btn_lock.setMinimumWidth(32)
        self.btn_lock.setToolTip("锁定/解锁位置")
        self.btn_lock.setStyleSheet("""
            QPushButton {
                color: #ffffff;
                background: transparent;
                border: none;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                color: #f8f0ff;
                background: rgba(199, 125, 255, 0.2);
                border-radius: 4px;
            }
        """)
        self.btn_lock.clicked.connect(self.toggle_lock)
        top_bar.addWidget(self.btn_lock)
        
        main_layout.addLayout(top_bar)
        
        # 信息行
        info_bar = QHBoxLayout()
        info_bar.setContentsMargins(0, 12, 0, 0)  # 增加顶部留白,与名字拉开更大距离
        
        left_info = QLabel("童话事件")
        left_info.setStyleSheet("color: #e0aaff; font-size: 12px;")
        info_bar.addWidget(left_info)
        
        info_bar.addStretch()
        
        self.lock_label = QLabel("锁定：幽系")
        self.lock_label.setStyleSheet("color: #c084fc; font-size: 12px;")
        info_bar.addWidget(self.lock_label)
        
        main_layout.addLayout(info_bar)
        
        # 当前洛克王国精灵显示
        current_lkwg_row = QHBoxLayout()
        current_lkwg_row.setContentsMargins(0, 0, 0, 0)
        current_lkwg_row.setSpacing(8)

        self.current_lkwg_label = QLabel("当前精灵：")
        self.current_lkwg_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-top: 4px;")
        self.current_lkwg_label.setVisible(True)
        current_lkwg_row.addWidget(self.current_lkwg_label)

        current_lkwg_row.addStretch()

        main_layout.addLayout(current_lkwg_row)
        
        # 大数字计数
        self.count_label = QLabel("32/80")
        self.count_label.setStyleSheet("""
            color: #f8f0ff;
            font-size: 36px;
            font-weight: bold;
        """)
        main_layout.addWidget(self.count_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(80)
        self.progress_bar.setValue(32)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(26, 15, 48, 0.8);
                border: none;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #c77dff, stop:1 #9d4edd);
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # 底部栏
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        
        self.remaining_label = QLabel("保底剩余 48")
        self.remaining_label.setStyleSheet("color: #c084fc; font-size: 12px;")
        bottom_bar.addWidget(self.remaining_label)
        
        bottom_bar.addStretch()
        
        # 童话事件提示（nightmare_template检测）
        self.nightmare_label = QLabel("童话事件提示: 0")
        self.nightmare_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
        bottom_bar.addWidget(self.nightmare_label)
        
        main_layout.addLayout(bottom_bar)
        
        # 快捷键状态提示栏
        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(0, 4, 0, 0)
        
        self.status_label = QLabel("Ctrl+N: 鼠标穿透 ✓ | +/-: 计数调整")
        self.status_label.setStyleSheet("color: #a78bfa; font-size: 10px;")
        status_bar.addWidget(self.status_label)
        
        status_bar.addStretch()
        
        main_layout.addLayout(status_bar)
    
    def _register_hotkey(self):
        """注册全局快捷键（从设置读取配置）"""
        try:
            from core.settings_manager import SettingsManager
            settings = SettingsManager()
            hotkeys = settings.get("hotkeys", {})

            user32 = ctypes.windll.user32

            # 注册所有热键，使用固定ID: 1-7
            self._hotkey_ids = {}

            hotkey_map = [
                (1, "toggle_passthrough", self._toggle_mouse_interaction),
                (2, "count_plus", lambda: self._adjust_nightmare_count(1)),
                (3, "count_minus", lambda: self._adjust_nightmare_count(-1)),
                (4, "counter_prev", lambda: self.counter_navigate.emit(-1)),
                (5, "counter_next", lambda: self.counter_navigate.emit(1)),
                (6, "nightmare_plus", lambda: self._emit_nightmare_adjust(1)),
                (7, "nightmare_minus", lambda: self._emit_nightmare_adjust(-1)),
            ]

            for hk_id_num, hk_config_key, _ in hotkey_map:
                cfg = hotkeys.get(hk_config_key, {})
                mod_code = cfg.get("mod_code", 0)
                vk = cfg.get("vk", 0)
                if vk == 0:
                    continue

                registered = user32.RegisterHotKey(
                    int(self.winId()),
                    hk_id_num,
                    mod_code,
                    vk
                )
                display = cfg.get("display", hk_config_key)
                if registered:
                    self._hotkey_ids[hk_id_num] = hk_config_key
                    print(f"✓ 全局快捷键 {display} 已注册")
                else:
                    print(f"✗ 全局快捷键 {display} 注册失败")

        except Exception as e:
            print(f"✗ 注册快捷键异常: {e}")

    def _unregister_hotkeys(self):
        """注销所有已注册的全局快捷键"""
        try:
            user32 = ctypes.windll.user32
            for hk_id in list(self._hotkey_ids.keys()):
                user32.UnregisterHotKey(int(self.winId()), hk_id)
            self._hotkey_ids.clear()
        except Exception as e:
            print(f"✗ 注销快捷键异常: {e}")
    
    def nativeEvent(self, eventType, message):
        """处理Windows原生消息 - 捕获全局快捷键"""
        if eventType == b'windows_generic_MSG':
            msg = ctypes.wintypes.MSG.from_address(message.__int__())
            WM_HOTKEY = 0x0312
            if msg.message == WM_HOTKEY:
                hk_id = msg.wParam
                hk_name = self._hotkey_ids.get(hk_id, "")
                if hk_name == "toggle_passthrough":
                    self._toggle_mouse_interaction()
                    return True, 0
                elif hk_name == "count_plus":
                    self._adjust_nightmare_count(1)
                    return True, 0
                elif hk_name == "count_minus":
                    self._adjust_nightmare_count(-1)
                    return True, 0
                elif hk_name == "counter_prev":
                    self.counter_navigate.emit(-1)
                    return True, 0
                elif hk_name == "counter_next":
                    self.counter_navigate.emit(1)
                    return True, 0
                elif hk_name == "nightmare_plus":
                    self._emit_nightmare_adjust(1)
                    return True, 0
                elif hk_name == "nightmare_minus":
                    self._emit_nightmare_adjust(-1)
                    return True, 0
        return super().nativeEvent(eventType, message)
    
    def _toggle_mouse_interaction(self):
        """切换鼠标交互状态"""
        self.mouse_enabled = not self.mouse_enabled
        if self.mouse_enabled:
            self._apply_passthrough(False)
            
            # 更新状态显示
            self.status_label.setText("Ctrl+N: 可交互 ✗")
            self.status_label.setStyleSheet("color: #10b981; font-size: 10px;")
        else:
            self._apply_passthrough(True)
            
            # 更新状态显示
            self.status_label.setText("Ctrl+N: 鼠标穿透 ✓")
            self.status_label.setStyleSheet("color: #a78bfa; font-size: 10px;")
    
    def _apply_passthrough(self, enabled):
        """统一设置鼠标穿透/交互状态"""
        self.mouse_enabled = not enabled
        self.setAttribute(Qt.WA_TransparentForMouseEvents, enabled)
        try:
            import win32gui
            import win32con
            hwnd = int(self.winId())
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if enabled:
                ex_style |= win32con.WS_EX_TRANSPARENT
            else:
                ex_style &= ~win32con.WS_EX_TRANSPARENT
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
        except ImportError:
            pass

    def _set_transparent_mode(self):
        """初始设置为透明穿透模式"""
        self._apply_passthrough(True)
        self.setWindowOpacity(self.normal_opacity)
        
    def _activate_interactive_mode(self):
        """激活交互模式"""
        if not self.interactive_mode:
            self.interactive_mode = True
            self._apply_passthrough(False)
            self.setWindowOpacity(1.0)
            
    def _deactivate_interactive_mode(self):
        """取消交互模式，恢复穿透"""
        if self.interactive_mode:
            self.interactive_mode = False
            self._apply_passthrough(True)
            self.setWindowOpacity(self.normal_opacity)
            self.hover_timer.stop()
    
    def enterEvent(self, event):
        """鼠标进入悬浮窗区域"""
        if not self.is_locked:
            self.hover_timer.start()  # 启动定时器
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开悬浮窗区域"""
        self.hover_timer.stop()  # 停止定时器
        self._deactivate_interactive_mode()  # 立即恢复穿透
        super().leaveEvent(event)
        
    def update_data(self, pokemon_name, type_, count, target, is_locked=False, nightmare_count=0, icon_id=0):
        """更新悬浮窗数据"""
        self.poke_name_label.setText(pokemon_name)
        lock_status = "🔒 锁定" if is_locked else f"锁定：{type_}"
        self.lock_label.setText(lock_status)
        self.count_label.setText(f"{count}/{target}")
        self.progress_bar.setMaximum(target)
        self.progress_bar.setValue(count)
        remaining = target - count
        self.remaining_label.setText(f"保底剩余 {remaining}")
        self.nightmare_label.setText(f"童话事件提示: {nightmare_count}")
        
        # 更新本地缓存
        self.current_breakthrough_count = count
        self.current_nightmare_count = nightmare_count
        
        # 加载精灵图标
        self._load_pokemon_icon(pokemon_name, icon_id)
    
    def update_current_lkwg(self, lkwg_name):
        """更新当前洛克王国精灵显示"""
        if lkwg_name:
            text = f"当前精灵：【{lkwg_name}】"
            self.current_lkwg_label.setText(text)
            print(f"✅ 设置文本: {text}")
        else:
            # OCR识别不到时，清空精灵名字，但保留“当前精灵：”
            self.current_lkwg_label.setText("当前精灵：")
            print(f"❌ OCR未识别到精灵，重置标签")

    def _load_pokemon_icon(self, pokemon_name, icon_id=0):
        """加载精灵图标"""
        # 获取基础目录
        base_dir = os.path.join(os.path.dirname(__file__), '..')
        
        image_loaded = False
        
        # 优先尝试使用icon_id从tj/images加载
        if icon_id > 0:
            image_dir = os.path.join(base_dir, "image", "tj", "images")
            image_path = os.path.join(image_dir, f"{icon_id:03d}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.icon_label.setPixmap(scaled_pixmap)
                    image_loaded = True
        
        # 如果icon_id未加载，尝试从ys文件夹加载（支持赛季目录）
        if not image_loaded:
            from core.pokemon_data import get_current_season
            season = get_current_season()
            
            # 先尝试从赛季子目录加载
            image_dir = os.path.join(base_dir, "image", "ys", season)
            image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            
            # 如果赛季目录没有，尝试从其他赛季目录加载
            if not os.path.exists(image_path):
                for s in ["第一赛季", "第二赛季", "第三赛季"]:
                    if s == season:
                        continue
                    other_dir = os.path.join(base_dir, "image", "ys", s)
                    other_path = os.path.join(other_dir, f"{pokemon_name}.png")
                    if os.path.exists(other_path):
                        image_path = other_path
                        break
            
            # 如果赛季目录都没有，尝试从通用目录加载（向后兼容）
            if not os.path.exists(image_path):
                image_dir = os.path.join(base_dir, "image", "ys")
                image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.icon_label.setPixmap(scaled_pixmap)
                    image_loaded = True
        
        # 如果都未加载，使用默认emoji
        if not image_loaded:
            self.icon_label.setText("🐾")
            self.icon_label.setStyleSheet("font-size: 16px; background: transparent;")
    
    def update_nightmare_count(self, count):
        """更新童话事件提示数"""
        self.current_nightmare_count = count
        self.nightmare_label.setText(f"童话事件提示: {count}")
    
    def _adjust_nightmare_count(self, delta):
        """调整童话事件计数（通过快捷键 +/-）"""
        # 更新本地计数
        self.current_breakthrough_count = max(0, self.current_breakthrough_count + delta)
        
        # 发射信号通知主窗口
        self.breakthrough_count_changed.emit(delta)
        
        # 立即更新显示
        self.count_label.setText(f"{self.current_breakthrough_count}/{self.progress_bar.maximum()}")
        remaining = self.progress_bar.maximum() - self.current_breakthrough_count
        self.remaining_label.setText(f"保底剩余 {remaining}")
        self.progress_bar.setValue(self.current_breakthrough_count)
        
        # 显示临时提示颜色
        if delta > 0:
            self.count_label.setStyleSheet("color: #10b981; font-size: 36px; font-weight: bold;")
        else:
            self.count_label.setStyleSheet("color: #f59e0b; font-size: 36px; font-weight: bold;")
        
        # 1秒后恢复原样式
        QTimer.singleShot(1000, lambda: self.count_label.setStyleSheet(
            "color: #f8f0ff; font-size: 36px; font-weight: bold;"
        ))
    
    def _emit_nightmare_adjust(self, delta):
        """发射童话事件提示调整信号（快捷键《》调用）"""
        self.nightmare_count_changed.emit(delta)
    
    def set_size(self, size_name):
        """设置悬浮窗大小
        
        Args:
            size_name: 'small', 'medium', 或 'large'
        """
        if size_name not in self.size_configs:
            return
        
        self.current_size = size_name
        config = self.size_configs[size_name]
        
        # 调整窗口大小
        width, height = config["size"]
        self._base_height = height  # 更新基础高度
        self.resize(width, height)
        
        # 调整布局间距
        self.layout().setContentsMargins(*config["margins"])
        self.layout().setSpacing(config["spacing"])
        
        # 根据尺寸调整字体大小
        self._adjust_font_sizes(size_name)
        
        # 如果性能监控面板正显示，重新计算窗口高度
        if self.performance_monitor.isVisible():
            self._resize_for_perf_monitor()
    
    def _adjust_font_sizes(self, size_name):
        """根据尺寸调整字体大小"""
        font_sizes = {
            "small": {
                "icon": 14,
                "name": 12,
                "info": 10,
                "current_lkwg": 11,
                "count": 28,
                "remaining": 10,
                "nightmare": 10
            },
            "medium": {
                "icon": 16,
                "name": 14,
                "info": 12,
                "current_lkwg": 13,
                "count": 36,
                "remaining": 12,
                "nightmare": 12
            },
            "large": {
                "icon": 18,
                "name": 16,
                "info": 14,
                "current_lkwg": 15,
                "count": 44,
                "remaining": 14,
                "nightmare": 14
            }
        }
        
        sizes = font_sizes[size_name]
        
        # 更新各个元素的样式
        # 这里需要通过遍历子组件来找到对应的标签并更新
        # 由于PySide6的限制，我们需要重新应用样式
        
    def toggle_lock(self):
        """切换锁定状态"""
        self.is_locked = not self.is_locked
        if self.is_locked:
            self.btn_lock.setText("🔒")
            self.btn_lock.setToolTip("已锁定，点击解锁")
        else:
            self.btn_lock.setText("📍")
            self.btn_lock.setToolTip("锁定/解锁位置")
    
    def set_performance_monitor_visible(self, visible):
        """显示/隐藏性能监控面板，自动调整窗口高度"""
        self.performance_monitor.setVisible(visible)
        self._resize_for_perf_monitor()

    def _resize_for_perf_monitor(self):
        """根据性能监控面板的当前可见状态和高度调整窗口"""
        # 强制刷新布局，确保 setVisible 等变更已生效
        self.layout().invalidate()
        self.layout().activate()
        if self.performance_monitor.isVisible():
            extra = self.performance_monitor.widget_height() + self.layout().spacing()
            self.resize(self.width(), self._base_height + extra)
        else:
            self.resize(self.width(), self._base_height)

    def set_performance_charts_visible(self, visible):
        """显示/隐藏曲线图（性能监控的子功能）"""
        self.performance_monitor.set_charts_visible(visible)
    
    def expand_to_main(self):
        """切换回主窗口"""
        if self.parent():
            self.hide()
            self.parent().show()
    
    def paintEvent(self, event):
        """绘制半透明背景和毛玻璃效果"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 半透明背景 + 边框（一次性绘制）
        bg_color = QColor(18, 8, 34, 235)  # rgba(18, 8, 34, 0.92)
        border_color = QColor(157, 78, 221, 128)  # rgba(157, 78, 221, 0.5)
        
        # 设置画笔宽度为2像素
        pen = painter.pen()
        pen.setWidth(2)
        pen.setColor(border_color)
        painter.setPen(pen)
        painter.setBrush(QBrush(bg_color))
        
        # 绘制圆角矩形（向内偏移1像素避免边框被裁剪）
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 16, 16)
    
    def mousePressEvent(self, event):
        """鼠标按下开始拖拽"""
        if event.button() == Qt.LeftButton and not self.is_locked:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动实现拖拽"""
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None and not self.is_locked:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        self.drag_pos = None
        event.accept()
