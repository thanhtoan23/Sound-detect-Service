"""
Configuration file for ReSpeaker Sound Detection Service
"""

# ReSpeaker Hardware Configuration
RESPEAKER_VID = 0x2886
RESPEAKER_PID = 0x0018
RESPEAKER_RATE = 16000
RESPEAKER_CHANNELS = 6
RESPEAKER_WIDTH = 2

# Audio Classification Thresholds
RMS_THRESHOLD_SPEECH = 500
RMS_THRESHOLD_MUSIC = 1000
ZCR_THRESHOLD_LOW = 0.05
ZCR_THRESHOLD_HIGH = 0.15

# Service Settings
HISTORY_MAX_SIZE = 100
UPDATE_INTERVAL = 0.5  # seconds
MONITOR_REFRESH_RATE = 0.3  # seconds

# LED Settings
LED_COUNT = 12
LED_BRIGHTNESS = 20  # 0-31

# API Settings
API_HOST = '0.0.0.0'
API_PORT = 5000
API_DEBUG = False

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
