import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from multiprocessing import Process, Queue
import itertools
import ctypes
from ascii_magic import AsciiArt
from PIL import Image, ImageEnhance

Image.MAX_IMAGE_PIXELS = 400_000_000

class ToolTip(ctk.CTkToplevel):
    def __init__(self, widget, text):
        super().__init__(widget)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        label = ctk.CTkLabel(
            self,
            text=text,
            font=("Segoe UI", 12),
            corner_radius=8,
            fg_color=("gray85", "gray20"),
            text_color=("black", "white"),
            padx=10,
            pady=6,
            justify="left",
            wraplength=260
        )
        label.pack()

        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event):
        x = event.widget.winfo_rootx() + 20
        y = event.widget.winfo_rooty() + 20
        self.geometry(f"+{x}+{y}")
        self.deiconify()

    def hide(self, event):
        self.withdraw()

def labeled_with_info(parent, text, info):
    frame = ctk.CTkFrame(parent, fg_color="transparent")

    lbl = ctk.CTkLabel(
        frame,
        text=text,
        font=("Segoe UI", 14)
    )
    lbl.pack(side="left")

    info_icon = ctk.CTkLabel(
        frame,
        text="ⓘ",
        font=("Segoe UI", 14, "bold"),
        text_color=("gray40", "gray70"),
        cursor="hand2"
    )
    info_icon.pack(side="left", padx=(6, 0))

    ToolTip(info_icon, info)

    return frame

def enable_dark_titlebar(window):
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())

        value = ctypes.c_int(1)

        # Windows 11
        DWMWA_USE_IMMERSIVE_DARK_MODE_WIN11 = 20
        # Windows 10
        DWMWA_USE_IMMERSIVE_DARK_MODE_WIN10 = 19

        # Erst Windows 11 versuchen
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE_WIN11,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )

        # Falls das fehlschlägt → Windows 10
        if result != 0:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_WIN10,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )

    except Exception:
        pass

# ---------- Appearance ----------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

def generate_ascii_worker(input_img, output, params, queue):
    rotate = params["rotate"]
    columns = params["columns"]
    brightness = params["brightness"]
    quality = params["quality"]
    mode = params["color_mode"]

    if mode == "Schwarz & Weiß":
        full_color = False
        monochrome = True
    elif mode == "8 Farben":
        full_color = False
        monochrome = False
    else:
        full_color = True
        monochrome = False

    output_dir = os.path.dirname(output) or "."
    temp_out = os.path.join(output_dir, "temp.jpg")

    try:
        my_art = AsciiArt.from_image(input_img)

        if brightness != 1:
            my_art.image = ImageEnhance.Brightness(
                my_art.image
            ).enhance(brightness)

        if rotate != 0:
            my_art.image = my_art.image.rotate(
                rotate, expand=True
            )

        my_art.to_image_file(
            temp_out,
            columns=columns,
            full_color=full_color,
            monochrome=monochrome
        )

        img = Image.open(temp_out)
        img.save(
            output,
            quality=quality,
            optimize=True,
            subsampling=0
        )
    except Exception as e:
        queue.put(e)  # Fehler in die Queue schreiben
        return
    finally:
        if os.path.exists(temp_out):
            os.remove(temp_out)

    # Erfolg in die Queue schreiben
    queue.put(True)

class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("ASCII Art Generator")
        self.geometry("720x820")
        self.configure(bg="#121212")
        self.after(10, lambda: enable_dark_titlebar(self))

        # ---------- Variables ----------
        self.input_image = ctk.StringVar()
        self.output_path = ctk.StringVar()

        self.columns = ctk.StringVar(value="300")
        self.rotation = ctk.StringVar(value="0")
        self.brightness = ctk.StringVar(value="1.0")
        self.color_mode = ctk.StringVar(value="Full Color")

        self.jpg_quality = ctk.IntVar(value=95)
        self.advanced = ctk.BooleanVar(value=False)

        self.spinner_running = False
        self.spinner_cycle = itertools.cycle(
            ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        )

        self.process = None  # Für den Multiprocessing-Prozess
        self.result_queue = Queue()  # Queue für die Kommunikation zwischen Prozessen

        self.build_ui()

    def start_move(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def do_move(self, e):
        self.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ---------- UI ----------
    def build_ui(self):
        main = ctk.CTkFrame(self, corner_radius=20)
        main.pack(padx=25, pady=(35, 25), fill="both", expand=True)

        ctk.CTkLabel(main, text="ASCII Art Generator",
                     font=("Segoe UI", 26, "bold")).pack(pady=(10, 25))

        # --- Drag & Drop ---
        self.drop_label = ctk.CTkLabel(
            main,
            text="📂 Bild hier hineinziehen\n\n",
            height=140,
            corner_radius=14,
            fg_color=("gray25", "gray15"),
            font=("Segoe UI", 16),
            justify="center"
        )
        self.drop_label.pack(fill="x", padx=25, pady=(0, 30))
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self.drop_file)

        # --- Output ---
        ctk.CTkLabel(main, text="Speicherort",
                     font=("Segoe UI", 14)).pack(anchor="center")

        path = ctk.CTkFrame(main, fg_color="transparent")
        path.pack(fill="x", padx=25, pady=(8, 30))

        ctk.CTkEntry(path, textvariable=self.output_path,
                     height=44).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(path, text="📁", width=54, height=44,
                      command=self.select_output).pack(side="left", padx=(10, 0))

        # --- Settings (2x2 Grid) ---
        settings = ctk.CTkFrame(main, fg_color="transparent")
        settings.pack(pady=(0, 35))

        # Spalten gleich breit
        settings.grid_columnconfigure((0, 1), weight=1)

        # Labels
        labeled_with_info(
            settings,
            "Columns",
            "Anzahl der Zeichen pro Zeile.\n"
            "Höher = mehr Details, aber größere Datei."
        ).grid(row=0, column=0, pady=(0, 6))

        labeled_with_info(
            settings,
            "Rotation",
            "Dreht das Bild vor der ASCII-Umwandlung nach links.\n"
            "Nützlich für Hochformat-Bilder."
        ).grid(row=0, column=1, pady=(0, 6))

        labeled_with_info(
            settings,
            "Helligkeit",
            "Passt die Bildhelligkeit an.\n"
            "1.0 = unverändert\n"
            "< 1 = dunkler\n"
            "> 1 = heller"
        ).grid(row=2, column=0, pady=(16, 6))

        labeled_with_info(
            settings,
            "Farbe",
            "Schwarz & Weiß: reines ASCII\n"
            "8 Farben: begrenzte Farbpalette\n"
            "Full Color: maximale Farbtiefe"
        ).grid(row=2, column=1, pady=(16, 6))

        # Eingabefelder
        ctk.CTkEntry(
            settings,
            textvariable=self.columns,
            width=180,
            height=44,
            justify="center"
        ).grid(row=1, column=0, padx=25)

        ctk.CTkOptionMenu(
            settings,
            values=["0", "90", "180", "270"],
            variable=self.rotation,
            height=44,
            width=180
        ).grid(row=1, column=1, padx=25)

        ctk.CTkEntry(
            settings,
            textvariable=self.brightness,
            width=180,
            height=44,
            justify="center"
        ).grid(row=3, column=0, padx=25)

        ctk.CTkOptionMenu(
            settings,
            values=["Schwarz & Weiß", "8 Farben", "Full Color"],
            variable=self.color_mode,
            height=44,
            width=180
        ).grid(row=3, column=1, padx=25)

        # --- Advanced (fix unten rechts, unabhängig vom Layout) ---
        self.adv_overlay = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        # unten rechts im Fenster
        self.adv_overlay.place(
            relx=1.0,
            rely=1.0,
            anchor="se",
            x=-20,
            y=-20
        )

        # Frame für die Advanced-Inhalte (links von Checkbox)
        self.adv_frame = ctk.CTkFrame(
            self.adv_overlay,
            fg_color="transparent"
        )

        ctk.CTkLabel(
            self.adv_frame,
            text="JPEG Qualität",
            font=("Segoe UI", 13)
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        ctk.CTkEntry(
            self.adv_frame,
            textvariable=self.jpg_quality,
            width=100,
            height=36
        ).grid(row=1, column=0, padx=(0, 8))

        # standardmäßig versteckt
        self.adv_frame.grid_forget()

        # Checkbox rechts außen
        ctk.CTkCheckBox(
            self.adv_overlay,
            text="Erweitert",
            variable=self.advanced,
            command=lambda:
                self.adv_frame.grid(row=0, column=0, rowspan=2, padx=(0, 12))
                if self.advanced.get()
                else self.adv_frame.grid_forget()
        ).grid(row=0, column=1, rowspan=2)

        # --- Generate ---
        gen = ctk.CTkFrame(main, fg_color="transparent")
        gen.pack(fill="x", padx=25, pady=25)

        self.generate_btn = ctk.CTkButton(
            gen, text="🚀 Generieren",
            height=54, font=("Segoe UI", 16, "bold"),
            command=self.run
        )
        self.generate_btn.pack(side="left", expand=True)

        self.loading_label = ctk.CTkLabel(
            gen, text="", font=("Segoe UI", 18)
        )
        self.loading_label.pack(side="left", padx=12)

    # ---------- Logic ----------
    def drop_file(self, event):
        path = os.path.abspath(event.data.strip("{}").replace("file://", ""))
        if not os.path.isfile(path):
            messagebox.showerror("Fehler", "Ungültige Datei.")
            return
        self.input_image.set(path)
        self.drop_label.configure(text=f"📂 Bild hier hineinziehen\n\n{path}")

    def select_output(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[
                ("JPEG", "*.jpg"),
                ("PNG", "*.png"),
                ("GIF", "*.gif"),
                ("TIFF", "*.tiff"),
                ("BMP", "*.bmp")
            ]
        )
        if path:
            self.output_path.set(path)

    def animate_spinner(self):
        if self.spinner_running:
            self.loading_label.configure(text=next(self.spinner_cycle))
            self.after(100, self.animate_spinner)
        else:
            # Falls der Spinner nicht mehr läuft, den Text zurücksetzen
            self.loading_label.configure(text="")

    # ---------- CORE ----------
    def run(self):
        input_img = self.input_image.get()
        output = self.output_path.get()

        if not input_img or not output:
            messagebox.showwarning("Fehler", "Input oder Output fehlt.")
            return

        try:
            params = {
                "rotate": int(self.rotation.get()),
                "columns": int(self.columns.get()),
                "brightness": float(str(self.brightness.get()).replace(",", ".")),
                "quality": int(self.jpg_quality.get()),
                "color_mode": self.color_mode.get()
            }
        except ValueError:
            messagebox.showerror("Fehler", "Ungültige Eingabewerte.")
            return

        # GUI aktualisieren
        self.generate_btn.configure(state="disabled", text="In Arbeit...")
        self.spinner_running = True
        self.after(0, self.animate_spinner)

        # Neues Queue-Objekt für jeden Generierungsvorgang erstellen
        self.result_queue = Queue()

        # Prozess starten
        self.process = Process(
            target=generate_ascii_worker,
            args=(input_img, output, params, self.result_queue),
            daemon=True
        )
        self.process.start()

        # Asynchron auf das Ergebnis warten (ohne zu blockieren)
        self.after(0, self.check_process_status)

    def check_process_status(self):
        if not self.process or self.process.exitcode is not None:
            # Prozess ist beendet, zurücksetzen der GUI
            self.finish_generation()
            return

        try:
            result = self.result_queue.get_nowait()
            if isinstance(result, Exception):
                # Fehlerbehandlung
                messagebox.showerror("Fehler", str(result))
                self.finish_generation()
            else:
                # Erfolgreiche Beendigung
                self.finish_generation()
        except:
            pass

        # Nur weiter überprüfen, wenn der Prozess noch läuft und kein Ergebnis vorliegt
        if self.process and self.process.exitcode is None:
            self.after(100, self.check_process_status)

    def finish_generation(self):
        self.spinner_running = False
        self.generate_btn.configure(state="normal", text="🚀 Generieren")
        # Der Text wird in animate_spinner zurückgesetzt

# ---------- Start ----------
if __name__ == "__main__":
    # Setzen des Startmethoden für multiprocessing (wichtig für Windows)
    if not os.environ.get('MPLCONFIGPROFILE', None):
        os.environ['MPLCONFIGPROFILE'] = 'spawn'

    app = App()
    app.mainloop()
