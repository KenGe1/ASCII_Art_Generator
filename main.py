import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import threading
import itertools

from ascii_magic import AsciiArt
from PIL import Image, ImageEnhance


# ---------- Appearance ----------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.overrideredirect(True)
        self.geometry("720x820")
        self.configure(bg="#121212")

        self._drag_x = 0
        self._drag_y = 0

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

        self.build_titlebar()
        self.build_ui()

    # ---------- Titlebar ----------
    def build_titlebar(self):
        bar = ctk.CTkFrame(self, height=36, fg_color="#1b1b1b", corner_radius=0)
        bar.pack(fill="x")

        bar.bind("<ButtonPress-1>", self.start_move)
        bar.bind("<B1-Motion>", self.do_move)

        ctk.CTkLabel(bar, text="ASCII Art Generator",
                     font=("Segoe UI", 14, "bold")).pack(side="left", padx=12)

        btns = ctk.CTkFrame(bar, fg_color="transparent")
        btns.pack(side="right", padx=6)

        ctk.CTkButton(btns, text="–", width=32, height=24,
                      command=self.iconify).pack(side="left", padx=4)

        ctk.CTkButton(btns, text="✕", width=32, height=24,
                      fg_color="#8b0000", hover_color="#a00000",
                      command=self.destroy).pack(side="left", padx=4)

    def start_move(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def do_move(self, e):
        self.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    # ---------- UI ----------
    def build_ui(self):
        main = ctk.CTkFrame(self, corner_radius=20)
        main.pack(padx=25, pady=25, fill="both", expand=True)

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
        ctk.CTkLabel(
            settings, text="Columns",
            font=("Segoe UI", 14)
        ).grid(row=0, column=0, padx=25, pady=(0, 6))

        ctk.CTkLabel(
            settings, text="Rotation",
            font=("Segoe UI", 14)
        ).grid(row=0, column=1, padx=25, pady=(0, 6))

        ctk.CTkLabel(
            settings, text="Helligkeit",
            font=("Segoe UI", 14)
        ).grid(row=2, column=0, padx=25, pady=(16, 6))

        ctk.CTkLabel(
            settings, text="Farbe",
            font=("Segoe UI", 14)
        ).grid(row=2, column=1, padx=25, pady=(16, 6))

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

        # absolut unten rechts im Fenster
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
            filetypes=[("JPEG", "*.jpg")]
        )
        if path:
            self.output_path.set(path)

    def animate_spinner(self):
        if self.spinner_running:
            self.loading_label.configure(text=next(self.spinner_cycle))
            self.after(100, self.animate_spinner)

    # ---------- CORE ----------
    def run(self):
        if not self.input_image.get() or not self.output_path.get():
            messagebox.showwarning("Fehler", "Input oder Output fehlt.")
            return

        self.generate_btn.configure(state="disabled", text="In Arbeit...")
        self.spinner_running = True
        self.after(0, self.animate_spinner)

        threading.Thread(
            target=self.generate_ascii,
            args=(self.input_image.get(), self.output_path.get()),
            daemon=True
        ).start()

    def generate_ascii(self, input_img, output):
        try:
            brightness = float(self.brightness.get().replace(",", ".").strip())
        except ValueError:
            brightness = 1.0

        rotate = int(self.rotation.get())
        columns = int(self.columns.get())
        quality = int(self.jpg_quality.get())

        mode = self.color_mode.get()
        full_color = mode == "Full Color"
        monochrome = mode == "Schwarz & Weiß"

        temp_out = os.path.join(os.path.dirname(output) or ".", "temp.png")

        try:
            art = AsciiArt.from_image(input_img)

            if brightness != 1:
                art.image = ImageEnhance.Brightness(art.image).enhance(brightness)
            if rotate != 0:
                art.image = art.image.rotate(rotate, expand=True)

            art.to_image_file(
                temp_out,
                columns=columns,
                full_color=full_color,
                monochrome=monochrome
            )

            Image.open(temp_out).save(
                output, quality=quality, optimize=True, subsampling=0
            )

        finally:
            if os.path.exists(temp_out):
                os.remove(temp_out)
            self.after(0, self.finish_generation)

    def finish_generation(self):
        self.spinner_running = False
        self.generate_btn.configure(state="normal", text="🚀 Generieren")
        self.loading_label.configure(text="")


# ---------- Start ----------
if __name__ == "__main__":
    App().mainloop()
