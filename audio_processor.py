"""
audio_processor.py - Phiên bản Clean Background
Kiểm soát AGC để không phóng đại tiếng ồn nền.
"""
import numpy as np
from scipy import signal

class AudioProcessor:
    def __init__(self, rate=16000, chunk_size=1024):
        self.rate = rate
        self.chunk_size = chunk_size
        
        # --- 1. BANDPASS FILTER (Giữ nguyên độ ấm) ---
        # Vẫn giữ 100Hz để giọng không bị mỏng.
        self.sos = signal.butter(4, [100, 7500], 'bandpass', fs=rate, output='sos')
        self.sos_state = signal.sosfilt_zi(self.sos)
        
        # --- 2. SPECTRAL GATING (Giữ nguyên độ trong) ---
        # Giữ mức 0.6 để không làm méo tiếng.
        self.spectral_threshold = 0.6
        
        # --- 3. AGC & NOISE GATE (ĐIỀU CHỈNH QUAN TRỌNG) ---
        self.agc_enabled = True
        
        # Max Gain: Giảm mạnh từ 25.0 xuống 15.0 dB
        # Tác dụng: Đây là "phanh hãm". Khi tín hiệu nhỏ (nền), nó không được phép
        # phóng to lên gấp chục lần nữa. Tiếng ồn sẽ giữ ở mức thấp.
        self.agc_max_gain = 15.0      
        
        self.agc_target_rms = 0.12
        self.agc_smooth = 0.1
        
        # Gate Threshold: Tăng nhẹ từ 0.008 lên 0.012
        # Tác dụng: Bắt buộc tín hiệu phải lớn hơn một chút (tiếng nói thực sự) 
        # thì mới bắt đầu kích hoạt khuếch đại.
        self.gate_threshold = 0.012   
        
        # Gate Ratio: Giảm từ 0.20 xuống 0.10 (10%)
        # Tác dụng: Khi không nói, dìm tiếng nền xuống còn 10%.
        # Mức này đủ nhỏ để không gây ồn, nhưng không bị tắt ngúm.
        self.gate_ratio = 0.10        
        
        self.current_gain = 1.0

    def apply_bandpass(self, chunk: np.ndarray) -> np.ndarray:
        filtered, self.sos_state = signal.sosfilt(self.sos, chunk, zi=self.sos_state)
        return filtered

    def apply_spectral_gate(self, chunk: np.ndarray) -> np.ndarray:
        # 1. FFT
        fft_data = np.fft.rfft(chunk)
        magnitude = np.abs(fft_data)
        
        # 2. Ngưỡng nhiễu
        noise_floor = np.mean(magnitude)
        
        # 3. Masking
        mask = magnitude > (noise_floor * self.spectral_threshold)
        mask = mask.astype(float)
        
        # 4. IFFT
        fft_filtered = fft_data * mask
        filtered_chunk = np.fft.irfft(fft_filtered)
        
        return filtered_chunk

    def apply_agc(self, chunk: np.ndarray) -> np.ndarray:
        if not self.agc_enabled:
            return chunk

        chunk_rms = np.sqrt(np.mean(chunk**2) + 1e-9)
        
        if chunk_rms < self.gate_threshold:
            # Vùng Silence: Giữ 10% volume (giảm ồn nền)
            target_gain = self.gate_ratio
            smoothing = 0.2 
        else:
            # Vùng Speech: Khuếch đại nhưng bị kìm hãm bởi agc_max_gain = 15
            target_gain = self.agc_target_rms / (chunk_rms + 1e-9)
            
            max_linear_gain = 10 ** (self.agc_max_gain / 20)
            if target_gain > max_linear_gain:
                target_gain = max_linear_gain
            
            if target_gain < 1.0: target_gain = 1.0
            smoothing = self.agc_smooth

        self.current_gain = (self.current_gain * (1 - smoothing)) + (target_gain * smoothing)
        processed = chunk * self.current_gain
        processed = np.clip(processed, -1.0, 1.0)
        return processed

    def process(self, chunk: np.ndarray) -> np.ndarray:
        if len(chunk) == 0: return chunk
        
        filtered = self.apply_bandpass(chunk)
        spectral_clean = self.apply_spectral_gate(filtered)
        normalized = self.apply_agc(spectral_clean)
        
        return normalized

    def reset_states(self):
        self.sos_state = signal.sosfilt_zi(self.sos)
        self.current_gain = 1.0