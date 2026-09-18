"""
Downland Video - Web app to download TikTok & Facebook videos.

- TikTok: uses tikwm.com API to fetch a no-watermark video URL.
- Facebook (and TikTok fallback): uses yt-dlp to resolve a direct video URL.

For personal use only. Respect content owners' rights.
"""

import re
import io
import mimetypes

import requests
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    Response,
    stream_with_context,
)

try:
    import yt_dlp
except ImportError:  # yt-dlp optional at import time; required for Facebook
    yt_dlp = None

app = Flask(__name__)

# A browser-like User-Agent helps avoid some basic blocks.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

TIKWM_API = "https://www.tikwm.com/api/"


def detect_platform(url: str) -> str:
    """Return 'tiktok', 'facebook', or 'unknown' based on the URL."""
    u = url.lower()
    if "tiktok.com" in u or "vt.tiktok" in u or "vm.tiktok" in u:
        return "tiktok"
    if "facebook.com" in u or "fb.watch" in u or "fb.com" in u:
        return "facebook"
    return "unknown"


def fetch_tiktok(url: str) -> dict:
    """Get a no-watermark TikTok video via the tikwm.com API."""
    resp = requests.post(
        TIKWM_API,
        data={"url": url, "hd": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != 0 or not data.get("data"):
        raise RuntimeError(data.get("msg") or "TikTok API failed")

    d = data["data"]
    # hdplay/play are no-watermark; wmplay has the watermark.
    video_url = d.get("hdplay") or d.get("play") or d.get("wmplay")
    if not video_url:
        raise RuntimeError("No downloadable video URL found for this TikTok link.")

    if video_url.startswith("/"):
        video_url = "https://www.tikwm.com" + video_url

    return {
        "title": d.get("title") or "tiktok_video",
        "video_url": video_url,
        "thumbnail": d.get("cover") or d.get("origin_cover"),
        "author": (d.get("author") or {}).get("nickname"),
        "no_watermark": True,
    }


def fetch_with_ytdlp(url: str) -> dict:
    """Resolve a direct video URL using yt-dlp (used for Facebook)."""
    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed. Run: pip install yt-dlp")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        # Prefer a progressive mp4 (video+audio in one file), then fall back.
        "format": (
            "best[ext=mp4][acodec!=none][vcodec!=none]/"
            "best[acodec!=none][vcodec!=none]/best"
        ),
        "http_headers": {
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # For playlists/multiple entries, take the first.
    if "entries" in info and info["entries"]:
        info = info["entries"][0]

    video_url = info.get("url")
    if not video_url and info.get("formats"):
        formats = info["formats"]
        # 1) Prefer a format with BOTH video and audio (progressive).
        for f in reversed(formats):
            if (
                f.get("url")
                and f.get("vcodec") not in (None, "none")
                and f.get("acodec") not in (None, "none")
            ):
                video_url = f["url"]
                break
        # 2) Otherwise, any format that has a video stream.
        if not video_url:
            for f in reversed(formats):
                if f.get("url") and f.get("vcodec") not in (None, "none"):
                    video_url = f["url"]
                    break

    if not video_url:
        raise RuntimeError("Could not extract a direct video URL.")

    return {
        "title": info.get("title") or "video",
        "video_url": video_url,
        "thumbnail": info.get("thumbnail"),
        "author": info.get("uploader"),
        "no_watermark": True,
    }


def safe_filename(name: str) -> str:
    """Turn a title into a safe Unicode filename (keeps Khmer, etc.)."""
    # Remove characters that are illegal in filenames but keep Unicode letters.
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "", name).strip()
    name = re.sub(r"\s+", "_", name)
    return (name or "video")[:80]


def ascii_fallback(name: str) -> str:
    """ASCII-only version of a name for the legacy Content-Disposition field."""
    ascii_name = name.encode("ascii", "ignore").decode("ascii").strip()
    ascii_name = re.sub(r"\s+", "_", ascii_name)
    return ascii_name or "video"


# Matches ANSI color/escape sequences (e.g. from yt-dlp error output).
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def clean_error(exc: Exception) -> str:
    """Strip ANSI codes and yt-dlp noise from an error message."""
    msg = ANSI_RE.sub("", str(exc)).strip()
    # yt-dlp prefixes with "ERROR:" — remove it for a cleaner message.
    msg = re.sub(r"^ERROR:\s*", "", msg)
    return msg


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def api_info():
    """Return video metadata + a resolved direct URL for the given link."""
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()

    if not url:
        return jsonify({"error": "សូមបញ្ចូល URL"}), 400

    platform = detect_platform(url)
    if platform == "unknown":
        return jsonify({"error": "គាំទ្រតែ TikTok និង Facebook ប៉ុណ្ណោះ"}), 400

    try:
        if platform == "tiktok":
            try:
                info = fetch_tiktok(url)
            except Exception:
                # Fallback to yt-dlp if the TikTok API fails.
                info = fetch_with_ytdlp(url)
        else:
            info = fetch_with_ytdlp(url)
    except Exception as exc:  # noqa: BLE001
        msg = clean_error(exc)
        if "No video formats found" in msg or "Unsupported URL" in msg:
            msg = (
                "រកវីដេអូមិនឃើញ។ សូមប្រាកដថា link ជាវីដេអូ public "
                "(មិនមែន private/reel ដែលត្រូវ login)។"
            )
        return jsonify({"error": f"ដោនឡូតបរាជ័យ: {msg}"}), 502

    info["platform"] = platform
    return jsonify(info)


@app.route("/download")
def download():
    """Proxy the remote video so the browser saves it directly."""
    from urllib.parse import quote

    video_url = request.args.get("url")
    raw_name = request.args.get("name") or "video"
    unicode_name = safe_filename(raw_name) + ".mp4"
    ascii_name = ascii_fallback(safe_filename(raw_name)) + ".mp4"

    if not video_url:
        return "Missing url", 400

    remote = requests.get(
        video_url,
        headers={"User-Agent": USER_AGENT},
        stream=True,
        timeout=60,
    )
    remote.raise_for_status()

    content_type = remote.headers.get("Content-Type") or "video/mp4"

    def generate():
        for chunk in remote.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    # RFC 5987: provide an ASCII fallback + a UTF-8 (URL-encoded) filename*.
    disposition = (
        "attachment; "
        f'filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(unicode_name)}"
    )
    headers = {
        "Content-Disposition": disposition,
    }
    length = remote.headers.get("Content-Length")
    if length:
        headers["Content-Length"] = length

    return Response(
        stream_with_context(generate()),
        headers=headers,
        content_type=content_type,
    )


if __name__ == "__main__":
    import os

    # PORT is provided by the hosting platform (Render, Railway, etc.).
    port = int(os.environ.get("PORT", 5000))
    # Enable debug only for local development.
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
