# MusicWeb Design Spec

**Date:** 2026-04-19  
**Status:** Approved  
**URL:** https://musicweb.nyxstudios.net  
**Project root:** `/home/legion/legionprojects/musicweb/`

---

## Overview

MusicWeb is a standalone FastAPI web application that gives remote users browser-based access to ACE-Step music generation. It mirrors all 10 tabs of AceTalk (Overview, Easy, Style, Instruments, Vocals, Lyrics, Parameters, Stems, Guide, Lint), runs on Nyx at port 8000, and is protected by Cloudflare Access (Google OAuth). Users never see ComfyUI — they interact with a dark-themed single-page app and download completed MP3s directly.

---

## Architecture

### Project structure

```
/home/legion/legionprojects/musicweb/
├── musicweb.py               # uvicorn entry point, FastAPI app factory
├── core/
│   ├── comfyui.py            # ComfyUI API client (adapted from AceTalk)
│   ├── job_tracker.py        # thread-safe JobTracker + JobInfo dataclass
│   ├── prompt_builder.py     # copied from AceTalk (build_caption, build_lyrics, build_prompt)
│   ├── prompt_linter.py      # copied from AceTalk (LintResult, PromptLinter)
│   ├── demucs.py             # subprocess wrapper (adapted from AceTalk DemucsWorker)
│   └── ollama.py             # Ollama model list + streaming token generator
├── routes/
│   ├── generate.py           # POST /generate, GET /events (SSE)
│   ├── queue.py              # GET /queue
│   ├── stems.py              # POST /stems/extract, POST /stems/demucs
│   ├── ollama.py             # GET /ollama/stream (SSE), GET /ollama/models
│   └── download.py           # GET /download/{filename}
├── static/
│   ├── app.js                # all frontend logic, tab switching, mwState
│   └── style.css             # dark theme (#0b0c10 bg, #7c65d9 accent)
├── templates/
│   └── index.html            # single-page shell, all 10 tabs
└── guide/
    └── Aceuser.html          # symlink or copy of AceTalk's Aceuser.html
```

### Tech stack

- **Backend:** FastAPI + uvicorn (Python 3.12)
- **Frontend:** Vanilla JS + HTML + CSS (no build step)
- **Real-time:** Server-Sent Events (SSE) for job status + Ollama token streaming + Demucs logs
- **Auth:** Cloudflare Access — `Cf-Access-Authenticated-User-Email` header, read on every request
- **Dependencies:** `fastapi`, `uvicorn[standard]`, `requests`, `python-multipart` (file upload for Stems Extract)

---

## User Identity

Every request includes `Cf-Access-Authenticated-User-Email` injected by Cloudflare Access. A FastAPI dependency `get_user_email(request)` reads this header. In local dev (no Cloudflare), it falls back to `"dev@local"`.

---

## Job Tracking

### JobInfo dataclass (`core/job_tracker.py`)

```python
@dataclass
class JobInfo:
    prompt_id: str
    user_email: str
    song_name: str
    submitted_at: datetime
    status: str           # "queued" | "running" | "done" | "error"
    output_files: list[str]  # MP3 filenames once done
    error_msg: str        # set on error
```

### JobTracker

- `dict[str, JobInfo]` protected by `threading.Lock`
- Background thread polls every 3 seconds:
  - ComfyUI `GET /queue` → update running/queued status
  - ComfyUI `GET /history/{prompt_id}` for each tracked job → detect completion
  - On completion: extract output filenames, mark `done`, push SSE `job_done` event to user
- Jobs persist in memory until server restart

---

## SSE Event Stream

`GET /events` — one persistent SSE connection per browser tab.

Events pushed to client:

| Event | Payload | When |
|-------|---------|------|
| `job_queued` | `{prompt_id, position}` | Immediately after submit |
| `job_running` | `{prompt_id}` | When ComfyUI starts processing |
| `job_done` | `{prompt_id, files: [filename]}` | When history shows output |
| `job_error` | `{prompt_id, message}` | On ComfyUI error |
| `queue_update` | `{running, pending}` | Every poll cycle |
| `ollama_token` | `{token}` | Each Ollama token during generation |
| `demucs_log` | `{line}` | Each stdout line from demucs subprocess |

User email from request header scopes all events — each user only receives their own job events.

---

## API Routes

### POST /generate
**Body:** `{tags, lyrics, bpm, steps, cfg_scale, duration, seed, key, scale, time_sig, temperature, top_p, top_k, min_p, song_name}`  
**Action:** Builds workflow via `build_workflow()`, POSTs to ComfyUI `/prompt`, registers job in JobTracker.  
**Returns:** `{prompt_id, queue_position}`

### GET /queue
**Returns:**
```json
{
  "my_jobs": [{"prompt_id", "song_name", "status", "submitted_at", "output_files"}],
  "all_jobs": [{"prompt_id", "user_email", "song_name", "status"}],
  "comfyui": {"running": N, "pending": N}
}
```

### GET /events
SSE stream. Heartbeat every 15 seconds to keep connection alive through Cloudflare.

### GET /download/{filename}
- Validates filename exists in a `done` job belonging to the requesting user
- Streams from `ComfyUI/output/audio/{filename}`
- Headers: `Content-Disposition: attachment; filename="{filename}"`
- Returns 403 if job belongs to another user, 404 if not found

### POST /stems/extract
**Body:** multipart — audio file + generation params  
**Action:** Copies file to ComfyUI `input/`, builds extract workflow, submits to ComfyUI, tracks job.  
**Returns:** `{prompt_id}`

### POST /stems/demucs
**Body:** `{filename, model}` — filename of an existing output MP3, model = "htdemucs" or "htdemucs_6s"  
**Action:** Starts demucs subprocess on Nyx, streams logs via SSE `demucs_log` events.  
**Returns:** `{started: true}`

### GET /ollama/models
**Returns:** `{models: ["gemma4:latest", ...]}`

### GET /ollama/stream
**Query params:** `topic, genre, key, mood, structure, subject, name_override, model`  
**Returns:** SSE stream of `ollama_token` events

### GET /guide/{section}
**Returns:** HTML fragment for the requested chapter section from Aceuser.html

---

## Frontend (Single Page App)

### State (`window.mwState`)

Mirrors AceTalk's SessionState:

```js
mwState = {
  genre: "", bpm: 120, key: "C", scale: "Major", mode: "",
  time_sig: "4/4", instruments: [], vocal_tags: [], lyrics: "",
  steps: 50, cfg_scale: 2.0, duration: 30.0, seed: -1,
  temperature: 0.85, top_p: 0.9, top_k: 0, min_p: 0.0,
  song_name: ""
}
```

### Tabs

| Tab | Key elements |
|-----|-------------|
| **Overview** | Tags preview, lyrics preview, song name input, Generate button, queue status badge, completed jobs list with download buttons |
| **Easy** | Topic, mood, subject, name-override inputs; Ollama model picker; Generate Lyrics button (SSE streaming into Lyrics tab textarea) |
| **Style** | Genre, BPM, key, scale, mode, time signature |
| **Instruments** | Token buttons → adds to `mwState.instruments` |
| **Vocals** | Vocal tag buttons → adds to `mwState.vocal_tags` |
| **Lyrics** | Textarea bound to `mwState.lyrics`; bracket insert buttons (17 tags); template picker |
| **Parameters** | Steps, CFG scale, duration, seed with lock toggle |
| **Stems** | Two panels: Extract (file upload, send to ComfyUI) + Demucs (model select, separate last MP3, live log panel) |
| **Guide** | 9 chapter sub-tabs; content fetched from `GET /guide/{section}` on first click |
| **Lint** | "Lint Current State" button + paste boxes; results panel with ❌/⚠/💡 sections |

### Real-time updates

- On page load: connect to `GET /events` SSE
- `job_done` event → append download button to Overview jobs list
- `queue_update` event → update queue badge on Overview tab
- `ollama_token` event → append to Lyrics textarea
- `demucs_log` event → append to Stems log panel

---

## Deployment

### systemd unit (`/etc/systemd/system/musicweb.service` on Nyx)

```ini
[Unit]
Description=MusicWeb
After=network.target

[Service]
User=legion
WorkingDirectory=/home/legion/legionprojects/musicweb
ExecStart=/usr/bin/python3 -m uvicorn musicweb:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Cloudflare tunnel (Astraea `~/.cloudflared/config.yml`)

Add ingress rule:
```yaml
- hostname: musicweb.nyxstudios.net
  service: http://192.168.1.236:8000
```

### Cloudflare Access

New application: `musicweb.nyxstudios.net` — same Google OAuth policy as existing protected services (`steve.j.petry@gmail.com` + any additional allowed emails).

---

## Out of Scope (v1)

- Preset save/load (users build from scratch each session)
- Job history persistence across server restarts
- Per-user rate limiting
- Audio preview/playback in browser (download only)
- Tag MP3 with ID3 metadata (AceTalk feature, not needed for web)
