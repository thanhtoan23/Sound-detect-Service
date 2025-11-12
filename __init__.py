"""
Package initialization for sound_service
"""

from .sound_detector import SoundDetector, Tuning
from .audio_classifier import AudioClassifier, SoundType
from .led_visualizer import LEDVisualizer, ColorScheme
from .sound_service import SoundDetectionService

__version__ = '1.0.0'
__all__ = [
    'SoundDetector',
    'Tuning',
    'AudioClassifier', 
    'SoundType',
    'LEDVisualizer',
    'ColorScheme',
    'SoundDetectionService'
]
