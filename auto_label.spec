# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 定义额外的资源文件
datas = [
    ('mobileclip-pytorch/', 'mobileclip-pytorch/'),
    ('mobileclip_blt.ts', '.'),
    ('modules/', 'modules/'),
]

# 定义隐藏的导入
hiddenimports = [
    'torch',
    'torchvision',
    'ultralytics',
    'numpy',
    'cv2',
    'PIL',
    'yaml',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
]

# 定义排除的模块（如果有的话）
excludes = []

# 创建 Analysis 对象
analysis = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 创建 PYZ 对象
pyz = PYZ(
    analysis.pure,
    analysis.zipped_data,
    cipher=block_cipher,
)

# 创建 EXE 对象
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name='自动标注系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标文件，可以在这里指定
)
