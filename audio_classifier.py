import enum
import time
from typing import Optional, Dict, Any, Tuple
from collections import deque

import sys
import os

import numpy as np
import pyaudio
import librosa
import tensorflow as tf


def get_resource_path(relative_path: str) -> str:
    """Giúp chạy exe (PyInstaller) hoặc chạy python thường đều tìm được file."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ============================================================
#                AUDIO / MODEL CONFIG
# ============================================================

DEFAULT_RATE = 16000
DEFAULT_CHUNK = 1024
DEFAULT_CHANNELS = 1
DEFAULT_FORMAT = pyaudio.paInt16

# Model train theo 5s
ENV_DURATION_SEC = 5.0
ENV_SAMPLES = int(DEFAULT_RATE * ENV_DURATION_SEC)

# lấy bao nhiêu giây cuối trong buffer để predict (segment ngắn hơn vẫn OK vì preprocess sẽ pad/cắt về 5s)
ENV_WINDOW_DURATION_SEC = 2.0
ENV_WINDOW_SAMPLES = int(DEFAULT_RATE * ENV_WINDOW_DURATION_SEC)

# Ngưỡng gọi model
ENV_MIN_RMS = 0.005

# Threshold quyết định unknown
ENV_CONF_THRESHOLD = 0.60
ENV_UNKNOWN_LABEL = "unknown"

# ===== Smoothing =====
ENV_SMOOTH_K = 3            # 3–7 hợp lý
ENV_PRED_HOP_SEC = 0.50     # predict mỗi 0.5s

# ===== Switching / Reset =====
ENV_RESET_ON_SILENCE_SEC = 0.8  # rms thấp liên tục > 0.8s => reset buffer+history
ENV_SWITCH_CONF = 0.70         # label mới raw_conf >= 0.75 => xem là đủ mạnh để switch nhanh
ENV_SWITCH_STREAK = 2           # cần 2 lần liên tiếp để switch (chống nhảy)

# ===== Model file name =====
ENV_MODEL_FILENAME = "audio_cnn_best.h5"
ENV_MODEL_PATH = get_resource_path(ENV_MODEL_FILENAME)

# IMPORTANT: đúng thứ tự classes lúc train (npz classes)
ENV_CLASSES = [
    "car_horn",
    "cat",
    "clock_alarm",
    "coughing",
    "crying_baby",
    "dog",
    "door_wood_knock",
    "engine",
    "frog",
    "laughing",
    "mouse_click",
    "rooster",
    "unknown",
    "water_drops",
]


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
#                   ENV SOUND MODEL
# ============================================================

class EnvSoundModel:
    """
    Input: waveform (float32) -> log-mel (128,64,1) giống training Kaggle.
    Output: probs (num_classes,)
    """

    def __init__(self, model_path: str = ENV_MODEL_PATH):
        print(f"[EnvSoundModel] Loading model from: {model_path}")
        self.model = tf.keras.models.load_model(model_path)
        self.classes = ENV_CLASSES

    def _fix_length_5s(self, y: np.ndarray) -> np.ndarray:
        if len(y) < ENV_SAMPLES:
            y = np.pad(y, (0, ENV_SAMPLES - len(y)))
        else:
            y = y[:ENV_SAMPLES]
        return y.astype(np.float32)

    def _wav_to_logmel(self, y: np.ndarray, sr: int = DEFAULT_RATE) -> np.ndarray:
        S = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=1024,
            hop_length=512,
            n_mels=64,
        )
        S_db = librosa.power_to_db(S, ref=np.max)  # (64, time)
        return S_db.astype(np.float32)

    def _pad_or_truncate_time(self, mel: np.ndarray) -> np.ndarray:
        TIME_STEPS = 128
        mel = mel.T  # (time, 64)
        if mel.shape[0] < TIME_STEPS:
            mel = np.pad(mel, ((0, TIME_STEPS - mel.shape[0]), (0, 0)))
        else:
            mel = mel[:TIME_STEPS, :]
        return mel.astype(np.float32)

    def _normalize_minmax(self, mel: np.ndarray) -> np.ndarray:
        m_min = float(mel.min())
        m_max = float(mel.max())
        return ((mel - m_min) / (m_max - m_min + 1e-6)).astype(np.float32)

    def preprocess_waveform(self, y: np.ndarray, sr: int = DEFAULT_RATE) -> np.ndarray:
        if sr != DEFAULT_RATE:
            y = librosa.resample(y, orig_sr=sr, target_sr=DEFAULT_RATE)
        y = self._fix_length_5s(y)
        mel = self._wav_to_logmel(y, sr=DEFAULT_RATE)
        mel = self._pad_or_truncate_time(mel)   # (128, 64)
        mel = self._normalize_minmax(mel)
        x = mel[np.newaxis, ..., np.newaxis].astype(np.float32)  # (1,128,64,1)
        return x

    def predict_probs(self, y: np.ndarray, sr: int = DEFAULT_RATE) -> np.ndarray:
        x = self.preprocess_waveform(y, sr)
        probs = self.model.predict(x, verbose=0)[0]
        return probs.astype(np.float32)


# ============================================================
#                     AUDIO CLASSIFIER
# ============================================================

class AudioClassifier:
    """
    - Đọc audio từ mic (PyAudio)
    - Rule-based: silence/speech/music/noise
    - EnvSoundModel:
        + gom buffer
        + predict theo hop (0.5s)
        + smoothing K lần (mean probs)
        + conf < threshold => unknown
        + reset on silence + fast switch
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

        self.env_model: Optional[EnvSoundModel] = None
        try:
            self.env_model = EnvSoundModel(ENV_MODEL_PATH)
        except Exception as e:
            print(f"[AudioClassifier] Không load được EnvSoundModel: {e}")
            self.env_model = None

        self.env_buffer = np.zeros(0, dtype=np.float32)
        self.env_prob_hist = deque(maxlen=ENV_SMOOTH_K)
        self._last_env_pred_ts = 0.0

        # reset/switch states
        self._low_rms_start_ts: Optional[float] = None
        self._switch_streak: int = 0
        self._last_raw_top: Optional[int] = None

        # giữ output gần nhất để UI không bị N/A giữa các hop
        self._last_env_label: Optional[str] = None
        self._last_env_conf: float = 0.0

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

    # alias tương thích code cũ
    def start_stream(self):
        self.start()

    def stop_stream(self):
        self.stop()

    def cleanup(self):
        self.stop()

    # ------------------------- READ AUDIO ----------------------------

    def read_audio_chunk(self) -> Optional[np.ndarray]:
        """Đọc chunk -> float32 [-1,1]"""
        if not self.stream or not self.is_recording:
            return None
        try:
            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)

            # lấy kênh 0
            audio_channel_0 = audio_data[0::self.CHANNELS].astype(np.float32)
            audio_channel_0 /= 32768.0
            return audio_channel_0
        except Exception as e:
            print(f"[AudioClassifier] Error reading audio: {e}")
            return None

    # ------------------------- FEATURES ------------------------------

    def extract_features(self, chunk: np.ndarray) -> Dict[str, float]:
        features: Dict[str, float] = {}
        rms = float(np.sqrt(np.mean(chunk ** 2) + 1e-9))
        features["rms"] = rms

        zcr = librosa.feature.zero_crossing_rate(
            chunk, frame_length=len(chunk), hop_length=len(chunk)
        )[0, 0]
        features["zcr"] = float(zcr)

        S = np.abs(librosa.stft(chunk, n_fft=512, hop_length=max(1, len(chunk)//2), center=False))
        centroid = librosa.feature.spectral_centroid(S=S, sr=self.RATE)[0, 0]
        bandwidth = librosa.feature.spectral_bandwidth(S=S, sr=self.RATE)[0, 0]
        features["centroid"] = float(centroid)
        features["bandwidth"] = float(bandwidth)
        return features

    # -------------------- RULE-BASED CLASSIFIER --------------------

    def classify_sound(self, chunk: np.ndarray) -> SoundType:
        feats = self.extract_features(chunk)
        rms = feats["rms"]
        zcr = feats["zcr"]
        centroid = feats["centroid"]

        SILENCE_RMS_TH = 0.0015
        SPEECH_RMS_MIN = 0.0015
        SPEECH_RMS_MAX = 0.02

        SPEECH_ZCR_MIN = 0.01
        SPEECH_ZCR_MAX = 0.2
        MUSIC_RMS_MIN = 0.01
        MUSIC_ZCR_MIN = 0.02

        if rms < SILENCE_RMS_TH:
            return SoundType.SILENCE

        if SPEECH_RMS_MIN <= rms <= SPEECH_RMS_MAX and SPEECH_ZCR_MIN <= zcr <= SPEECH_ZCR_MAX:
            return SoundType.SPEECH

        if rms >= MUSIC_RMS_MIN and zcr >= MUSIC_ZCR_MIN and centroid > 1000:
            return SoundType.MUSIC

        return SoundType.NOISE

    # ------------------ ENV MODEL + SMOOTHING -----------------------

    def _reset_env_state(self):
        self.env_buffer = np.zeros(0, dtype=np.float32)
        self.env_prob_hist.clear()
        self._switch_streak = 0
        self._last_raw_top = None
        self._last_env_label = None
        self._last_env_conf = 0.0

    def _append_env_buffer(self, chunk: np.ndarray):
        if self.env_buffer.size == 0:
            self.env_buffer = chunk
        else:
            self.env_buffer = np.concatenate([self.env_buffer, chunk])

        if self.env_buffer.size > ENV_SAMPLES:
            self.env_buffer = self.env_buffer[-ENV_SAMPLES:]

    def _update_env_buffer_and_predict(self, chunk: np.ndarray) -> Tuple[Optional[str], float, bool]:
        """
        Returns: (label, conf, updated)
        - updated=True nếu vừa predict mới theo hop
        - updated=False nếu chưa đến hop (giữ kết quả cũ)
        """
        if self.env_model is None:
            return None, 0.0, False

        self._append_env_buffer(chunk)

        if self.env_buffer.size < ENV_WINDOW_SAMPLES:
            return None, 0.0, False

        now = time.time()
        if (now - self._last_env_pred_ts) < ENV_PRED_HOP_SEC:
            # chưa đến hop
            return self._last_env_label, self._last_env_conf, False

        self._last_env_pred_ts = now

        segment = self.env_buffer[-ENV_WINDOW_SAMPLES:]
        probs = self.env_model.predict_probs(segment, sr=self.RATE)  # (C,)

        # ===== Fast switch logic (dựa trên raw probs) =====
        raw_top = int(np.argmax(probs))
        raw_conf = float(probs[raw_top])

        if self._last_raw_top is None:
            self._last_raw_top = raw_top
            self._switch_streak = 0
        else:
            if raw_top != self._last_raw_top and raw_conf >= ENV_SWITCH_CONF:
                self._switch_streak += 1
                if self._switch_streak >= ENV_SWITCH_STREAK:
                    # reset history để chuyển nhanh sang label mới
                    self.env_prob_hist.clear()
                    self._switch_streak = 0
                    self._last_raw_top = raw_top
            else:
                self._switch_streak = max(0, self._switch_streak - 1)
                self._last_raw_top = raw_top

        # ===== Smoothing =====
        self.env_prob_hist.append(probs)
        avg_probs = np.mean(np.stack(list(self.env_prob_hist), axis=0), axis=0)

        idx = int(np.argmax(avg_probs))
        label = ENV_CLASSES[idx]
        conf = float(avg_probs[idx])

        self._last_env_label = label
        self._last_env_conf = conf
        return label, conf, True

    # ---------------------- PUBLIC API ------------------------------

    def classify_chunk(self, chunk: np.ndarray) -> Tuple[SoundType, Dict[str, Any]]:
        """
        Dùng cho pipeline/GUI: bạn đưa chunk (đã DSP hoặc raw) vào đây.
        Trả:
        - sound_type (rule-based)
        - features có env_label/env_conf
          * env_label sẽ giữ kết quả gần nhất giữa các hop
          * nếu conf < ENV_CONF_THRESHOLD => env_label='unknown'
          * reset khi im lặng đủ lâu
        """
        if chunk is None or len(chunk) == 0:
            return SoundType.UNKNOWN, {}

        features = self.extract_features(chunk)
        sound_type = self.classify_sound(chunk)
        rms = float(features.get("rms", 0.0))

        # ===== Auto reset when silence/low energy =====
        now = time.time()
        if rms < ENV_MIN_RMS or sound_type == SoundType.SILENCE:
            if self._low_rms_start_ts is None:
                self._low_rms_start_ts = now
            elif (now - self._low_rms_start_ts) >= ENV_RESET_ON_SILENCE_SEC:
                self._reset_env_state()
        else:
            self._low_rms_start_ts = None

        env_label: Optional[str] = self._last_env_label
        env_conf: float = float(self._last_env_conf)

        if self.env_model is not None and sound_type is not SoundType.SILENCE and rms > ENV_MIN_RMS:
            pred_label, pred_conf, updated = self._update_env_buffer_and_predict(chunk)

            # nếu có label (kể cả giữ từ lần trước) thì cập nhật lại
            if pred_label is not None:
                env_label = pred_label
                env_conf = float(pred_conf)

                # === RULE bạn muốn: conf < threshold => unknown ===
                if env_conf < ENV_CONF_THRESHOLD:
                    env_label = ENV_UNKNOWN_LABEL

        features["env_label"] = env_label
        features["env_conf"] = float(env_conf)
        features["rms"] = float(rms)
        return sound_type, features

    def classify_audio(self) -> Tuple[SoundType, Dict[str, Any]]:
        """Đọc 1 chunk từ mic rồi classify_chunk()."""
        chunk = self.read_audio_chunk()
        if chunk is None:
            return SoundType.UNKNOWN, {}
        return self.classify_chunk(chunk)


# ============================================================
# Test chạy lẻ
# ============================================================
if __name__ == "__main__":
    clf = AudioClassifier()
    try:
        clf.start()
        print("Đang nghe... Ctrl+C để dừng.")
        last_print = time.time()
        while True:
            st, feats = clf.classify_audio()
            now = time.time()
            if now - last_print > 0.2:
                env_label = feats.get("env_label")
                env_conf = feats.get("env_conf", 0.0)
                rms = feats.get("rms", 0.0)

                if env_label is not None:
                    print(f"type={st.value:7s} | rms={rms:.4f} | env={env_label} (conf={env_conf:.2f})")

                last_print = now
    except KeyboardInterrupt:
        print("\nStop by user.")
    finally:
        clf.cleanup()
