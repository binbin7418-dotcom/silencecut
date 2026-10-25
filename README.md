# SilenceCut — One-Click Silence & Gap Cutting for Talking-Head Video

Raw auto-editor is powerful but speaks in thresholds and margins.
SilenceCut wraps it in three plain-language presets, a desktop window,
optional loudness normalization, and a **re-check report** that measures
the output: duration before/after, seconds of dead air removed, silence
remaining. 100% local.

## Presets
- **Talking head — standard**: everyday YouTube / course videos
- **Short-form — tight**: Shorts / Reels / TikTok pacing
- **Lecture / interview — gentle**: keeps natural pauses, cuts only dead air

## Verified behaviour
On a seeded 9.0 s test video (3 s tone, 3 s silence, 3 s tone), the
standard preset produced a 6.5 s cut — 2.5 s of dead air removed, silence
down from 3.0 s to 0.4 s — and normalized loudness from −11.8 to −15.9 LUFS,
all measured on the output file.

## Honest scope
SilenceCut removes **silences and gaps**. Filler *words* (um, uh) are
speech, not silence — removing them requires transcription, which this
tool does not do and does not claim to do.

## Run from source
```
python silence_cut.py video.mp4 output_folder standard
```
Needs `auto-editor` and `ffmpeg`/`ffprobe` next to the app or on PATH
(the Windows package bundles pinned builds of both — see ENGINE_NOTICE.md).
