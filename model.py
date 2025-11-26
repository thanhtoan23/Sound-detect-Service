# env_model.py
import numpy as np
import librosa
import tensorflow as tf

SR = 16000
DURATION = 5.0
SAMPLES = int(SR * DURATION)

N_MELS = 64
N_FFT = 1024
HOP_LENGTH = 512
TIME_STEPS = 128

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
    def __init__(self, model_path: str = "env_sounds_cnn_11cls.h5"):
        print(f"[EnvModel] Loading model from {model_path} ...")
        self.model = tf.keras.models.load_model(model_path)
        self.classes = ENV_CLASSES

    def _fix_length(self, y: np.ndarray) -> np.ndarray:
        if len(y) < SAMPLES:
            pad_width = SAMPLES - len(y)
            y = np.pad(y, (0, pad_width))
        else:
            y = y[:SAMPLES]
        return y

    def _wav_to_logmel(self, y: np.ndarray, sr: int = SR) -> np.ndarray:
        S = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
            n_mels=N_MELS,
        )
        S_db = librosa.power_to_db(S, ref=np.max)  # (n_mels, time)
        return S_db

    def _pad_or_truncate_time(self, mel: np.ndarray) -> np.ndarray:
        # mel: (n_mels, time) -> (time, n_mels)
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

    def preprocess_waveform(self, y: np.ndarray, sr: int = SR) -> np.ndarray:
        if sr != SR:
            y = librosa.resample(y, orig_sr=sr, target_sr=SR)
        y = self._fix_length(y)
        mel = self._wav_to_logmel(y, sr=SR)
        mel = self._pad_or_truncate_time(mel)
        mel = self._normalize_minmax(mel)
        x = mel[np.newaxis, ..., np.newaxis].astype(np.float32)  # (1, T, M, 1)
        return x

    def predict_from_waveform(self, y: np.ndarray, sr: int = SR):
        x = self.preprocess_waveform(y, sr)
        probs = self.model.predict(x, verbose=0)[0]  # (11,)
        idx = int(np.argmax(probs))
        label = self.classes[idx]
        conf = float(probs[idx])
        return label, conf, probs
