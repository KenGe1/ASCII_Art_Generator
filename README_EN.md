# ASCII Art Generator (GUI)

A modern **ASCII art generator with a graphical user interface**, written in Python.  
The tool converts images into color or monochrome ASCII art and offers numerous customization options — including **drag & drop**, **live status indicators**, and **multiprocessing** for performant processing.

---

## ✨ Features

- 🖼️ **Image → ASCII Art conversion**
- 🎨 Color modes:
  - Black & White
  - 8 colors
  - Full color
- 📐 Image rotation (0°, 90°, 180°, 270°)
- ☀️ Brightness adjustment
- 🔢 Variable column count (level of detail)
- 🧵 **Multiprocessing** (GUI remains responsive)
- 📂 **Drag & Drop** for images
- 💾 Export as JPG, PNG, GIF, TIFF, BMP
- 🎞️ Animated GIFs are processed frame-by-frame and exported as animated GIFs
- 🪟 Modern dark-mode GUI with `customtkinter`
- 🔄 Loading spinner & status feedback
- 🧩 Advanced settings (JPEG quality)

---

## 🚀 Installation (Python)

### Requirements

- **Python 3.10 or newer**
- Windows 10 / 11

### Install dependencies

```bash
pip install ascii-magic, customtkinter, pillow, tkinterdnd2
```

---

## ▶️ Run

```bash
python main.py
```

---

## 📦 Build as EXE (Nuitka)

The project is fully compatible with **Nuitka**, including GUI & multiprocessing.

### Recommended build (onefile, no console)

```powershell
python -m nuitka ^
  --onefile ^
  --windows-disable-console ^
  --enable-plugin=tk-inter ^
  --include-package=ascii_magic ^
  --include-data-dir=.venv\Lib\site-packages\ascii_magic=ascii_magic ^
  --include-module=multiprocessing.spawn ^
  --include-module=multiprocessing.resource_tracker ^
  --output-filename=ASCII_Art_Generator.exe ^
  main.py
```

> **Note:**  
> The `include-*` options are required so that all resources (fonts, internal data) are correctly bundled into the EXE.

---

## 🧠 Technical details

- **GUI:** customtkinter + tkinterdnd2  
- **Image processing:** Pillow  
- **ASCII rendering:** ascii_magic  
- **Parallelization:** multiprocessing (spawn method)  
- **Windows optimizations:**
  - Dark title bar (Windows 10 / 11)
  - GUI subsystem (no console)

---

## 🧪 Why multiprocessing?

ASCII generation can be very CPU-intensive for large images.  
A separate worker process keeps the user interface **responsive** at all times.

---

## ⚠️ Known limitations

- Very large images require a lot of memory
- Onefile EXE starts a bit slower (temporary extraction)
- Currently optimized primarily for Windows

---

## 🤝 Contributing

Pull requests, issues, and improvement suggestions are welcome.  
Especially appreciated:

- UI improvements
- Performance optimizations
- Linux / macOS support

---

## ❤️ Credits

- ascii_magic  
- customtkinter  
- Pillow  
- Python open-source community
