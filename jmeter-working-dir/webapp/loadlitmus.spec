# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for LoadLitmus.

Build with: pyinstaller loadlitmus.spec
Output: dist/loadlitmus.exe
"""

block_cipher = None

a = Analysis(
    ['__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('config', 'config'),
        ('prompts', 'prompts'),
        ('jtl_filter.py', '.'),
    ],
    hiddenimports=[
        # uvicorn loads these dynamically
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # multipart form handling
        'multipart',
        # our routers and services
        'routers.dashboard',
        'routers.config',
        'routers.test_data',
        'routers.test_plans',
        'routers.results',
        'routers.settings',
        'routers.extensions',
        'services.auth',
        'services.config_parser',
        'services.data',
        'services.jmeter',
        'services.jmx_patcher',
        'services.jtl_parser',
        'services.analysis',
        'services.report',
        'services.report_properties',
        'services.settings',
        'services.slaves',
        'services.process_manager',
        'services.templates',
        'services.paths',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test dependencies to reduce size
        'pytest',
        'pytest_cov',
        'coverage',
        'tkinter',
        'matplotlib',
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='loadlitmus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='static/favicon.ico',  # Uncomment when .ico file is available
)
