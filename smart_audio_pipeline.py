"""
smart_audio_pipeline.py
Kết hợp AudioProcessor (lọc nhiễu) và AudioClassifier (nhận diện AI)
"""
import time
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.live import Live

# Import các module của bạn
from audio_classifier import AudioClassifier, SoundType
from audio_processor import AudioProcessor

class SmartAudioSystem:
    def __init__(self):
        # 1. Khởi tạo Processor
        self.processor = AudioProcessor(rate=16000)
        
        # 2. Khởi tạo Classifier
        # Lưu ý: Classifier này đã load EnvSoundModel bên trong
        self.classifier = AudioClassifier(rate=16000)
        
        self.is_running = False
        self.console = Console()

    def start(self):
        """Bắt đầu stream và pipeline"""
        self.classifier.start_stream()
        self.is_running = True
        self.processor.reset_states()
        self.console.print("[bold green]Smart Audio Pipeline Started...[/bold green]")

    def stop(self):
        """Dừng hệ thống"""
        self.is_running = False
        self.classifier.stop_stream()
        self.console.print("[bold red]Stopped.[/bold red]")

    def process_and_predict(self):
        """
        Hàm trung tâm:
        1. Đọc Raw Audio từ Mic
        2. Qua bộ lọc (DSP)
        3. Feature Extraction & Rule-base
        4. Deep Learning Prediction
        """
        # 1. Đọc dữ liệu thô (Raw)
        raw_chunk = self.classifier.read_audio_chunk()
        if raw_chunk is None:
            return None

        # 2. Xử lý tín hiệu (DSP Enhancement)
        # Tín hiệu này đã sạch noise thấp và cân bằng âm lượng
        clean_chunk = self.processor.process(raw_chunk)

        # 3. Phân loại (Sử dụng dữ liệu ĐÃ LỌC để dự đoán)
        # Lưu ý: Chúng ta gọi các hàm nội bộ của classifier nhưng truyền clean_chunk vào
        
        # A. Rule-based (Silence/Speech/Music/Noise)
        # Logic này nằm trong classifier.classify_sound
        basic_type = self.classifier.classify_sound(clean_chunk)
        
        # Trích xuất đặc trưng để hiển thị
        features = self.classifier.extract_features(clean_chunk)
        
        # B. Deep Learning (EnvSoundModel)
        # Logic: Nạp clean_chunk vào buffer -> Nếu đủ 3s -> Predict
        env_label = None
        env_conf = 0.0
        
        # Chỉ gọi model DL nếu không phải im lặng và RMS đủ lớn (sau khi AGC)
        # Ngưỡng RMS ở đây có thể để cao hơn chút vì AGC đã boost tín hiệu
        if basic_type != SoundType.SILENCE and features['rms'] > 0.02:
            raw_label, raw_conf = self.classifier._update_env_buffer_and_predict(clean_chunk)
            if raw_label:
                env_label = raw_label
                env_conf = raw_conf

        return {
            "basic_type": basic_type,
            "env_label": env_label,
            "env_conf": env_conf,
            "rms_raw": np.sqrt(np.mean(raw_chunk**2)), # Để so sánh hiệu quả AGC
            "rms_clean": features['rms'],
            "gain_applied": self.processor.current_gain
        }

    def run_demo(self):
        """Chạy demo hiển thị trực quan"""
        self.start()
        
        table = Table(title="Smart Audio Analysis", show_lines=True)
        table.add_column("DSP Status", style="cyan", width=25)
        table.add_column("Basic Type", style="magenta", width=15)
        table.add_column("AI Prediction (Model)", style="green", justify="center")
        
        try:
            with Live(table, refresh_per_second=4, console=self.console) as live:
                while self.is_running:
                    result = self.process_and_predict()
                    
                    if result:
                        # Format thông tin DSP
                        dsp_info = (
                            f"Gain: {result['gain_applied']:.1f}x\n"
                            f"RMS In : {result['rms_raw']:.4f}\n"
                            f"RMS Out: {result['rms_clean']:.4f}"
                        )
                        
                        # Format AI Label
                        ai_text = "..."
                        if result['env_label']:
                            conf_percent = result['env_conf'] * 100
                            # Highlight nếu độ tin cậy cao
                            color = "bold green" if conf_percent > 70 else "yellow"
                            ai_text = f"[{color}]{result['env_label'].upper()}\n({conf_percent:.1f}%)[/{color}]"
                        
                        # Cập nhật bảng (giữ lại 1 dòng mới nhất hoặc append history tùy ý)
                        # Ở đây mình tạo table mới mỗi frame cho gọn effect, hoặc dùng layout
                        table = Table(title="Smart Audio Analysis (DSP + AI)", box=None)
                        table.add_column("DSP Processing", style="dim cyan")
                        table.add_column("Basic Detection", style="magenta")
                        table.add_column("AI Classification", style="bold white")
                        
                        table.add_row(
                            dsp_info,
                            result['basic_type'].value.upper(),
                            ai_text
                        )
                        live.update(table)
                        
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            self.stop()

if __name__ == "__main__":
    system = SmartAudioSystem()
    system.run_demo()