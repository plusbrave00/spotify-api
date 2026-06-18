from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__)
CORS(app)

COOKIES = os.environ.get('YT_COOKIES', '')

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

    opts = {
        'quiet': True, 'no_warnings': True,
        'extract_flat': 'in_playlist', 'skip_download': True,
        'default_search': f'ytsearch{limit}',
    }
    if COOKIES and os.path.exists(COOKIES):
        opts['cookiefile'] = COOKIES

    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(q, download=False)

    results = []
    for r in (data.get('entries') or [data]):
        if not r:
            continue
        results.append({
            'id': r.get('id'),
            'title': r.get('title'),
            'artist': r.get('uploader') or r.get('channel') or 'Unknown',
            'duration': r.get('duration'),
            'thumbnail': r.get('thumbnail') or f"https://i.ytimg.com/vi/{r.get('id')}/hqdefault.jpg",
            'url': f"https://youtube.com/watch?v={r.get('id')}",
        })
    return jsonify({'status': 'ok', 'count': len(results), 'results': results})

@app.route('/stream')
def stream():
    url = request.args.get('url')
    quality = request.args.get('quality', 'high')
    if not url:
        return jsonify({'error': 'Missing ?url'}), 400

    opts = {
        'quiet': True, 'no_warnings': True, 'skip_download': True,
        'format': {'low': 'worstaudio', 'medium': 'bestaudio[abr<=64]', 'high': 'bestaudio'}.get(quality, 'bestaudio'),
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    if COOKIES and os.path.exists(COOKIES):
        opts['cookiefile'] = COOKIES

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

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
    opts = {
        'quiet': True, 'no_warnings': True,
        'extract_flat': 'in_playlist', 'skip_download': True,
        'default_search': f'ytsearch20',
    }
    if COOKIES and os.path.exists(COOKIES):
        opts['cookiefile'] = COOKIES

    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(f'{country} trending music 2026', download=False)

    results = []
    for r in (data.get('entries') or []):
        if not r:
            continue
        results.append({
            'id': r.get('id'),
            'title': r.get('title'),
            'artist': r.get('uploader') or r.get('channel') or 'Unknown',
            'duration': r.get('duration'),
            'thumbnail': r.get('thumbnail') or f"https://i.ytimg.com/vi/{r.get('id')}/hqdefault.jpg",
            'url': f"https://youtube.com/watch?v={r.get('id')}",
        })
    return jsonify({'status': 'ok', 'count': len(results), 'results': results})

@app.route('/info')
def info():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing ?url'}), 400

    opts = {
        'quiet': True, 'no_warnings': True, 'skip_download': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    if COOKIES and os.path.exists(COOKIES):
        opts['cookiefile'] = COOKIES

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

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

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'spotify-clone-api'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
