# Build-time only. PyInstaller supplies Analysis/PYZ/EXE/COLLECT/BUNDLE.
from platform import mac_ver

from build_macos import APP_VERSION, BUILD_NUMBER, BUNDLE_ID, DATA_FILES, ROOT, TARGET_ARCH


analysis = Analysis(
    [str(ROOT / "app_entry.py")], pathex=[str(ROOT)], binaries=[],
    datas=[(str(ROOT / name), ".") for name in DATA_FILES],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["build_macos", "pytest"], noarchive=False, optimize=0,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, [], exclude_binaries=True, name="TrustBench",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, argv_emulation=False, target_arch=TARGET_ARCH,
    codesign_identity=None, entitlements_file=None,
)
collection = COLLECT(
    executable, analysis.binaries, analysis.datas, strip=False, upx=False, name="TrustBench",
)
application = BUNDLE(
    collection, name="TrustBench.app", bundle_identifier=BUNDLE_ID, version=APP_VERSION,
    info_plist={
        "CFBundleDisplayName": "TrustBench",
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": BUILD_NUMBER,
        "LSMinimumSystemVersion": mac_ver()[0],
        "NSHighResolutionCapable": True,
    },
)
