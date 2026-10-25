#!/usr/bin/env python3
"""
SilenceCut — one-click silence & gap cutting for talking-head video.

Wraps the open-source auto-editor engine (Unlicense) with the parts a
non-technical creator actually needs:
  - Three plain-language presets instead of threshold/margin syntax
  - A loudness measurement of the source before anything is cut
  - Optional loudness normalization of the result (podcast target -16 LUFS)
  - A re-check report: duration before/after, seconds removed, and how
    much silence remains in the output — measured, not promised.

Honest scope: SilenceCut removes silences and long gaps (the "air" in a
recording). Removing filler *words* (um, uh) needs speech transcription;
no threshold tool can hear words, and this one does not claim to.
Local only; bundles auto-editor + ffmpeg in the Windows package.
"""
import json
import os
import re
import shutil
import subprocess
import sys

PRESETS = {
    "standard":   {"label": "Talking head — standard", "threshold": "3%", "margin": "0.2s",
                   "desc": "everyday YouTube / course videos"},
    "shortform":  {"label": "Short-form — tight", "threshold": "4%", "margin": "0.08s",
                   "desc": "Shorts / Reels / TikTok pacing"},
    "gentle":     {"label": "Lecture / interview — gentle", "threshold": "2.5%", "margin": "0.35s",
                   "desc": "keeps natural pauses, cuts only the dead air"},
}


def find_tool(name):
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    exe_dir = os.path.dirname(sys.executable)
    for d in (here, exe_dir, os.getcwd()):
        p = os.path.join(d, name + (".exe" if os.name == "nt" else ""))
        if os.path.isfile(p):
            return p
    return shutil.which(name)


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=7200)


def probe_duration(path):
    fp = find_tool("ffprobe")
    r = _run([fp, "-v", "quiet", "-show_entries", "format=duration", "-of", "json", path])
    return float(json.loads(r.stdout)["format"]["duration"])


def silence_seconds(path):
    ff = find_tool("ffmpeg")
    r = _run([ff, "-hide_banner", "-i", path, "-af",
              "silencedetect=noise=-45dB:d=0.4", "-f", "null", "-"])
    total = 0.0
    for m in re.finditer(r"silence_duration: ([\d.]+)", r.stderr):
        total += float(m.group(1))
    return round(total, 1)


def measure_lufs(path):
    ff = find_tool("ffmpeg")
    r = _run([ff, "-hide_banner", "-i", path, "-af",
              "loudnorm=print_format=json", "-f", "null", "-"])
    m = re.search(r"\{\s*\"input_i\".*?\}", r.stderr, re.S)
    return float(json.loads(m.group(0))["input_i"]) if m else None


def run_silencecut(src_path, outdir, preset="standard", normalize=True):
    if preset not in PRESETS:
        raise ValueError(f"unknown preset '{preset}' (choose from {', '.join(PRESETS)})")
    ae = find_tool("auto-editor")
    if not ae:
        raise RuntimeError("auto-editor engine not found next to the app")
    p = PRESETS[preset]
    os.makedirs(outdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src_path))[0]
    ext = os.path.splitext(src_path)[1] or ".mp4"

    dur_before = probe_duration(src_path)
    sil_before = silence_seconds(src_path)
    lufs_before = measure_lufs(src_path)

    cut_path = os.path.join(outdir, base + "_cut" + ext)
    cmd = [ae, src_path, "--edit", f"audio:threshold={p['threshold']}",
           "--margin", p["margin"], "-o", cut_path, "--no-open", "-q"]
    r = _run(cmd)
    if r.returncode != 0 or not os.path.isfile(cut_path):
        raise RuntimeError("auto-editor failed: " + ((r.stderr or r.stdout).strip().splitlines() or ["unknown"])[-1])

    final_path = cut_path
    norm_note = "not applied"
    if normalize:
        norm_path = os.path.join(outdir, base + "_cut_loud" + ext)
        ff = find_tool("ffmpeg")
        rn = _run([ff, "-hide_banner", "-y", "-i", cut_path, "-af",
                   "loudnorm=I=-16:TP=-1:LRA=11", "-c:v", "copy", norm_path])
        if rn.returncode == 0 and os.path.isfile(norm_path):
            final_path = norm_path
            norm_note = "loudnorm applied toward -16 LUFS (podcast target)"

    dur_after = probe_duration(final_path)
    sil_after = silence_seconds(final_path)
    lufs_after = measure_lufs(final_path)
    removed = dur_before - dur_after
    pct = removed / dur_before * 100 if dur_before else 0.0

    lines = ["# SilenceCut — cut & re-check report", "",
             f"Source file: {os.path.basename(src_path)}  ·  Preset: {p['label']} ({p['desc']})", "",
             "## Before / after (output re-measured)",
             f"- Duration: {dur_before:.1f}s → {dur_after:.1f}s ({removed:.1f}s of dead air removed, {pct:.0f}%)",
             f"- Silence remaining: {sil_before:.1f}s → {sil_after:.1f}s",
             (f"- Loudness: {lufs_before:.1f} LUFS → {lufs_after:.1f} LUFS ({norm_note})"
              if lufs_before is not None and lufs_after is not None else "- Loudness: not measured"),
             "",
             "## What happened",
             f"- auto-editor cut every section under the preset's loudness threshold "
             f"({p['threshold']}), keeping a {p['margin']} breathing margin around speech",
             f"- Output file: {os.path.basename(final_path)}",
             "",
             "Scope note: SilenceCut removes silences and gaps. Filler words (um, uh) are "
             "speech, not silence — removing them needs transcription, which this tool "
             "does not do and does not claim to do."]
    report_path = os.path.join(outdir, "cut_report.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"dur_before": round(dur_before, 1), "dur_after": round(dur_after, 1),
            "removed": round(removed, 1), "silence_before": sil_before,
            "silence_after": sil_after, "final_path": final_path,
            "report_path": report_path}


def main(argv):
    if len(argv) < 3:
        print("usage: silence_cut.py <video file> <outdir> [standard|shortform|gentle] [nonorm]")
        return 2
    preset = argv[3] if len(argv) > 3 else "standard"
    s = run_silencecut(argv[1], argv[2], preset, normalize=not (len(argv) > 4 and argv[4] == "nonorm"))
    print(f"duration={s['dur_before']}->{s['dur_after']} removed={s['removed']}s silence={s['silence_before']}->{s['silence_after']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
