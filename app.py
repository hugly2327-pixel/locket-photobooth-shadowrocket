from flask import Flask, request, jsonify, send_from_directory, Response
from pathlib import Path
from werkzeug.utils import secure_filename
import json, os, secrets, threading, time, uuid

BASE = Path(__file__).resolve().parent
# Cloud Run container storage is ephemeral. Mount a private Cloud Storage bucket
# at LOCKET_DATA_DIR to persist the Locket session across cold starts/revisions.
DATA = Path(os.environ.get('LOCKET_DATA_DIR', str(BASE / 'data'))).resolve()
UPLOADS = Path(os.environ.get('UPLOAD_TMP_DIR', '/tmp/locket-uploads')).resolve()
DATA.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)
SESSION = DATA / 'locketlam_session.json'

app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024
client = None
login_failures = {}
login_lock = threading.Lock()
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 900


def private_site_auth():
    """Protect the entire site with HTTP Basic Auth using deployment env vars."""
    username = os.environ.get('APP_USERNAME', '').strip()
    password = os.environ.get('APP_PASSWORD', '')
    # Refuse to expose the app if the owner forgot to configure the gate.
    if not username or not password:
        return False
    auth = request.authorization
    return bool(auth and secrets.compare_digest(auth.username or '', username)
                and secrets.compare_digest(auth.password or '', password))


@app.before_request
def require_site_password():
    if request.path == '/healthz':
        return None
    if not private_site_auth():
        return Response('Website password required. Configure APP_USERNAME and APP_PASSWORD.',
                        401, {'WWW-Authenticate': 'Basic realm="Locket Photobooth", charset="UTF-8"'})
    return None


def get_client():
    global client
    if client is None:
        from locketlam import LocketClient
        client = LocketClient(session_path=str(SESSION))
    return client


def authed():
    try:
        return get_client().is_authenticated()
    except Exception:
        return False


def clean(value, depth=0):
    if depth > 6:
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        blocked = ('token', 'password', 'secret', 'authorization', 'cookie')
        return {str(k): clean(v, depth + 1) for k, v in value.items()
                if not any(term in str(k).lower() for term in blocked)}
    if isinstance(value, (list, tuple)):
        return [clean(v, depth + 1) for v in value]
    if hasattr(value, 'isoformat'):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def is_login_blocked(ip):
    now = time.time()
    with login_lock:
        attempts = [t for t in login_failures.get(ip, []) if now - t < LOCKOUT_SECONDS]
        login_failures[ip] = attempts
        return len(attempts) >= MAX_LOGIN_ATTEMPTS


def record_login_failure(ip):
    now = time.time()
    with login_lock:
        attempts = [t for t in login_failures.get(ip, []) if now - t < LOCKOUT_SECONDS]
        attempts.append(now)
        login_failures[ip] = attempts


def clear_login_failures(ip):
    with login_lock:
        login_failures.pop(ip, None)


@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(self), microphone=(self), geolocation=()'
    response.headers['Cache-Control'] = 'no-store'
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.get('/healthz')
def healthz():
    return jsonify(ok=True, service='locket-photobooth')


@app.get('/')
def index():
    return send_from_directory('static', 'index.html')


@app.get('/api/status')
def status():
    ok = authed()
    profile = None
    if ok:
        try:
            profile = clean(get_client().user.get_profile())
        except Exception:
            pass
    return jsonify(authenticated=ok, profile=profile)


@app.post('/api/login')
def login():
    global client
    ip = request.remote_addr or 'unknown'
    if is_login_blocked(ip):
        return jsonify(error='Tạm khóa đăng nhập 15 phút do có quá nhiều lần thử sai.'), 429
    body = request.get_json(silent=True) or {}
    email = (body.get('email') or '').strip()
    password = body.get('password') or ''
    if not email or not password:
        return jsonify(error='Nhập email và mật khẩu.'), 400
    try:
        c = get_client()
        c.login(email, password)
        client = c
        clear_login_failures(ip)
        try:
            os.chmod(SESSION, 0o600)
        except Exception:
            pass
        return jsonify(ok=True, profile=clean(c.user.get_profile()))
    except Exception:
        record_login_failure(ip)
        return jsonify(ok=False, error='Đăng nhập thất bại. Kiểm tra thông tin, xác minh bổ sung hoặc khả năng API Locket đã thay đổi.'), 401


@app.post('/api/logout')
def logout():
    global client
    client = None
    if SESSION.exists():
        SESSION.unlink()
    return jsonify(ok=True)


@app.get('/api/friends')
def friends():
    if not authed():
        return jsonify(error='Chưa đăng nhập'), 401
    try:
        return jsonify(friends=clean(get_client().friends.get_all_friends()))
    except Exception as exc:
        return jsonify(error=f'Không tải được bạn bè ({type(exc).__name__}).'), 502


@app.get('/api/feed')
def feed():
    if not authed():
        return jsonify(error='Chưa đăng nhập'), 401
    try:
        return jsonify(moments=clean(get_client().moments.get_latest()))
    except Exception as exc:
        return jsonify(error=f'Không tải được bảng tin ({type(exc).__name__}).'), 502


@app.post('/api/post')
def post():
    if not authed():
        return jsonify(error='Chưa đăng nhập'), 401
    media = request.files.get('media')
    if not media:
        return jsonify(error='Chưa chọn ảnh/video'), 400
    ext = Path(secure_filename(media.filename or 'upload')).suffix.lower()
    allowed = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.m4v', '.webm'}
    if ext not in allowed:
        return jsonify(error='Định dạng hỗ trợ: JPG, PNG, WEBP, MP4, MOV, WEBM.'), 400
    path = UPLOADS / (uuid.uuid4().hex + ext)
    media.save(path)
    thumb_path = None
    try:
        recipients = json.loads(request.form.get('recipients', '[]'))
        if not isinstance(recipients, list):
            recipients = []
        caption = (request.form.get('caption') or '').strip() or None
        c = get_client()
        if ext in {'.mp4', '.mov', '.m4v', '.webm'}:
            thumbnail = request.files.get('thumbnail')
            if not thumbnail:
                return jsonify(error='Video cần thumbnail.'), 400
            thumb_path = UPLOADS / (uuid.uuid4().hex + '.jpg')
            thumbnail.save(thumb_path)
            result = c.moments.post(image=str(thumb_path), video=str(path), caption=caption,
                                    is_private=False, recipients=recipients or None)
        else:
            result = c.moments.post(image=str(path), caption=caption,
                                    is_private=False, recipients=recipients or None)
        return jsonify(ok=True, result=clean(result))
    except Exception as exc:
        return jsonify(ok=False, error=f'Đăng thất bại ({type(exc).__name__}). API riêng có thể đã thay đổi.'), 502
    finally:
        path.unlink(missing_ok=True)
        if thumb_path:
            thumb_path.unlink(missing_ok=True)


@app.errorhandler(413)
def too_big(_error):
    return jsonify(error='Tệp vượt quá 30 MB.'), 413


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8765'))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
