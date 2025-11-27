# """Audio Classifier Module for ReSpeaker"""

# import pyaudio
# import numpy as np
# import wave
# import time
# from scipy import signal
# from typing import Dict, List, Optional
# from enum import Enum


# class SoundType(Enum):
#     SILENCE = "silence"
#     SPEECH = "speech"
#     MUSIC = "music"
#     NOISE = "noise"
#     UNKNOWN = "unknown"


# class AudioClassifier:
    
#     CHUNK = 1024
#     RATE = 16000
#     CHANNELS = 6
#     FORMAT = pyaudio.paInt16
    
#     SILENCE_THRESHOLD = 500
#     SPEECH_ZCR_MIN = 0.01
#     SPEECH_ZCR_MAX = 0.15
#     MUSIC_ZCR_MIN = 0.001
#     MUSIC_ZCR_MAX = 0.05
    
#     def __init__(self, device_index: Optional[int] = None):
#         self.device_index = device_index
#         self.p = pyaudio.PyAudio()
#         self.stream = None
#         self.is_recording = False
        
#         if device_index is None:
#             self.device_index = self._find_respeaker_device()

#     def _find_respeaker_device(self) -> Optional[int]:
#         info = self.p.get_host_api_info_by_index(0)
#         num_devices = info.get('deviceCount')
        
#         for i in range(num_devices):
#             device_info = self.p.get_device_info_by_host_api_device_index(0, i)
#             if device_info.get('maxInputChannels') > 0:
#                 name = device_info.get('name')
#                 if 'ReSpeaker' in name or 'UAC1.0' in name:
#                     print(f"Found ReSpeaker: {name} (index: {i})")
#                     return i
        
#         print("Warning: ReSpeaker not found, using default device")
#         return None

#     def list_audio_devices(self):
#         print("\nAudio Devices:")
#         print("=" * 60)
#         info = self.p.get_host_api_info_by_index(0)
#         num_devices = info.get('deviceCount')
        
#         for i in range(num_devices):
#             device_info = self.p.get_device_info_by_host_api_device_index(0, i)
#             if device_info.get('maxInputChannels') > 0:
#                 print(f"  [{i}] {device_info.get('name')}")
#                 print(f"      Channels: {device_info.get('maxInputChannels')}")
#                 print(f"      Sample Rate: {device_info.get('defaultSampleRate')}")
#                 print()

#     def start_stream(self):
#         try:
#             self.stream = self.p.open(
#                 format=self.FORMAT,
#                 channels=self.CHANNELS,
#                 rate=self.RATE,
#                 input=True,
#                 input_device_index=self.device_index,
#                 frames_per_buffer=self.CHUNK
#             )
#             self.is_recording = True
#             print("Audio stream started")
#             return True
#         except Exception as e:
#             print(f"Error opening stream: {e}")
#             return False

#     def stop_stream(self):
#         if self.stream:
#             self.stream.stop_stream()
#             self.stream.close()
#             self.is_recording = False
#             print("Audio stream stopped")

#     def read_audio_chunk(self) -> Optional[np.ndarray]:
#         if not self.stream or not self.is_recording:
#             return None
        
#         try:
#             data = self.stream.read(self.CHUNK, exception_on_overflow=False)
#             audio_data = np.frombuffer(data, dtype=np.int16)
            
#             audio_channel_0 = audio_data[0::self.CHANNELS]
            
#             return audio_channel_0
#         except Exception as e:
#             print(f"Error reading audio: {e}")
#             return None

#     def calculate_rms(self, audio_data: np.ndarray) -> float:
#         return np.sqrt(np.mean(audio_data.astype(float) ** 2))

#     def calculate_zcr(self, audio_data: np.ndarray) -> float:
#         signs = np.sign(audio_data)
#         signs[signs == 0] = -1
#         zero_crossings = np.abs(np.diff(signs))
#         zcr = np.sum(zero_crossings) / (2 * len(audio_data))
#         return zcr

#     def calculate_spectral_centroid(self, audio_data: np.ndarray) -> float:
#         spectrum = np.abs(np.fft.rfft(audio_data))
#         freqs = np.fft.rfftfreq(len(audio_data), 1/self.RATE)
        
#         if np.sum(spectrum) == 0:
#             return 0
        
#         centroid = np.sum(freqs * spectrum) / np.sum(spectrum)
#         return centroid

#     def extract_features(self, audio_data: np.ndarray) -> Dict:
#         """
#         Trích xuất tất cả đặc trưng từ audio
        
#         Args:
#             audio_data: Numpy array của audio
            
#         Returns:
#             Dictionary chứa các features
#         """
#         if audio_data is None or len(audio_data) == 0:
#             return {}
        
#         return {
#             'rms': self.calculate_rms(audio_data),
#             'zcr': self.calculate_zcr(audio_data),
#             'spectral_centroid': self.calculate_spectral_centroid(audio_data),
#             'max_amplitude': np.max(np.abs(audio_data)),
#             'mean_amplitude': np.mean(np.abs(audio_data))
#         }

#     def classify_sound(self, audio_data: np.ndarray) -> SoundType:
#         """
#         Phân loại loại âm thanh
        
#         Args:
#             audio_data: Numpy array của audio
            
#         Returns:
#             SoundType enum
#         """
#         features = self.extract_features(audio_data)
        
#         if not features:
#             return SoundType.UNKNOWN
#         rms = features['rms']
#         zcr = features['zcr']
        
#         if rms < self.SILENCE_THRESHOLD:
#             return SoundType.SILENCE
        
#         if self.SPEECH_ZCR_MIN < zcr < self.SPEECH_ZCR_MAX:
#             return SoundType.SPEECH
        
#         if self.MUSIC_ZCR_MIN < zcr < self.MUSIC_ZCR_MAX and rms > self.SILENCE_THRESHOLD * 2:
#             return SoundType.MUSIC
        
#         if zcr > self.SPEECH_ZCR_MAX:
#             return SoundType.NOISE
        
#         return SoundType.UNKNOWN

#     def classify_audio(self):
#         chunk = self.read_audio_chunk()
#         if chunk is None:
#             return (SoundType.UNKNOWN, {})
        
#         features = self.extract_features(chunk)
#         sound_type = self.classify_sound(chunk)
        
#         return (sound_type, features)

#     def analyze_continuous(self, duration: int = 10, interval: float = 0.5):
#         if not self.is_recording:
#             print("Stream not opened. Call start_stream() first.")
#             return
        
#         print(f"Analyzing audio for {duration} seconds...")
#         print("=" * 60)
        
#         start_time = time.time()
#         sound_counts = {st: 0 for st in SoundType}
        
#         try:
#             while time.time() - start_time < duration:
#                 chunks = []
#                 for _ in range(int(interval * self.RATE / self.CHUNK)):
#                     chunk = self.read_audio_chunk()
#                     if chunk is not None:
#                         chunks.append(chunk)
                
#                 if chunks:
#                     audio_data = np.concatenate(chunks)
#                     features = self.extract_features(audio_data)
#                     sound_type = self.classify_sound(audio_data)
                    
#                     sound_counts[sound_type] += 1
                    
#                     emoji_map = {
#                         SoundType.SILENCE: "🤫",
#                         SoundType.SPEECH: "🗣️",
#                         SoundType.MUSIC: "🎵",
#                         SoundType.NOISE: "🔊",
#                         SoundType.UNKNOWN: "❓"
#                     }
                    
#                     print(f"{emoji_map[sound_type]} {sound_type.value.upper():8} | "
#                           f"RMS: {features['rms']:7.0f} | "
#                           f"ZCR: {features['zcr']:.4f} | "
#                           f"Centroid: {features['spectral_centroid']:.0f} Hz")
                
#                 time.sleep(max(0, interval - (time.time() - start_time) % interval))
                
#         except KeyboardInterrupt:
#             print("\nStopped analysis")
        
#         print("\n" + "=" * 60)
#         print("STATISTICS:")
#         total = sum(sound_counts.values())
#         for sound_type, count in sound_counts.items():
#             if total > 0:
#                 percent = (count / total) * 100
#                 print(f"  {sound_type.value:8}: {count:3} times ({percent:5.1f}%)")

#     def classify_continuous(self, duration: int = 10):
#         """
#         Phân loại liên tục và trả về kết quả
#         Tương thích với CLI
        
#         Args:
#             duration: Thời gian phân loại (giây)
            
#         Returns:
#             Dict[str, int]: Số lần phát hiện mỗi loại
#         """
#         if not self.start_stream():
#             return {}
        
#         sound_counts = {st.value: 0 for st in SoundType}
#         start_time = time.time()
        
#         try:
#             while time.time() - start_time < duration:
#                 sound_type, _ = self.classify_audio()
#                 sound_counts[sound_type.value] += 1
#                 time.sleep(0.5)
#         except KeyboardInterrupt:
#             pass
        
#         return sound_counts

#     def record_to_file(self, filename: str, duration: int = 5):
#         """
#         Ghi âm và lưu vào file WAV
        
#         Args:
#             filename: Tên file output
#             duration: Thời gian ghi (giây)
#         """
#         if not self.is_recording:
#             print("❌ Stream chưa được mở")
#             return
        
#         print(f"🔴 Đang ghi âm {duration} giây...")
#         frames = []
        
#         for _ in range(0, int(self.RATE / self.CHUNK * duration)):
#             data = self.stream.read(self.CHUNK, exception_on_overflow=False)
#             frames.append(data)
        
#         print(f"💾 Đang lưu vào {filename}...")
        
#         wf = wave.open(filename, 'wb')
#         wf.setnchannels(self.CHANNELS)
#         wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
#         wf.setframerate(self.RATE)
#         wf.writeframes(b''.join(frames))
#         wf.close()
        
#         print(f"Saved: {filename}")

#     def cleanup(self):
#         """Cleanup resources"""
#         self.stop_stream()
#         self.p.terminate()
#         print("Resources cleaned")
    
#     def stop(self):
#         """Alias for cleanup"""
#         self.cleanup()


# def main():
#     """AudioClassifier demo"""
#     print("=" * 60)
#     print("ReSpeaker Audio Classifier Demo")
#     print("=" * 60)
    
#     classifier = AudioClassifier()
    
#     classifier.list_audio_devices()
    
#     if not classifier.start_stream():
#         return
    
#     try:
#         classifier.analyze_continuous(duration=30, interval=0.5)
        
#     except KeyboardInterrupt:
#         print("\n\nStopped")
#     finally:
#         classifier.cleanup()


# if __name__ == '__main__':
#     main()
# audio_classifier.py
# audio_classifier.py

import enum
import time
from typing import Optional, Dict, Any, Tuple

import numpy as np
import pyaudio
import librosa
import tensorflow as tf


# ============================================================
#                CẤU HÌNH CHUNG CHO AUDIO
# ============================================================

DEFAULT_RATE = 16000      # sample rate
DEFAULT_CHUNK = 1024      # số frame mỗi lần đọc (≈ 64ms @16k)
DEFAULT_CHANNELS = 1      # dùng 1 kênh
DEFAULT_FORMAT = pyaudio.paInt16

# Model môi trường train với 5 giây @ 16kHz
ENV_DURATION = 5.0
ENV_SAMPLES = int(DEFAULT_RATE * ENV_DURATION)

# Cửa sổ dùng để predict (ví dụ 3 giây)
ENV_WINDOW_DURATION = 2.0
ENV_WINDOW_SAMPLES = int(DEFAULT_RATE * ENV_WINDOW_DURATION)

# Ngưỡng để quyết định có nên gọi / tin model môi trường
ENV_MIN_RMS = 0.005          # âm lượng tối thiểu để quan tâm (có thể chỉnh 0.015–0.02)
ENV_CONF_THRESHOLD = 0.55    # độ tự tin tối thiểu để chấp nhận label

ENV_MODEL_PATH = "env_sounds_cnn_11cls.h5"


# ============================================================
#                     KIỂU LOẠI ÂM THANH
# ============================================================

class SoundType(enum.Enum):
    UNKNOWN = "unknown"
    SILENCE = "silence"
    SPEECH = "speech"
    MUSIC = "music"
    NOISE = "noise"


# ============================================================
#                   MODEL NHẬN DIỆN 11 LỚP
# ============================================================

ENV_CLASSES = [
    "cat",
    "clapping",
    "clock_alarm",
    "coughing",
    "dog",
    "door_wood_knock",
    "laughing",
    "rain",
    "unknown",
    "water_drops",
    "wind",
]


class EnvSoundModel:
    """
    Model CNN 11 lớp (cat, dog, rain, unknown, ...)
    sử dụng log-mel spectrogram giống pipeline train trên Kaggle.
    """

    def __init__(self, model_path: str = ENV_MODEL_PATH):
        print(f"[EnvSoundModel] Loading model from {model_path} ...")
        self.model = tf.keras.models.load_model(model_path)
        self.classes = ENV_CLASSES

    def _fix_length(self, y: np.ndarray) -> np.ndarray:
        if len(y) < ENV_SAMPLES:
            pad_width = ENV_SAMPLES - len(y)
            y = np.pad(y, (0, pad_width))
        else:
            y = y[:ENV_SAMPLES]
        return y

    def _wav_to_logmel(self, y: np.ndarray, sr: int = DEFAULT_RATE) -> np.ndarray:
        S = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=1024,
            hop_length=512,
            n_mels=64,
        )
        S_db = librosa.power_to_db(S, ref=np.max)  # (n_mels, time)
        return S_db

    def _pad_or_truncate_time(self, mel: np.ndarray) -> np.ndarray:
        # mel: (n_mels, time) -> (time, n_mels)
        TIME_STEPS = 128
        mel = mel.T
        if mel.shape[0] < TIME_STEPS:
            pad_width = TIME_STEPS - mel.shape[0]
            mel = np.pad(mel, ((0, pad_width), (0, 0)))
        else:
            mel = mel[:TIME_STEPS, :]
        return mel

    def _normalize_minmax(self, mel: np.ndarray) -> np.ndarray:
        m_min = mel.min()
        m_max = mel.max()
        return (mel - m_min) / (m_max - m_min + 1e-6)

    def preprocess_waveform(self, y: np.ndarray, sr: int = DEFAULT_RATE) -> np.ndarray:
        if sr != DEFAULT_RATE:
            y = librosa.resample(y, orig_sr=sr, target_sr=DEFAULT_RATE)
        y = self._fix_length(y)
        mel = self._wav_to_logmel(y, sr=DEFAULT_RATE)
        mel = self._pad_or_truncate_time(mel)
        mel = self._normalize_minmax(mel)
        x = mel[np.newaxis, ..., np.newaxis].astype(np.float32)  # (1, T, M, 1)
        return x

    def predict_from_waveform(self, y: np.ndarray, sr: int = DEFAULT_RATE):
        x = self.preprocess_waveform(y, sr)
        probs = self.model.predict(x, verbose=0)[0]  # (11,)
        idx = int(np.argmax(probs))
        label = self.classes[idx]
        conf = float(probs[idx])
        return label, conf, probs


# ============================================================
#                     AUDIO CLASSIFIER
# ============================================================

class AudioClassifier:
    """
    - Đọc audio từ micro bằng PyAudio
    - Tính feature đơn giản (RMS, ZCR, spectral centroid, bandwidth)
    - Rule-based: SILENCE / SPEECH / MUSIC / NOISE
    - Tích hợp EnvSoundModel:
        * Gom buffer
        * Lấy ~3s cuối để predict 11 lớp môi trường
    """

    def __init__(
        self,
        rate: int = DEFAULT_RATE,
        chunk: int = DEFAULT_CHUNK,
        channels: int = DEFAULT_CHANNELS,
        input_device_index: Optional[int] = None,
    ):
        self.RATE = rate
        self.CHUNK = chunk
        self.CHANNELS = channels
        self.FORMAT = DEFAULT_FORMAT
        self.input_device_index = input_device_index

        self.p = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_recording: bool = False

        # buffer cho EnvSoundModel
        self.env_buffer = np.zeros(0, dtype=np.float32)
        self.env_model: Optional[EnvSoundModel] = None

        # cố gắng load model, nếu lỗi thì vẫn cho hệ thống chạy được
        try:
            self.env_model = EnvSoundModel(ENV_MODEL_PATH)
        except Exception as e:
            print(f"[AudioClassifier] Không load được EnvSoundModel: {e}")
            self.env_model = None

    # ---------------------------- STREAM ----------------------------

    def start(self):
        if self.stream is not None:
            return

        print("[AudioClassifier] Opening audio input stream...")
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            input_device_index=self.input_device_index,
        )
        self.is_recording = True
        print("[AudioClassifier] Stream started.")

    def stop(self):
        if self.stream is not None:
            print("[AudioClassifier] Stopping stream...")
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        if self.p is not None:
            self.p.terminate()
            self.p = None

        self.is_recording = False
        print("[AudioClassifier] Stopped.")

    # ==== alias giữ tương thích code cũ ====

    def start_stream(self):
        self.start()

    def stop_stream(self):
        self.stop()

    def cleanup(self):
        self.stop()

    # ------------------------- ĐỌC AUDIO ----------------------------

    def read_audio_chunk(self) -> Optional[np.ndarray]:
        """
        Đọc một chunk từ stream, trả về numpy float32 (1 kênh) đã scale về [-1,1].
        """
        if not self.stream or not self.is_recording:
            return None

        try:
            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)

            # chọn kênh 0 (nếu nhiều kênh)
            audio_channel_0 = audio_data[0::self.CHANNELS].astype(np.float32)

            # scale về [-1,1]
            audio_channel_0 /= 32768.0
            return audio_channel_0
        except Exception as e:
            print(f"[AudioClassifier] Error reading audio: {e}")
            return None

    # ------------------------- FEATURE ------------------------------

    def extract_features(self, chunk: np.ndarray) -> Dict[str, float]:
        """
        Tính một số feature đơn giản:
        - RMS
        - ZCR
        - Spectral centroid
        - Spectral bandwidth
        """
        features: Dict[str, float] = {}

        # RMS
        rms = np.sqrt(np.mean(chunk ** 2))
        features["rms"] = float(rms)

        # Zero-crossing rate
        zcr = librosa.feature.zero_crossing_rate(
            chunk,
            frame_length=len(chunk),
            hop_length=len(chunk)
        )[0, 0]
        features["zcr"] = float(zcr)

        # Spectral features: 1 frame STFT
        S = np.abs(librosa.stft(chunk, n_fft=512, hop_length=len(chunk), center=False))
        centroid = librosa.feature.spectral_centroid(S=S, sr=self.RATE)[0, 0]
        bandwidth = librosa.feature.spectral_bandwidth(S=S, sr=self.RATE)[0, 0]

        features["centroid"] = float(centroid)
        features["bandwidth"] = float(bandwidth)

        return features

    # -------------------- RULE-BASED CLASSIFIER --------------------

    def classify_sound(self, chunk: np.ndarray) -> SoundType:
        """
        Phân loại đơn giản dựa trên ngưỡng:
        - SILENCE: RMS rất nhỏ
        - SPEECH: RMS vừa, ZCR & centroid trong khoảng trung bình
        - MUSIC: RMS vừa/khá, centroid cao hơn
        - NOISE: còn lại
        """
        features = self.extract_features(chunk)
        rms = features["rms"]
        zcr = features["zcr"]
        centroid = features["centroid"]

        # Ngưỡng đơn giản, có thể tinh chỉnh theo thực tế
        SILENCE_RMS_TH = 0.0015
        SPEECH_RMS_MIN = 0.0015
        SPEECH_RMS_MAX = 0.02
        MUSIC_RMS_MIN = 0.01

        SPEECH_ZCR_MIN = 0.01
        SPEECH_ZCR_MAX = 0.2
        MUSIC_ZCR_MIN = 0.02

        if rms < SILENCE_RMS_TH:
            return SoundType.SILENCE

        # speech
        if SPEECH_RMS_MIN <= rms <= SPEECH_RMS_MAX and SPEECH_ZCR_MIN <= zcr <= SPEECH_ZCR_MAX:
            return SoundType.SPEECH

        # music (rms cao và zcr cao hơn)
        if rms >= MUSIC_RMS_MIN and zcr >= MUSIC_ZCR_MIN and centroid > 1000:
            return SoundType.MUSIC

        # còn lại xem như noise
        return SoundType.NOISE

    # ------------------ BUFFER + ENV MODEL --------------------------

    def _update_env_buffer_and_predict(self, chunk: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Gom chunk vào buffer.
        Khi buffer đủ dài thì lấy ENV_WINDOW_DURATION (ví dụ 3s) cuối cùng
        để gửi vào EnvSoundModel. Model sẽ tự pad/cắt về 5s.
        """
        if self.env_model is None:
            return None, 0.0

        # nối chunk mới
        if self.env_buffer.size == 0:
            self.env_buffer = chunk
        else:
            self.env_buffer = np.concatenate([self.env_buffer, chunk])

        # giữ buffer tối đa 5 giây
        if self.env_buffer.size > ENV_SAMPLES:
            self.env_buffer = self.env_buffer[-ENV_SAMPLES:]

        # chỉ predict khi đã có ít nhất ENV_WINDOW_DURATION giây
        if self.env_buffer.size < ENV_WINDOW_SAMPLES:
            return None, 0.0

        # lấy đúng ENV_WINDOW_DURATION giây cuối
        segment = self.env_buffer[-ENV_WINDOW_SAMPLES:]

        label, conf, _ = self.env_model.predict_from_waveform(segment, sr=self.RATE)
        return label, conf

    # ---------------------- PUBLIC API ------------------------------

    def classify_audio(self) -> Tuple[SoundType, Dict[str, Any]]:
        """
        - Đọc 1 chunk
        - Phân loại rule-based (silence/speech/music/noise)
        - CHỈ gọi EnvSoundModel khi:
            + không phải SILENCE
            + rms đủ lớn (ENV_MIN_RMS)
        - CHỈ trả env_label khi model tự tin >= ENV_CONF_THRESHOLD
        """
        chunk = self.read_audio_chunk()
        if chunk is None:
            return SoundType.UNKNOWN, {}

        # ---- Rule-based phần nền ----
        features = self.extract_features(chunk)
        sound_type = self.classify_sound(chunk)
        rms = features.get("rms", 0.0)

        env_label: Optional[str] = None
        env_conf: float = 0.0

        # ---- Gọi model môi trường nếu có tiếng đủ lớn ----
        if (
            self.env_model is not None
            and sound_type is not SoundType.SILENCE
            and rms > ENV_MIN_RMS
        ):
            raw_label, raw_conf = self._update_env_buffer_and_predict(chunk)

            if raw_label is not None:
                env_conf = float(raw_conf)
                # chỉ chấp nhận label khi model tự tin đủ cao
                if env_conf >= ENV_CONF_THRESHOLD:
                    env_label = raw_label

        # luôn đưa info vào features để bên ngoài dễ xem/log
        features["env_label"] = env_label        # None nếu model chưa đủ tự tin
        features["env_conf"] = env_conf          # luôn là số 0–1
        features["rms"] = float(rms)

        return sound_type, features


# ============================================================
#                  TEST ĐƠN GIẢN (CHẠY LẺ)
# ============================================================

if __name__ == "__main__":
    """
    Chạy thử độc lập:
    - Mở micro
    - Mỗi ~3s in ra sound_type + env_label (nếu có)
    """
    clf = AudioClassifier()
    try:
        clf.start()
        print("Đang nghe... Nhấn Ctrl+C để dừng.")
        last_print = time.time()
        while True:
            st, feats = clf.classify_audio()
            now = time.time()

            if now - last_print > 0.5:
                env_label = feats.get("env_label")
                env_conf = feats.get("env_conf", 0.0)
                rms = feats.get("rms", 0.0)

                # ❗ Chỉ log khi env_label KHÔNG phải None
                if env_label is not None:
                    print(
                        f"type={st.value:7s} | rms={rms:.4f} | "
                        f"env={env_label} (conf={env_conf:.2f})"
                    )
                    last_print = now
    except KeyboardInterrupt:
        print("\nStop by user.")
    finally:
        clf.cleanup()
