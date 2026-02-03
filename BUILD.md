# Build (PyInstaller)

## Prereqs
- Python 3.x
- `icon.ico` placed in the repo root (same folder as `main.py`)

## Commands
```bash
python -m pip install --upgrade pyinstaller
python -m pyinstaller --noconfirm --onefile --windowed --name "cx.manager" --icon icon.ico main.py
```

If you see `No module named pyinstaller`, install it for the same Python you’re using:
```bash
python -m pip install pyinstaller
```

The executable will be in `dist/cx.manager.exe`.
