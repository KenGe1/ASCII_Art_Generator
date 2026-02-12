import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import multiprocessing
from multiprocessing import Process, Queue, freeze_support
from queue import Empty
import itertools
import ctypes
import shutil
import subprocess
from ascii_magic import AsciiArt
from PIL import Image, ImageEnhance, ImageSequence
import sys
import tempfile

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


def render_ascii_file(source_path, output_path, render_params):
    output_dir = os.path.dirname(output_path) or "."

    with tempfile.NamedTemporaryFile(
        suffix=".png", dir=output_dir, delete=False
    ) as temp_out_file:
        temp_out = temp_out_file.name

    my_art = AsciiArt.from_image(source_path)

    if render_params["brightness"] != 1:
        my_art.image = ImageEnhance.Brightness(
            my_art.image
        ).enhance(render_params["brightness"])

    if render_params["rotate"] != 0:
        my_art.image = my_art.image.rotate(
            render_params["rotate"], expand=True
        )

    my_art.to_image_file(
        temp_out,
        columns=render_params["columns"],
        full_color=render_params["full_color"],
        monochrome=render_params["monochrome"]
    )

    with Image.open(temp_out) as rendered:
        rendered.convert("RGBA").save(output_path, optimize=True)

    os.remove(temp_out)


def process_single_frame_payload(payload):
    source_path, output_path, render_params = payload
    render_ascii_file(source_path, output_path, render_params)
    return 1




def extract_video_segment_frames(payload):
    input_video, start_time, duration, segment_dir = payload
    output_pattern = os.path.join(segment_dir, "frame_%08d.png")

    command = [
        "ffmpeg",
        "-y",
        "-v", "error",
        "-ss", f"{start_time:.6f}",
        "-t", f"{duration:.6f}",
        "-i", input_video,
        "-vsync", "0",
        output_pattern,
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RuntimeError(
            "FFmpeg wurde nicht gefunden. Bitte FFmpeg installieren und zum PATH hinzufügen."
        ) from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise RuntimeError(stderr or "FFmpeg-Befehl fehlgeschlagen.") from e

    return sum(
        1
        for file_name in os.listdir(segment_dir)
        if file_name.startswith("frame_") and file_name.endswith(".png")
    )


def generate_ascii_worker(input_img, output, params, queue):
    rotate = params["rotate"]
    columns = params["columns"]
    brightness = params["brightness"]
    quality = params["quality"]
    mode = params["color_mode"]
    frame_cores = max(1, int(params.get("frame_cores", 1)))

    if mode == "Schwarz & Weiß":
        full_color = False
        monochrome = True
    elif mode == "8 Farben":
        full_color = False
        monochrome = False
    else:
        full_color = True
        monochrome = False

    render_params = {
        "rotate": rotate,
        "columns": columns,
        "brightness": brightness,
        "full_color": full_color,
        "monochrome": monochrome,
    }

    output_dir = os.path.dirname(output) or "."

    def run_command(command):
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout
        except FileNotFoundError as e:
            raise RuntimeError(
                "FFmpeg wurde nicht gefunden. Bitte FFmpeg installieren und zum PATH hinzufügen."
            ) from e
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            raise RuntimeError(stderr or "FFmpeg-Befehl fehlgeschlagen.") from e

    def get_video_fps(video_path):
        output_text = run_command([
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate",
            "-of", "default=nokey=1:noprint_wrappers=1",
            video_path,
        ]).strip()

        if not output_text or output_text == "0/0":
            return 30.0

        if "/" in output_text:
            num, den = output_text.split("/", 1)
            den_value = float(den)
            if den_value == 0:
                return 30.0
            return float(num) / den_value

        return float(output_text)

    def get_video_duration(video_path):
        output_text = run_command([
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nokey=1:noprint_wrappers=1",
            video_path,
        ]).strip()

        if not output_text or output_text == "N/A":
            return 0.0

        return max(0.0, float(output_text))

    def has_audio_stream(video_path):
        output_text = run_command([
            "ffprobe",
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            video_path,
        ]).strip()
        return bool(output_text)

    def render_ascii_image(source_path):
        with tempfile.NamedTemporaryFile(
            suffix=".png", dir=output_dir, delete=False
        ) as temp_out_file:
            temp_out = temp_out_file.name

        render_ascii_file(source_path, temp_out, render_params)

        with Image.open(temp_out) as rendered:
            result_img = rendered.convert("RGBA")
        os.remove(temp_out)
        return result_img

    def process_frames_parallel(frame_pairs):
        total_frames = len(frame_pairs)
        if total_frames == 0:
            return

        workers = max(1, min(frame_cores, total_frames))
        processed_frames = 0

        if workers == 1:
            for source_path, target_path in frame_pairs:
                render_ascii_file(source_path, target_path, render_params)
                processed_frames += 1
                queue.put(("progress", processed_frames, total_frames))
            return

        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(processes=workers) as pool:
            payloads = [
                (source_path, target_path, render_params)
                for source_path, target_path in frame_pairs
            ]
            for processed_one in pool.imap_unordered(process_single_frame_payload, payloads):
                processed_frames += processed_one
                queue.put(("progress", processed_frames, total_frames))

    def process_mp4_video(input_video, output_video):
        fps = get_video_fps(input_video)
        duration = get_video_duration(input_video)

        with tempfile.TemporaryDirectory(dir=output_dir) as temp_dir:
            source_pattern = os.path.join(temp_dir, "source_%08d.png")
            ascii_pattern = os.path.join(temp_dir, "ascii_%08d.png")
            temp_video = os.path.join(temp_dir, "video_no_audio.mp4")

            extraction_workers = max(1, min(frame_cores, multiprocessing.cpu_count()))
            use_parallel_extraction = extraction_workers > 1 and duration > 0

            if use_parallel_extraction:
                segment_root = os.path.join(temp_dir, "segments")
                os.makedirs(segment_root, exist_ok=True)

                segment_duration = duration / extraction_workers
                extraction_jobs = []

                for segment_index in range(extraction_workers):
                    start_time = segment_index * segment_duration
                    current_duration = (
                        duration - start_time
                        if segment_index == extraction_workers - 1
                        else segment_duration
                    )
                    if current_duration <= 0:
                        continue

                    segment_dir = os.path.join(segment_root, f"segment_{segment_index:03d}")
                    os.makedirs(segment_dir, exist_ok=True)
                    extraction_jobs.append(
                        (input_video, start_time, current_duration, segment_dir)
                    )

                if extraction_jobs:
                    ctx = multiprocessing.get_context("spawn")
                    with ctx.Pool(processes=min(extraction_workers, len(extraction_jobs))) as pool:
                        list(pool.imap_unordered(extract_video_segment_frames, extraction_jobs))

                source_frame_index = 1
                for _, _, _, segment_dir in extraction_jobs:
                    segment_frames = sorted(
                        file_name
                        for file_name in os.listdir(segment_dir)
                        if file_name.startswith("frame_") and file_name.endswith(".png")
                    )
                    for segment_frame in segment_frames:
                        source_path = os.path.join(segment_dir, segment_frame)
                        merged_path = os.path.join(
                            temp_dir,
                            f"source_{source_frame_index:08d}.png"
                        )
                        shutil.move(source_path, merged_path)
                        source_frame_index += 1
            else:
                run_command([
                    "ffmpeg",
                    "-y",
                    "-i", input_video,
                    "-vsync", "0",
                    source_pattern,
                ])

            source_frames = sorted(
                file_name
                for file_name in os.listdir(temp_dir)
                if file_name.startswith("source_") and file_name.endswith(".png")
            )

            if not source_frames:
                raise RuntimeError("Das MP4 enthält keine verarbeitbaren Frames.")

            frame_pairs = [
                (
                    os.path.join(temp_dir, frame_name),
                    os.path.join(temp_dir, f"ascii_{index:08d}.png")
                )
                for index, frame_name in enumerate(source_frames, start=1)
            ]
            process_frames_parallel(frame_pairs)

            run_command([
                "ffmpeg",
                "-y",
                "-framerate", f"{fps:.6f}",
                "-i", ascii_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                temp_video,
            ])

            if has_audio_stream(input_video):
                run_command([
                    "ffmpeg",
                    "-y",
                    "-i", temp_video,
                    "-i", input_video,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "copy",
                    "-shortest",
                    output_video,
                ])
            else:
                shutil.copyfile(temp_video, output_video)

    def process_mp4_video(input_video, output_video):
        fps = get_video_fps(input_video)

        with tempfile.TemporaryDirectory(dir=output_dir) as temp_dir:
            source_pattern = os.path.join(temp_dir, "source_%08d.png")
            ascii_pattern = os.path.join(temp_dir, "ascii_%08d.png")
            temp_video = os.path.join(temp_dir, "video_no_audio.mp4")

            run_command([
                "ffmpeg",
                "-y",
                "-i", input_video,
                "-vsync", "0",
                source_pattern,
            ])

            source_frames = sorted(
                file_name
                for file_name in os.listdir(temp_dir)
                if file_name.startswith("source_") and file_name.endswith(".png")
            )

            if not source_frames:
                raise RuntimeError("Das MP4 enthält keine verarbeitbaren Frames.")

            for index, frame_name in enumerate(source_frames, start=1):
                source_path = os.path.join(temp_dir, frame_name)
                ascii_path = os.path.join(temp_dir, f"ascii_{index:08d}.png")
                ascii_img = render_ascii_image(source_path)
                ascii_img.save(ascii_path, optimize=True)
                queue.put(("progress", index, len(source_frames)))

            run_command([
                "ffmpeg",
                "-y",
                "-framerate", f"{fps:.6f}",
                "-i", ascii_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                temp_video,
            ])

            if has_audio_stream(input_video):
                run_command([
                    "ffmpeg",
                    "-y",
                    "-i", temp_video,
                    "-i", input_video,
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "copy",
                    "-c:a", "copy",
                    "-shortest",
                    output_video,
                ])
            else:
                shutil.copyfile(temp_video, output_video)

    try:
        if input_img.lower().endswith(".mp4"):
            process_mp4_video(input_img, output)
            queue.put(True)
            return

        with Image.open(input_img) as source_image:
            is_animated_gif = (
                source_image.format == "GIF"
                and getattr(source_image, "is_animated", False)
                and source_image.n_frames > 1
            )

            if is_animated_gif:
                with tempfile.TemporaryDirectory(dir=output_dir) as temp_dir:
                    loop = source_image.info.get("loop", 0)
                    durations = []
                    frame_pairs = []

                    for index, frame in enumerate(ImageSequence.Iterator(source_image), start=1):
                        source_frame_path = os.path.join(temp_dir, f"gif_source_{index:08d}.png")
                        ascii_frame_path = os.path.join(temp_dir, f"gif_ascii_{index:08d}.png")

                        frame.convert("RGBA").save(source_frame_path, format="PNG")
                        durations.append(frame.info.get("duration", 100))
                        frame_pairs.append((source_frame_path, ascii_frame_path))

                    if not frame_pairs:
                        raise ValueError("Das GIF enthält keine Frames.")

                    process_frames_parallel(frame_pairs)

                    frames = []
                    for _, ascii_path in frame_pairs:
                        with Image.open(ascii_path) as ascii_frame:
                            frames.append(ascii_frame.convert("P", palette=Image.ADAPTIVE))

                    frames[0].save(
                        output,
                        save_all=True,
                        append_images=frames[1:],
                        duration=durations,
                        loop=loop,
                        optimize=False,
                        disposal=2,
                    )
            else:
                img = render_ascii_image(input_img)
                save_params = {
                    "optimize": True,
                }

                if output.lower().endswith((".jpg", ".jpeg")):
                    save_params.update({"quality": quality, "subsampling": 0})
                    img = img.convert("RGB")

                img.save(output, **save_params)
    except Exception as e:
        queue.put(e)
        return

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

        self.jpg_quality = ctk.StringVar(value="95")
        self.frame_cores = ctk.StringVar(value=str(max(1, multiprocessing.cpu_count() // 2)))
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
            text="📂 Bild/GIF/MP4 hier hineinziehen\n\n",
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
        ).grid(row=1, column=0, padx=(0, 8), pady=(0, 8))

        ctk.CTkLabel(
            self.adv_frame,
            text="GIF/Video Kerne",
            font=("Segoe UI", 13)
        ).grid(row=2, column=0, sticky="w", padx=(0, 8))

        ctk.CTkEntry(
            self.adv_frame,
            textvariable=self.frame_cores,
            width=100,
            height=36
        ).grid(row=3, column=0, padx=(0, 8))

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
        self.drop_label.configure(text=f"📂 Bild/GIF/MP4 hier hineinziehen\n\n{path}")

    def select_output(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[
                ("JPEG", "*.jpg"),
                ("PNG", "*.png"),
                ("GIF", "*.gif"),
                ("TIFF", "*.tiff"),
                ("BMP", "*.bmp"),
                ("MP4 Video", "*.mp4")
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
            if input_img.lower().endswith(".mp4"):
                is_animated_gif = False
            else:
                with Image.open(input_img) as source_image:
                    is_animated_gif = (
                        source_image.format == "GIF"
                        and getattr(source_image, "is_animated", False)
                        and source_image.n_frames > 1
                    )
        except Exception:
            is_animated_gif = False

        if is_animated_gif and not output.lower().endswith(".gif"):
            messagebox.showwarning(
                "Fehler",
                "Animierte GIFs können nur als .gif ausgegeben werden."
            )
            return

        if input_img.lower().endswith(".mp4") and not output.lower().endswith(".mp4"):
            messagebox.showwarning(
                "Fehler",
                "MP4-Dateien können nur als .mp4 ausgegeben werden."
            )
            return

        try:
            quality_text = str(self.jpg_quality.get()).strip()
            cores_text = str(self.frame_cores.get()).strip()

            quality = int(quality_text) if quality_text else 95
            frame_cores = int(cores_text) if cores_text else max(1, multiprocessing.cpu_count() // 2)

            params = {
                "rotate": int(self.rotation.get()),
                "columns": int(self.columns.get()),
                "brightness": float(str(self.brightness.get()).replace(",", ".")),
                "quality": max(1, min(100, quality)),
                "color_mode": self.color_mode.get(),
                "frame_cores": max(1, min(frame_cores, multiprocessing.cpu_count()))
            }
        except ValueError:
            messagebox.showerror("Fehler", "Ungültige Eingabewerte.")
            return

        # Eingabefelder bei Bedarf auf bereinigte Werte zurücksetzen
        self.jpg_quality.set(str(params["quality"]))
        self.frame_cores.set(str(params["frame_cores"]))

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
        )
        self.process.start()

        # Asynchron auf das Ergebnis warten (ohne zu blockieren)
        self.after(0, self.check_process_status)

    def check_process_status(self):
        # 1️⃣ Alle verfügbaren Queue-Nachrichten verarbeiten
        while True:
            try:
                result = self.result_queue.get_nowait()
            except Empty:
                break

            if isinstance(result, tuple) and len(result) == 3 and result[0] == "progress":
                current = result[1]
                total = result[2]
                self.generate_btn.configure(text=f"In Arbeit... {current}/{total}")
                continue

            if isinstance(result, Exception):
                messagebox.showerror("Fehler", str(result))
                self.finish_generation()
                return

            # Erfolg ODER unbekannte End-Nachricht → Generation beenden
            self.finish_generation()
            return

        # 2️⃣ DANACH prüfen, ob der Prozess beendet ist
        if self.process and self.process.exitcode is not None:
            self.finish_generation()
            return

        # 3️⃣ Weiter pollen
        self.after(100, self.check_process_status)


    def finish_generation(self):
        self.spinner_running = False
        self.generate_btn.configure(state="normal", text="🚀 Generieren")
        # Der Text wird in animate_spinner zurückgesetzt

# ---------- Start ----------
def main():
    # 🔥 Arbeitsverzeichnis korrekt setzen
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    app = App()
    app.mainloop()
    
if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)
    main()
