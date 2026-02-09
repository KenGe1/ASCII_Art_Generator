**English version available here: [README_EN.md](README_EN.md).
---
# ASCII Art Generator (GUI)

Ein moderner **ASCII Art Generator mit grafischer Benutzeroberfläche**, geschrieben in Python.  
Das Tool konvertiert Bilder in farbiges oder monochromes ASCII-Art und bietet zahlreiche Anpassungsmöglichkeiten – inklusive **Drag & Drop**, **Live-Statusanzeige** und **Multiprocessing** für performante Verarbeitung.

---

## ✨ Features

- 🖼️ **Bild → ASCII Art Konvertierung**
- 🎨 Farbmodi:
  - Schwarz & Weiß
  - 8 Farben
  - Full Color
- 📐 Bildrotation (0°, 90°, 180°, 270°)
- ☀️ Helligkeitsanpassung
- 🔢 Variable Spaltenanzahl (Detailgrad)
- 🧵 **Multiprocessing** (GUI bleibt responsiv)
- 📂 **Drag & Drop** für Bilder
- 💾 Export als JPG, PNG, GIF, TIFF, BMP
- 🪟 Moderne Dark-Mode-GUI mit `customtkinter`
- 🔄 Lade-Spinner & Statusfeedback
- 🧩 Erweiterte Einstellungen (JPEG-Qualität)

---

## 🚀 Installation (Python)

### Voraussetzungen

- **Python 3.10 oder neuer**
- Windows 10 / 11

### Abhängigkeiten installieren

```bash
pip install ascii-magic, customtkinter, pillow, tkinterdnd2
```

---

## ▶️ Starten

```bash
python main.py
```

---

## 📦 Als EXE bauen (Nuitka)

Das Projekt ist vollständig kompatibel mit **Nuitka**, inklusive GUI & Multiprocessing.

### Empfohlener Build (Onefile, ohne Konsole)

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

> **Hinweis:**  
> Die `include-*` Optionen sind notwendig, damit alle Ressourcen (Fonts, interne Daten) korrekt in der EXE enthalten sind.

---

## 🧠 Technische Details

- **GUI:** customtkinter + tkinterdnd2  
- **Bildverarbeitung:** Pillow  
- **ASCII-Rendering:** ascii_magic  
- **Parallelisierung:** multiprocessing (spawn-Methode)  
- **Windows-Optimierungen:**
  - Dark Titlebar (Windows 10 / 11)
  - GUI-Subsystem (keine Konsole)

---

## 🧪 Warum Multiprocessing?

Die ASCII-Generierung kann bei großen Bildern sehr rechenintensiv sein.  
Durch einen separaten Worker-Prozess bleibt die Benutzeroberfläche jederzeit **reaktionsfähig**.

---

## ⚠️ Bekannte Einschränkungen

- Sehr große Bilder benötigen viel Speicher
- Onefile-EXE startet etwas langsamer (temporäres Entpacken)
- Aktuell primär für Windows optimiert

---

## 🤝 Mitwirken

Pull Requests, Issues und Verbesserungsvorschläge sind willkommen.  
Besonders gern gesehen:

- UI-Verbesserungen
- Performance-Optimierungen
- Linux / macOS Support
- Verarbeitung von GIF Animationen

---

## ❤️ Credits

- ascii_magic  
- customtkinter  
- Pillow  
- Python Open-Source Community
