from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os, traceback

app = Flask(__name__)
CORS(app)

COOKIES = os.environ.get('YT_COOKIES', '')
PROXY = os.environ.get('YT_PROXY', '')

def base_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web', 'ios', 'tv'],
                'skip': ['dash', 'hls'],
            }
        },
    }
    if COOKIES and os.path.exists(COOKIES):
        opts['cookiefile'] = COOKIES
    if PROXY:
        opts['proxy'] = PROXY
    return opts

def extract_json(data):
    if not data:
        return None
    return {
        'id': data.get('id'),
        'title': data.get('title'),
        'artist': data.get('uploader') or data.get('channel') or 'Unknown',
        'duration': data.get('duration'),
        'thumbnail': data.get('thumbnail') or f"https://i.ytimg.com/vi/{data.get('id')}/hqdefault.jpg",
        'url': f"https://youtube.com/watch?v={data.get('id')}",
    }

@app.route('/')
def home():
    return jsonify({
        'app': 'Spotify Clone API',
        'endpoints': {
            '/search': '?q=&limit=10',
            '/stream': '?url=&quality=high',
            '/trending': '?country=IN',
            '/info': '?url=',
        }
    })

@app.route('/search')
def search():
    q = request.args.get('q')
    limit = int(request.args.get('limit', 10))
    if not q:
        return jsonify({'error': 'Missing ?q'}), 400

    opts = base_opts()
    opts['extract_flat'] = 'in_playlist'
    opts['default_search'] = f'ytsearch{limit}'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(q, download=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    results = []
    for r in (data.get('entries') or [data]):
        item = extract_json(r)
        if item:
            results.append(item)
    return jsonify({'status': 'ok', 'count': len(results), 'results': results})

@app.route('/stream')
def stream():
    url = request.args.get('url')
    quality = request.args.get('quality', 'high')
    if not url:
        return jsonify({'error': 'Missing ?url'}), 400

    quality_map = {'low': 'worstaudio', 'medium': 'bestaudio[abr<=64]', 'high': 'bestaudio'}
    fmt = quality_map.get(quality, 'bestaudio')

    opts = base_opts()
    opts['format'] = fmt
    opts['socket_timeout'] = 15

    print(f"[stream] url={url} quality={quality} fmt={fmt}", flush=True)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            print("[stream] extracting...", flush=True)
            info = ydl.extract_info(url, download=False)
            print(f"[stream] extracted: {info is not None}", flush=True)
    except Exception as e:
        print(f"[stream] EXCEPTION: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

    if not info:
        return jsonify({'error': 'No data extracted'}), 500

    return jsonify({
        'status': 'ok',
        'title': info.get('title'),
        'artist': info.get('uploader') or info.get('channel') or 'Unknown',
        'duration': info.get('duration'),
        'thumbnail': info.get('thumbnail'),
        'audio_url': info.get('url'),
        'quality': quality,
    })

@app.route('/trending')
def trending():
    country = request.args.get('country', 'IN')
    opts = base_opts()
    opts['extract_flat'] = 'in_playlist'
    opts['default_search'] = 'ytsearch20'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(f'{country} trending music 2026', download=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    results = []
    for r in (data.get('entries') or []):
        item = extract_json(r)
        if item:
            results.append(item)
    return jsonify({'status': 'ok', 'count': len(results), 'results': results})

@app.route('/info')
def info():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing ?url'}), 400

    opts = base_opts()
    opts['socket_timeout'] = 15

    print(f"[info] url={url}", flush=True)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            print("[info] extracting...", flush=True)
            info = ydl.extract_info(url, download=False)
            print(f"[info] extracted: {info is not None}", flush=True)
    except Exception as e:
        print(f"[info] EXCEPTION: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

    if not info:
        return jsonify({'error': 'No data extracted'}), 500

    formats = []
    for f in info.get('formats', []):
        if f.get('acodec') and f['acodec'] != 'none':
            formats.append({
                'id': f.get('format_id'),
                'ext': f.get('ext'),
                'bitrate': f.get('abr'),
                'size': f.get('filesize'),
            })

    return jsonify({
        'status': 'ok',
        'title': info.get('title'),
        'artist': info.get('uploader') or info.get('channel') or 'Unknown',
        'duration': info.get('duration'),
        'thumbnail': info.get('thumbnail'),
        'formats': formats,
    })

@app.errorhandler(Exception)
def handle_all_errors(e):
    if hasattr(e, 'code') and e.code == 404:
        return jsonify({'error': 'Not found'}), 404
    traceback.print_exc()
    return jsonify({'error': str(e), 'type': type(e).__name__}), 500

@app.route('/test_error')
def test_error():
    raise RuntimeError("test error from /test_error")

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'spotify-clone-api'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
