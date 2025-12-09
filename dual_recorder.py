"""
dual_recorder.py
Ghi âm song song: Raw (Gốc) và Processed (Đã lọc qua AudioProcessor)
Mục đích: So sánh hiệu quả của thuật toán lọc âm/AGC.
"""

import pyaudio
import wave
import numpy as np
import time
from typing import Optional
from audio_processor import AudioProcessor  # Import file xử lý âm thanh của bạn

class DualAudioRecorder:
    def __init__(self, 
                 rate: int = 16000, 
                 chunk: int = 1024, 
                 channels: int = 1,
                 filename_raw: str = "recording_raw.wav",
                 filename_clean: str = "recording_processed.wav"):
        
        self.RATE = rate
        self.CHUNK = chunk
        self.CHANNELS = channels
        self.FORMAT = pyaudio.paInt16
        
        self.filename_raw = filename_raw
        self.filename_clean = filename_clean
        
        self.p = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.processor = AudioProcessor(rate=rate, chunk_size=chunk)
        
        # Buffer để chứa dữ liệu audio
        self.frames_raw = []
        self.frames_clean = []
        self.is_recording = False

    def start_recording(self):
        """Bắt đầu stream ghi âm"""
        self.frames_raw = []
        self.frames_clean = []
        self.processor.reset_states() # Reset bộ lọc
        
        try:
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            self.is_recording = True
            print(f"🎤 Đang ghi âm... (Rate: {self.RATE}Hz)")
        except Exception as e:
            print(f"❌ Lỗi mở stream: {e}")

    def record_loop(self, duration: int = 5):
        """
        Vòng lặp ghi âm chính
        Args:
            duration: Thời gian ghi (giây)
        """
        if not self.is_recording:
            self.start_recording()
            
        print(f"🔴 REC ({duration}s) - Hãy thử nói nhỏ/xa và nói to/gần...")
        
        start_time = time.time()
        try:
            while time.time() - start_time < duration:
                # 1. Đọc dữ liệu thô (bytes -> int16)
                data_bytes = self.stream.read(self.CHUNK, exception_on_overflow=False)
                data_int16 = np.frombuffer(data_bytes, dtype=np.int16)
                
                # Lưu vào buffer Raw (giữ nguyên bytes)
                self.frames_raw.append(data_bytes)
                
                # 2. Chuẩn bị dữ liệu cho Processor (int16 -> float32 [-1, 1])
                # Đây là định dạng mà AudioProcessor mong muốn
                data_float = data_int16.astype(np.float32) / 32768.0
                
                # 3. Xử lý qua AudioProcessor (Lọc + AGC)
                processed_float = self.processor.process(data_float)
                
                # 4. Chuyển đổi ngược lại để lưu file wav (float32 -> int16 -> bytes)
                # Clip để tránh lỗi tràn số khi convert
                processed_float = np.clip(processed_float, -1.0, 1.0)
                processed_int16 = (processed_float * 32767.0).astype(np.int16)
                
                # Lưu vào buffer Clean
                self.frames_clean.append(processed_int16.tobytes())
                
        except KeyboardInterrupt:
            print("\n⏹️ Dừng bởi người dùng.")
        finally:
            self.stop_and_save()

    def stop_and_save(self):
        """Dừng stream và lưu ra 2 file"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.is_recording = False
        
        # Lưu file Raw
        self._save_wav(self.filename_raw, self.frames_raw)
        
        # Lưu file Processed
        self._save_wav(self.filename_clean, self.frames_clean)
        
        print("\n✅ Đã xuất file thành công:")
        print(f"   1. {self.filename_raw} (Gốc - có thể nhỏ/ồn)")
        print(f"   2. {self.filename_clean} (Đã xử lý - To hơn/sạch hơn)")
        
        self.p.terminate()

    def _save_wav(self, filename, frames):
        """Hàm hỗ trợ lưu file WAV"""
        if not frames:
            return
            
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

# ==========================================
# CHẠY TEST
# ==========================================
if __name__ == "__main__":
    # Tạo object ghi âm
    recorder = DualAudioRecorder(
        filename_raw="test_before.wav",
        filename_clean="test_after.wav"
    )
    
    # Ghi âm trong 8 giây
    # Bạn hãy thử:
    # 1. 3 giây đầu: Nói bình thường
    # 2. 3 giây giữa: Đi ra xa 2-3 mét nói nhỏ (để test AGC)
    # 3. 2 giây cuối: Gõ bàn hoặc tạo tiếng ồn trầm (để test High-pass filter)
    recorder.record_loop(duration=5)