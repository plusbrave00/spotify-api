from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os, traceback, base64

app = Flask(__name__)
CORS(app)

COOKIES = os.environ.get('YT_COOKIES', '')
PROXY = os.environ.get('YT_PROXY', '')
COOKIES_CONTENT = os.environ.get('YT_COOKIES_CONTENT', '')
COOKIES_B64 = os.environ.get('YT_COOKIES_B64', '')

if COOKIES_CONTENT and not os.path.exists(COOKIES):
    COOKIES = '/app/cookies.txt'
    with open(COOKIES, 'w') as f:
        f.write(COOKIES_CONTENT.replace('\\n', '\n'))
elif COOKIES_B64 and not os.path.exists(COOKIES):
    COOKIES = '/app/cookies.txt'
    with open(COOKIES, 'wb') as f:
        f.write(base64.b64decode(COOKIES_B64))

def base_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web', 'ios', 'tv'],
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

    opts = base_opts()
    opts['format'] = 'bestaudio/best'
    opts['socket_timeout'] = 15

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({'error': str(e), 'type': type(e).__name__}), 500

    if not info:
        return jsonify({'error': 'No data extracted'}), 500

    audio_url = info.get('url')
    if not audio_url and info.get('formats'):
        audio_formats = [f for f in info['formats'] if f.get('acodec') and f.get('acodec') != 'none']
        if not audio_formats:
            audio_formats = info['formats']
        quality_map = {'low': 32, 'medium': 64, 'high': 999}
        target_abr = quality_map.get(quality, 999)
        best = min(audio_formats, key=lambda f: abs((f.get('abr') or 0) - target_abr) if target_abr < 999 else -(f.get('abr') or 0))
        audio_url = best.get('url')

    return jsonify({
        'status': 'ok',
        'title': info.get('title'),
        'artist': info.get('uploader') or info.get('channel') or 'Unknown',
        'duration': info.get('duration'),
        'thumbnail': info.get('thumbnail'),
        'audio_url': audio_url,
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
    opts['format'] = 'bestaudio/best'
    opts['socket_timeout'] = 15

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
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

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'spotify-clone-api'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
