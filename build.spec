# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# --- CHIẾN THUẬT 1: LẤY ĐƯỜNG DẪN TUYỆT ĐỐI ---
# Lấy đường dẫn của thư mục hiện tại nơi chứa file spec này
current_dir = os.path.abspath(os.getcwd())

# --- CHIẾN THUẬT 2: KHAI BÁO RÕ RÀNG CÁC MODULE ---
# Ép buộc PyInstaller phải nhìn thấy các file này
my_hidden_imports = [
    'smart_audio_pipeline',  # <--- Module đang bị lỗi
    'sound_detector',
    'audio_classifier',
    'audio_processor',
    'config',
    'queue',
    'threading',
    'tkinter',
    'tensorflow',  # Thêm tensorflow vào để chắc chắn hooks hoạt động
]

a = Analysis(
    ['gui_app.py'],
    pathex=[current_dir], # <--- QUAN TRỌNG: Ép PyInstaller tìm file ở đây
    binaries=[],
    datas=[('env_sounds_cnn_11cls.h5', '.')],
    hiddenimports=my_hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SmartAudioMonitor_Final', # Đổi tên để tránh nhầm file cũ
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # GIỮ LẠI MÀN HÌNH ĐEN ĐỂ DEBUG NẾU CÒN LỖI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)