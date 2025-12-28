"""Sound Detector Module for ReSpeaker Mic Array v2.0"""

import usb.core
import usb.util
import time
from typing import Optional, Dict, Tuple


class Tuning:
    TIMEOUT = 100000

    def __init__(self, dev):
        self.dev = dev

    def write(self, name, value):
        try:
            self.dev.ctrl_transfer(
                usb.util.CTRL_OUT | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
                0, 0, int(name), [int(value)], self.TIMEOUT)
        except usb.core.USBError as e:
            print(f"USB Error khi ghi {name}: {e}")

    def read(self, name):
        try:
            params = {
                19: 'int',
                21: 'int',
                22: 'int',
                6: 'float'
            }
            
            param_id = int(name)
            param_type = params.get(param_id, 'int')
            
            offsets = {
                19: 32,
                21: 0,
                22: 22,
                6: 3
            }
            
            offset = offsets.get(param_id, 0)
            
            cmd = 0x80 | offset
            if param_type == 'int':
                cmd |= 0x40
            
            response = self.dev.ctrl_transfer(
                usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
                0, cmd, param_id, 8, self.TIMEOUT)
            
            import struct
            result = struct.unpack('ii', bytes(response))
            
            if param_type == 'int':
                return result[0]
            else:
                return result[0] * (2.0 ** result[1])
                
        except Exception as e:
            return None

    @property
    def direction(self):
        try:
            return self.read(21)
        except:
            return None

    @property
    def is_voice(self):
        try:
            return self.read(19)
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
