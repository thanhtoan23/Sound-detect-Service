import os
import numpy as np
import librosa
import tensorflow as tf
from model import EnvSoundModel, ENV_CLASSES  # dùng lại class bạn có

DATA_DIR = r"D:\4_nam_BKU\Major\ĐỒ ÁN\demo\ESC50_subset_with_unknown_aug"  # thư mục chứa wav + csv của bạn
MODEL_PATH = "env_sounds_cnn_11cls.h5"   # model tốt nhất lưu khi train

model = EnvSoundModel(MODEL_PATH)

def test_one_file(rel_path):
    path = os.path.join(DATA_DIR, rel_path)
    y, sr = librosa.load(path, sr=16000)
    label, conf, probs = model.predict_from_waveform(y, sr)
    print("File:", rel_path)
    print("Pred:", label, conf)
    for c, p in zip(ENV_CLASSES, probs):
        print(f"  {c:15s}: {p:.3f}")

# ví dụ test 1 file dog và 1 file door_wood_knock
test_one_file("door_wood_knock/1-26188-A-30.wav")          # chỉnh đúng tên file
# test_one_file("door_wood_knock/yyy.wav")