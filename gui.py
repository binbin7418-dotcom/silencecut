#!/usr/bin/env python3
"""SilenceCut desktop shell (tkinter). Pick a video -> cut the dead air & re-check."""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from silence_cut import run_silencecut, PRESETS


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SilenceCut — Talking-Head Silence Remover")
        self.geometry("680x560")
        self.src = tk.StringVar()
        self.preset = tk.StringVar(value="standard")
        self.norm = tk.BooleanVar(value=True)
        tk.Label(self, text="Talking-head video (mp4 / mov / mkv …):").pack(anchor="w", padx=12, pady=(12, 2))
        row = tk.Frame(self)
        row.pack(fill="x", padx=12)
        tk.Entry(row, textvariable=self.src).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Browse…", command=self.pick).pack(side="left", padx=6)
        tk.Label(self, text="Cutting style:").pack(anchor="w", padx=12, pady=(10, 0))
        for key, p in PRESETS.items():
            tk.Radiobutton(self, text=f"{p['label']} — {p['desc']}",
                           variable=self.preset, value=key).pack(anchor="w", padx=20)
        tk.Checkbutton(self, text="Also normalize loudness to −16 LUFS (podcast target)",
                       variable=self.norm).pack(anchor="w", padx=12, pady=(6, 0))
        self.btn = tk.Button(self, text="Cut the Dead Air", command=self.run, height=2)
        self.btn.pack(pady=12)
        self.log = scrolledtext.ScrolledText(self, wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.write("SilenceCut removes the silences and long gaps from talking-head\n"
                   "video in one click, then re-measures the result and shows you\n"
                   "exactly how much dead air came out. All local.\n")

    def write(self, s):
        self.log.insert("end", s)
        self.log.see("end")

    def pick(self):
        p = filedialog.askopenfilename(
            filetypes=[("Video", "*.mp4 *.mov *.mkv *.webm *.avi"), ("All files", "*.*")])
        if p:
            self.src.set(p)

    def run(self):
        src = self.src.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showerror("SilenceCut", "Choose a video file first.")
            return
        self.btn.config(state="disabled")
        threading.Thread(target=self._work, args=(src,), daemon=True).start()

    def _work(self, src):
        try:
            outdir = os.path.join(os.path.dirname(src), "silencecut_output")
            s = run_silencecut(src, outdir, self.preset.get(), self.norm.get())
            self.write(f"\nDone. Duration: {s['dur_before']}s → {s['dur_after']}s "
                       f"({s['removed']}s of dead air removed) · silence left: {s['silence_after']}s\n"
                       f"Output: {s['final_path']}\nReport: {s['report_path']}\n")
        except Exception as e:
            self.write(f"\nError: {e}\n")
        finally:
            self.btn.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
