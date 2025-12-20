import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time
import math
import datetime
import sys

# Import module hệ thống của bạn
from smart_audio_pipeline import SmartAudioSystem
from sound_detector import SoundDetector
from audio_classifier import SoundType

# --- COLOR PALETTE ---
COLOR_BG_MAIN = "#050a14"
COLOR_BG_PANEL = "#0a1221"
COLOR_ACCENT = "#ff9f1c"
COLOR_TEXT = "#ffcf99"
COLOR_TEXT_DIM = "#5d6d7e"
COLOR_BAR_FILL = "#ff8000"

class SmartAudioGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ReSpeaker Smart Audio Dashboard")
        self.root.geometry("1280x720")
        self.root.configure(bg=COLOR_BG_MAIN)
        self.root.minsize(1024, 600)

        # --- Backend Systems ---
        self.audio_system = None
        self.sound_detector = None
        
        self.is_running = False
        self.data_queue = queue.Queue()
        self.thread = None

        # --- Setup Styles & UI ---
        self.setup_styles()
        self.setup_ui()
        
        # Init System (Lazy check - Chỉ kiểm tra trạng thái, không báo lỗi ngay)
        self.root.after(100, self.init_backend_status)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam') 

        self.style.configure("Main.TFrame", background=COLOR_BG_MAIN)
        self.style.configure("Panel.TFrame", background=COLOR_BG_PANEL, relief="flat")
        
        self.style.configure("TLabel", background=COLOR_BG_PANEL, foreground=COLOR_TEXT, font=("Segoe UI", 11))
        self.style.configure("Header.TLabel", background=COLOR_BG_MAIN, foreground=COLOR_ACCENT, font=("Segoe UI", 24, "bold"))
        self.style.configure("SubHeader.TLabel", background=COLOR_BG_PANEL, foreground=COLOR_ACCENT, font=("Segoe UI", 14, "bold"))
        self.style.configure("BigValue.TLabel", background=COLOR_BG_PANEL, foreground="#ffffff", font=("Segoe UI", 28, "bold"))
        
        self.style.configure("TLabelframe", background=COLOR_BG_PANEL, bordercolor=COLOR_ACCENT, relief="solid", borderwidth=1)
        self.style.configure("TLabelframe.Label", background=COLOR_BG_PANEL, foreground=COLOR_ACCENT, font=("Segoe UI", 12, "bold"))

        self.style.configure("Orange.Horizontal.TProgressbar", 
                             troughcolor=COLOR_BG_MAIN, 
                             bordercolor=COLOR_BG_PANEL, 
                             background=COLOR_ACCENT, 
                             lightcolor=COLOR_BAR_FILL, 
                             darkcolor=COLOR_BAR_FILL)

    def setup_ui(self):
        # --- HEADER SECTION ---
        header_frame = ttk.Frame(self.root, style="Main.TFrame")
        header_frame.pack(fill="x", padx=25, pady=15)
        
        lbl_title = ttk.Label(header_frame, text="SMART AUDIO MONITOR", style="Header.TLabel")
        lbl_title.pack(side="left")

        # Control Buttons
        btn_frame = tk.Frame(header_frame, bg=COLOR_BG_MAIN)
        btn_frame.pack(side="right")

        self.btn_start = tk.Button(btn_frame, text="▶ START MONITOR", command=self.start_system,
                                   bg=COLOR_ACCENT, fg="black", font=("Segoe UI", 10, "bold"), 
                                   bd=0, padx=20, pady=8, activebackground="#ffb74d")
        self.btn_start.pack(side="left", padx=5)
        
        self.btn_stop = tk.Button(btn_frame, text="⏹ STOP", command=self.stop_system,
                                  bg="#34495e", fg="white", font=("Segoe UI", 10, "bold"), 
                                  bd=0, padx=20, pady=8, state="disabled")
        self.btn_stop.pack(side="left", padx=5)

        # --- MAIN CONTENT ---
        content_frame = ttk.Frame(self.root, style="Main.TFrame")
        content_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.columnconfigure(2, weight=1)
        content_frame.rowconfigure(0, weight=3) 
        content_frame.rowconfigure(1, weight=1) 

        # 1. DSP PANEL
        pnl_dsp = ttk.LabelFrame(content_frame, text=" SIGNAL PROCESSING ", style="TLabelframe")
        pnl_dsp.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        self._build_dsp_panel(pnl_dsp)

        # 2. AI PANEL
        pnl_ai = ttk.LabelFrame(content_frame, text=" AI EVENT DETECTION ", style="TLabelframe")
        pnl_ai.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
        self._build_ai_panel(pnl_ai)

        # 3. RADAR PANEL
        pnl_radar = ttk.LabelFrame(content_frame, text=" DIRECTION OF ARRIVAL ", style="TLabelframe")
        pnl_radar.grid(row=0, column=2, sticky="nsew", padx=10, pady=5)
        self._build_radar_panel(pnl_radar)

        # --- BOTTOM LOGS ---
        pnl_log = ttk.LabelFrame(content_frame, text=" EVENT LOGS ", style="TLabelframe")
        pnl_log.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)
        
        self.log_tree = ttk.Treeview(pnl_log, columns=("Time", "Detail", "Conf"), show="headings", height=5)
        self.log_tree.heading("Time", text="TIMESTAMP")
        self.log_tree.heading("Detail", text="DETECTED EVENT")
        self.log_tree.heading("Conf", text="CONFIDENCE")
        
        self.log_tree.column("Time", width=150, anchor="center")
        self.log_tree.column("Detail", width=300, anchor="center")
        self.log_tree.column("Conf", width=100, anchor="center")
        
        style_tree = ttk.Style()
        style_tree.configure("Treeview", background=COLOR_BG_PANEL, foreground="white", fieldbackground=COLOR_BG_PANEL, rowheight=25)
        style_tree.map("Treeview", background=[("selected", COLOR_ACCENT)])
        style_tree.configure("Treeview.Heading", background="#2c3e50", foreground="white", font=("Segoe UI", 10, "bold"))
        
        scrollbar = ttk.Scrollbar(pnl_log, orient="vertical", command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=scrollbar.set)
        
        self.log_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)

        # Status Bar
        self.lbl_status = tk.Label(self.root, text="System Ready", bg=COLOR_BG_MAIN, fg=COLOR_TEXT_DIM, anchor="e", font=("Consolas", 9))
        self.lbl_status.pack(side="bottom", fill="x", padx=20, pady=2)

    def _build_dsp_panel(self, parent):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="INPUT LEVEL (RAW)", style="SubHeader.TLabel", font=("Segoe UI", 10)).pack(anchor="w")
        self.pb_rms_raw = ttk.Progressbar(frame, orient="horizontal", length=100, mode="determinate", style="Orange.Horizontal.TProgressbar")
        self.pb_rms_raw.pack(fill="x", pady=(5, 20))
        
        ttk.Label(frame, text="OUTPUT LEVEL (CLEAN)", style="SubHeader.TLabel", font=("Segoe UI", 10)).pack(anchor="w")
        self.pb_rms_clean = ttk.Progressbar(frame, orient="horizontal", length=100, mode="determinate", style="Orange.Horizontal.TProgressbar")
        self.pb_rms_clean.pack(fill="x", pady=(5, 20))
        
        ttk.Label(frame, text="AGC GAIN", style="SubHeader.TLabel", font=("Segoe UI", 10)).pack(anchor="center", pady=(10,0))
        self.lbl_gain = ttk.Label(frame, text="1.0x", style="BigValue.TLabel", foreground="#3498db")
        self.lbl_gain.pack(anchor="center")

    def _build_ai_panel(self, parent):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        container = ttk.Frame(frame, style="Panel.TFrame")
        container.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0)
        
        ttk.Label(container, text="DETECTED CLASS", style="SubHeader.TLabel", font=("Segoe UI", 12)).pack(anchor="center", pady=(0, 15))
        self.lbl_env_label = ttk.Label(container, text="...", style="BigValue.TLabel", font=("Segoe UI", 40, "bold"), foreground=COLOR_ACCENT)
        self.lbl_env_label.pack(anchor="center", pady=(0, 15))
        
        self.lbl_conf = ttk.Label(container, text="Confidence: 0%", style="TLabel", font=("Consolas", 12))
        self.lbl_conf.pack(anchor="center", pady=(0, 5))
        self.pb_conf = ttk.Progressbar(container, orient="horizontal", length=200, mode="determinate", style="Orange.Horizontal.TProgressbar")
        self.pb_conf.pack(fill="x", padx=40, pady=(0, 15))

    def _build_radar_panel(self, parent):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.canvas_size = 220
        self.canvas = tk.Canvas(frame, width=self.canvas_size, height=self.canvas_size, bg=COLOR_BG_PANEL, highlightthickness=0)
        self.canvas.pack(anchor="center")
        self.draw_radar_grid()
        self.lbl_direction = ttk.Label(frame, text="SOURCE: N/A", style="BigValue.TLabel", font=("Consolas", 16))
        self.lbl_direction.pack(anchor="center", pady=15)

    def draw_radar_grid(self):
        c = self.canvas_size // 2
        r_outer = c - 10
        r_inner = r_outer // 2
        grid_color = "#34495e"
        self.canvas.create_oval(c-r_outer, c-r_outer, c+r_outer, c+r_outer, outline=grid_color, width=2)
        self.canvas.create_oval(c-r_inner, c-r_inner, c+r_inner, c+r_inner, outline=grid_color, dash=(2, 4))
        self.canvas.create_line(c, c-r_outer, c, c+r_outer, fill=grid_color)
        self.canvas.create_line(c-r_outer, c, c+r_outer, c, fill=grid_color)
        
        text_color = COLOR_TEXT_DIM
        offset = 12
        self.canvas.create_text(c, c-r_outer+offset, text="N", fill=text_color, font=("Arial", 9, "bold"))
        self.canvas.create_text(c, c+r_outer-offset, text="S", fill=text_color, font=("Arial", 9, "bold"))
        self.canvas.create_text(c-r_outer+offset, c, text="W", fill=text_color, font=("Arial", 9, "bold"))
        self.canvas.create_text(c+r_outer-offset, c, text="E", fill=text_color, font=("Arial", 9, "bold"))
        
        self.needle = self.canvas.create_line(c, c, c, 20, fill=COLOR_ACCENT, width=4, arrow=tk.LAST, tags="needle", state="hidden")
        self.center_dot = self.canvas.create_oval(c-5, c-5, c+5, c+5, fill=COLOR_ACCENT, outline=COLOR_BG_MAIN)

    def update_radar(self, angle):
        if angle is None:
            self.canvas.itemconfigure("needle", state="hidden")
            self.lbl_direction.config(text="SOURCE: N/A", foreground="#5d6d7e")
            return
        self.canvas.itemconfigure("needle", state="normal")
        c = self.canvas_size // 2
        r = (self.canvas_size // 2) - 25
        rad = math.radians(angle - 90)
        x = c + r * math.cos(rad)
        y = c + r * math.sin(rad)
        self.canvas.coords("needle", c, c, x, y)
        self.lbl_direction.config(text=f"SOURCE: {angle}°", foreground=COLOR_ACCENT)

    # --- CORE LOGIC ĐÃ SỬA ĐỔI ---

    def init_backend_status(self):
        """Chỉ khởi tạo detector để check trạng thái ban đầu, không bật Audio System"""
        try:
            if not self.sound_detector:
                self.sound_detector = SoundDetector()
            
            # Thử kết nối nhẹ để biết trạng thái
            if self.sound_detector.connect():
                self.lbl_status.config(text="System Ready: ReSpeaker Mic Array Detected")
            else:
                self.lbl_status.config(text="Waiting for ReSpeaker connection...")
        except Exception:
            self.lbl_status.config(text="Hardware Check Failed")

    def check_hardware_ready(self):
        """
        Hàm kiểm tra cứng: 
        - Nếu chưa có đối tượng -> Tạo mới.
        - Nếu đã có -> Kiểm tra kết nối.
        """
        try:
            # 1. Xử lý SoundDetector (Kiểm tra hướng/kết nối USB)
            if self.sound_detector is None:
                self.sound_detector = SoundDetector()

            # Thử kết nối (nếu chưa kết nối)
            if not self.sound_detector.connect():
                # Nếu kết nối thất bại, hủy luôn đối tượng để lần sau tạo lại sạch sẽ
                self.sound_detector = None 
                return False

            # 2. Xử lý AudioSystem (Hệ thống thu âm & AI)
            # Luôn đảm bảo tạo mới nếu nó đang là None (do nút Stop gán về None)
            if self.audio_system is None:
                self.audio_system = SmartAudioSystem()
            
            return True

        except Exception as e:
            print(f"Hardware Check Error: {e}")
            # Nếu có lỗi bất ngờ, reset hết về None cho an toàn
            self.sound_detector = None
            self.audio_system = None
            return False

    def start_system(self):
        # 1. KIỂM TRA PHẦN CỨNG LẠI TỪ ĐẦU
        self.lbl_status.config(text="Checking Hardware Connection...")
        self.root.update()

        # Gọi hàm check, hàm này sẽ TỰ ĐỘNG TẠO MỚI audio_system nếu nó đang là None
        if not self.check_hardware_ready():
            messagebox.showerror(
                "ReSpeaker Not Found", 
                "⚠ Không tìm thấy thiết bị ReSpeaker!\n\n"
                "Vui lòng:\n"
                "1. Cắm cáp USB vào máy tính.\n"
                "2. Kiểm tra driver.\n"
                "3. Nhấn Start lại."
            )
            self.lbl_status.config(text="Error: ReSpeaker Not Found")
            return

        # 2. Bắt đầu hệ thống
        try:
            self.is_running = True
            
            # Lúc này self.audio_system chắc chắn đã được tạo mới bởi check_hardware_ready
            self.audio_system.start() 
            
            # UI Updates
            self.btn_start.config(state="disabled", bg="#2c3e50", fg="gray")
            self.btn_stop.config(state="normal", bg="#c0392b")
            self.lbl_status.config(text="Monitoring active...")
            
            # Start Processing Thread
            self.thread = threading.Thread(target=self.processing_loop, daemon=True)
            self.thread.start()
            self.update_ui_loop()
            
        except Exception as e:
            self.is_running = False
            messagebox.showerror("Error", f"Failed to start audio stream: {e}")
            self.lbl_status.config(text="Start Failed")
            
            # Reset trạng thái nếu start lỗi
            self.stop_system()

    def stop_system(self):
        """Dừng hệ thống và HỦY HẾT đối tượng để lần sau Start sẽ tạo mới"""
        self.is_running = False 
        self.lbl_status.config(text="Stopping...")
        self.root.update()

        try:
            # 1. Dừng Audio System
            if self.audio_system:
                self.audio_system.stop()
            
            # 2. Ngắt kết nối Detector (để giải phóng cổng USB hoàn toàn)
            if self.sound_detector:
                self.sound_detector.disconnect()

        except Exception as e:
            print(f"Error stopping: {e}")
        finally:
            # --- QUAN TRỌNG NHẤT: GÁN VỀ NONE ---
            # Việc này ép buộc hàm start_system lần sau phải chạy lại `SmartAudioSystem()`
            # để tạo ra một instance mới tinh, tránh lỗi 'NoneType has no attribute open'
            self.audio_system = None
            self.sound_detector = None

            # Reset UI
            self.btn_start.config(state="normal", bg=COLOR_ACCENT, fg="black")
            self.btn_stop.config(state="disabled", bg="#34495e")
            self.lbl_status.config(text="Stopped. Ready to restart.")
            
            # Reset hiển thị
            self.pb_rms_raw['value'] = 0
            self.pb_rms_clean['value'] = 0
            self.lbl_env_label.config(text="...")
            self.pb_conf['value'] = 0
            self.update_radar(None)

            # Clear queue
            with self.data_queue.mutex:
                self.data_queue.queue.clear()

    def log_event(self, timestamp, detail, conf):
        self.log_tree.insert("", 0, values=(timestamp, detail, conf))
        if len(self.log_tree.get_children()) > 50:
            self.log_tree.delete(self.log_tree.get_children()[-1])

    def processing_loop(self):
        while self.is_running:
            try:
                if self.audio_system:
                    audio_result = self.audio_system.process_and_predict()
                    
                    direction = None
                    if self.sound_detector and self.sound_detector.connected:
                        direction = self.sound_detector.get_direction()
                    
                    if audio_result:
                        self.data_queue.put({
                            "audio": audio_result,
                            "direction": direction,
                            "ts": datetime.datetime.now().strftime("%H:%M:%S")
                        })
                time.sleep(0.05)
            except Exception as e:
                print(f"Loop error: {e}")
                break

    def update_ui_loop(self):
        try:
            # Xử lý tất cả item trong queue
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                audio = data.get("audio")
                direction = data.get("direction")
                ts = data.get("ts")
                
                # DSP
                self.pb_rms_raw['value'] = min(audio['rms_raw'] * 1200, 100) 
                self.pb_rms_clean['value'] = min(audio['rms_clean'] * 1200, 100)
                self.lbl_gain.config(text=f"{audio['gain_applied']:.1f}x")
                
                # AI Label
                env_label = audio['env_label']
                if env_label:
                    self.lbl_env_label.config(text=env_label.upper())
                    conf = audio['env_conf'] * 100
                    self.pb_conf['value'] = conf
                    self.lbl_conf.config(text=f"Confidence: {conf:.1f}%")
                    
                    if conf > 60:
                        self.log_event(ts, env_label.upper(), f"{conf:.0f}%")
                
                # Radar
                self.update_radar(direction)
                
        except queue.Empty:
            pass
        
        # Chỉ gọi lại loop nếu is_running vẫn là True
        if self.is_running:
            self.root.after(50, self.update_ui_loop)

    def on_closing(self):
        try:
            self.is_running = False
            if self.audio_system:
                self.audio_system.stop()
            if self.sound_detector:
                self.sound_detector.disconnect()
            self.root.destroy()
            sys.exit(0)
        except Exception as e:
            print(f"Error while closing: {e}")
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartAudioGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()