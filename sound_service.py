"""Sound Detection Service - Main integration module"""

import time
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

from sound_detector import SoundDetector
from audio_classifier import AudioClassifier, SoundType


class SoundDetectionService:
    
    def __init__(self, 
                 enable_audio_classification: bool = True,
                 history_size: int = 100):
        self.sound_detector = SoundDetector()
        self.audio_classifier = AudioClassifier() if enable_audio_classification else None
        
        self.enable_audio_classification = enable_audio_classification
        
        self.is_running = False
        self.thread = None
        
        self.history = deque(maxlen=history_size)
        self.statistics = {
            'total_detections': 0,
            'vad_count': 0,
            'speech_count': 0,
            'sound_types': {st.value: 0 for st in SoundType},
            'direction_histogram': [0] * 12
        }
        
        self.current_state = {
            'vad': False,
            'speech': False,
            'direction': None,
            'sound_type': SoundType.UNKNOWN,
            'timestamp': None
        }

    def start(self) -> bool:
        print("=" * 60)
        print("Starting Sound Detection Service...")
        print("=" * 60)
        
        if not self.sound_detector.connect():
            print("Failed to start: Cannot connect to ReSpeaker")
            return False
        
        if self.enable_audio_classification:
            if not self.audio_classifier.start_stream():
                print("Warning: Cannot start audio stream, disabling audio classification")
                self.enable_audio_classification = False
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        print("Service started successfully!")
        print(f"   - Audio Classification: {'ON' if self.enable_audio_classification else 'OFF'}")
        print()
        
        return True

    def stop(self):
        """Dừng service"""
        print("\n⏹️  Đang dừng service...")
        
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        # Cleanup
        self.sound_detector.disconnect()
        
        if self.audio_classifier:
            self.audio_classifier.cleanup()
        
        print("Service stopped")

    def _run_loop(self):
        """Main loop chạy trong thread"""
        print("🔄 Service loop đang chạy...")
        
        while self.is_running:
            try:
                # 1. Lấy thông tin từ hardware
                vad = self.sound_detector.is_voice_detected()
                speech = self.sound_detector.is_speech_detected()
                direction = self.sound_detector.get_direction()
                
                # 2. Phân loại âm thanh (nếu enable)
                sound_type = SoundType.UNKNOWN
                if self.enable_audio_classification:
                    audio_data = self.audio_classifier.read_audio_chunk()
                    if audio_data is not None:
                        sound_type = self.audio_classifier.classify_sound(audio_data)
                else:
                    # Fallback: dùng VAD để phân loại đơn giản
                    if vad:
                        sound_type = SoundType.SPEECH
                    else:
                        sound_type = SoundType.SILENCE
                
                # 3. Update state
                self.current_state = {
                    'vad': vad,
                    'speech': speech,
                    'direction': direction,
                    'sound_type': sound_type,
                    'timestamp': datetime.now()
                }
                
                # 4. Update statistics
                self._update_statistics(self.current_state)
                
                # 5. Save to history (chỉ khi có thay đổi quan trọng)
                if vad or sound_type != SoundType.SILENCE:
                    self._add_to_history(self.current_state)
                
                # 6. Sleep một chút
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in service loop: {e}")
                time.sleep(1)

    def _update_statistics(self, state: Dict):
        self.statistics['total_detections'] += 1
        
        if state['vad']:
            self.statistics['vad_count'] += 1
        
        if state['speech']:
            self.statistics['speech_count'] += 1
        
        sound_type = state['sound_type']
        if isinstance(sound_type, SoundType):
            self.statistics['sound_types'][sound_type.value] += 1
        
        direction = state['direction']
        if direction is not None:
            # Convert direction to LED bin (0-11)
            led_bin = int((direction + 15) % 360 / 30) % 12
            self.statistics['direction_histogram'][led_bin] += 1

    def _add_to_history(self, state: Dict):
        """Thêm vào history"""
        event = {
            'timestamp': state['timestamp'].isoformat(),
            'vad': state['vad'],
            'speech': state['speech'],
            'direction': state['direction'],
            'sound_type': state['sound_type'].value if isinstance(state['sound_type'], SoundType) else str(state['sound_type'])
        }
        self.history.append(event)

    def get_current_state(self) -> Dict:
        state = self.current_state.copy()
        if isinstance(state.get('sound_type'), SoundType):
            state['sound_type'] = state['sound_type'].value
        if isinstance(state.get('timestamp'), datetime):
            state['timestamp'] = state['timestamp'].isoformat()
        return state

    def get_statistics(self) -> Dict:
        """Lấy thống kê"""
        return self.statistics.copy()

    def get_history(self, limit: int = 50) -> List[Dict]:
        """
        Lấy history
        Args:
            limit: Số lượng events tối đa
        Returns:
            List of events
        """
        return list(self.history)[-limit:]

    def print_status(self):
        """In status ra console (tiện cho debugging)"""
        state = self.current_state
        
        vad_icon = "🔴" if state['vad'] else "⚫"
        speech_icon = "🗣️" if state['speech'] else "🤫"
        direction = state['direction'] if state['direction'] is not None else "N/A"
        
        sound_type = state['sound_type']
        if isinstance(sound_type, SoundType):
            sound_type_str = sound_type.value
        else:
            sound_type_str = str(sound_type)
        
        emoji_map = {
            'silence': '🤫',
            'speech': '🗣️',
            'music': '🎵',
            'noise': '🔊',
            'unknown': '❓'
        }
        type_icon = emoji_map.get(sound_type_str, '❓')
        
        print(f"{vad_icon} VAD | "
              f"{speech_icon} Speech | "
              f"🧭 {direction}° | "
              f"{type_icon} {sound_type_str.upper()}")

    def monitor_console(self, interval: float = 0.5):
        """
        Monitor và in ra console
        Args:
            interval: Khoảng cách giữa các lần in (giây)
        """
        print("\n" + "=" * 60)
        print("📊 MONITOR MODE (Nhấn Ctrl+C để dừng)")
        print("=" * 60)
        
        try:
            while self.is_running:
                self.print_status()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n⏹️  Đã dừng monitor")


def main():
    """Demo chạy service"""
    print("=" * 60)
    print("🎤 ReSpeaker Sound Detection Service")
    print("=" * 60)
    
    # Khởi tạo service
    service = SoundDetectionService(
        enable_led=True,
        enable_audio_classification=True,
        history_size=100
    )
    
    # Khởi động
    if not service.start():
        print("❌ Không thể khởi động service")
        return
    
    try:
        # Monitor console
        service.monitor_console(interval=0.5)
        
        # Hoặc chỉ đợi
        # while True:
        #     time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Nhận tín hiệu dừng")
    finally:
        # Dừng service
        service.stop()
        
        # In statistics
        print("\n" + "=" * 60)
        print("📊 THỐNG KÊ:")
        print("=" * 60)
        stats = service.get_statistics()
        print(f"  Tổng detections: {stats['total_detections']}")
        print(f"  VAD triggers: {stats['vad_count']}")
        print(f"  Speech detections: {stats['speech_count']}")
        print(f"\n  Phân bố loại âm thanh:")
        for sound_type, count in stats['sound_types'].items():
            if count > 0:
                print(f"    {sound_type:8}: {count}")
        print(f"\n  Phân bố hướng (histogram):")
        for i, count in enumerate(stats['direction_histogram']):
            angle = i * 30
            bar = '█' * int(count / 10) if count > 0 else ''
            print(f"    {angle:3}°: {bar} ({count})")
        
        print("\n👋 Tạm biệt!")


if __name__ == '__main__':
    main()
