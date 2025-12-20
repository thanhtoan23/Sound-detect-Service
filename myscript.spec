# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# DANH SÁCH CÁC FILE CODE CỦA BẠN
# Chúng ta liệt kê TẤT CẢ các file .py ở đây để PyInstaller không thể bỏ sót
my_scripts = [
    'gui_app.py',
    'smart_audio_pipeline.py',
    'audio_classifier.py',
    'audio_processor.py',
    'sound_detector.py',
    'config.py'
]

a = Analysis(
    my_scripts,
    pathex=[],
    binaries=[],
    # Đưa file model .h5 vào thư mục gốc (.)
    datas=[('env_sounds_cnn_11cls.h5', '.')],
    # Thêm các thư viện ẩn nếu cần (đôi khi sklearn/scipy cần cái này)
    hiddenimports=['sklearn.utils._cython_blas', 'sklearn.neighbors.typedefs', 'sklearn.neighbors.quad_tree', 'sklearn.tree', 'sklearn.tree._utils'],
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
    name='gui_app',  # Tên file exe sẽ tạo ra
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Đặt False để ẩn màn hình đen, đặt True để hiện debug nếu lỗi
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)