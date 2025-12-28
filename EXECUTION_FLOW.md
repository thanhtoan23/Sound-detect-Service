# Luồng Thực Thi Chương Trình - Smart Audio Detection Service
## Điểm Đích: smart_audio_pipeline.py

---

## 📊 SƠ ĐỒ TỔNG QUAN

```
┌─────────────────────────────────────────────────────────────┐
│                    ENTRY POINTS (3 Điểm Vào)               │
├─────────────────────────────────────────────────────────────┤
│  1. gui_app.py           (GUI với Tkinter)                  │
│  2. api.py               (REST API với Flask)               │
│  3. smart_audio_pipeline.py (Demo Console - TRỰC TIẾP)      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  SmartAudioSystem (Pipeline)       │
        │  (smart_audio_pipeline.py)         │
        │                                    │
        │  - Khởi tạo Processor + Classifier │
        │  - Vòng lặp xử lý âm thanh         │
        │  - Hiển thị kết quả                │
        └────┬─────────────────────┬─────────┘
             │                     │
      ┌──────▼──────┐      ┌──────▼──────────┐
      │AudioProcessor│     │ AudioClassifier │
      │(Lọc nhiễu, AGC)│      │(Phân loại AI)     │
      └──────────────┘      └──────────────────┘
             │                     │
             ├──► Raw Audio        │
             │   Input             │
             │   (from Mic)        │
             │                     │
             └─────► Clean Audio ──► AI Model
                    (DSP Out)       (DL Prediction)
```

---

## 🎯 CHI TIẾT LUỒNG THỰC THI

### **1. ĐỌC FILE VÀ KHỞI ĐỘNG**

```python
if __name__ == "__main__":
    system = SmartAudioSystem()
    system.run_demo()
```

**File:** [smart_audio_pipeline.py](smart_audio_pipeline.py#L180-L182)

### **2. KHỞI ĐỘNG HỆ THỐNG (SmartAudioSystem.__init__)**

```python
class SmartAudioSystem:
    def __init__(self):
        # Bước 1: Khởi tạo Processor (DSP)
        self.processor = AudioProcessor(rate=16000)
        
        # Bước 2: Khởi tạo Classifier (AI + Model Load)
        self.classifier = AudioClassifier(rate=16000)
        
        self.is_running = False
        self.console = Console()
```

**Chuỗi khởi tạo:**
1. `AudioProcessor` → Chuẩn bị lọc nhiễu, AGC (Automatic Gain Control)
2. `AudioClassifier` → Load model Deep Learning (audio_cnn_best.h5)

**File:** [smart_audio_pipeline.py](smart_audio_pipeline.py#L15-L25)

### **3. KHỞI ĐỘNG STREAM AUDIO (SmartAudioSystem.start)**

```python
def start(self):
    self.classifier.start_stream()  # Mở Mic, PyAudio stream
    self.is_running = True
    self.processor.reset_states()   # Reset bộ lọc & AGC
    self.console.print("[bold green]Smart Audio Pipeline Started...[/bold green]")
```

**File:** [smart_audio_pipeline.py](smart_audio_pipeline.py#L27-L32)

### **4. VÒNG LẶP CHÍNH (SmartAudioSystem.run_demo)**

```python
def run_demo(self):
    self.start()
    
    # Hiển thị bảng trực quan
    table = Table(title="Smart Audio Analysis")
    
    try:
        with Live(table, refresh_per_second=4) as live:
            while self.is_running:
                result = self.process_and_predict()  # ⭐ HÀM TRUNG TÂM
                
                if result:
                    # Cập nhật bảng với kết quả
                    live.update(table)
                
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        self.stop()
```

**File:** [smart_audio_pipeline.py](smart_audio_pipeline.py#L103-L147)

### **5. XỬ LÝ & DỰ ĐOÁN (SmartAudioSystem.process_and_predict) ⭐ TRUNG TÂM**

```python
def process_and_predict(self):
    """Hàm trung tâm kết hợp DSP + AI"""
    
    # BƯỚC 1: ĐỌC DỮ LIỆU THỰC (RAW)
    raw_chunk = self.classifier.read_audio_chunk()
    if raw_chunk is None:
        return None
    
    # BƯỚC 2: XỬ LÝ TÍN HIỆU (DSP - Lọc Nhiễu + AGC)
    clean_chunk = self.processor.process(raw_chunk)
    
    # BƯỚC 3: PHÂN LOẠI CƠ BẢN (Rule-based)
    basic_type = self.classifier.classify_sound(clean_chunk)
    
    # BƯỚC 4: TRÍCH XUẤT ĐẶC TRƯNG
    features = self.classifier.extract_features(clean_chunk)
    
    # BƯỚC 5: GỌI MODEL DL (Nếu không im lặng)
    env_label = None
    env_conf = 0.0
    
    if basic_type != SoundType.SILENCE and features['rms'] > 0.02:
        raw_label, raw_conf = self.classifier._update_env_buffer_and_predict(clean_chunk)
        if raw_label:
            env_label = raw_label
            env_conf = raw_conf
    
    return {
        "basic_type": basic_type,
        "env_label": env_label,
        "env_conf": env_conf,
        "rms_raw": np.sqrt(np.mean(raw_chunk**2)),
        "rms_clean": features['rms'],
        "gain_applied": self.processor.current_gain
    }
```

**File:** [smart_audio_pipeline.py](smart_audio_pipeline.py#L46-L80)

---

## 📋 LUỒNG CHI TIẾT - TỪNG BƯỚC

### **CHI TIẾT CÁC BƯỚC:**

#### **BƯỚC 1: ĐỌC AUDIO (Raw)**
```python
raw_chunk = self.classifier.read_audio_chunk()
```
- **Từ:** Microphone (PyAudio Stream)
- **Kích thước:** 1024 mẫu (16-bit PCM)
- **Tần suất:** 16000 Hz
- **Định dạng:** np.int16

**File:** [audio_classifier.py](audio_classifier.py)

---

#### **BƯỚC 2: LỌC NHIỄU & AGC (AudioProcessor)**

```python
clean_chunk = self.processor.process(raw_chunk)
```

**Các xử lý bên trong AudioProcessor:**
1. **Noise Gate** → Lọc bỏ âm thanh yếu
2. **High-pass Filter** → Loại bỏ tần số thấp
3. **Noise Subtraction** → Trừ đi noise nền
4. **AGC (Automatic Gain Control)** → Tăng/giảm độ to

**File:** [audio_processor.py](audio_processor.py)

---

#### **BƯỚC 3: PHÂN LOẠI CƠ BẢN (Rule-based)**

```python
basic_type = self.classifier.classify_sound(clean_chunk)
```

**Logic phân loại:**
```
Input: clean_chunk (Waveform)
  ↓
Tính RMS, Spectral Centroid, ZCR
  ↓
So sánh với Thresholds:
  - RMS < 0.001           → SILENCE
  - Spectral Centroid cao → SPEECH
  - ZCR thấp              → MUSIC  
  - Khác                  → NOISE
  ↓
Output: SoundType (Enum)
```

**Return:** `SoundType.SILENCE | SPEECH | MUSIC | NOISE`

**File:** [audio_classifier.py](audio_classifier.py)

---

#### **BƯỚC 4: TRÍCH XUẤT ĐẶC TRƯNG**

```python
features = self.classifier.extract_features(clean_chunk)
```

**Các đặc trưng trích xuất:**
- `rms`: Root Mean Square (độ lớn)
- `zcr`: Zero Crossing Rate (số lần đổi dấu)
- `spectral_centroid`: Tâm tần số
- `mfcc`: Mel-Frequency Cepstral Coefficients
- `chroma`: Đặc trưng màu âm

**File:** [audio_classifier.py](audio_classifier.py)

---

#### **BƯỚC 5: DỰ ĐOÁN DEEP LEARNING**

```python
if basic_type != SoundType.SILENCE and features['rms'] > 0.02:
    raw_label, raw_conf = self.classifier._update_env_buffer_and_predict(clean_chunk)
```

**Luồng chi tiết:**

```
Input: clean_chunk (1024 mẫu)
  ↓
Buffer Accumulation (Tích lũy vào buffer)
  ↓
buffer_length >= 5s? (80000 mẫu)
  ├─ YES: Gọi Model Dự đoán
  │         ↓
  │       Convert waveform → Log-Mel Spectrogram (128, 64, 1)
  │         ↓
  │       Đưa vào CNN Model (audio_cnn_best.h5)
  │         ↓
  │       Output: Probabilities cho 14 class
  │         ↓
  │       Lọc Smoothing + Voting (3 frame)
  │         ↓
  │       Output: (label, confidence)
  │
  └─ NO: Chờ dữ liệu thêm
```

**Model Output:**
- **Labels:** 14 class (car_horn, cat, dog, speech, ..., unknown)
- **Confidence:** 0.0 - 1.0
- **Smoothing:** Top-3 predictions được smooth để chống nhiễu

**File:** [audio_classifier.py](audio_classifier.py)

---

## 🔄 LUỒNG DỮ LIỆU TẠI smart_audio_pipeline.py

```
                  SmartAudioSystem
                  (smart_audio_pipeline.py)
                           │
              ┌────────────┴────────────┐
              │                         │
         raw_chunk              AudioProcessor
         (16000Hz)                    │
              │                       │
              ├──(1) read_audio──────►│
              │                       │
              │◄─(2) clean_chunk─────┤
              │                       │
              │                       │ (DSP Filter)
              │                       │
              ├──(3) classify_sound──┤
              │                   │   │
              ├──(4) extract_features──┤
              │     (RMS, ZCR...)     │
              │                       │
         AudioClassifier             │
              │                       │
              ├──(5) predict DL───────┤
              │     (CNN Model)       │
              │                       │
              ▼                       ▼
         Output Result:
         {
           "basic_type": SoundType,
           "env_label": str (class name),
           "env_conf": float (0.0-1.0),
           "rms_raw": float,
           "rms_clean": float,
           "gain_applied": float
         }
```

---

## 📊 LUỒNG TOÀN BỘ (End-to-End)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ENTRY POINT                                              │
│    if __name__ == "__main__":                               │
│        system = SmartAudioSystem()                           │
│        system.run_demo()                                    │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 2. INITIALIZATION (__init__)                                │
│    - Create AudioProcessor()                                │
│    - Create AudioClassifier() + Load Model                  │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 3. START SYSTEM (start())                                   │
│    - Start Audio Stream (PyAudio)                           │
│    - Set is_running = True                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 4. MAIN LOOP (run_demo())                                   │
│    while is_running:                                        │
│        result = process_and_predict()  ⭐ TRUNG TÂM         │
│        display(result)                                      │
│        sleep(0.1)                                           │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │ process_and_predict()
        │ (ĐỤC LỌC XỬ LÝ)
        │
        ├─► 1️⃣  read_audio_chunk()       [Mic Input]
        │       │
        │       └─► np.int16 array
        │
        ├─► 2️⃣  processor.process()      [DSP Processing]
        │       ├─ Noise Gate
        │       ├─ High-pass Filter
        │       ├─ Noise Subtraction
        │       └─ AGC (Automatic Gain Control)
        │       │
        │       └─► Float array (normalized)
        │
        ├─► 3️⃣  classify_sound()         [Rule-based]
        │       ├─ Calculate RMS, ZCR, Spectral features
        │       ├─ Compare with thresholds
        │       └─► SoundType (SILENCE/SPEECH/MUSIC/NOISE)
        │
        ├─► 4️⃣  extract_features()       [Feature Extraction]
        │       └─► Dict {rms, zcr, ...}
        │
        └─► 5️⃣  _update_env_buffer_and_predict()  [Deep Learning]
                ├─ Accumulate 5 seconds of audio
                ├─ Convert to Log-Mel Spectrogram
                ├─ Pass through CNN Model (audio_cnn_best.h5)
                ├─ Smooth predictions (3-frame window)
                └─► (env_label: str, env_conf: float)
                    ├─ car_horn, cat, clock_alarm, ...
                    └─ Confidence: 0.0 ~ 1.0

                ↓ RETURN TO CALLER
                
        ┌───────────────────────────────────┐
        │ result = {                         │
        │   "basic_type": SoundType,         │
        │   "env_label": str,                │
        │   "env_conf": float,               │
        │   "rms_raw": float,                │
        │   "rms_clean": float,              │
        │   "gain_applied": float            │
        │ }                                  │
        └───────────────────────────────────┘
                ↓
        ┌───────────────────────────────────┐
        │ 5. DISPLAY RESULTS                │
        │    (Rich Table Format)             │
        │    ┌──────────────────────────┐   │
        │    │ DSP | Basic | AI Predict │   │
        │    ├──────────────────────────┤   │
        │    │ info| info | info        │   │
        │    └──────────────────────────┘   │
        └───────────────────────────────────┘
                ↓
        ┌───────────────────────────────────┐
        │ sleep(0.1) - chờ chunk tiếp theo  │
        └───────────────────────────────────┘
```

---

## 📁 CÁC FILE LIÊN QUAN

| File | Vai trò | Chức năng |
|------|---------|----------|
| [smart_audio_pipeline.py](smart_audio_pipeline.py) | **TRUNG TÂM** | Kết hợp DSP + AI, vòng lặp chính |
| [audio_processor.py](audio_processor.py) | DSP Layer | Lọc nhiễu, AGC, tăng/giảm độ to |
| [audio_classifier.py](audio_classifier.py) | AI Layer | Phân loại, trích đặc trưng, DL model |
| gui_app.py | UI | Giao diện Tkinter, hiển thị Dashboard |
| api.py | API Server | Flask REST API cho remote control |
| sound_service.py | Service | Tích hợp high-level, quản lý vòng lặp |

---

## 🎬 TÓMEÝ LUỒNG THỰC THI

**Entry Point:**
```
smart_audio_pipeline.py (if __name__ == "__main__")
    ↓
SmartAudioSystem() init (Khởi tạo)
    ↓
.start() (Mở stream mic)
    ↓
.run_demo() (Vòng lặp chính)
    ↓
.process_and_predict() ⭐ TRUNG TÂM
    ├─ Read Mic (RAW) → AudioClassifier
    ├─ Process DSP (Clean) → AudioProcessor
    ├─ Classify Basic (Rule) → AudioClassifier
    ├─ Extract Features → AudioClassifier
    └─ Predict DL (AI Model) → AudioClassifier + TensorFlow
    ↓
Display Results (Rich Table)
    ↓
Loop → sleep(0.1) → back to process_and_predict()
    ↓
Ctrl+C → .stop() → Đóng stream
```

---

## 🔑 KEY INSIGHT

**smart_audio_pipeline.py** là file trung tâm kết hợp:
1. **DSP Processing** (AudioProcessor) - Xử lý tín hiệu
2. **AI Classification** (AudioClassifier) - Phân loại AI + Model DL

Vòng lặp chính ở hàm `process_and_predict()` liên tục:
- Đọc audio từ mic
- Lọc nhiễu
- Phân loại rule-based
- Gọi Deep Learning model
- Hiển thị kết quả

**Tốc độ:** ~100ms/chunk (10 chunks/giây)
