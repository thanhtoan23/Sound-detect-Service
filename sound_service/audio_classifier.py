"""Audio Classifier Module for ReSpeaker"""

import pyaudio
import numpy as np
import wave
import time
from scipy import signal
from typing import Dict, List, Optional
from enum import Enum


class SoundType(Enum):
    SILENCE = "silence"
    SPEECH = "speech"
    MUSIC = "music"
    NOISE = "noise"
    UNKNOWN = "unknown"


class AudioClassifier:
    
    CHUNK = 1024
    RATE = 16000
    CHANNELS = 6
    FORMAT = pyaudio.paInt16
    
    SILENCE_THRESHOLD = 500
    SPEECH_ZCR_MIN = 0.01
    SPEECH_ZCR_MAX = 0.15
    MUSIC_ZCR_MIN = 0.001
    MUSIC_ZCR_MAX = 0.05
    
    def __init__(self, device_index: Optional[int] = None):
        self.device_index = device_index
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        
        if device_index is None:
            self.device_index = self._find_respeaker_device()

    def _find_respeaker_device(self) -> Optional[int]:
        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        for i in range(num_devices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                name = device_info.get('name')
                if 'ReSpeaker' in name or 'UAC1.0' in name:
                    print(f"✅ Tìm thấy ReSpeaker: {name} (index: {i})")
                    return i
        
        print("Warning: ReSpeaker not found, using default device")
        return None

    def list_audio_devices(self):
        print("\nAudio Devices:")
        print("=" * 60)
        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        for i in range(num_devices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"  [{i}] {device_info.get('name')}")
                print(f"      Channels: {device_info.get('maxInputChannels')}")
                print(f"      Sample Rate: {device_info.get('defaultSampleRate')}")
                print()

    def start_stream(self):
        try:
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.CHUNK
            )
            self.is_recording = True
            print("Audio stream started")
            return True
        except Exception as e:
            print(f"Error opening stream: {e}")
            return False

    def stop_stream(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.is_recording = False
            print("Audio stream stopped")

    def read_audio_chunk(self) -> Optional[np.ndarray]:
        if not self.stream or not self.is_recording:
            return None
        
        try:
            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            audio_channel_0 = audio_data[0::self.CHANNELS]
            
            return audio_channel_0
        except Exception as e:
            print(f"Error reading audio: {e}")
            return None

    def calculate_rms(self, audio_data: np.ndarray) -> float:
        return np.sqrt(np.mean(audio_data.astype(float) ** 2))

    def calculate_zcr(self, audio_data: np.ndarray) -> float:
        signs = np.sign(audio_data)
        signs[signs == 0] = -1
        zero_crossings = np.abs(np.diff(signs))
        zcr = np.sum(zero_crossings) / (2 * len(audio_data))
        return zcr

    def calculate_spectral_centroid(self, audio_data: np.ndarray) -> float:
        # FFT để lấy phổ tần số
        spectrum = np.abs(np.fft.rfft(audio_data))
        freqs = np.fft.rfftfreq(len(audio_data), 1/self.RATE)
        
        # Tính centroid
        if np.sum(spectrum) == 0:
            return 0
        
        centroid = np.sum(freqs * spectrum) / np.sum(spectrum)
        return centroid

    def extract_features(self, audio_data: np.ndarray) -> Dict:
        """
        Trích xuất tất cả đặc trưng từ audio
        
        Args:
            audio_data: Numpy array của audio
            
        Returns:
            Dictionary chứa các features
        """
        if audio_data is None or len(audio_data) == 0:
            return {}
        
        return {
            'rms': self.calculate_rms(audio_data),
            'zcr': self.calculate_zcr(audio_data),
            'spectral_centroid': self.calculate_spectral_centroid(audio_data),
            'max_amplitude': np.max(np.abs(audio_data)),
            'mean_amplitude': np.mean(np.abs(audio_data))
        }

    def classify_sound(self, audio_data: np.ndarray) -> SoundType:
        """
        Phân loại loại âm thanh
        
        Args:
            audio_data: Numpy array của audio
            
        Returns:
            SoundType enum
        """
        features = self.extract_features(audio_data)
        
        if not features:
            return SoundType.UNKNOWN
        
        rms = features['rms']
        zcr = features['zcr']
        
        # Rule 1: Silence detection
        if rms < self.SILENCE_THRESHOLD:
            return SoundType.SILENCE
        
        # Rule 2: Speech detection
        # Speech có ZCR trung bình, RMS dao động
        if self.SPEECH_ZCR_MIN < zcr < self.SPEECH_ZCR_MAX:
            return SoundType.SPEECH
        
        # Rule 3: Music detection
        # Music có ZCR thấp, mượt mà hơn
        if self.MUSIC_ZCR_MIN < zcr < self.MUSIC_ZCR_MAX and rms > self.SILENCE_THRESHOLD * 2:
            return SoundType.MUSIC
        
        # Rule 4: Noise
        # ZCR rất cao hoặc không đều
        if zcr > self.SPEECH_ZCR_MAX:
            return SoundType.NOISE
        
        return SoundType.UNKNOWN

    def classify_audio(self):
        chunk = self.read_audio_chunk()
        if chunk is None:
            return (SoundType.UNKNOWN, {})
        
        features = self.extract_features(chunk)
        sound_type = self.classify_sound(chunk)
        
        return (sound_type, features)

    def analyze_continuous(self, duration: int = 10, interval: float = 0.5):
        if not self.is_recording:
            print("Stream not opened. Call start_stream() first.")
            return
        
        print(f"Analyzing audio for {duration} seconds...")
        print("=" * 60)
        
        start_time = time.time()
        sound_counts = {st: 0 for st in SoundType}
        
        try:
            while time.time() - start_time < duration:
                chunks = []
                for _ in range(int(interval * self.RATE / self.CHUNK)):
                    chunk = self.read_audio_chunk()
                    if chunk is not None:
                        chunks.append(chunk)
                
                if chunks:
                    audio_data = np.concatenate(chunks)
                    features = self.extract_features(audio_data)
                    sound_type = self.classify_sound(audio_data)
                    
                    sound_counts[sound_type] += 1
                    
                    emoji_map = {
                        SoundType.SILENCE: "🤫",
                        SoundType.SPEECH: "🗣️",
                        SoundType.MUSIC: "🎵",
                        SoundType.NOISE: "🔊",
                        SoundType.UNKNOWN: "❓"
                    }
                    
                    print(f"{emoji_map[sound_type]} {sound_type.value.upper():8} | "
                          f"RMS: {features['rms']:7.0f} | "
                          f"ZCR: {features['zcr']:.4f} | "
                          f"Centroid: {features['spectral_centroid']:.0f} Hz")
                
                time.sleep(max(0, interval - (time.time() - start_time) % interval))
                
        except KeyboardInterrupt:
            print("\n⏹️  Đã dừng phân tích")
        
        # Thống kê
        print("\n" + "=" * 60)
        print("📊 THỐNG KÊ:")
        total = sum(sound_counts.values())
        for sound_type, count in sound_counts.items():
            if total > 0:
                percent = (count / total) * 100
                print(f"  {sound_type.value:8}: {count:3} lần ({percent:5.1f}%)")

    def classify_continuous(self, duration: int = 10):
        """
        Phân loại liên tục và trả về kết quả
        Tương thích với CLI
        
        Args:
            duration: Thời gian phân loại (giây)
            
        Returns:
            Dict[str, int]: Số lần phát hiện mỗi loại
        """
        if not self.start_stream():
            return {}
        
        sound_counts = {st.value: 0 for st in SoundType}
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                sound_type, _ = self.classify_audio()
                sound_counts[sound_type.value] += 1
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        
        return sound_counts

    def record_to_file(self, filename: str, duration: int = 5):
        """
        Ghi âm và lưu vào file WAV
        
        Args:
            filename: Tên file output
            duration: Thời gian ghi (giây)
        """
        if not self.is_recording:
            print("❌ Stream chưa được mở")
            return
        
        print(f"🔴 Đang ghi âm {duration} giây...")
        frames = []
        
        for _ in range(0, int(self.RATE / self.CHUNK * duration)):
            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            frames.append(data)
        
        print(f"💾 Đang lưu vào {filename}...")
        
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"✅ Đã lưu: {filename}")

    def cleanup(self):
        """Dọn dẹp resources"""
        self.stop_stream()
        self.p.terminate()
        print("🧹 Đã dọn dẹp resources")
    
    def stop(self):
        """Alias for cleanup - for compatibility"""
        self.cleanup()


def main():
    """Demo sử dụng AudioClassifier"""
    print("=" * 60)
    print("🎵 ReSpeaker Audio Classifier Demo")
    print("=" * 60)
    
    classifier = AudioClassifier()
    
    # Liệt kê devices
    classifier.list_audio_devices()
    
    # Bắt đầu stream
    if not classifier.start_stream():
        return
    
    try:
        # Phân tích liên tục
        classifier.analyze_continuous(duration=30, interval=0.5)
        
        # Ghi âm demo (optional)
        # classifier.record_to_file("test_recording.wav", duration=5)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Đã dừng")
    finally:
        classifier.cleanup()


if __name__ == '__main__':
    main()
