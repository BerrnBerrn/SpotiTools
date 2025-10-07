import requests
import base64
import webbrowser
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse
import tkinter as tk
from tkinter import ttk, font, messagebox
from PIL import Image, ImageTk
import io
import urllib.request
import os
import pickle
from cryptography.fernet import Fernet
import sys
import keyboard


def get_encryption_key():
    key_file = "spotify_key.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
        return key


def encrypt_data(data, key):
    fernet = Fernet(key)
    return fernet.encrypt(pickle.dumps(data))


def decrypt_data(encrypted_data, key):
    fernet = Fernet(key)
    return pickle.loads(fernet.decrypt(encrypted_data))


def credentials_exist():
    return os.path.exists("spotify_credentials.enc")


def load_credentials():
    encryption_key = get_encryption_key()
    try:
        with open("spotify_credentials.enc", "rb") as f:
            encrypted_data = f.read()
        return decrypt_data(encrypted_data, encryption_key)
    except:
        return None


def save_credentials(client_id, client_secret):
    encryption_key = get_encryption_key()
    data = {"client_id": client_id, "client_secret": client_secret}
    encrypted_data = encrypt_data(data, encryption_key)
    with open("spotify_credentials.enc", "wb") as f:
        f.write(encrypted_data)


def load_settings():
    default_settings = {
        "hotkeys": {
            "play_pause": "ctrl+shift+p",
            "next_track": "ctrl+shift+]",
            "previous_track": "ctrl+shift+[",
            "hide_window": "ctrl+shift+h"
        },
        "update_interval": 3000,
        "always_on_top": True
    }

    if os.path.exists("settings.json"):
        try:
            with open("settings.json", "r") as f:
                saved_settings = json.load(f)
                default_settings.update(saved_settings)
        except:
            pass

    return default_settings


def save_settings(settings):
    with open("settings.json", "w") as f:
        json.dump(settings, f, indent=2)


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if 'code' in params:
            self.server.auth_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body style="background: #121212; color: white; font-family: Arial; text-align: center; padding: 50px;">
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to the app.</p>
                </body>
                </html>
            """)


class HotkeyRecorder:
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        self.recording = False
        self.current_keys = []
        self.setup_window()

    def setup_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("Record Hotkey")
        self.window.geometry("300x250")
        self.window.configure(bg="#121212")
        self.window.resizable(False, False)
        self.window.attributes('-topmost', True)
        self.window.overrideredirect(True)

        header_frame = tk.Frame(self.window, bg="#121212", height=30, cursor="fleur")
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        x = self.parent.winfo_x() + 100
        y = self.parent.winfo_y() + 100
        self.window.geometry(f"+{x}+{y}")

        header_frame.bind("<ButtonPress-1>", self.start_move)
        header_frame.bind("<ButtonRelease-1>", self.stop_move)
        header_frame.bind("<B1-Motion>", self.on_motion)

        tk.Label(header_frame, text="🎵 Record Hotkey", font=("Arial", 11, "bold"),
                 bg="#121212", fg="#1DB954").pack(side=tk.LEFT, padx=10)

        close_btn = tk.Label(header_frame, text="✕", font=("Arial", 12),
                             bg="#121212", fg="#B3B3B3", cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=10)
        close_btn.bind("<Button-1>", lambda e: self.window.destroy())

        main_frame = tk.Frame(self.window, bg="#121212", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(main_frame, text="Press any key combination...",
                                     bg="#121212", fg="#1DB954", font=("Arial", 12))
        self.status_label.pack(pady=(10, 20))

        self.key_display = tk.Label(main_frame, text="", bg="#282828", fg="#1DB954",
                                    font=("Arial", 14, "bold"), width=20, height=2)
        self.key_display.pack(pady=(0, 20))

        button_frame = tk.Frame(main_frame, bg="#121212")
        button_frame.pack()

        tk.Button(button_frame, text="Confirm", command=self.confirm_hotkey,
                  bg="#1DB954", fg="white", font=("Arial", 10, "bold"),
                  relief=tk.FLAT, padx=20).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="Cancel", command=self.window.destroy,
                  bg="#282828", fg="white", font=("Arial", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.LEFT, padx=5)

        self.start_recording()

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def on_motion(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f"+{x}+{y}")

    def start_recording(self):
        self.recording = True
        self.current_keys = []
        self.status_label.config(text="Press any key combination...")
        self.key_display.config(text="")

        def record_keys(event):
            if self.recording and event.event_type == keyboard.KEY_DOWN:
                if event.name not in self.current_keys:
                    self.current_keys.append(event.name)
                    self.update_display()

        keyboard.hook(record_keys)

    def update_display(self):
        if self.current_keys:
            display_text = "+".join(self.current_keys)
            self.key_display.config(text=display_text)
            self.status_label.config(text="Press Confirm to save")

    def confirm_hotkey(self):
        if self.current_keys:
            hotkey = "+".join(self.current_keys).lower()
            self.callback(hotkey)
        self.window.destroy()

    def __del__(self):
        try:
            keyboard.unhook_all()
        except:
            pass


class SettingsWindow:
    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        self.settings = load_settings()
        self.setup_window()

    def setup_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("Settings")
        self.window.geometry("400x500")
        self.window.configure(bg="#121212")
        self.window.resizable(False, False)
        self.window.attributes('-topmost', True)
        self.window.overrideredirect(True)

        header_frame = tk.Frame(self.window, bg="#121212", height=30, cursor="fleur")
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        x = self.parent.winfo_x() + 50
        y = self.parent.winfo_y() + 50
        self.window.geometry(f"+{x}+{y}")

        header_frame.bind("<ButtonPress-1>", self.start_move)
        header_frame.bind("<ButtonRelease-1>", self.stop_move)
        header_frame.bind("<B1-Motion>", self.on_motion)

        tk.Label(header_frame, text="⚙️ Settings", font=("Arial", 11, "bold"),
                 bg="#121212", fg="#1DB954").pack(side=tk.LEFT, padx=10)

        close_btn = tk.Label(header_frame, text="✕", font=("Arial", 12),
                             bg="#121212", fg="#B3B3B3", cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=10)
        close_btn.bind("<Button-1>", lambda e: self.window.destroy())

        main_frame = tk.Frame(self.window, bg="#121212", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style()
        style.configure("TNotebook", background="#121212", borderwidth=0)
        style.configure("TNotebook.Tab", background="#282828", foreground="black",
                        font=("Arial", 10), padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", "#1DB954")])

        hotkey_frame = tk.Frame(notebook, bg="black")
        general_frame = tk.Frame(notebook, bg="black")

        notebook.add(hotkey_frame, text="Hotkeys")
        notebook.add(general_frame, text="General")

        self.setup_hotkeys_tab(hotkey_frame)
        self.setup_general_tab(general_frame)

        button_frame = tk.Frame(main_frame, bg="#121212")
        button_frame.pack(fill=tk.X, pady=(20, 0))

        tk.Button(button_frame, text="Save", command=self.save_settings,
                  bg="#1DB954", fg="white", font=("Arial", 10, "bold"),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=(10, 0))

        tk.Button(button_frame, text="Cancel", command=self.window.destroy,
                  bg="#282828", fg="white", font=("Arial", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def on_motion(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f"+{x}+{y}")

    def setup_hotkeys_tab(self, parent):
        hotkeys = self.settings["hotkeys"]

        tk.Label(parent, text="Play/Pause:", bg="#121212", fg="#1DB954", font=("Arial", 10, "bold")).pack(anchor="w",
                                                                                                          pady=(15, 5))
        self.play_pause_var = tk.StringVar(value=hotkeys["play_pause"])
        frame1 = tk.Frame(parent, bg="#121212")
        frame1.pack(fill=tk.X, pady=(0, 15))
        tk.Label(frame1, textvariable=self.play_pause_var, bg="#282828", fg="#1DB954",
                 font=("Arial", 10, "bold"), width=20, relief=tk.SUNKEN, bd=1).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(frame1, text="Record", command=lambda: self.record_hotkey("play_pause"),
                  bg="#1DB954", fg="black", font=("Arial", 9), relief=tk.FLAT).pack(side=tk.LEFT)

        tk.Label(parent, text="Next Track:", bg="#121212", fg="#1DB954", font=("Arial", 10, "bold")).pack(anchor="w",
                                                                                                          pady=(15, 5))
        self.next_track_var = tk.StringVar(value=hotkeys["next_track"])
        frame2 = tk.Frame(parent, bg="#121212")
        frame2.pack(fill=tk.X, pady=(0, 15))
        tk.Label(frame2, textvariable=self.next_track_var, bg="#282828", fg="#1DB954",
                 font=("Arial", 10, "bold"), width=20, relief=tk.SUNKEN, bd=1).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(frame2, text="Record", command=lambda: self.record_hotkey("next_track"),
                  bg="#1DB954", fg="black", font=("Arial", 9), relief=tk.FLAT).pack(side=tk.LEFT)

        tk.Label(parent, text="Previous Track:", bg="#121212", fg="#1DB954", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(15, 5))
        self.previous_track_var = tk.StringVar(value=hotkeys["previous_track"])
        frame3 = tk.Frame(parent, bg="#121212")
        frame3.pack(fill=tk.X, pady=(0, 15))
        tk.Label(frame3, textvariable=self.previous_track_var, bg="#282828", fg="#1DB954",
                 font=("Arial", 10, "bold"), width=20, relief=tk.SUNKEN, bd=1).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(frame3, text="Record", command=lambda: self.record_hotkey("previous_track"),
                  bg="#1DB954", fg="black", font=("Arial", 9), relief=tk.FLAT).pack(side=tk.LEFT)

        tk.Label(parent, text="Hide Window:", bg="#121212", fg="#1DB954", font=("Arial", 10, "bold")).pack(anchor="w",
                                                                                                           pady=(15, 5))
        self.hide_window_var = tk.StringVar(value=hotkeys["hide_window"])
        frame4 = tk.Frame(parent, bg="#121212")
        frame4.pack(fill=tk.X, pady=(0, 15))
        tk.Label(frame4, textvariable=self.hide_window_var, bg="#282828", fg="#1DB954",
                 font=("Arial", 10, "bold"), width=20, relief=tk.SUNKEN, bd=1).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(frame4, text="Record", command=lambda: self.record_hotkey("hide_window"),
                  bg="#1DB954", fg="black", font=("Arial", 9), relief=tk.FLAT).pack(side=tk.LEFT)

    def record_hotkey(self, hotkey_type):
        def set_hotkey(hotkey):
            if hotkey_type == "play_pause":
                self.play_pause_var.set(hotkey)
            elif hotkey_type == "next_track":
                self.next_track_var.set(hotkey)
            elif hotkey_type == "previous_track":
                self.previous_track_var.set(hotkey)
            elif hotkey_type == "hide_window":
                self.hide_window_var.set(hotkey)

        HotkeyRecorder(self.window, set_hotkey)

    def setup_general_tab(self, parent):
        self.always_top_var = tk.BooleanVar(value=self.settings["always_on_top"])
        tk.Checkbutton(parent, text="Always on top", variable=self.always_top_var,
                       bg="#121212", fg="#1DB954", font=("Arial", 10), selectcolor="#282828",
                       activebackground="#121212", activeforeground="#1DB954").pack(anchor="w", pady=(15, 5))

        tk.Label(parent, text="Update Interval (ms):", bg="#121212", fg="#1DB954", font=("Arial", 10, "bold")).pack(
            anchor="w", pady=(20, 5))
        self.interval_var = tk.IntVar(value=self.settings["update_interval"])
        scale = tk.Scale(parent, from_=1000, to=10000, variable=self.interval_var, orient=tk.HORIZONTAL,
                         bg="#121212", fg="#1DB954", highlightthickness=0, troughcolor="#282828",
                         sliderrelief=tk.FLAT, font=("Arial", 9))
        scale.pack(fill=tk.X, pady=(0, 10))
        scale.configure(sliderrelief=tk.FLAT, borderwidth=0)

    def save_settings(self):
        new_settings = {
            "hotkeys": {
                "play_pause": self.play_pause_var.get().lower(),
                "next_track": self.next_track_var.get().lower(),
                "previous_track": self.previous_track_var.get().lower(),
                "hide_window": self.hide_window_var.get().lower()
            },
            "update_interval": self.interval_var.get(),
            "always_on_top": self.always_top_var.get()
        }

        save_settings(new_settings)
        self.controller.apply_settings(new_settings)
        self.window.destroy()


class SetupWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("Spotify Controller - Setup")
        self.root.geometry("600x500")
        self.root.configure(bg="#121212")
        self.root.resizable(False, False)

        self.setup_gui()

    def setup_gui(self):
        main_frame = tk.Frame(self.root, bg="#121212", padx=30, pady=30)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(main_frame, text="🎵 Spotify Controller Setup",
                               font=("Arial", 16, "bold"), bg="#121212", fg="#1DB954")
        title_label.pack(pady=(0, 20))

        # Instructions
        instructions = (
            "To use this application, you need to provide your Spotify App credentials.\n\n"
            "1. Go to https://developer.spotify.com/dashboard\n"
            "2. Log in and create a new app\n"
            "3. Add http://127.0.0.1:8888/callback as a redirect URI\n"
            "4. Copy your Client ID and Client Secret below"
        )

        instructions_label = tk.Label(main_frame, text=instructions,
                                      font=("Arial", 10), bg="#121212", fg="white",
                                      justify=tk.LEFT)
        instructions_label.pack(pady=(0, 30))

        # Client ID
        tk.Label(main_frame, text="Client ID:", font=("Arial", 10, "bold"),
                 bg="#121212", fg="#1DB954", anchor="w").pack(fill=tk.X, pady=(5, 0))
        self.client_id_entry = tk.Entry(main_frame, font=("Arial", 10), bg="#282828",
                                        fg="white", insertbackground="white")
        self.client_id_entry.pack(fill=tk.X, pady=(5, 15))

        # Client Secret
        tk.Label(main_frame, text="Client Secret:", font=("Arial", 10, "bold"),
                 bg="#121212", fg="#1DB954", anchor="w").pack(fill=tk.X, pady=(5, 0))
        self.client_secret_entry = tk.Entry(main_frame, font=("Arial", 10), bg="#282828",
                                            fg="white", insertbackground="white", show="*")
        self.client_secret_entry.pack(fill=tk.X, pady=(5, 15))

        # Buttons
        button_frame = tk.Frame(main_frame, bg="#121212")
        button_frame.pack(fill=tk.X, pady=(20, 0))

        tk.Button(button_frame, text="Save Credentials", command=self.save_credentials,
                  bg="#1DB954", fg="white", font=("Arial", 10, "bold"),
                  relief=tk.FLAT, padx=20, pady=10).pack(side=tk.RIGHT, padx=(10, 0))

        tk.Button(button_frame, text="Cancel", command=self.root.quit,
                  bg="#282828", fg="white", font=("Arial", 10),
                  relief=tk.FLAT, padx=20, pady=10).pack(side=tk.RIGHT)

        # Bind Enter key to save
        self.root.bind('<Return>', lambda e: self.save_credentials())

    def save_credentials(self):
        client_id = self.client_id_entry.get().strip()
        client_secret = self.client_secret_entry.get().strip()

        if not client_id or not client_secret:
            messagebox.showerror("Error", "Please enter both Client ID and Client Secret")
            return

        try:
            save_credentials(client_id, client_secret)
            messagebox.showinfo("Success", "Credentials saved successfully!\nThe application will now start.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save credentials: {str(e)}")

class SpotifyController:
    def __init__(self, root):
        self.root = root
        self.credentials = load_credentials()
        self.settings = load_settings()
        self.client_id = self.credentials["client_id"]
        self.client_secret = self.credentials["client_secret"]
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.current_volume = 50
        self.is_expanded = True
        self.is_dragging_progress = False
        self.animating = False
        self.is_hidden = False
        self.auth_server = None
        self.auth_attempts = 0
        self.max_auth_attempts = 3

        self.root.overrideredirect(True)
        self.root.attributes('-topmost', self.settings["always_on_top"])

        if sys.platform == "win32":
            try:
                import ctypes
                HWND_TOPMOST = -1
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE)
            except:
                pass

        self.setup_gui()
        self.setup_global_hotkeys()
        self.authenticate()

        self.root.bind('<FocusIn>', self.on_focus_in)
        self.root.bind('<FocusOut>', self.on_focus_out)

    def apply_settings(self, new_settings):
        self.settings = new_settings
        self.root.attributes('-topmost', self.settings["always_on_top"])
        self.setup_global_hotkeys()

    def setup_global_hotkeys(self):
        try:
            keyboard.unhook_all()

            hotkeys = self.settings["hotkeys"]
            for hotkey_name, hotkey_combo in hotkeys.items():
                try:
                    if hotkey_name == "play_pause":
                        keyboard.add_hotkey(hotkey_combo, self.toggle_playback, suppress=False)
                    elif hotkey_name == "next_track":
                        keyboard.add_hotkey(hotkey_combo, self.next_track, suppress=False)
                    elif hotkey_name == "previous_track":
                        keyboard.add_hotkey(hotkey_combo, self.previous_track, suppress=False)
                    elif hotkey_name == "hide_window":
                        keyboard.add_hotkey(hotkey_combo, self.toggle_window_visibility, suppress=False)
                except:
                    continue
        except Exception as e:
            print(f"Hotkey setup error: {e}")

    def toggle_window_visibility(self):
        if self.is_hidden:
            self.root.deiconify()
            self.is_hidden = False
        else:
            self.root.withdraw()
            self.is_hidden = True

    def setup_gui(self):
        self.root.configure(bg="#121212")
        self.root.geometry("230x490")

        self.title_font = font.Font(family="Arial", size=12, weight="bold")
        self.normal_font = font.Font(family="Arial", size=10)
        self.small_font = font.Font(family="Arial", size=9)
        self.tiny_font = font.Font(family="Arial", size=8)

        self.main_container = tk.Frame(self.root, bg="#121212")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.expanded_frame = tk.Frame(self.main_container, bg="#121212")

        header_frame = tk.Frame(self.expanded_frame, bg="#121212", height=30, cursor="fleur")
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)

        header_frame.bind("<ButtonPress-1>", self.start_move)
        header_frame.bind("<ButtonRelease-1>", self.stop_move)
        header_frame.bind("<B1-Motion>", self.on_motion)

        tk.Label(header_frame, text="🎵 Spotify", font=self.title_font,
                 bg="#121212", fg="#1DB954").pack(side=tk.LEFT, padx=10)

        settings_btn = tk.Label(header_frame, text="⚙️", font=("Arial", 12),
                                bg="#121212", fg="#1DB954", cursor="hand2")
        settings_btn.pack(side=tk.RIGHT, padx=5)
        settings_btn.bind("<Button-1>", lambda e: SettingsWindow(self.root, self))

        hotkey_btn = tk.Label(header_frame, text="⌨️", font=("Arial", 12),
                              bg="#121212", fg="#1DB954", cursor="hand2")
        hotkey_btn.pack(side=tk.RIGHT, padx=5)
        hotkey_btn.bind("<Button-1>", self.show_hotkey_help)

        close_btn = tk.Label(header_frame, text="✕", font=("Arial", 12),
                             bg="#121212", fg="#B3B3B3", cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=10)
        close_btn.bind("<Button-1>", lambda e: self.cleanup_and_exit())

        now_playing_frame = tk.Frame(self.expanded_frame, bg="#121212", padx=15, pady=15)
        now_playing_frame.pack(fill=tk.X, pady=(0, 15))

        self.album_art_label = tk.Label(now_playing_frame, bg="#282828", width=80, height=80,
                                        text="No\nImage", font=self.normal_font, fg="#1DB954",
                                        justify=tk.CENTER)
        self.album_art_label.pack(pady=(0, 15))

        self.track_label = tk.Label(now_playing_frame, text="Please authenticate",
                                    font=self.title_font, bg="#121212", fg="#1DB954", wraplength=200)
        self.track_label.pack()

        self.artist_label = tk.Label(now_playing_frame, text="Connect to Spotify to begin",
                                     font=self.small_font, bg="#121212", fg="#B3B3B3", wraplength=200)
        self.artist_label.pack(pady=(5, 0))

        self.reauth_label = tk.Label(now_playing_frame, text="",
                                     font=self.normal_font, bg="#121212", fg="#E22134")
        self.reauth_label.pack(pady=(5, 0))

        progress_container = tk.Frame(now_playing_frame, bg="#121212")
        progress_container.pack(fill=tk.X, pady=(15, 10))

        self.time_start = tk.Label(progress_container, text="0:00", font=self.tiny_font,
                                   bg="#121212", fg="#1DB954", width=4)
        self.time_start.pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(progress_container, orient=tk.HORIZONTAL,
                                            length=120, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.progress_bar.bind("<ButtonPress-1>", self.start_progress_drag)
        self.progress_bar.bind("<ButtonRelease-1>", self.end_progress_drag)
        self.progress_bar.bind("<B1-Motion>", self.on_progress_drag)

        self.time_end = tk.Label(progress_container, text="0:00", font=self.tiny_font,
                                 bg="#121212", fg="#1DB954", width=4)
        self.time_end.pack(side=tk.RIGHT)

        self.status_label = tk.Label(now_playing_frame, text="Not connected",
                                     font=self.small_font, bg="#121212", fg="#E22134")
        self.status_label.pack(pady=(5, 10))

        controls_frame = tk.Frame(self.expanded_frame, bg="#121212")
        controls_frame.pack(pady=(0, 15))

        button_style = {
            'bg': '#000000', 'fg': '#1DB954', 'font': self.normal_font,
            'border': 0, 'padx': 12, 'pady': 8, 'width': 5,  # Reduced width by 15% (from 6 to 5)
            'state': 'disabled'
        }

        buttons_frame = tk.Frame(controls_frame, bg="#121212")
        buttons_frame.pack()

        self.prev_btn = tk.Button(buttons_frame, text="⏮", command=self.previous_track, **button_style)
        self.prev_btn.pack(side=tk.LEFT, padx=3)

        self.play_btn = tk.Button(buttons_frame, text="▶", command=self.toggle_playback, **button_style)
        self.play_btn.pack(side=tk.LEFT, padx=3)

        self.next_btn = tk.Button(buttons_frame, text="⏭", command=self.next_track, **button_style)
        self.next_btn.pack(side=tk.LEFT, padx=3)

        # Removed hotkey labels section completely

        volume_frame = tk.Frame(controls_frame, bg="#121212")
        volume_frame.pack(pady=(10, 0))

        tk.Label(volume_frame, text="🔈", bg="#121212", fg="#1DB954", font=self.small_font).pack(side=tk.LEFT)

        self.volume_scale = tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                     bg="#121212", fg="#1DB954", highlightthickness=0,
                                     length=120, sliderrelief=tk.FLAT, showvalue=False,
                                     state='disabled', troughcolor="#282828")
        self.volume_scale.set(50)
        self.volume_scale.pack(side=tk.LEFT, padx=5)

        tk.Label(volume_frame, text="🔊", bg="#121212", fg="#1DB954", font=self.small_font).pack(side=tk.LEFT)

        status_bar = tk.Frame(self.expanded_frame, bg="#282828", height=25)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.connection_status = tk.Label(status_bar, text="Click here to authenticate", bg="#282828",
                                          fg="#1DB954", font=self.tiny_font, cursor="hand2")
        self.connection_status.pack(side=tk.LEFT, padx=10)
        self.connection_status.bind("<Button-1>", lambda e: self.authenticate(force=True))

        self.collapsed_frame = tk.Frame(self.main_container, bg="#121212", height=90)

        mini_container = tk.Frame(self.collapsed_frame, bg="#121212", padx=10, pady=10)
        mini_container.pack(fill=tk.BOTH, expand=True)

        self.album_art_mini = tk.Label(mini_container, bg="#282828", width=40, height=40,
                                       text="🎵", font=("Arial", 16), fg="#1DB954")
        self.album_art_mini.pack(side=tk.LEFT, padx=(0, 10))

        info_frame = tk.Frame(mini_container, bg="#121212")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.track_mini = tk.Label(info_frame, text="Not connected", font=self.small_font,
                                   bg="#121212", fg="#1DB954", anchor="w")
        self.track_mini.pack(fill=tk.X)

        self.artist_mini = tk.Label(info_frame, text="", font=self.tiny_font,
                                    bg="#121212", fg="#B3B3B3", anchor="w")
        self.artist_mini.pack(fill=tk.X)

        self.progress_mini = ttk.Progressbar(info_frame, orient=tk.HORIZONTAL,
                                             length=80, mode='determinate')
        self.progress_mini.pack(fill=tk.X, pady=(5, 0))

        self.expanded_frame.pack(fill=tk.BOTH, expand=True)

        self.configure_styles()
        self.update_playback_info()

    def cleanup_and_exit(self):
        try:
            keyboard.unhook_all()
        except:
            pass
        if self.auth_server:
            self.auth_server.shutdown()
        self.root.quit()

    def show_hotkey_help(self, event):
        help_window = tk.Toplevel(self.root)
        help_window.title("Hotkeys")
        help_window.geometry("300x200")
        help_window.configure(bg="#121212")
        help_window.attributes('-topmost', True)
        help_window.resizable(False, False)

        tk.Label(help_window, text="🎵 Global Hotkeys",
                 font=self.title_font, bg="#121212", fg="#1DB954").pack(pady=(15, 10))

        hotkeys = self.settings["hotkeys"]
        hotkey_list = [
            (hotkeys["play_pause"], "Play/Pause"),
            (hotkeys["previous_track"], "Previous Track"),
            (hotkeys["next_track"], "Next Track"),
            (hotkeys["hide_window"], "Hide/Show Window")
        ]

        for hotkey, action in hotkey_list:
            frame = tk.Frame(help_window, bg="#121212")
            frame.pack(fill=tk.X, padx=20, pady=2)
            tk.Label(frame, text=hotkey, font=self.normal_font,
                     bg="#121212", fg="#1DB954", width=15, anchor="w").pack(side=tk.LEFT)
            tk.Label(frame, text=action, font=self.normal_font,
                     bg="#121212", fg="white", anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(help_window, text="Close", command=help_window.destroy,
                  bg="#1DB954", fg="white", border=0, padx=20, pady=5).pack(pady=10)

    def configure_styles(self):
        style = ttk.Style()
        style.configure("TScale", background="#121212", troughcolor="#535353")
        style.configure("Horizontal.TProgressbar",
                        background='#1DB954',
                        troughcolor='#535353',
                        borderwidth=0,
                        lightcolor='#1DB954',
                        darkcolor='#1DB954')

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def on_motion(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def start_progress_drag(self, event):
        self.is_dragging_progress = True
        self.seek_to_position(event.x)

    def end_progress_drag(self, event):
        self.is_dragging_progress = False

    def on_progress_drag(self, event):
        if self.is_dragging_progress:
            self.seek_to_position(event.x)

    def seek_to_position(self, x_pos):
        if not self.access_token:
            return

        progress_width = self.progress_bar.winfo_width()
        if progress_width > 0:
            position_percent = min(max(x_pos / progress_width, 0), 1)
            playback = self.get_current_playback()
            if playback and playback.get('item'):
                duration_ms = playback['item']['duration_ms']
                position_ms = int(position_percent * duration_ms)
                self.make_request("PUT", f"/me/player/seek?position_ms={position_ms}")

    def on_focus_in(self, event):
        if not self.is_expanded and not self.animating:
            self.expand_window()

    def on_focus_out(self, event):
        if self.is_expanded and not self.animating:
            self.collapse_window()

    def expand_window(self):
        if self.animating:
            return

        self.animating = True
        self.is_expanded = True

        self.collapsed_frame.pack_forget()
        self.expanded_frame.pack(fill=tk.BOTH, expand=True)

        current_height = 90
        target_height = 490

        def animate_expand():
            nonlocal current_height
            if current_height < target_height:
                current_height += 40
                if current_height > target_height:
                    current_height = target_height
                self.root.geometry(f"230x{current_height}")
                self.root.after(10, animate_expand)
            else:
                self.animating = False

        animate_expand()

    def collapse_window(self):
        if self.animating:
            return

        self.animating = True
        self.is_expanded = False

        self.expanded_frame.pack_forget()
        self.collapsed_frame.pack(fill=tk.BOTH, expand=True)

        current_height = 490
        target_height = 90

        def animate_collapse():
            nonlocal current_height
            if current_height > target_height:
                current_height -= 40
                if current_height < target_height:
                    current_height = target_height
                self.root.geometry(f"230x{current_height}")
                self.root.after(10, animate_collapse)
            else:
                self.animating = False

        animate_collapse()

    def enable_controls(self):
        self.prev_btn.config(state='normal')
        self.play_btn.config(state='normal')
        self.next_btn.config(state='normal')
        self.volume_scale.config(state='normal')
        self.status_label.config(text="Connected", fg="#1DB954")
        self.reauth_label.config(text="")
        self.auth_attempts = 0

    def set_volume(self, volume):
        self.current_volume = int(volume)
        if self.access_token:
            self.make_request("PUT", f"/me/player/volume?volume_percent={self.current_volume}")

    def start_callback_server(self):
        self.auth_server = HTTPServer(('127.0.0.1', 8888), CallbackHandler)
        self.auth_server.auth_code = None

        server_thread = threading.Thread(target=self.auth_server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        return self.auth_server

    def authenticate(self, force=False):
        if self.auth_attempts >= self.max_auth_attempts:
            self.connection_status.config(text="Too many attempts - Restart app", fg="#E22134")
            self.reauth_label.config(text="Please restart the application to authenticate")
            return

        if not force and self.access_token and self.token_expiry and time.time() < self.token_expiry:
            return

        self.auth_attempts += 1
        self.connection_status.config(
            text=f"Starting authentication... ({self.auth_attempts}/{self.max_auth_attempts})")
        self.reauth_label.config(text="Opening browser for authentication...")

        if self.auth_server:
            try:
                self.auth_server.shutdown()
            except:
                pass

        server = self.start_callback_server()

        redirect_uri = "http://127.0.0.1:8888/callback"

        auth_url = (
            f"https://accounts.spotify.com/authorize?"
            f"client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
            f"&scope=user-read-playback-state user-modify-playback-state user-read-currently-playing"
            f"&state=12345"
        )

        # Actually open the browser for authentication
        try:
            webbrowser.open(auth_url)
            self.connection_status.config(text="Check your browser...", fg="#1DB954")
            self.reauth_label.config(text="Complete authentication in browser")
        except Exception as e:
            self.connection_status.config(text="Failed to open browser", fg="#E22134")
            self.reauth_label.config(text=f"Please visit: {auth_url}")
            return

        def check_auth():
            start_time = time.time()
            while server.auth_code is None and time.time() - start_time < 60:  # Increased timeout to 60 seconds
                time.sleep(0.5)

            try:
                server.shutdown()
            except:
                pass

            if server.auth_code:
                self.exchange_code_for_token(server.auth_code, redirect_uri)
            else:
                if self.auth_attempts < self.max_auth_attempts:
                    self.connection_status.config(
                        text=f"Authentication timed out - Click to retry ({self.auth_attempts}/{self.max_auth_attempts})",
                        fg="#E22134")
                    self.reauth_label.config(text="Click below to try again")
                else:
                    self.connection_status.config(text="Too many failures - Restart app", fg="#E22134")
                    self.reauth_label.config(text="Please restart the application")

        auth_thread = threading.Thread(target=check_auth)
        auth_thread.daemon = True
        auth_thread.start()

    def exchange_code_for_token(self, code, redirect_uri):
        token_url = "https://accounts.spotify.com/api/token"

        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }

        try:
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token")
            self.token_expiry = time.time() + token_data["expires_in"]

            self.connection_status.config(text="Connected ✓", fg="#1DB954")
            self.enable_controls()
            self.volume_scale.config(command=self.set_volume)

        except Exception as e:
            self.connection_status.config(text="Auth error - Click to retry", fg="#E22134")
            self.reauth_label.config(text="Authentication failed - click below to retry")

    def make_request(self, method, endpoint, data=None):
        if not self.access_token:
            return None

        if time.time() > self.token_expiry:
            self.authenticate(force=True)
            return None

        url = f"https://api.spotify.com/v1{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)

            if response.status_code == 204:
                return {"success": True}

            response.raise_for_status()

            if response.content:
                return response.json()
            else:
                return {"success": True}

        except:
            return None

    def get_current_playback(self):
        return self.make_request("GET", "/me/player")

    def pause_playback(self):
        result = self.make_request("PUT", "/me/player/pause")
        if result is not None:
            self.play_btn.config(text="▶")

    def start_playback(self):
        result = self.make_request("PUT", "/me/player/play")
        if result is not None:
            self.play_btn.config(text="⏸")

    def next_track(self):
        self.make_request("POST", "/me/player/next")

    def previous_track(self):
        self.make_request("POST", "/me/player/previous")

    def toggle_playback(self):
        playback = self.get_current_playback()
        if playback and playback.get('is_playing', False):
            self.pause_playback()
        else:
            self.start_playback()

    def format_time(self, milliseconds):
        if not milliseconds:
            return "0:00"
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"

    def load_image_from_url(self, url):
        try:
            with urllib.request.urlopen(url) as u:
                raw_data = u.read()
            image = Image.open(io.BytesIO(raw_data))
            image = image.resize((80, 80), Image.LANCZOS)
            return ImageTk.PhotoImage(image)
        except:
            return None

    def update_playback_info(self):
        if self.access_token and not self.animating:
            playback = self.get_current_playback()
            if playback:
                if playback.get('item'):
                    track_name = playback['item']['name']
                    artists = ", ".join([artist['name'] for artist in playback['item']['artists']])

                    self.track_label.config(text=track_name)
                    self.artist_label.config(text=artists)

                    self.track_mini.config(text=track_name)
                    self.artist_mini.config(text=artists)

                    if playback['item']['album']['images']:
                        image_url = playback['item']['album']['images'][0]['url']
                        album_image = self.load_image_from_url(image_url)
                        if album_image:
                            self.album_art_label.config(image=album_image, text="")
                            self.album_art_mini.config(image=album_image, text="")
                            self.album_image = album_image
                        else:
                            self.album_art_label.config(image="", text="No\nImage")
                            self.album_art_mini.config(image="", text="🎵")

                if playback.get('progress_ms') and playback.get('item') and not self.is_dragging_progress:
                    progress = playback['progress_ms']
                    duration = playback['item']['duration_ms']

                    progress_percent = (progress / duration) * 100
                    self.progress_bar['value'] = progress_percent
                    self.progress_mini['value'] = progress_percent

                    self.time_start.config(text=self.format_time(progress))
                    self.time_end.config(text=self.format_time(duration))

                is_playing = playback.get('is_playing', False)
                status_text = "▶️ Playing" if is_playing else "⏸️ Paused"
                self.status_label.config(text=status_text, fg="#1DB954" if is_playing else "#B3B3B3")

        self.root.after(self.settings["update_interval"], self.update_playback_info)


def main():
    if not credentials_exist():
        root = tk.Tk()
        wizard = SetupWizard(root)
        root.mainloop()

    root = tk.Tk()
    app = SpotifyController(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.cleanup_and_exit()


if __name__ == "__main__":
    main()
