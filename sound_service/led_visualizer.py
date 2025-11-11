"""
LED Visualizer Module
Điều khiển LED dựa trên kết quả phát hiện âm thanh

Chức năng:
- Hiển thị hướng âm thanh (DOA) bằng LED màu xanh
- Hiển thị loại âm thanh bằng màu sắc khác nhau
- Animation động theo VAD
"""

import sys
import os
import time
from typing import Optional

# Import pixel_ring từ thư mục testing_feature
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'testing_feature', 'control_led', 'pixel_ring'))

try:
    from pixel_ring import pixel_ring
    PIXEL_RING_AVAILABLE = True
except ImportError:
    PIXEL_RING_AVAILABLE = False
    print("⚠️  Không thể import pixel_ring, chạy ở chế độ simulation")


class ColorScheme:
    """Bảng màu cho các loại âm thanh"""
    
    # Màu cơ bản (RGB format: 0xRRGGBB)
    OFF = 0x000000
    
    # Màu cho loại âm thanh
    SILENCE = 0x0A0A0A      # Xám đậm (gần như tắt)
    SPEECH = 0x00FF00       # Xanh lá (speech)
    MUSIC = 0xFF00FF        # Tím (music)
    NOISE = 0xFF0000        # Đỏ (noise)
    UNKNOWN = 0xFFFF00      # Vàng (unknown)
    
    # Màu cho direction indicator
    DIRECTION = 0x00FFFF    # Cyan (chỉ hướng)
    
    # Màu cho VAD
    VAD_ACTIVE = 0x0000FF   # Xanh dương (có tiếng nói)
    VAD_INACTIVE = 0x1A1A1A # Xám nhạt (không có tiếng nói)


class LEDVisualizer:
    """
    Điều khiển LED ring để hiển thị kết quả detect âm thanh
    """
    
    # Số LED trong ring
    NUM_LEDS = 12
    
    # Độ sáng mặc định (0-100)
    DEFAULT_BRIGHTNESS = 30
    
    def __init__(self, simulation_mode: bool = False):
        """
        Khởi tạo LED Visualizer
        
        Args:
            simulation_mode: True = không điều khiển LED thật, chỉ in console
        """
        self.simulation_mode = simulation_mode or not PIXEL_RING_AVAILABLE
        self.current_pattern = "google"  # google hoặc echo
        self.brightness = self.DEFAULT_BRIGHTNESS
        
        if not self.simulation_mode:
            try:
                pixel_ring.set_brightness(self.brightness)
                pixel_ring.change_pattern(self.current_pattern)
                print(f"✅ Đã khởi tạo LED ring (pattern: {self.current_pattern})")
            except Exception as e:
                print(f"⚠️  Lỗi khởi tạo LED: {e}, chuyển sang simulation mode")
                self.simulation_mode = True
        else:
            print("🎨 Chạy ở chế độ simulation (không điều khiển LED thật)")

    def set_brightness(self, brightness: int):
        """
        Đặt độ sáng LED
        
        Args:
            brightness: 0-100
        """
        self.brightness = max(0, min(100, brightness))
        
        if not self.simulation_mode:
            try:
                pixel_ring.set_brightness(self.brightness)
                print(f"💡 Độ sáng: {self.brightness}%")
            except:
                pass
        else:
            print(f"[SIM] 💡 Brightness: {self.brightness}%")

    def change_pattern(self, pattern: str):
        """
        Đổi pattern LED (echo hoặc google)
        
        Args:
            pattern: 'echo' hoặc 'google'
        """
        if pattern not in ['echo', 'google']:
            print(f"⚠️  Pattern không hợp lệ: {pattern}")
            return
        
        self.current_pattern = pattern
        
        if not self.simulation_mode:
            try:
                pixel_ring.change_pattern(pattern)
                print(f"🎨 Pattern: {pattern}")
            except:
                pass
        else:
            print(f"[SIM] 🎨 Pattern: {pattern}")

    def show_direction(self, angle: int, color: int = ColorScheme.DIRECTION):
        """
        Hiển thị hướng âm thanh bằng 1 LED sáng
        
        Args:
            angle: Góc 0-359 độ
            color: Màu hiển thị (RGB)
        """
        if angle is None:
            return
        
        # Tính LED position từ góc (12 LEDs, mỗi LED = 30 độ)
        led_position = int((angle + 15) % 360 / 30) % self.NUM_LEDS
        
        if not self.simulation_mode:
            try:
                pixel_ring.wakeup(angle)
                # Hoặc có thể dùng: pixel_ring.set_color(rgb=color)
            except Exception as e:
                print(f"⚠️  Lỗi hiển thị direction: {e}")
        else:
            # Visualize trong console
            leds = ['⚫'] * self.NUM_LEDS
            leds[led_position] = '🟢'
            print(f"[SIM] 🧭 Direction {angle}°: {' '.join(leds)}")

    def show_sound_type(self, sound_type: str):
        """
        Hiển thị loại âm thanh bằng màu sắc
        
        Args:
            sound_type: 'silence', 'speech', 'music', 'noise', 'unknown'
        """
        # Map loại âm thanh sang màu
        color_map = {
            'silence': ColorScheme.SILENCE,
            'speech': ColorScheme.SPEECH,
            'music': ColorScheme.MUSIC,
            'noise': ColorScheme.NOISE,
            'unknown': ColorScheme.UNKNOWN
        }
        
        color = color_map.get(sound_type.lower(), ColorScheme.UNKNOWN)
        
        if not self.simulation_mode:
            try:
                # Set tất cả LEDs cùng màu
                pixel_ring.set_color(rgb=color)
            except Exception as e:
                print(f"⚠️  Lỗi hiển thị sound type: {e}")
        else:
            # Emoji cho mỗi loại
            emoji_map = {
                'silence': '🤫',
                'speech': '🗣️',
                'music': '🎵',
                'noise': '🔊',
                'unknown': '❓'
            }
            emoji = emoji_map.get(sound_type.lower(), '❓')
            hex_color = f"#{color:06X}"
            print(f"[SIM] 🎨 Sound Type: {emoji} {sound_type} (color: {hex_color})")

    def show_vad_status(self, is_voice: bool):
        """
        Hiển thị trạng thái VAD (có tiếng nói không)
        
        Args:
            is_voice: True nếu có tiếng nói
        """
        if not self.simulation_mode:
            try:
                if is_voice:
                    pixel_ring.listen()  # LED xanh dương
                else:
                    pixel_ring.off()
            except:
                pass
        else:
            status = "🔴 VAD: ACTIVE" if is_voice else "⚫ VAD: INACTIVE"
            print(f"[SIM] {status}")

    def show_thinking(self):
        """Animation đang xử lý"""
        if not self.simulation_mode:
            try:
                pixel_ring.think()
            except:
                pass
        else:
            print("[SIM] 🤔 Thinking...")

    def show_speaking(self):
        """Animation đang nói"""
        if not self.simulation_mode:
            try:
                pixel_ring.speak()
            except:
                pass
        else:
            print("[SIM] 💬 Speaking...")

    def show_combined(self, direction: Optional[int], sound_type: str, is_voice: bool):
        """
        Hiển thị kết hợp: hướng + loại âm thanh + VAD
        
        Args:
            direction: Góc 0-359 (None nếu không có)
            sound_type: Loại âm thanh
            is_voice: Có tiếng nói không
        """
        if sound_type == 'silence':
            self.off()
            return
        
        # Ưu tiên hiển thị hướng nếu có tiếng nói
        if is_voice and direction is not None:
            self.show_direction(direction)
        else:
            self.show_sound_type(sound_type)

    def show_volume(self, volume: int):
        """
        Hiển thị volume (0-12)
        
        Args:
            volume: Mức volume 0-12
        """
        volume = max(0, min(12, volume))
        
        if not self.simulation_mode:
            try:
                pixel_ring.set_volume(volume)
            except:
                pass
        else:
            bars = '▓' * volume + '░' * (12 - volume)
            print(f"[SIM] 📊 Volume: {bars} ({volume}/12)")

    def off(self):
        """Tắt tất cả LED"""
        if not self.simulation_mode:
            try:
                pixel_ring.off()
            except:
                pass
        else:
            print("[SIM] ⚫ LEDs OFF")

    def demo_colors(self):
        """Demo tất cả màu sắc"""
        print("\n🎨 DEMO MÀU SẮC:")
        print("=" * 60)
        
        sound_types = ['silence', 'speech', 'music', 'noise', 'unknown']
        
        for sound_type in sound_types:
            print(f"\n  Hiển thị: {sound_type.upper()}")
            self.show_sound_type(sound_type)
            time.sleep(2)
        
        print("\n  Hiển thị: DIRECTION (0°, 90°, 180°, 270°)")
        for angle in [0, 90, 180, 270]:
            self.show_direction(angle)
            time.sleep(1)
        
        self.off()
        print("\n✅ Demo hoàn tất")

    def demo_animations(self):
        """Demo các animations"""
        print("\n🎬 DEMO ANIMATIONS:")
        print("=" * 60)
        
        animations = [
            ('Thinking', self.show_thinking),
            ('Speaking', self.show_speaking),
            ('VAD Active', lambda: self.show_vad_status(True)),
            ('VAD Inactive', lambda: self.show_vad_status(False))
        ]
        
        for name, anim_func in animations:
            print(f"\n  Animation: {name}")
            anim_func()
            time.sleep(3)
        
        self.off()
        print("\n✅ Demo hoàn tất")


def main():
    """Demo sử dụng LEDVisualizer"""
    print("=" * 60)
    print("💡 ReSpeaker LED Visualizer Demo")
    print("=" * 60)
    
    # Khởi tạo (simulation_mode=True để test mà không cần hardware)
    visualizer = LEDVisualizer(simulation_mode=False)
    
    try:
        # Demo 1: Màu sắc
        visualizer.demo_colors()
        
        time.sleep(2)
        
        # Demo 2: Animations
        visualizer.demo_animations()
        
        time.sleep(2)
        
        # Demo 3: Combined visualization
        print("\n🎯 DEMO COMBINED:")
        print("=" * 60)
        
        scenarios = [
            (180, 'speech', True, "Có tiếng nói từ phía sau (180°)"),
            (90, 'music', False, "Nhạc từ bên phải (90°)"),
            (0, 'noise', False, "Tiếng ồn từ phía trước (0°)"),
            (None, 'silence', False, "Im lặng")
        ]
        
        for direction, sound_type, is_voice, description in scenarios:
            print(f"\n  Scenario: {description}")
            visualizer.show_combined(direction, sound_type, is_voice)
            time.sleep(3)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Đã dừng")
    finally:
        visualizer.off()
        print("\n👋 Tạm biệt!")


if __name__ == '__main__':
    main()
