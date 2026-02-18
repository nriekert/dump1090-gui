import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import shutil
import os

MODES = [
    ("Interactive",           ["--interactive"]),
    ("Network + Interactive", ["--interactive", "--net"]),
    ("Headless (net only)",   ["--net", "--quiet"]),
    ("Aggressive gain",       ["--net", "--gain", "-10", "--interactive"]),
    ("Low gain",              ["--net", "--gain", "20", "--interactive"]),
    ("MLAT ready",            ["--net", "--mlat", "--interactive"]),
    ("Net-only (no SDR)",     ["--net", "--net-only"]),
]

BINARIES = ["dump1090", "dump1090-fa", "dump1090-mutability"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("dump1090")
        self.resizable(False, False)
        self._proc = None
        self._build()

    def _build(self):
        ttk.Style().theme_use("clam")

        f = tk.Frame(self, padx=10, pady=10)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Binary Path:").grid(row=0, column=0, sticky="e", pady=4, padx=(0, 6))

        bin_row = tk.Frame(f)
        bin_row.grid(row=0, column=1, sticky="ew", pady=4)

        detected = next((b for b in BINARIES if shutil.which(b)), "")
        self._bin_var = tk.StringVar(value=detected)
        self._bin_var.trace_add("write", lambda *_: self._refresh())

        ttk.Entry(bin_row, textvariable=self._bin_var, width=26).pack(side="left")
        ttk.Button(bin_row, text="Browse…", command=self._browse).pack(side="left", padx=(4, 0))

        tk.Label(f, text="Mode:").grid(row=1, column=0, sticky="ne", pady=4, padx=(0, 6))

        self._mode_var = tk.IntVar(value=0)
        mode_frame = tk.LabelFrame(f, padx=6, pady=4)
        mode_frame.grid(row=1, column=1, sticky="ew", pady=4)

        for i, (name, _) in enumerate(MODES):
            tk.Radiobutton(mode_frame, text=name, variable=self._mode_var,
                           value=i, command=self._refresh).pack(anchor="w")

        tk.Label(f, text="Extra args:").grid(row=2, column=0, sticky="e", pady=4, padx=(0, 6))
        self._extra_var = tk.StringVar()
        self._extra_var.trace_add("write", lambda *_: self._refresh())
        ttk.Entry(f, textvariable=self._extra_var, width=32).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Separator(f, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)

        tk.Label(f, text="Command:").grid(row=4, column=0, sticky="e", pady=4, padx=(0, 6))
        self._preview_var = tk.StringVar()
        tk.Label(f, textvariable=self._preview_var, relief="sunken",
                 anchor="w", width=40, bg="white").grid(row=4, column=1, sticky="ew", pady=4)

        btn_frame = tk.Frame(f)
        btn_frame.grid(row=5, column=0, columnspan=2, sticky="e", pady=(10, 0))

        self._stop_btn = ttk.Button(btn_frame, text="Stop", command=self._stop, state="disabled")
        self._stop_btn.pack(side="right", padx=(4, 0))

        self._launch_btn = ttk.Button(btn_frame, text="Start", command=self._launch)
        self._launch_btn.pack(side="right")

        ttk.Separator(f, orient="horizontal").grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 4))

        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(f, textvariable=self._status_var, anchor="w",
                 font=("TkDefaultFont", 8)).grid(row=7, column=0, columnspan=2, sticky="ew")

        f.columnconfigure(1, weight=1)
        self._refresh()

    def _browse(self):
        path = filedialog.askopenfilename(title="Select dump1090 binary")
        if path:
            self._bin_var.set(path)

    def _cmd(self):
        parts = [self._bin_var.get()] + MODES[self._mode_var.get()][1]
        extra = self._extra_var.get().strip()
        if extra:
            parts += extra.split()
        return parts

    def _refresh(self):
        self._preview_var.set(" ".join(self._cmd()))

    def _set_status(self, msg):
        self._status_var.set(msg)

    def _launch(self):
        if self._proc and self._proc.poll() is None:
            messagebox.showinfo("Already running", "Stop the current process first.")
            return

        cmd = self._cmd()
        binary = cmd[0]

        resolved = shutil.which(binary) or (binary if os.path.isfile(binary) else None)
        if not resolved:
            messagebox.showerror(
                "Binary not found",
                f"Could not find '{binary}'.\n\nUse Browse… to locate the dump1090 executable."
            )
            return

        cmd[0] = resolved

        try:
            self._proc = subprocess.Popen(cmd)
            self._set_status(f"Running (PID {self._proc.pid})  —  {' '.join(cmd)}")
            self._launch_btn.configure(state="disabled")
            self._stop_btn.configure(state="normal")
            self.after(1500, self._check_alive)
        except PermissionError:
            messagebox.showerror("Permission denied", f"Cannot execute '{resolved}'.\nTry: chmod +x {resolved}")
        except Exception as e:
            messagebox.showerror("Launch failed", str(e))

    def _stop(self):
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
        self._set_status("Stopped.")
        self._launch_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

    def _check_alive(self):
        if self._proc is None:
            return
        rc = self._proc.poll()
        if rc is not None:
            self._set_status(f"Process exited with code {rc}.")
            self._launch_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            if rc != 0:
                messagebox.showwarning(
                    "Process exited",
                    f"dump1090 exited with code {rc}.\nCheck that your SDR device is connected."
                )
        else:
            self.after(2000, self._check_alive)

    def destroy(self):
        self._stop()
        super().destroy()


if __name__ == "__main__":
    App().mainloop()