from setuptools import setup

APP = ['src/zennode/app/menubar.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True, # Don't show in the Dock
        'NSMicrophoneUsageDescription': 'AuDHD Pipeline needs access to record your voice dumps.',
    },
    'packages': ['rumps', 'pydub', 'pyaudio', 'zennode'],
}

setup(
    name="AuDHD Pipeline",
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
)
