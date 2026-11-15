#!/usr/bin/env python3
"""Sounddrop YouTube downloader backend supporting video & audio formats with CORS."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
import json
import os
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "6969"))

# Find yt-dlp executable in system PATH or local .venv
YTDLP_BIN = shutil.which("yt-dlp") or (ROOT / ".venv" / "bin" / "yt-dlp")


def normalize_source(value):
    value = value.strip()
    if not value:
        raise ValueError("Enter a video link or search phrase.")
    if re.match(r"^https?://", value, re.I):
        host = (urlparse(value).hostname or "").lower()
        if host not in {
            "youtube.com", "www.youtube.com", "m.youtube.com",
            "music.youtube.com", "youtu.be", "www.youtube-nocookie.com"
        }:
            raise ValueError("Only YouTube links are supported.")
        parsed = urlparse(value)
        # Normalize youtu.be short links
        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/")[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        # Normalize YouTube Shorts to standard watch URL
        if parsed.path.startswith("/shorts/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                video_id = parts[1]
                return f"https://www.youtube.com/watch?v={video_id}"
        if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"} and parsed.path.rstrip("/") == "/results":
            query = parse_qs(parsed.query).get("search_query", [""])[0].strip()
            if query:
                return "ytsearch1:" + query
            raise ValueError("That YouTube search link has no search phrase.")
        return value
    # Plain search phrase
    return "ytsearch1:" + value


def get_ytdlp_args(fmt: str, output_pattern: str, source: str) -> list[str]:
    base_args = [
        str(YTDLP_BIN), "--no-playlist", "--playlist-items", "1", "--no-warnings",
        "--windows-filenames", "--trim-filenames", "180",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "--extractor-args", "youtube:player_client=android,ios,web"
    ]
    node = shutil.which("node") or shutil.which("nodejs")
    if node:
        base_args.extend(["--js-runtimes", "node:" + node])

    # MP3 formats
    if fmt == "mp3_320k":
        return base_args + ["-x", "--audio-format", "mp3", "--audio-quality", "320k", "--output", output_pattern, "--", source]
    if fmt == "mp3_192k":
        return base_args + ["-x", "--audio-format", "mp3", "--audio-quality", "192k", "--output", output_pattern, "--", source]
    if fmt in ("mp3", "mp3_128k"):
        return base_args + ["-x", "--audio-format", "mp3", "--audio-quality", "128k", "--output", output_pattern, "--", source]

    # Specific audio codecs
    if fmt == "m4a_129k":
        return base_args + ["-x", "--audio-format", "m4a", "--audio-quality", "128k", "--output", output_pattern, "--", source]
    if fmt == "m4a_49k":
        return base_args + ["-x", "--audio-format", "m4a", "--audio-quality", "48k", "--output", output_pattern, "--", source]
    if fmt == "opus_155k":
        return base_args + ["-x", "--audio-format", "opus", "--audio-quality", "160k", "--output", output_pattern, "--", source]
    if fmt == "opus_83k":
        return base_args + ["-x", "--audio-format", "opus", "--audio-quality", "80k", "--output", output_pattern, "--", source]
    if fmt == "opus_64k":
        return base_args + ["-x", "--audio-format", "opus", "--audio-quality", "64k", "--output", output_pattern, "--", source]
    if fmt == "wav":
        return base_args + ["-x", "--audio-format", "wav", "--output", output_pattern, "--", source]
    if fmt == "flac":
        return base_args + ["-x", "--audio-format", "flac", "--output", output_pattern, "--", source]

    # Recommended 360p progressive / fast video
    if fmt == "video_360p_rec":
        return base_args + ["-f", "18/best[height<=360]/bestvideo[height<=360]+bestaudio/best", "--output", output_pattern, "--", source]

    # Video resolutions and containers
    if fmt.startswith("video_"):
        parts = fmt.split("_")
        height = parts[1].replace("p", "")
        container = parts[2] if len(parts) > 2 else "mp4"
        if container == "webm":
            spec = f"bestvideo[height<={height}][ext=webm]+bestaudio[ext=webm]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
            return base_args + ["-f", spec, "--merge-output-format", "webm", "--output", output_pattern, "--", source]
        else:
            spec = f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
            return base_args + ["-f", spec, "--merge-output-format", "mp4", "--output", output_pattern, "--", source]

    # Default to 320k MP3
    return base_args + ["-x", "--audio-format", "mp3", "--audio-quality", "0", "--output", output_pattern, "--", source]


class Handler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range")
        self.send_header("Access-Control-Expose-Headers", "Content-Disposition, Content-Length, Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if self.path in ("/health", "/ping"):
            self.reply(200, {"status": "ok", "message": "Sounddrop backend ready"})
            return
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        page = (ROOT / "index.html").read_bytes()
        self.send_response(200)
        self.send_cors_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self):
        if self.path != "/download":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 100_000:
                raise ValueError("Request is too large.")
            data = json.loads(self.rfile.read(length))
            source = normalize_source(str(data.get("source", "")))
            fmt = str(data.get("format", "video_360p_rec")).strip().lower()
        except (ValueError, json.JSONDecodeError, AttributeError) as exc:
            self.reply(400, {"error": str(exc)})
            return

        with tempfile.TemporaryDirectory(prefix="sounddrop-dl-") as tmp:
            output = Path(tmp) / "%(title)s [%(id)s].%(ext)s"
            cmd = get_ytdlp_args(fmt, str(output), source)
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
            except subprocess.TimeoutExpired:
                self.reply(504, {"error": "Download timed out. Try another link or resolution."})
                return

            files = [p for p in Path(tmp).rglob("*") if p.is_file() and not p.name.endswith(".part")]
            if result.returncode or not files:
                message = (result.stderr or result.stdout or "Could not download this result.").strip()
                if "page needs to be reloaded" in message.lower() or "bot" in message.lower():
                    message = "YouTube anti-bot challenge encountered. Try pasting the direct video URL."
                else:
                    message = message[-500:]
                self.reply(422, {"error": message})
                return

            downloaded = files[0]
            data_bytes = downloaded.read_bytes()
            filename = downloaded.name

            mime_types = {
                ".mp3": "audio/mpeg",
                ".m4a": "audio/mp4",
                ".opus": "audio/opus",
                ".ogg": "audio/ogg",
                ".wav": "audio/wav",
                ".flac": "audio/flac",
                ".mp4": "video/mp4",
                ".webm": "video/webm",
                ".mkv": "video/x-matroska",
            }
            content_type = mime_types.get(downloaded.suffix.lower(), "application/octet-stream")

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data_bytes)))
            self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + quote(filename, safe=""))
            self.end_headers()
            self.wfile.write(data_bytes)

    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


if __name__ == "__main__":
    ytdlp_path = Path(str(YTDLP_BIN))
    if not ytdlp_path.exists() and not shutil.which("yt-dlp"):
        raise SystemExit("Missing yt-dlp. Run ./start.sh or install requirements.txt.")
    print(f"Sounddrop server active on port {PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
