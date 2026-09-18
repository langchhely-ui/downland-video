"""
Downland Video - Web app to download TikTok & Facebook videos.

- TikTok: uses tikwm.com API to fetch a no-watermark video URL.
- Facebook (and TikTok fallback): uses yt-dlp to resolve a direct video URL.

Design note: /download re-resolves the video from the ORIGINAL page URL right
before streaming. This keeps it stateless (works with multiple gunicorn workers)
and guarantees the CDN URL + headers are fresh, which Facebook requires.

For personal use only. Respect content owners' rights.
"""

import re

import requests
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    Response,
    stream_with_context,
    redirect,
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


def resolve_tiktok(url: str) -> dict:
    """Get a no-watermark TikTok video via the tikwm.com API.

    Returns dict with: title, video_url, thumbnail, author, headers.
    """
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
        "headers": {"User-Agent": USER_AGENT, "Referer": "https://www.tikwm.com/"},
    }


def resolve_ytdlp(url: str) -> dict:
    """Resolve a direct video URL + required headers using yt-dlp (Facebook).

    Returns dict with: title, video_url, thumbnail, author, headers.
    """
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
    dl_headers = dict(info.get("http_headers") or {})

    if not video_url and info.get("formats"):
        formats = info["formats"]
        chosen = None
        # 1) Prefer a format with BOTH video and audio (progressive).
        for f in reversed(formats):
            if (
                f.get("url")
                and f.get("vcodec") not in (None, "none")
                and f.get("acodec") not in (None, "none")
            ):
                chosen = f
                break
        # 2) Otherwise, any format that has a video stream.
        if not chosen:
            for f in reversed(formats):
                if f.get("url") and f.get("vcodec") not in (None, "none"):
                    chosen = f
                    break
        if chosen:
            video_url = chosen["url"]
            if chosen.get("http_headers"):
                dl_headers = dict(chosen["http_headers"])

    if not video_url:
        raise RuntimeError("Could not extract a direct video URL.")

    if not dl_headers.get("User-Agent"):
        dl_headers["User-Agent"] = USER_AGENT

    return {
        "title": info.get("title") or "video",
        "video_url": video_url,
        "thumbnail": info.get("thumbnail"),
        "author": info.get("uploader"),
        "headers": dl_headers,
    }


def resolve(url: str, platform: str) -> dict:
    """Resolve a source page URL into a direct video URL + headers."""
    if platform == "tiktok":
        try:
            return resolve_tiktok(url)
        except Exception:
            # Fallback to yt-dlp if the TikTok API fails.
            return resolve_ytdlp(url)
    return resolve_ytdlp(url)


def safe_filename(name: str) -> str:
    """Turn a title into a safe Unicode filename (keeps Khmer, etc.)."""
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
    msg = re.sub(r"^ERROR:\s*", "", msg)
    return msg


def friendly_error(exc: Exception) -> str:
    msg = clean_error(exc)
    if "No video formats found" in msg or "Unsupported URL" in msg:
        return (
            "រកវីដេអូមិនឃើញ។ សូមប្រាកដថា link ជាវីដេអូ public "
            "(មិនមែន private/reel ដែលត្រូវ login)។"
        )
    return msg


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def api_info():
    """Return video metadata for preview. The download itself re-resolves."""
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()

    if not url:
        return jsonify({"error": "សូមបញ្ចូល URL"}), 400

    platform = detect_platform(url)
    if platform == "unknown":
        return jsonify({"error": "គាំទ្រតែ TikTok និង Facebook ប៉ុណ្ណោះ"}), 400

    try:
        info = resolve(url, platform)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"ដោនឡូតបរាជ័យ: {friendly_error(exc)}"}), 502

    return jsonify(
        {
            "title": info["title"],
            "thumbnail": info.get("thumbnail"),
            "author": info.get("author"),
            "platform": platform,
            "no_watermark": True,
            # The frontend sends this back to /download so we can re-resolve.
            "source": url,
        }
    )


@app.route("/download")
def download():
    """Re-resolve the video from its source page URL, then stream it.

    Being stateless (no cross-request cache) makes this work reliably across
    multiple gunicorn workers, and guarantees fresh CDN URLs + headers.
    """
    from urllib.parse import quote

    source = request.args.get("source")
    raw_name = request.args.get("name") or "video"

    if not source:
        return "Missing source", 400

    platform = detect_platform(source)
    if platform == "unknown":
        return "Unsupported URL", 400

    # Resolve fresh, right before streaming.
    try:
        info = resolve(source, platform)
    except Exception as exc:  # noqa: BLE001
        return f"Resolve failed: {clean_error(exc)}", 502

    video_url = info["video_url"]
    req_headers = dict(info.get("headers") or {})
    req_headers.setdefault("User-Agent", USER_AGENT)
    req_headers.setdefault("Accept", "*/*")

    # Forward the browser's Range header so seeking works.
    range_header = request.headers.get("Range")
    if range_header:
        req_headers["Range"] = range_header

    try:
        remote = requests.get(
            video_url,
            headers=req_headers,
            stream=True,
            timeout=(15, 300),
        )
        remote.raise_for_status()
    except requests.RequestException:
        # Last resort: let the browser try the direct URL.
        return redirect(video_url, code=302)

    content_type = remote.headers.get("Content-Type") or "video/mp4"

    unicode_name = safe_filename(raw_name) + ".mp4"
    ascii_name = ascii_fallback(safe_filename(raw_name)) + ".mp4"

    def generate():
        try:
            for chunk in remote.iter_content(chunk_size=65536):
                if chunk:
                    yield chunk
        finally:
            remote.close()

    disposition = (
        "attachment; "
        f'filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(unicode_name)}"
    )
    resp_headers = {"Content-Disposition": disposition}
    length = remote.headers.get("Content-Length")
    if length:
        resp_headers["Content-Length"] = length

    return Response(
        stream_with_context(generate()),
        headers=resp_headers,
        content_type=content_type,
    )


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
