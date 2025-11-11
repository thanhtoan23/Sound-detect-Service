"""
Sound Detector Module
Phát hiện âm thanh sử dụng VAD và DOA từ ReSpeaker Mic Array v2.0

Chức năng:
- Voice Activity Detection (VAD): Phát hiện có tiếng nói không
- Direction of Arrival (DOA): Xác định hướng âm thanh (0-359 độ)
- Lấy các tham số từ chip XVF-3000
"""

import usb.core
import usb.util
import time
from typing import Optional, Dict, Tuple


class Tuning:
    """
    Class để giao tiếp với chip XVF-3000 qua USB
    Lấy thông tin VAD, DOA và các tham số khác
    """
    TIMEOUT = 100000

    def __init__(self, dev):
        self.dev = dev

    def write(self, name, value):
        """Ghi giá trị vào parameter"""
        try:
            self.dev.ctrl_transfer(
                usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
                0, 0, int(name), [int(value)], self.TIMEOUT)
        except usb.core.USBError as e:
            print(f"USB Error khi ghi {name}: {e}")

    def read(self, name):
        """Đọc giá trị từ parameter - theo code gốc từ respeaker/usb_4_mic_array"""
        try:
            # Parameters mapping: name -> (id, offset, type, ...)
            # VAD (VOICEACTIVITY): id=19, offset=32, type='int'
            # DOA (DOAANGLE): id=21, offset=0, type='int'
            # SPEECH (SPEECHDETECTED): id=19, offset=22, type='int'
            # AGC (AGCGAIN): id=19, offset=3, type='float'
            
            params = {
                19: 'int',  # VOICEACTIVITY
                21: 'int',  # DOAANGLE  
                22: 'int',  # SPEECHDETECTED
                6: 'float'  # AGCGAIN
            }
            
            param_id = int(name)
            param_type = params.get(param_id, 'int')
            
            # Offset mapping
            offsets = {
                19: 32,  # VOICEACTIVITY
                21: 0,   # DOAANGLE
                22: 22,  # SPEECHDETECTED
                6: 3     # AGCGAIN
            }
            
            offset = offsets.get(param_id, 0)
            
            # Build command: bit 7 set for read, bit 6 set for int type
            cmd = 0x80 | offset
            if param_type == 'int':
                cmd |= 0x40
            
            # Read 8 bytes
            response = self.dev.ctrl_transfer(
                usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
                0, cmd, param_id, 8, self.TIMEOUT)
            
            # Unpack response: two int32 values
            import struct
            result = struct.unpack('ii', bytes(response))
            
            if param_type == 'int':
                return result[0]
            else:
                # Float: mantissa * 2^exponent
                return result[0] * (2.0 ** result[1])
                
        except Exception as e:
            return None

    @property
    def direction(self):
        """Lấy góc DOA (Direction of Arrival) - 0-359 độ"""
        try:
            return self.read(21)  # DOAANGLE parameter
        except:
            return None

    @property
    def is_voice(self):
        """Kiểm tra có tiếng nói không - Voice Activity Detection"""
        try:
            return self.read(19)  # VOICEACTIVITY parameter
        except:
            return 0

    @property
    def speech_detected(self):
        """Phát hiện speech (chính xác hơn VAD)"""
        try:
            return self.read(22)  # SPEECHDETECTED parameter
        except:
            return 0

    @property
    def agc_gain(self):
        """Lấy AGC gain hiện tại (Automatic Gain Control)"""
        try:
            return self.read(6)  # AGCGAIN parameter
        except:
            return None

    def set_vad_threshold(self, threshold):
        """
        Đặt ngưỡng VAD (GAMMAVAD_SR)
        threshold: 0-60 dB (default: 3.5dB)
        Càng cao thì càng khó trigger
        """
        self.write(23, int(threshold))


class SoundDetector:
    """
    Class chính để phát hiện âm thanh
    Kết hợp VAD, DOA và các tính năng khác
    """
    
    # USB Vendor ID và Product ID của ReSpeaker USB 4 Mic Array
    VENDOR_ID = 0x2886
    PRODUCT_ID = 0x0018

    def __init__(self):
        self.dev = None
        self.tuning = None
        self.connected = False
        self._last_direction = 0
        self._last_vad_state = 0

    def connect(self) -> bool:
        """
        Kết nối với ReSpeaker Mic Array
        Returns: True nếu kết nối thành công
        """
        try:
            self.dev = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)
            
            if not self.dev:
                print("❌ Không tìm thấy ReSpeaker Mic Array v2.0")
                print("   Kiểm tra:")
                print("   - Đã cắm USB chưa?")
                print("   - Driver đã cài đặt chưa? (Windows cần libusb-win32)")
                return False

            self.tuning = Tuning(self.dev)
            self.connected = True
            print("✅ Đã kết nối ReSpeaker Mic Array v2.0")
            return True

        except Exception as e:
            print(f"❌ Lỗi khi kết nối: {e}")
            return False

    def disconnect(self):
        """Ngắt kết nối"""
        if self.dev:
            try:
                usb.util.dispose_resources(self.dev)
            except:
                pass
        self.connected = False
        print("🔌 Đã ngắt kết nối")

    def get_direction(self) -> Optional[int]:
        """
        Lấy hướng âm thanh (Direction of Arrival)
        Returns: Góc 0-359 độ, hoặc None nếu lỗi
        """
        if not self.connected:
            return None
        
        direction = self.tuning.direction
        if direction is not None:
            self._last_direction = direction
        return direction

    def is_voice_detected(self) -> bool:
        """
        Kiểm tra có phát hiện tiếng nói không
        Returns: True nếu có tiếng nói
        """
        if not self.connected:
            return False
        
        vad = self.tuning.is_voice
        self._last_vad_state = vad
        return bool(vad)

    def is_speech_detected(self) -> bool:
        """
        Kiểm tra có phát hiện speech không (chính xác hơn VAD)
        Returns: True nếu có speech
        """
        if not self.connected:
            return False
        
        return bool(self.tuning.speech_detected)

    def get_status(self) -> Dict:
        """
        Lấy trạng thái đầy đủ
        Returns: Dictionary chứa tất cả thông tin
        """
        if not self.connected:
            return {
                'connected': False,
                'error': 'Not connected to device'
            }

        return {
            'connected': True,
            'vad': self.is_voice_detected(),
            'speech': self.is_speech_detected(),
            'direction': self.get_direction(),
            'agc_gain': self.tuning.agc_gain,
            'timestamp': time.time()
        }

    def monitor(self, duration: int = 10, interval: float = 0.5):
        """
        Monitor liên tục trong khoảng thời gian
        
        Args:
            duration: Thời gian monitor (giây)
            interval: Khoảng cách giữa các lần đọc (giây)
        """
        if not self.connected:
            print("❌ Chưa kết nối với thiết bị")
            return

        print(f"🎤 Bắt đầu monitor trong {duration} giây...")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                status = self.get_status()
                
                vad_icon = "🔴" if status['vad'] else "⚫"
                speech_icon = "🗣️" if status['speech'] else "🤫"
                direction = status['direction'] if status['direction'] is not None else "N/A"
                agc = status['agc_gain'] if status['agc_gain'] is not None else 0
                
                print(f"{vad_icon} VAD: {status['vad']}  "
                      f"{speech_icon} Speech: {status['speech']}  "
                      f"🧭 Direction: {direction}°  "
                      f"📊 AGC: {agc}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Đã dừng monitor")

    def wait_for_sound(self, timeout: int = 30) -> Optional[Tuple[int, bool]]:
        """
        Chờ đến khi phát hiện âm thanh
        
        Args:
            timeout: Thời gian chờ tối đa (giây)
            
        Returns:
            Tuple (direction, is_speech) hoặc None nếu timeout
        """
        if not self.connected:
            return None

        print(f"⏳ Đang chờ phát hiện âm thanh (timeout: {timeout}s)...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.is_voice_detected():
                direction = self.get_direction()
                speech = self.is_speech_detected()
                print(f"✅ Phát hiện âm thanh! Hướng: {direction}°, Speech: {speech}")
                return (direction, speech)
            
            time.sleep(0.1)

        print("⏱️  Timeout - Không phát hiện âm thanh")
        return None


def main():
    """Demo sử dụng SoundDetector"""
    print("=" * 60)
    print("🎤 ReSpeaker Sound Detector Demo")
    print("=" * 60)
    
    detector = SoundDetector()
    
    # Kết nối
    if not detector.connect():
        return
    
    try:
        # Test 1: Lấy status hiện tại
        print("\n📊 Status hiện tại:")
        status = detector.get_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # Test 2: Monitor liên tục
        print("\n🔄 Monitor mode (nhấn Ctrl+C để dừng):")
        detector.monitor(duration=30, interval=0.5)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Đã dừng")
    finally:
        detector.disconnect()


if __name__ == '__main__':
    main()
