from flask import Flask, request, redirect, url_for, session, render_template_string, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3
import os
import html
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-now')
DATABASE = os.environ.get('CHAT_DB', 'great_iraq_guest_chat.db')
ROOM_CAPACITY = 50
OWNER_PASSWORD = os.environ.get('OWNER_PASSWORD', '06041990')
OWNER_NAME = 'ملك الشات'
ALL_PERMISSIONS = [
    'create_rooms',
    'delete_rooms',
    'manage_admins',
    'reset_admin_passwords',
    'kick_members',
    'permanent_ban',
    'temp_ban',
    'ip_ban',
    'unban_users',
    'mute_members',
    'delete_messages',
    'clear_rooms',
    'view_admin_panel',
]
PERMISSION_LABELS = {
    'create_rooms': 'إنشاء غرف داخل المحافظات',
    'delete_rooms': 'حذف الغرف',
    'manage_admins': 'إنشاء مشرفين وتحديد صلاحياتهم',
    'reset_admin_passwords': 'تغيير الرمز السري للمشرفين',
    'kick_members': 'طرد أعضاء من الغرف',
    'permanent_ban': 'حظر دائم للزوار',
    'temp_ban': 'حظر مؤقت للزوار',
    'ip_ban': 'حظر IP',
    'unban_users': 'فك الحظر',
    'mute_members': 'كتم أعضاء داخل الغرف',
    'delete_messages': 'حذف الرسائل',
    'clear_rooms': 'إفراغ الغرف من الأعضاء والرسائل',
    'view_admin_panel': 'دخول لوحة المشرف',
}

IRAQI_PROVINCES = [
    ('baghdad', 'بغداد'),
    ('basra', 'البصرة'),
    ('nineveh', 'نينوى'),
    ('erbil', 'أربيل'),
    ('najaf', 'النجف'),
    ('karbala', 'كربلاء'),
    ('maysan', 'ميسان'),
    ('dhiqar', 'ذي قار'),
    ('muthanna', 'المثنى'),
    ('qadisiyah', 'القادسية'),
    ('babil', 'بابل'),
    ('wasit', 'واسط'),
    ('diyala', 'ديالى'),
    ('anbar', 'الأنبار'),
    ('salahuddin', 'صلاح الدين'),
    ('kirkuk', 'كركوك'),
    ('duhok', 'دهوك'),
    ('sulaymaniyah', 'السليمانية'),
]
PROVINCE_MAP = dict(IRAQI_PROVINCES)

BASE_TEMPLATE = r'''
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/remixicon@4.3.0/fonts/remixicon.css" rel="stylesheet">
  <style>
    :root{
      --primary:#7c3aed;--accent:#06b6d4;--pink:#ec4899;--dark:#21124a;
      --text:#1f2440;--muted:#6b7280;--border:rgba(124,58,237,.16);
      --danger:#e11d48;--success:#10b981;--warning:#f59e0b;
      --shadow:0 14px 34px rgba(55,25,110,.13);--radius:24px;
    }
    *{box-sizing:border-box}
    body{margin:0;font-family:'Cairo',sans-serif;color:var(--text);min-height:100vh;background:
      radial-gradient(circle at top right,rgba(124,58,237,.22),transparent 25%),
      radial-gradient(circle at top left,rgba(6,182,212,.16),transparent 24%),
      radial-gradient(circle at bottom left,rgba(236,72,153,.12),transparent 28%),
      linear-gradient(180deg,#f8f5ff,#f6fbff 48%,#fff7fb)}
    a{text-decoration:none;color:inherit}.app{display:flex;min-height:100vh}
    .sidebar{width:280px;min-height:100vh;position:sticky;top:0;background:linear-gradient(180deg,#291856,#172554);color:#fff;padding:18px 14px;box-shadow:0 0 30px rgba(0,0,0,.18);overflow:auto}
    .brand{display:flex;gap:12px;align-items:center;padding:14px;border-radius:22px;background:linear-gradient(135deg,rgba(255,255,255,.12),rgba(255,255,255,.05));border:1px solid rgba(255,255,255,.1);margin-bottom:18px}
    .logo{width:54px;height:54px;border-radius:18px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#8b5cf6,#06b6d4,#ec4899);font-size:28px;box-shadow:0 12px 28px rgba(124,58,237,.35)}
    .brand h1{font-size:18px;line-height:1.4;margin:0;font-weight:900}.brand p{font-size:12px;margin:3px 0 0;color:rgba(255,255,255,.75)}
    .nav-label{font-size:12px;color:rgba(255,255,255,.55);display:block;padding:10px 12px}.nav-link{display:flex;align-items:center;gap:11px;padding:12px 14px;border-radius:16px;color:rgba(255,255,255,.9);margin-bottom:8px;border:1px solid transparent;transition:.2s}
    .nav-link:hover,.nav-link.active{background:linear-gradient(135deg,rgba(255,255,255,.12),rgba(255,255,255,.06));border-color:rgba(255,255,255,.12);transform:translateY(-1px)}.nav-link i{font-size:20px}
    .user-mini{margin-top:18px;padding:14px;border-radius:18px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.08)}
    .main{flex:1;min-width:0;padding:18px}.topbar{position:sticky;top:12px;z-index:20;background:rgba(255,255,255,.78);backdrop-filter:blur(16px);border:1px solid var(--border);border-radius:24px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;box-shadow:var(--shadow)}
    .topbar h2{margin:0;font-size:24px;font-weight:900}.topbar p{margin:3px 0 0;color:var(--muted);font-size:13px}.content{padding-top:18px}
    .btn,button{border:none;cursor:pointer;font-family:inherit;font-weight:800;border-radius:16px;padding:12px 16px;display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;box-shadow:0 10px 24px rgba(124,58,237,.18);transition:.18s}.btn:hover,button:hover{transform:translateY(-1px)}
    .btn-light{background:#fff;color:var(--text);border:1px solid var(--border);box-shadow:none}.btn-soft{background:linear-gradient(135deg,rgba(124,58,237,.08),rgba(6,182,212,.08));color:var(--primary);border:1px solid rgba(124,58,237,.14);box-shadow:none}.btn-danger{background:linear-gradient(135deg,#fb7185,#e11d48);color:#fff}.btn-success{background:linear-gradient(135deg,#34d399,#10b981);color:#fff}.btn-warning{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#fff}
    .grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}.col-12{grid-column:span 12}.col-8{grid-column:span 8}.col-6{grid-column:span 6}.col-4{grid-column:span 4}.col-3{grid-column:span 3}
    .card{background:rgba(255,255,255,.87);backdrop-filter:blur(18px);border:1px solid var(--border);border-radius:var(--radius);padding:20px;box-shadow:var(--shadow)}
    .hero{background:linear-gradient(135deg,rgba(124,58,237,.98),rgba(6,182,212,.92),rgba(236,72,153,.88));color:#fff;position:relative;overflow:hidden}.hero h1,.hero h3{margin:0 0 8px;font-size:32px;font-weight:900}.hero p{margin:0;line-height:1.9;color:rgba(255,255,255,.92)}
    .section-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap}.section-head h3{margin:0;font-size:21px;font-weight:900}.section-head p{margin:4px 0 0;color:var(--muted);font-size:13px}
    .list{display:flex;flex-direction:column;gap:12px}.item{display:flex;align-items:center;justify-content:space-between;gap:14px;border:1px solid var(--border);border-radius:20px;padding:14px;background:rgba(255,255,255,.72)}.item-main{display:flex;align-items:center;gap:13px;min-width:0}.avatar{width:54px;height:54px;border-radius:18px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#ede9fe,#cffafe,#fce7f3);color:#7c3aed;font-weight:900;font-size:21px;flex-shrink:0}.item h4{margin:0;font-size:17px}.muted{color:var(--muted);font-size:13px;line-height:1.8}.badge{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;font-size:12px;font-weight:800;background:linear-gradient(135deg,rgba(124,58,237,.1),rgba(6,182,212,.08));color:var(--primary);border:1px solid rgba(124,58,237,.14)}.badge-danger{background:rgba(225,29,72,.08);color:var(--danger);border-color:rgba(225,29,72,.15)}.badge-success{background:rgba(16,185,129,.08);color:var(--success);border-color:rgba(16,185,129,.15)}.badge-warning{background:rgba(245,158,11,.1);color:#b45309;border-color:rgba(245,158,11,.15)}
    label{display:block;font-size:14px;font-weight:800;margin-bottom:7px}input,textarea,select{width:100%;border-radius:16px;border:1px solid rgba(124,58,237,.17);background:rgba(255,255,255,.92);padding:14px 15px;font-family:inherit;font-size:15px;outline:none;resize:vertical}input:focus,textarea:focus,select:focus{border-color:rgba(124,58,237,.45);box-shadow:0 0 0 4px rgba(124,58,237,.08)}.field{margin-bottom:14px}
    .flash{display:flex;gap:10px;margin:0 0 14px;padding:14px 16px;border-radius:18px;background:rgba(254,249,195,.82);border:1px solid rgba(250,204,21,.25);color:#854d0e}
    .role-name-owner{color:#d4af37;font-weight:900;text-shadow:0 1px 0 rgba(212,175,55,.22),0 0 10px rgba(212,175,55,.18)}
    .role-name-admin{color:#2563eb;font-weight:900;text-shadow:0 1px 0 rgba(37,99,235,.06)}
    .role-name-visitor{color:var(--text);font-weight:900}
    .badge-owner{background:linear-gradient(135deg,rgba(255,215,0,.20),rgba(245,158,11,.10));color:#b7791f;border-color:rgba(212,175,55,.35)}
    .badge-admin{background:rgba(37,99,235,.10);color:#2563eb;border-color:rgba(37,99,235,.20)}
.auth-shell{min-height:100vh;display:grid;place-items:center;padding:20px}.auth-card{width:min(100%,640px)}.role-box{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}.role-choice input{display:none}.role-choice span{display:flex;align-items:center;justify-content:center;gap:8px;border:1px solid var(--border);border-radius:18px;padding:15px;background:#fff;font-weight:900;cursor:pointer}.role-choice input:checked+span{background:linear-gradient(135deg,rgba(124,58,237,.14),rgba(6,182,212,.10));color:var(--primary);border-color:rgba(124,58,237,.32)}
    .province-grid,.room-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.province-card,.room-card{display:block;background:linear-gradient(180deg,rgba(255,255,255,.94),rgba(255,255,255,.84));border:1px solid var(--border);border-radius:22px;padding:16px;box-shadow:var(--shadow);transition:.18s}.province-card:hover,.room-card:hover{transform:translateY(-2px);box-shadow:0 18px 36px rgba(124,58,237,.15)}.city-icon{width:58px;height:58px;border-radius:20px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#ddd6fe,#cffafe,#fbcfe8);color:#7c3aed;font-size:25px;margin-bottom:14px}.province-card h3,.room-card h3{margin:0 0 8px;font-size:22px;font-weight:900}
    .chat-layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:16px}.chat-box{display:flex;flex-direction:column;gap:12px;max-height:520px;overflow:auto;padding:10px;background:linear-gradient(180deg,#fcf7ff,#eefcfe,#fff3fa);border-radius:22px;border:1px solid var(--border)}.msg{display:flex}.msg.me{justify-content:flex-start}.msg.other{justify-content:flex-end}.bubble{max-width:min(78%,560px);padding:13px 16px;border-radius:22px;background:#fff;border:1px solid var(--border);line-height:1.9;box-shadow:0 10px 24px rgba(15,23,42,.05)}.msg.me .bubble{background:linear-gradient(135deg,#ede9fe,#e0f2fe,#fce7f3)}.meta{font-size:12px;color:var(--muted);margin-top:6px}.empty{padding:20px;text-align:center;color:var(--muted);border:1px dashed rgba(124,58,237,.24);border-radius:18px;background:rgba(255,255,255,.55)}
    .owner-entry-mini{position:fixed;right:12px;bottom:12px;width:34px;height:34px;border-radius:999px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,rgba(124,58,237,.96),rgba(6,182,212,.92));color:#fff;border:1px solid rgba(255,255,255,.55);box-shadow:0 10px 24px rgba(55,25,110,.22);z-index:140;opacity:.72;transition:.18s;font-size:15px}
    .owner-entry-mini:hover{opacity:1;transform:translateY(-1px) scale(1.03)}
    .owner-entry-mini span{position:absolute;bottom:42px;right:0;background:rgba(33,18,74,.95);color:#fff;padding:7px 10px;border-radius:12px;font-size:11px;white-space:nowrap;opacity:0;pointer-events:none;transform:translateY(6px);transition:.18s}
    .owner-entry-mini:hover span{opacity:1;transform:translateY(0)}
    .mobile-toggle{display:none}@media(max-width:1000px){.col-8,.col-6,.col-4,.col-3{grid-column:span 12}.chat-layout{grid-template-columns:1fr}.sidebar{position:fixed;right:0;top:0;bottom:0;z-index:100;transform:translateX(100%);transition:.22s;width:min(88vw,320px)}.sidebar.open{transform:translateX(0)}.app{display:block}.main{padding:14px}.mobile-toggle{display:inline-flex}.hero h1,.hero h3{font-size:27px}.role-box{grid-template-columns:1fr}.owner-entry-mini{right:10px;bottom:10px;width:32px;height:32px}}
  </style>
</head>
<body>
{% if auth_page %}
  <div class="auth-shell"><div class="auth-card">{% for m in flashes %}<div class="flash"><i class="ri-error-warning-line"></i><div>{{ m }}</div></div>{% endfor %}{{ content|safe }}</div></div>
{% else %}
  <div class="app">
    <aside class="sidebar" id="sidebar">
      <div class="brand"><div class="logo"><i class="ri-message-3-fill"></i></div><div><h1>دردشة العراق العظيم</h1><p>زائر / مشرف بدون تسجيل</p></div></div>
      <span class="nav-label">القائمة</span>
      <a class="nav-link {% if active=='home' %}active{% endif %}" href="{{ url_for('dashboard') }}"><i class="ri-home-5-line"></i> الرئيسية</a>
      <a class="nav-link {% if active=='provinces' %}active{% endif %}" href="{{ url_for('provinces') }}"><i class="ri-map-pin-2-line"></i> المحافظات</a>
      {% if user.role != 'visitor' %}<a class="nav-link {% if active=='admin' %}active{% endif %}" href="{{ url_for('admin_panel') }}"><i class="ri-shield-star-line"></i> لوحة المشرف</a>{% endif %}
      <a class="nav-link" href="{{ url_for('logout') }}"><i class="ri-logout-box-r-line"></i> خروج / تغيير اسم</a>
      <div class="user-mini"><div class="item-main"><div class="avatar">{{ user.name[:1] }}</div><div><div style="font-weight:900">{{ user.name }}</div><div class="muted" style="color:rgba(255,255,255,.7)">{{ user.role_label }}</div></div></div></div>
    </aside>
    <main class="main">
      <div class="topbar"><div><h2>{{ title }}</h2><p>{{ subtitle }}</p></div><div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn-light mobile-toggle" onclick="toggleSidebar()"><i class="ri-menu-line"></i> القائمة</button><a class="btn-soft" href="{{ url_for('provinces') }}"><i class="ri-map-pin-line"></i> المحافظات</a></div></div>
      <div class="content">{% for m in flashes %}<div class="flash"><i class="ri-error-warning-line"></i><div>{{ m }}</div></div>{% endfor %}{{ content|safe }}</div>
    </main>
  </div>
  {% if user.role == 'visitor' %}
    <a class="owner-entry-mini" href="{{ url_for('admin_login') }}" title="دخول صاحب البرنامج">
      <i class="ri-key-2-line"></i>
      <span>دخول صاحب البرنامج</span>
    </a>
  {% endif %}
{% endif %}
<script>
function toggleSidebar(){const s=document.getElementById('sidebar'); if(s) s.classList.toggle('open');}
function toggleAdminPassword(){const role=document.querySelector('input[name="role"]:checked')?.value; const box=document.getElementById('admin-pass-box'); if(box) box.style.display = (role === 'admin') ? 'block' : 'none';}
</script>
</body></html>
'''


def db():
    conn = sqlite3.connect(DATABASE, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn


def now():
    return datetime.utcnow().isoformat(timespec='seconds')


def esc(x):
    return html.escape(str(x or ''))


def get_client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def add_log(action, target_name='', room_id=None, note='', conn=None):
    own_conn = conn is None
    if own_conn:
        conn = db()
    conn.execute(
        'INSERT INTO moderation_actions (action, actor_name, target_name, room_id, ip_address, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (action, session.get('display_name', 'system'), target_name, room_id, get_client_ip(), note, now())
    )
    if own_conn:
        conn.close()


def parse_minutes(value, default=60):
    try:
        minutes = int(value)
        if minutes < 1:
            minutes = default
        if minutes > 43200:
            minutes = 43200
        return minutes
    except Exception:
        return default


def expires_after_minutes(minutes):
    from datetime import timedelta
    return (datetime.utcnow() + timedelta(minutes=minutes)).isoformat(timespec='seconds')


def cleanup_expired_restrictions():
    conn = db()
    current = now()
    conn.execute('DELETE FROM user_bans WHERE expires_at != "" AND expires_at <= ?', (current,))
    conn.execute('DELETE FROM ip_bans WHERE expires_at != "" AND expires_at <= ?', (current,))
    conn.execute('DELETE FROM muted_members WHERE expires_at != "" AND expires_at <= ?', (current,))
    conn.commit()
    conn.close()


def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS subrooms(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        province_slug TEXT NOT NULL,
        name TEXT NOT NULL,
        created_by TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS room_members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        display_name TEXT NOT NULL,
        role TEXT NOT NULL,
        joined_at TEXT NOT NULL,
        UNIQUE(room_id, session_id)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS room_messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        display_name TEXT NOT NULL,
        role TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS admins(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_owner INTEGER DEFAULT 0,
        permissions TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS user_bans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        display_name TEXT DEFAULT '',
        session_id TEXT DEFAULT '',
        ip_address TEXT DEFAULT '',
        ban_type TEXT NOT NULL DEFAULT 'permanent',
        reason TEXT DEFAULT '',
        expires_at TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS ip_bans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip_address TEXT NOT NULL,
        reason TEXT DEFAULT '',
        expires_at TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS muted_members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        display_name TEXT DEFAULT '',
        reason TEXT DEFAULT '',
        expires_at TEXT DEFAULT '',
        created_by TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        UNIQUE(room_id, session_id)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS moderation_actions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        actor_name TEXT DEFAULT '',
        target_name TEXT DEFAULT '',
        room_id INTEGER,
        ip_address TEXT DEFAULT '',
        note TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )''')
    existing_cols = [r[1] for r in cur.execute('PRAGMA table_info(room_members)').fetchall()]
    if 'ip_address' not in existing_cols:
        cur.execute('ALTER TABLE room_members ADD COLUMN ip_address TEXT DEFAULT ""')
    owner = cur.execute('SELECT id FROM admins WHERE is_owner=1 LIMIT 1').fetchone()
    if not owner:
        cur.execute('INSERT INTO admins (username, password_hash, is_owner, permissions, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (OWNER_NAME, generate_password_hash(OWNER_PASSWORD), 1, ','.join(ALL_PERMISSIONS), 'system', now()))
    conn.commit()
    conn.close()


def role_label(role):
    if role == 'owner':
        return 'مشرف أساسي'
    if role == 'admin':
        return 'مشرف'
    return 'زائر'


def user_obj():
    if not session.get('display_name') or not session.get('role'):
        return None
    role = session.get('role')
    perms = session.get('permissions', '')
    if role == 'owner':
        perms_list = ALL_PERMISSIONS[:]
    else:
        perms_list = [x for x in perms.split(',') if x]
    return {
        'name': session['display_name'],
        'role': role,
        'role_label': role_label(role),
        'sid': session.get('sid'),
        'permissions': perms_list,
    }


def is_admin_user(user):
    return user and user.get('role') in ('owner', 'admin')


def has_perm(user, perm):
    return user and (user.get('role') == 'owner' or perm in user.get('permissions', []))


def permissions_for_form(user):
    if user and user.get('role') == 'owner':
        return ALL_PERMISSIONS[:]
    return [p for p in ALL_PERMISSIONS if has_perm(user, p)]


def lower_admin_form_for_member(user, member_id, display_name):
    if not has_perm(user, 'manage_admins'):
        return ''
    allowed = permissions_for_form(user)
    # المشرف الفرعي يستطيع إعطاء صلاحيات يملكها فقط.
    checks = ''.join([
        '<label class="role-choice" style="min-width:190px"><input type="checkbox" name="permissions" value="{}"><span><i class="ri-checkbox-circle-line"></i> {}</span></label>'.format(
            p, PERMISSION_LABELS.get(p, p)
        ) for p in allowed
    ])
    return '''
      <details style="width:100%;margin-top:8px">
        <summary class="btn-soft" style="list-style:none;cursor:pointer;display:inline-flex"><i class="ri-shield-user-line"></i> سوي مشرف</summary>
        <form method="post" action="{}" style="margin-top:10px;padding:12px;border:1px solid var(--border);border-radius:16px;background:rgba(255,255,255,.68)">
          <div class="grid">
            <div class="col-6"><div class="field"><label>اسم المشرف</label><input name="username" value="{}" placeholder="اسم المشرف"></div></div>
            <div class="col-6"><div class="field"><label>رمز المشرف</label><input type="password" name="password" placeholder="رمز سري"></div></div>
          </div>
          <label>صلاحياته الأقل أو المساوية لصلاحياتك</label>
          <div class="role-box" style="grid-template-columns:repeat(auto-fit,minmax(190px,1fr))">{}</div>
          <button type="submit"><i class="ri-user-star-line"></i> إنشاء مشرف من هذا العضو</button>
        </form>
      </details>
    '''.format(url_for('make_member_admin', member_id=member_id), esc(display_name), checks)


def require_entry():
    user = user_obj()
    if not user:
        return None, redirect(url_for('entry'))
    cleanup_expired_restrictions()
    conn = db()
    banned = conn.execute(
        'SELECT * FROM user_bans WHERE (session_id=? AND session_id != "") OR (display_name=? AND display_name != "") ORDER BY id DESC LIMIT 1',
        (user.get('sid', ''), user.get('name', ''))
    ).fetchone()
    conn.close()
    if banned:
        session.clear()
        reason = banned['reason'] or 'مخالفة قواعد التطبيق'
        if banned['expires_at']:
            flash('أنت محظور مؤقتًا إلى ' + banned['expires_at'].replace('T', ' ') + '. السبب: ' + reason)
        else:
            flash('أنت محظور دائمًا. السبب: ' + reason)
        return None, redirect(url_for('entry'))
    return user, None


def render_page(title, content, subtitle='دردشة العراق العظيم', active='home', auth_page=False):
    from flask import get_flashed_messages
    public_user = user_obj() or {
        'name': 'زائر',
        'role': 'visitor',
        'role_label': 'زائر',
        'sid': '',
        'permissions': [],
    }
    return render_template_string(BASE_TEMPLATE, title=title, subtitle=subtitle, content=content, user=public_user, active=active, flashes=get_flashed_messages(), auth_page=auth_page)


@app.before_request
def block_banned_ip():
    if request.endpoint == 'static':
        return None
    cleanup_expired_restrictions()
    ip = get_client_ip()
    conn = db()
    banned = conn.execute('SELECT * FROM ip_bans WHERE ip_address=? ORDER BY id DESC LIMIT 1', (ip,)).fetchone()
    conn.close()
    if banned:
        msg = 'هذا الـ IP محظور'
        if banned['expires_at']:
            msg += ' إلى ' + banned['expires_at'].replace('T', ' ')
        return render_template_string('<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><body style="font-family:Tahoma;padding:30px;background:#fff5f5;color:#7f1d1d"><h2>تم منع الدخول</h2><p>{{msg}}</p><p>{{reason}}</p></body></html>', msg=msg, reason=banned['reason'] or 'مخالفة قواعد التطبيق'), 403
    return None


@app.route('/')
def entry():
    """الصفحة الأولى: تظهر المحافظات مباشرة بدون إنشاء جلسة زائر."""
    return redirect(url_for('provinces'))


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """دخول مخفي للمشرفين وصاحب البرنامج. لا يظهر للزوار في الواجهة."""
    if request.method == 'POST':
        name = request.form.get('display_name', '').strip()
        password = request.form.get('admin_password', '')
        if not name or not password:
            flash('اكتب اسم المشرف وكلمة السر.')
            return redirect(url_for('admin_login'))

        session.clear()
        session['display_name'] = name
        session['sid'] = str(uuid.uuid4())
        session['ip_address'] = get_client_ip()

        conn = db()
        if name == OWNER_NAME and password == OWNER_PASSWORD:
            session['role'] = 'owner'
            session['permissions'] = ','.join(ALL_PERMISSIONS)
            conn.close()
            flash('تم الدخول كصاحب البرنامج: ' + name)
            return redirect(url_for('dashboard'))

        admin = conn.execute('SELECT * FROM admins WHERE username=? AND is_owner=0', (name,)).fetchone()
        conn.close()
        if not admin or not check_password_hash(admin['password_hash'], password):
            flash('اسم المشرف أو كلمة المرور غير صحيحة.')
            return redirect(url_for('admin_login'))

        session['role'] = 'admin'
        session['permissions'] = admin['permissions'] or ''
        flash('تم الدخول كمشرف: ' + name)
        return redirect(url_for('dashboard'))

    content = """
      <div class="card hero" style="margin-bottom:16px">
        <h1>دخول المشرف</h1>
        <p>هذه صفحة مخفية للمشرفين وصاحب البرنامج فقط. الزائر يفتح المحافظات مباشرة بدون هذه الصفحة.</p>
      </div>
      <div class="card">
        <div class="section-head"><div><h3>دخول المشرف</h3><p>اكتب اسم المشرف وكلمة السر</p></div></div>
        <form method="post">
          <div class="field"><label>اسم المشرف</label><input name="display_name" placeholder="مثال: ملك الشات"></div>
          <div class="field"><label>كلمة السر</label><input type="password" name="admin_password" placeholder="كلمة السر"></div>
          <button type="submit"><i class="ri-login-circle-line"></i> دخول</button>
        </form>
      </div>
    """
    return render_page('دخول المشرف', content, subtitle='صفحة مخفية للمشرفين', auth_page=True)


@app.route('/dashboard')
def dashboard():
    user, resp = require_entry()
    if resp:
        return resp
    conn = db()
    room_count = conn.execute('SELECT COUNT(*) AS c FROM subrooms').fetchone()['c']
    msg_count = conn.execute('SELECT COUNT(*) AS c FROM room_messages').fetchone()['c']
    online_count = conn.execute("SELECT COUNT(*) AS c FROM room_members WHERE role != 'owner'").fetchone()['c']
    conn.close()
    content = f'''
      <div class="card hero">
        <h3>أهلاً {esc(user['name'])}</h3>
        <p>أنت داخل الآن كـ <strong>{user['role_label']}</strong>. المستخدم لا يحتاج تسجيل دخول، فقط اسم مستخدم.</p>
      </div>
      <div class="grid" style="margin-top:16px">
        <div class="col-4"><div class="card"><div class="item-main"><div class="avatar"><i class="ri-map-pin-line"></i></div><div><h4>المحافظات</h4><div class="muted">18 محافظة</div></div></div></div></div>
        <div class="col-4"><div class="card"><div class="item-main"><div class="avatar"><i class="ri-chat-voice-line"></i></div><div><h4>الغرف المنشأة</h4><div class="muted">{room_count} غرفة</div></div></div></div></div>
        <div class="col-4"><div class="card"><div class="item-main"><div class="avatar"><i class="ri-team-line"></i></div><div><h4>داخل الغرف</h4><div class="muted">{online_count} عضو / الرسائل {msg_count}</div></div></div></div></div>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="section-head"><div><h3>ابدأ الآن</h3><p>ادخل محافظة ثم اختر غرفة</p></div><a class="btn" href="{url_for('provinces')}"><i class="ri-arrow-left-line"></i> المحافظات</a></div>
      </div>
    '''
    return render_page('الرئيسية', content, subtitle='دخول باسم مستخدم فقط', active='home')


@app.route('/provinces')
def provinces():
    # صفحة عامة: لا تحتاج دخول ولا تنشئ جلسة.
    conn = db()
    counts = {r['province_slug']: r['c'] for r in conn.execute('SELECT province_slug, COUNT(*) AS c FROM subrooms GROUP BY province_slug').fetchall()}
    conn.close()
    cards = []
    for slug, name in IRAQI_PROVINCES:
        cards.append(f'''
          <a class="province-card" href="{url_for('province_rooms', province_slug=slug)}">
            <div class="city-icon"><i class="ri-community-line"></i></div>
            <h3>{esc(name)}</h3>
            <div class="muted">غرف فرعية خاصة بمحافظة {esc(name)}</div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px"><span class="badge"><i class="ri-chat-1-line"></i> {counts.get(slug,0)} غرفة</span><strong style="color:var(--primary)">دخول</strong></div>
          </a>
        ''')
    content = f'<div class="card"><div class="section-head"><div><h3>المحافظات العراقية</h3><p>اختر محافظة لعرض الغرف داخلها</p></div></div><div class="province-grid">{"".join(cards)}</div></div>'
    return render_page('المحافظات', content, subtitle='أقسام رئيسية للمحافظات', active='provinces')


@app.route('/provinces/<province_slug>', methods=['GET', 'POST'])
def province_rooms(province_slug):
    # صفحة عرض الغرف عامة. إنشاء الغرف يحتاج مشرف فقط.
    user = user_obj()
    if province_slug not in PROVINCE_MAP:
        flash('المحافظة غير موجودة.')
        return redirect(url_for('provinces'))
    conn = db()
    if request.method == 'POST':
        if not has_perm(user, 'create_rooms'):
            conn.close()
            flash('لا تملك صلاحية إنشاء الغرف.')
            return redirect(url_for('province_rooms', province_slug=province_slug))
        name = request.form.get('room_name', '').strip()
        if not name:
            conn.close()
            flash('اكتب اسم الغرفة.')
            return redirect(url_for('province_rooms', province_slug=province_slug))
        conn.execute('INSERT INTO subrooms (province_slug, name, created_by, created_at) VALUES (?, ?, ?, ?)', (province_slug, name, user['name'], now()))
        conn.commit()
        flash('تم إنشاء الغرفة: ' + name)
        return redirect(url_for('province_rooms', province_slug=province_slug))

    rooms = conn.execute('SELECT * FROM subrooms WHERE province_slug=? ORDER BY id DESC', (province_slug,)).fetchall()
    counts = {r['room_id']: r['c'] for r in conn.execute("SELECT room_id, COUNT(*) AS c FROM room_members WHERE role != 'owner' GROUP BY room_id").fetchall()}
    conn.close()
    create_box = ''
    if has_perm(user, 'create_rooms'):
        create_box = f'''
          <div class="card" style="margin-bottom:16px">
            <div class="section-head">
              <div><h3>إنشاء الغرف من لوحة المشرف</h3><p>لإنشاء غرفة جديدة داخل أي محافظة مع مشرفها وصلاحياته، افتح لوحة المشرف.</p></div>
              <a class="btn" href="{url_for('admin_panel')}"><i class="ri-shield-star-line"></i> لوحة المشرف</a>
            </div>
          </div>
        '''
    cards = []
    for room in rooms:
        current = counts.get(room['id'], 0)
        full = current >= ROOM_CAPACITY
        delete_btn = ''
        if has_perm(user, 'delete_rooms'):
            delete_btn = f'<form method="post" action="{url_for("delete_room", room_id=room["id"])}" onsubmit="return confirm(\'حذف الغرفة؟\')"><button class="btn-danger" type="submit"><i class="ri-delete-bin-line"></i> حذف</button></form>'
        action = f'<a class="btn" href="{url_for("enter_room", room_id=room["id"])}"><i class="ri-login-circle-line"></i> دخول</a>' if not full else '<span class="badge badge-danger"><i class="ri-lock-line"></i> ممتلئة</span>'
        cards.append(f'''
          <div class="room-card">
            <div class="city-icon"><i class="ri-chat-smile-3-line"></i></div>
            <h3>{esc(room['name'])}</h3>
            <div class="muted">أنشأها: {esc(room['created_by'])} • {esc(room['created_at']).replace('T',' ')[:16]}</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:12px">
              <span class="badge {'badge-danger' if full else 'badge-success'}"><i class="ri-team-line"></i> {current}/{ROOM_CAPACITY}</span>
              {action}
              {delete_btn}
            </div>
          </div>
        ''')
    content = f'''
      {create_box}
      <div class="card">
        <div class="section-head"><div><h3>غرف محافظة {esc(PROVINCE_MAP[province_slug])}</h3><p>الغرف التي أنشأها المشرف داخل هذه المحافظة</p></div><a class="btn-light" href="{url_for('provinces')}"><i class="ri-arrow-right-line"></i> رجوع</a></div>
        <div class="room-grid">{''.join(cards) if cards else '<div class="empty">لا توجد غرف بعد. المشرف يستطيع إنشاء أول غرفة.</div>'}</div>
      </div>
    '''
    return render_page(PROVINCE_MAP[province_slug], content, subtitle='غرف فرعية داخل المحافظة', active='provinces')


@app.route('/rooms/<int:room_id>/enter', methods=['GET', 'POST'])
def enter_room(room_id):
    # دخول الغرفة: إذا لا توجد جلسة، تظهر صفحة اختيار زائر/مشرف.
    cleanup_expired_restrictions()
    conn = db()
    room = conn.execute('SELECT * FROM subrooms WHERE id=?', (room_id,)).fetchone()
    if not room:
        conn.close()
        flash('الغرفة غير موجودة.')
        return redirect(url_for('provinces'))

    user = user_obj()
    needs_entry_form = user is None or session.get('guest_needs_name') == '1'

    if needs_entry_form:
        if request.method == 'POST':
            entry_role = request.form.get('entry_role', 'visitor').strip()
            name = request.form.get('display_name', '').strip()
            password = request.form.get('admin_password', '')

            if not name:
                conn.close()
                flash('اكتب اسم المستخدم حتى تدخل الغرفة.')
                return redirect(url_for('enter_room', room_id=room_id))

            # امسح أي جلسة قديمة قبل الدخول الجديد
            old_sid = session.get('sid')
            if old_sid:
                conn.execute('DELETE FROM room_members WHERE session_id=?', (old_sid,))
                conn.commit()
            session.clear()

            if entry_role == 'visitor':
                session['display_name'] = name
                session['role'] = 'visitor'
                session['permissions'] = ''
                session['sid'] = str(uuid.uuid4())
                session['ip_address'] = get_client_ip()
                conn.close()
                flash('تم دخولك كزائر: ' + name)
                return redirect(url_for('enter_room', room_id=room_id))

            if entry_role == 'admin':
                if not password:
                    conn.close()
                    flash('اكتب رمز المشرف.')
                    return redirect(url_for('enter_room', room_id=room_id))

                if name == OWNER_NAME and password == OWNER_PASSWORD:
                    session['display_name'] = name
                    session['role'] = 'owner'
                    session['permissions'] = ','.join(ALL_PERMISSIONS)
                    session['sid'] = str(uuid.uuid4())
                    session['ip_address'] = get_client_ip()
                    conn.close()
                    flash('تم دخول صاحب البرنامج.')
                    return redirect(url_for('enter_room', room_id=room_id))

                admin = conn.execute('SELECT * FROM admins WHERE username=? AND is_owner=0', (name,)).fetchone()
                if not admin or not check_password_hash(admin['password_hash'], password):
                    conn.close()
                    flash('اسم المشرف أو الرمز غير صحيح.')
                    return redirect(url_for('enter_room', room_id=room_id))

                session['display_name'] = name
                session['role'] = 'admin'
                session['permissions'] = admin['permissions'] or ''
                session['sid'] = str(uuid.uuid4())
                session['ip_address'] = get_client_ip()
                conn.close()
                flash('تم دخولك كمشرف: ' + name)
                return redirect(url_for('enter_room', room_id=room_id))

            conn.close()
            flash('نوع الدخول غير صحيح.')
            return redirect(url_for('enter_room', room_id=room_id))

        conn.close()
        content = f"""
          <div class="card hero" style="margin-bottom:16px">
            <h1>دخول الغرفة</h1>
            <p>أنت تدخل غرفة: <strong>{esc(room['name'])}</strong>. اختر زائر أو مشرف.</p>
          </div>
          <div class="card">
            <div class="section-head"><div><h3>اختر نوع الدخول</h3><p>الزائر يدخل باسم فقط، والمشرف يدخل باسمه ورمزه.</p></div></div>
            <form method="post">
              <div class="field"><label>اسم المستخدم</label><input name="display_name" placeholder="مثال: هشام"></div>
              <div class="role-box">
                <label class="role-choice"><input type="radio" name="entry_role" value="visitor" checked onchange="toggleAdminPass(false)"><span><i class="ri-user-smile-line"></i> زائر</span></label>
                <label class="role-choice"><input type="radio" name="entry_role" value="admin" onchange="toggleAdminPass(true)"><span><i class="ri-shield-user-line"></i> مشرف</span></label>
              </div>
              <div class="field" id="admin-pass-box" style="display:none"><label>رمز المشرف</label><input type="password" name="admin_password" placeholder="اكتب رمز المشرف"></div>
              <button type="submit"><i class="ri-login-circle-line"></i> دخول الغرفة</button>
            </form>
          </div>
          <script>
          function toggleAdminPass(show){{
            document.getElementById('admin-pass-box').style.display = show ? 'block' : 'none';
          }}
          </script>
        """
        return render_page('دخول الغرفة', content, subtitle='زائر أو مشرف', auth_page=True)

    user, resp = require_entry()
    if resp:
        conn.close()
        return resp

    if user['role'] == 'owner':
        conn.close()
        return redirect(url_for('room_chat', room_id=room_id))

    exists = conn.execute('SELECT id FROM room_members WHERE room_id=? AND session_id=?', (room_id, user['sid'])).fetchone()
    count = conn.execute("SELECT COUNT(*) AS c FROM room_members WHERE room_id=? AND role != 'owner'", (room_id,)).fetchone()['c']
    if not exists and count >= ROOM_CAPACITY:
        conn.close()
        flash('الغرفة ممتلئة، الحد الأقصى 50 شخص.')
        return redirect(url_for('province_rooms', province_slug=room['province_slug']))
    if not exists:
        conn.execute('INSERT INTO room_members (room_id, session_id, display_name, role, joined_at, ip_address) VALUES (?, ?, ?, ?, ?, ?)', (room_id, user['sid'], user['name'], user['role'], now(), get_client_ip()))
        conn.commit()
    conn.close()
    return redirect(url_for('room_chat', room_id=room_id))


@app.route('/rooms/<int:room_id>', methods=['GET', 'POST'])
def room_chat(room_id):
    user, resp = require_entry()
    if resp:
        return resp
    conn = db()
    room = conn.execute('SELECT * FROM subrooms WHERE id=?', (room_id,)).fetchone()
    if not room:
        conn.close()
        flash('الغرفة غير موجودة.')
        return redirect(url_for('provinces'))
    member = conn.execute('SELECT * FROM room_members WHERE room_id=? AND session_id=?', (room_id, user['sid'])).fetchone()
    if not member and user['role'] != 'owner':
        conn.close()
        return redirect(url_for('enter_room', room_id=room_id))
    if request.method == 'POST':
        muted = None if user['role'] == 'owner' else conn.execute('SELECT * FROM muted_members WHERE room_id=? AND session_id=?', (room_id, user['sid'])).fetchone()
        if muted:
            conn.close()
            flash('أنت مكتوم داخل هذه الغرفة ولا يمكنك إرسال رسائل الآن.')
            return redirect(url_for('room_chat', room_id=room_id))
        text = request.form.get('text', '').strip()
        if text:
            conn.execute('INSERT INTO room_messages (room_id, session_id, display_name, role, text, created_at) VALUES (?, ?, ?, ?, ?, ?)', (room_id, user['sid'], user['name'], user['role'], text, now()))
            conn.commit()
            conn.close()
            return redirect(url_for('room_chat', room_id=room_id))
        flash('لا يمكن إرسال رسالة فارغة.')
    msgs = conn.execute('SELECT * FROM room_messages WHERE room_id=? ORDER BY id ASC', (room_id,)).fetchall()
    members = conn.execute("SELECT * FROM room_members WHERE room_id=? AND role != 'owner' ORDER BY id DESC", (room_id,)).fetchall()
    conn.close()
    msg_html = []
    for m in msgs:
        mine = m['session_id'] == user['sid']
        delete_msg = ''
        if has_perm(user, 'delete_messages'):
            delete_msg = '<form method="post" action="{}" style="margin-top:8px"><button class="btn-danger" type="submit"><i class="ri-delete-bin-line"></i> حذف الرسالة</button></form>'.format(url_for('delete_message', message_id=m['id']))
        role_badge = 'مشرف أساسي' if m['role'] == 'owner' else ('مشرف' if m['role'] == 'admin' else 'زائر')
        role_name_class = 'role-name-owner' if m['role'] == 'owner' else ('role-name-admin' if m['role'] == 'admin' else 'role-name-visitor')
        badge_class = 'badge-owner' if m['role'] == 'owner' else ('badge-admin' if m['role'] == 'admin' else '')
        msg_html.append(f'''
          <div class="msg {'me' if mine else 'other'}"><div class="bubble">
            <div style="font-weight:900;margin-bottom:4px"><span class="{role_name_class}">{esc(m['display_name'])}</span> <span class="badge {badge_class}">{role_badge}</span></div>
            <div>{esc(m['text'])}</div><div class="meta">{esc(m['created_at']).replace('T',' ')[:16]}</div>{delete_msg}
          </div></div>
        ''')
    member_parts = []
    for x in members:
        controls = ''
        if is_admin_user(user) and x['session_id'] != user['sid']:
            if has_perm(user, 'kick_members'):
                controls += '<form method="post" action="{}"><button class="btn-warning" type="submit"><i class="ri-logout-circle-line"></i> طرد</button></form>'.format(url_for('kick_member', member_id=x['id']))
            if has_perm(user, 'mute_members'):
                controls += '<form method="post" action="{}" style="display:flex;gap:6px;flex-wrap:wrap"><input name="minutes" value="60" style="width:90px;padding:9px"><button class="btn-soft" type="submit"><i class="ri-volume-mute-line"></i> كتم</button></form>'.format(url_for('mute_member', member_id=x['id']))
            if has_perm(user, 'temp_ban'):
                controls += '<form method="post" action="{}" style="display:flex;gap:6px;flex-wrap:wrap"><input type="hidden" name="ban_type" value="temporary"><input name="minutes" value="60" style="width:90px;padding:9px"><button class="btn-warning" type="submit"><i class="ri-timer-line"></i> حظر مؤقت</button></form>'.format(url_for('ban_member', member_id=x['id']))
            if has_perm(user, 'permanent_ban'):
                controls += '<form method="post" action="{}"><input type="hidden" name="ban_type" value="permanent"><button class="btn-danger" type="submit"><i class="ri-forbid-line"></i> حظر دائم</button></form>'.format(url_for('ban_member', member_id=x['id']))
            if has_perm(user, 'ip_ban'):
                controls += '<form method="post" action="{}" style="display:flex;gap:6px;flex-wrap:wrap"><input type="hidden" name="ban_type" value="ip"><input name="minutes" value="1440" style="width:90px;padding:9px"><button class="btn-danger" type="submit"><i class="ri-router-line"></i> حظر IP</button></form>'.format(url_for('ban_member', member_id=x['id']))
        role_text = 'مشرف أساسي' if x['role'] == 'owner' else ('مشرف' if x['role'] == 'admin' else 'زائر')
        role_name_class = 'role-name-owner' if x['role'] == 'owner' else ('role-name-admin' if x['role'] == 'admin' else 'role-name-visitor')
        role_badge_class = 'badge-owner' if x['role'] == 'owner' else ('badge-admin' if x['role'] == 'admin' else '')
        member_parts.append(f'<div class="item"><div class="item-main"><div class="avatar">{esc(x["display_name"][:1])}</div><div><h4 class="{role_name_class}">{esc(x["display_name"])}</h4><div class="muted"><span class="badge {role_badge_class}">{role_text}</span> • IP: {esc(x["ip_address"] or "-")}</div></div></div><div style="display:flex;gap:6px;flex-wrap:wrap">{controls}</div></div>')
    member_html = ''.join(member_parts)
    content = f'''
      <div class="chat-layout">
        <div class="card">
          <div class="section-head"><div><h3>{esc(room['name'])}</h3><p>محافظة {esc(PROVINCE_MAP.get(room['province_slug'], room['province_slug']))} • الموجودين {len(members)}/{ROOM_CAPACITY}</p></div><div style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn-light" href="{url_for('province_rooms', province_slug=room['province_slug'])}"><i class="ri-arrow-right-line"></i> رجوع</a>{'<form method="post" action="'+url_for('clear_room', room_id=room_id)+'"><button class="btn-warning" type="submit"><i class="ri-brush-line"></i> إفراغ الغرفة</button></form>' if has_perm(user, 'clear_rooms') else ''}<a class="btn-danger" href="{url_for('leave_room', room_id=room_id)}"><i class="ri-logout-circle-line"></i> مغادرة</a></div></div>
          <div class="chat-box" id="messages-box" data-room-id="{room_id}">{''.join(msg_html) if msg_html else '<div class="empty">لا توجد رسائل بعد داخل هذه الغرفة.</div>'}</div>
          <script>
          (function() {{
            const box = document.getElementById('messages-box');
            if (!box) return;
            let lastHtml = box.innerHTML;
            let userScrolling = false;
            function isNearBottom() {{
              return box.scrollHeight - box.scrollTop - box.clientHeight < 80;
            }}
            box.addEventListener('scroll', function() {{
              userScrolling = !isNearBottom();
            }});
            async function refreshMessages() {{
              try {{
                const res = await fetch('/rooms/{room_id}/messages-fragment', {{cache: 'no-store'}});
                if (!res.ok) return;
                const data = await res.json();
                if (data.html && data.html !== lastHtml) {{
                  const keepBottom = isNearBottom() && !userScrolling;
                  box.innerHTML = data.html;
                  lastHtml = data.html;
                  if (keepBottom) box.scrollTop = box.scrollHeight;
                }}
              }} catch (e) {{}}
            }}
            box.scrollTop = box.scrollHeight;
            setInterval(refreshMessages, 1000);
          }})();
          </script>
          <form method="post" style="margin-top:14px">
            <div class="field"><label>رسالتك</label><textarea name="text" rows="4" placeholder="اكتب رسالتك هنا..."></textarea></div>
            <button type="submit"><i class="ri-send-plane-fill"></i> إرسال</button>
          </form>
        </div>
        <div class="card"><div class="section-head"><div><h3>أعضاء الغرفة</h3><p>{len(members)} من {ROOM_CAPACITY}</p></div></div><div class="list">{member_html if member_html else '<div class="empty">لا يوجد أعضاء.</div>'}</div></div>
      </div>
    '''
    return render_page(room['name'], content, subtitle='شات غرفة فرعية', active='provinces')


@app.route('/rooms/<int:room_id>/messages-fragment')
def room_messages_fragment(room_id):
    user, resp = require_entry()
    if resp:
        return jsonify({'html': ''}), 401
    conn = db()
    room = conn.execute('SELECT * FROM subrooms WHERE id=?', (room_id,)).fetchone()
    if not room:
        conn.close()
        return jsonify({'html': '<div class="empty">الغرفة غير موجودة.</div>'}), 404
    member = conn.execute('SELECT * FROM room_members WHERE room_id=? AND session_id=?', (room_id, user['sid'])).fetchone()
    if not member and user['role'] != 'owner':
        conn.close()
        return jsonify({'html': '<div class="empty">يجب دخول الغرفة أولاً.</div>'}), 403
    msgs = conn.execute('SELECT * FROM room_messages WHERE room_id=? ORDER BY id ASC', (room_id,)).fetchall()
    conn.close()
    msg_html = []
    for m in msgs:
        mine = m['session_id'] == user['sid']
        delete_msg = ''
        if has_perm(user, 'delete_messages'):
            delete_msg = '<form method="post" action="{}" style="margin-top:8px"><button class="btn-danger" type="submit"><i class="ri-delete-bin-line"></i> حذف الرسالة</button></form>'.format(url_for('delete_message', message_id=m['id']))
        role_badge = 'مشرف أساسي' if m['role'] == 'owner' else ('مشرف' if m['role'] == 'admin' else 'زائر')
        role_name_class = 'role-name-owner' if m['role'] == 'owner' else ('role-name-admin' if m['role'] == 'admin' else 'role-name-visitor')
        badge_class = 'badge-owner' if m['role'] == 'owner' else ('badge-admin' if m['role'] == 'admin' else '')
        msg_html.append(f"""
          <div class="msg {'me' if mine else 'other'}"><div class="bubble">
            <div style="font-weight:900;margin-bottom:4px"><span class="{role_name_class}">{esc(m['display_name'])}</span> <span class="badge {badge_class}">{role_badge}</span></div>
            <div>{esc(m['text'])}</div><div class="meta">{esc(m['created_at']).replace('T',' ')[:16]}</div>{delete_msg}
          </div></div>
        """)
    html_content = ''.join(msg_html) if msg_html else '<div class="empty">لا توجد رسائل بعد داخل هذه الغرفة.</div>'
    return jsonify({'html': html_content})


@app.route('/rooms/<int:room_id>/leave')
def leave_room(room_id):
    user, resp = require_entry()
    if resp:
        return resp
    conn = db()
    room = conn.execute('SELECT * FROM subrooms WHERE id=?', (room_id,)).fetchone()
    conn.execute('DELETE FROM room_members WHERE room_id=? AND session_id=?', (room_id, user['sid']))
    conn.commit()
    conn.close()
    flash('تمت مغادرة الغرفة.')
    if room:
        return redirect(url_for('province_rooms', province_slug=room['province_slug']))
    return redirect(url_for('provinces'))


@app.route('/rooms/<int:room_id>/delete', methods=['POST'])
def delete_room(room_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'delete_rooms'):
        flash('لا تملك صلاحية حذف الغرف.')
        return redirect(url_for('provinces'))
    conn = db()
    room = conn.execute('SELECT * FROM subrooms WHERE id=?', (room_id,)).fetchone()
    if not room:
        conn.close()
        flash('الغرفة غير موجودة.')
        return redirect(url_for('provinces'))
    province_slug = room['province_slug']
    conn.execute('DELETE FROM room_messages WHERE room_id=?', (room_id,))
    conn.execute('DELETE FROM room_members WHERE room_id=?', (room_id,))
    conn.execute('DELETE FROM muted_members WHERE room_id=?', (room_id,))
    conn.execute('DELETE FROM subrooms WHERE id=?', (room_id,))
    conn.commit()
    conn.close()
    flash('تم حذف الغرفة.')
    return redirect(url_for('province_rooms', province_slug=province_slug))


@app.route('/admin')
def admin_panel():
    user, resp = require_entry()
    if resp:
        return resp
    if not is_admin_user(user) or not has_perm(user, 'view_admin_panel'):
        flash('هذه الصفحة تحتاج صلاحية دخول لوحة المشرف.')
        return redirect(url_for('dashboard'))
    conn = db()
    rooms = conn.execute('SELECT * FROM subrooms ORDER BY id DESC').fetchall()
    admins = conn.execute('SELECT * FROM admins WHERE is_owner=0 AND username != ? ORDER BY id DESC', (OWNER_NAME,)).fetchall()
    members = conn.execute('''SELECT rm.*, sr.name AS room_name, sr.province_slug
                              FROM room_members rm
                              JOIN subrooms sr ON sr.id = rm.room_id
                              WHERE rm.role != 'owner'
                              ORDER BY rm.id DESC LIMIT 80''').fetchall()
    user_bans = conn.execute('SELECT * FROM user_bans ORDER BY id DESC LIMIT 80').fetchall()
    ip_bans = conn.execute('SELECT * FROM ip_bans ORDER BY id DESC LIMIT 80').fetchall()
    actions = conn.execute('SELECT * FROM moderation_actions ORDER BY id DESC LIMIT 50').fetchall()
    conn.close()

    room_items = []
    for r in rooms:
        delete_form = ''
        if has_perm(user, 'delete_rooms'):
            delete_form = f'<form method="post" action="{url_for("delete_room", room_id=r["id"])}"><button class="btn-danger"><i class="ri-delete-bin-line"></i> حذف</button></form>'
        room_items.append(f'<div class="item"><div class="item-main"><div class="avatar"><i class="ri-chat-3-line"></i></div><div><h4>{esc(r["name"])}</h4><div class="muted">{esc(PROVINCE_MAP.get(r["province_slug"], r["province_slug"]))} • {esc(r["created_at"]).replace("T"," ")[:16]}</div></div></div>{delete_form}</div>')
    rooms_html = ''.join(room_items) if room_items else '<div class="empty">لا توجد غرف حاليًا.</div>'

    admin_items = []
    for a in admins:
        labels = []
        for perm in (a['permissions'] or '').split(','):
            if perm:
                labels.append(f'<span class="badge"><i class="ri-key-2-line"></i> {PERMISSION_LABELS.get(perm, perm)}</span>')
        role_badge = '<span class="badge badge-warning"><i class="ri-vip-crown-fill"></i> صاحب البرنامج</span>' if a['is_owner'] else '<span class="badge"><i class="ri-shield-user-line"></i> مشرف</span>'
        admin_actions = ''
        if not a['is_owner'] and has_perm(user, 'reset_admin_passwords'):
            admin_actions += (
                '<form method="post" action="{}" style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">'
                '<input type="password" name="new_password" placeholder="رمز جديد" style="width:130px;padding:8px">'
                '<button class="btn-warning" type="submit"><i class="ri-key-2-line"></i> تغيير الرمز</button>'
                '</form>'
            ).format(url_for('reset_admin_password', admin_id=a['id']))
        if not a['is_owner'] and has_perm(user, 'manage_admins'):
            admin_actions += f'<form method="post" action="{url_for("delete_admin", admin_id=a["id"])}"><button class="btn-danger" type="submit"><i class="ri-delete-bin-line"></i> حذف</button></form>'
        admin_items.append(f'<div class="item"><div class="item-main"><div class="avatar"><i class="ri-shield-star-line"></i></div><div><h4>{esc(a["username"])}</h4><div class="muted">أنشأه: {esc(a["created_by"])} • {esc(a["created_at"]).replace("T"," ")[:16]}</div><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">{role_badge}{"".join(labels)}</div></div></div><div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end">{admin_actions}</div></div>')
    admins_html = ''.join(admin_items) if admin_items else '<div class="empty">لا يوجد مشرفون.</div>'

    member_items = []
    for m in members:
        controls = ''
        if has_perm(user, 'kick_members'):
            controls += '<form method="post" action="{}"><button class="btn-warning" type="submit"><i class="ri-logout-circle-line"></i> طرد</button></form>'.format(url_for('kick_member', member_id=m['id']))
        if has_perm(user, 'mute_members'):
            controls += '<form method="post" action="{}" style="display:flex;gap:6px;flex-wrap:wrap"><input name="minutes" value="60" style="width:80px;padding:8px"><button class="btn-soft" type="submit">كتم</button></form>'.format(url_for('mute_member', member_id=m['id']))
        if has_perm(user, 'temp_ban'):
            controls += '<form method="post" action="{}" style="display:flex;gap:6px;flex-wrap:wrap"><input type="hidden" name="ban_type" value="temporary"><input name="minutes" value="60" style="width:80px;padding:8px"><button class="btn-warning" type="submit">حظر مؤقت</button></form>'.format(url_for('ban_member', member_id=m['id']))
        if has_perm(user, 'permanent_ban'):
            controls += '<form method="post" action="{}"><input type="hidden" name="ban_type" value="permanent"><button class="btn-danger" type="submit">حظر دائم</button></form>'.format(url_for('ban_member', member_id=m['id']))
        if has_perm(user, 'ip_ban'):
            controls += '<form method="post" action="{}" style="display:flex;gap:6px;flex-wrap:wrap"><input type="hidden" name="ban_type" value="ip"><input name="minutes" value="1440" style="width:80px;padding:8px"><button class="btn-danger" type="submit">حظر IP</button></form>'.format(url_for('ban_member', member_id=m['id']))
        controls += lower_admin_form_for_member(user, m['id'], m['display_name'])
        role_name_class = 'role-name-owner' if m['role'] == 'owner' else ('role-name-admin' if m['role'] == 'admin' else 'role-name-visitor')
        role_text = 'مشرف أساسي' if m['role'] == 'owner' else ('مشرف' if m['role'] == 'admin' else 'زائر')
        member_items.append(f'<div class="item"><div class="item-main"><div class="avatar">{esc(m["display_name"][:1])}</div><div><h4 class="{role_name_class}">{esc(m["display_name"])}</h4><div class="muted">{role_text} • {esc(m["room_name"])} • {esc(PROVINCE_MAP.get(m["province_slug"], m["province_slug"]))} • IP: {esc(m["ip_address"] or "-")}</div></div></div><div style="display:flex;gap:6px;flex-wrap:wrap">{controls}</div></div>')
    members_html = ''.join(member_items) if member_items else '<div class="empty">لا يوجد أعضاء داخل الغرف الآن.</div>'

    ban_items = []
    for b in user_bans:
        unban = '<form method="post" action="{}"><button class="btn-success" type="submit"><i class="ri-lock-unlock-line"></i> فك</button></form>'.format(url_for('unban_user', ban_id=b['id'])) if has_perm(user, 'unban_users') else ''
        expire_text = ('دائم' if not b['expires_at'] else 'إلى ' + esc(b['expires_at'].replace('T',' ')))
        ban_items.append(f'<div class="item"><div class="item-main"><div class="avatar"><i class="ri-forbid-line"></i></div><div><h4>{esc(b["display_name"] or b["session_id"] or "زائر")}</h4><div class="muted">{esc(b["ban_type"])} • {expire_text} • {esc(b["reason"])}</div></div></div>{unban}</div>')
    for b in ip_bans:
        unban = '<form method="post" action="{}"><button class="btn-success" type="submit"><i class="ri-lock-unlock-line"></i> فك IP</button></form>'.format(url_for('unban_ip', ban_id=b['id'])) if has_perm(user, 'unban_users') else ''
        expire_text = ('دائم' if not b['expires_at'] else 'إلى ' + esc(b['expires_at'].replace('T',' ')))
        ban_items.append(f'<div class="item"><div class="item-main"><div class="avatar"><i class="ri-router-line"></i></div><div><h4>IP: {esc(b["ip_address"])}</h4><div class="muted">{expire_text} • {esc(b["reason"])}</div></div></div>{unban}</div>')
    bans_html = ''.join(ban_items) if ban_items else '<div class="empty">لا توجد حالات حظر حاليًا.</div>'

    log_html = ''.join([f'<div class="item"><div class="item-main"><div class="avatar"><i class="ri-history-line"></i></div><div><h4>{esc(a["action"])}</h4><div class="muted">بواسطة {esc(a["actor_name"])} → {esc(a["target_name"])} • {esc(a["created_at"]).replace("T"," ")[:16]}<br>{esc(a["note"])}</div></div></div></div>' for a in actions]) or '<div class="empty">لا يوجد سجل بعد.</div>'

    create_room_admin_box = ''
    allowed = permissions_for_form(user)
    if has_perm(user, 'create_rooms'):
        province_options = ''.join([f'<option value="{slug}">{name}</option>' for slug, name in IRAQI_PROVINCES])
        checks = ''.join([f'<label class="role-choice"><input type="checkbox" name="permissions" value="{p}"><span><i class="ri-checkbox-circle-line"></i> {PERMISSION_LABELS[p]}</span></label>' for p in allowed])
        create_room_admin_box = f'''
          <div class="card" style="margin-bottom:16px">
            <div class="section-head">
              <div>
                <h3>إنشاء غرفة مع مشرفها</h3>
                <p>اختَر المحافظة، اكتب اسم الغرفة، وأنشئ معها مشرفًا بصلاحيات محددة.</p>
              </div>
            </div>
            <form method="post" action="{url_for('admin_create_room_with_supervisor')}">
              <div class="grid">
                <div class="col-6"><div class="field"><label>المحافظة</label><select name="province_slug">{province_options}</select></div></div>
                <div class="col-6"><div class="field"><label>اسم الغرفة</label><input name="room_name" placeholder="مثال: محادثة ابن الغزالية"></div></div>
                <div class="col-6"><div class="field"><label>اسم مشرف الغرفة</label><input name="admin_username" placeholder="مثال: مشرف الغزالية"></div></div>
                <div class="col-6"><div class="field"><label>رمز مشرف الغرفة</label><input type="password" name="admin_password" placeholder="رمز سري للمشرف"></div></div>
              </div>
              <label>صلاحيات مشرف الغرفة</label>
              <div class="role-box" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">{checks}</div>
              <button type="submit"><i class="ri-add-circle-line"></i> إنشاء الغرفة والمشرف</button>
            </form>
          </div>
        '''

    create_admin_box = ''
    if has_perm(user, 'manage_admins'):
        admin_checks = ''.join([f'<label class="role-choice"><input type="checkbox" name="permissions" value="{p}"><span><i class="ri-checkbox-circle-line"></i> {PERMISSION_LABELS[p]}</span></label>' for p in allowed])
        create_admin_box = f'''
          <div class="card" style="margin-bottom:16px">
            <div class="section-head">
              <div>
                <h3>إنشاء مشرف أقل صلاحية</h3>
                <p>المشرف الحالي يستطيع إعطاء صلاحيات يملكها فقط. لا يمكنه إعطاء صلاحية أعلى منه.</p>
              </div>
            </div>
            <form method="post" action="{url_for('create_admin')}">
              <div class="grid">
                <div class="col-6"><div class="field"><label>اسم المشرف الجديد</label><input name="username" placeholder="مثال: مشرف مساعد"></div></div>
                <div class="col-6"><div class="field"><label>رمز المشرف الجديد</label><input type="password" name="password" placeholder="رمز سري"></div></div>
              </div>
              <label>صلاحيات المشرف الجديد</label>
              <div class="role-box" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">{admin_checks}</div>
              <button type="submit"><i class="ri-user-add-line"></i> إنشاء مشرف أقل صلاحية</button>
            </form>
          </div>
        '''

    content = (
        create_room_admin_box +
        create_admin_box +
        '<div class="grid">'
        '<div class="col-6"><div class="card"><div class="section-head"><div><h3>المشرفون والصلاحيات</h3><p>إدارة المشرفين حسب الرتبة</p></div></div><div class="list">' + admins_html + '</div></div></div>'
        '<div class="col-6"><div class="card"><div class="section-head"><div><h3>الغرف</h3><p>إدارة الغرف حسب صلاحياتك</p></div></div><div class="list">' + rooms_html + '</div></div></div>'
        '<div class="col-12"><div class="card"><div class="section-head"><div><h3>الأعضاء داخل الغرف الآن</h3><p>طرد، حظر مؤقت، حظر دائم، حظر IP، وكتم</p></div></div><div class="list">' + members_html + '</div></div></div>'
        '<div class="col-6"><div class="card"><div class="section-head"><div><h3>الحظر النشط</h3><p>حظر أسماء، جلسات، و IP</p></div></div><div class="list">' + bans_html + '</div></div></div>'
        '<div class="col-6"><div class="card"><div class="section-head"><div><h3>سجل الإجراءات</h3><p>آخر عمليات الإشراف</p></div></div><div class="list">' + log_html + '</div></div></div>'
        '</div>'
    )
    return render_page('لوحة المشرف', content, subtitle='صلاحيات المشرفين والغرف', active='admin')


@app.route('/admin/create-room-with-supervisor', methods=['POST'])
def admin_create_room_with_supervisor():
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'create_rooms'):
        flash('لا تملك صلاحية إنشاء الغرف.')
        return redirect(url_for('admin_panel'))

    province_slug = request.form.get('province_slug', '').strip()
    room_name = request.form.get('room_name', '').strip()
    admin_username = request.form.get('admin_username', '').strip()
    admin_password = request.form.get('admin_password', '')
    requested = request.form.getlist('permissions')
    allowed = set(permissions_for_form(user))
    selected = [p for p in requested if p in allowed and p != 'manage_admins']

    if province_slug not in PROVINCE_MAP:
        flash('اختَر محافظة صحيحة.')
        return redirect(url_for('admin_panel'))
    if not room_name:
        flash('اكتب اسم الغرفة.')
        return redirect(url_for('admin_panel'))
    if not admin_username or not admin_password:
        flash('اكتب اسم مشرف الغرفة ورمزه السري.')
        return redirect(url_for('admin_panel'))

    conn = db()
    existing_admin = conn.execute('SELECT id FROM admins WHERE username=?', (admin_username,)).fetchone()
    if existing_admin:
        conn.close()
        flash('اسم مشرف الغرفة موجود مسبقًا، اختر اسمًا آخر.')
        return redirect(url_for('admin_panel'))

    conn.execute('INSERT INTO subrooms (province_slug, name, created_by, created_at) VALUES (?, ?, ?, ?)',
                 (province_slug, room_name, user['name'], now()))
    room_id = conn.execute('SELECT last_insert_rowid() AS id').fetchone()['id']

    conn.execute('INSERT INTO admins (username, password_hash, is_owner, permissions, created_by, created_at) VALUES (?, ?, 0, ?, ?, ?)',
                 (admin_username, generate_password_hash(admin_password), ','.join(selected), user['name'], now()))

    add_log('إنشاء غرفة مع مشرف', admin_username, room_id, 'الغرفة: ' + room_name + ' / المحافظة: ' + PROVINCE_MAP[province_slug], conn=conn)
    conn.close()
    flash('تم إنشاء الغرفة وإنشاء مشرفها بنجاح.')
    return redirect(url_for('admin_panel'))


@app.route('/admin/create', methods=['POST'])
def create_admin():
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'manage_admins'):
        flash('لا تملك صلاحية إنشاء مشرفين.')
        return redirect(url_for('admin_panel'))
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    requested = request.form.getlist('permissions')
    allowed = set(permissions_for_form(user))
    selected = [p for p in requested if p in allowed]
    if not username or not password:
        flash('اكتب اسم المشرف وكلمة المرور.')
        return redirect(url_for('admin_panel'))
    conn = db()
    exists = conn.execute('SELECT id FROM admins WHERE username=?', (username,)).fetchone()
    if exists:
        conn.close()
        flash('اسم المشرف موجود مسبقًا.')
        return redirect(url_for('admin_panel'))
    conn.execute('INSERT INTO admins (username, password_hash, is_owner, permissions, created_by, created_at) VALUES (?, ?, 0, ?, ?, ?)',
                 (username, generate_password_hash(password), ','.join(selected), user['name'], now()))
    conn.commit()
    conn.close()
    flash('تم إنشاء المشرف: ' + username)
    return redirect(url_for('admin_panel'))


@app.route('/admin/<int:admin_id>/reset-password', methods=['POST'])
def reset_admin_password(admin_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'reset_admin_passwords'):
        flash('لا تملك صلاحية تغيير رموز المشرفين.')
        return redirect(url_for('admin_panel'))
    new_password = request.form.get('new_password', '').strip()
    if len(new_password) < 4:
        flash('الرمز الجديد يجب أن يكون 4 أحرف أو أرقام على الأقل.')
        return redirect(url_for('admin_panel'))
    conn = db()
    target = conn.execute('SELECT * FROM admins WHERE id=?', (admin_id,)).fetchone()
    if not target:
        conn.close()
        flash('المشرف غير موجود.')
        return redirect(url_for('admin_panel'))
    if target['is_owner']:
        conn.close()
        flash('لا يمكن تغيير رمز صاحب البرنامج من هذه الصفحة.')
        return redirect(url_for('admin_panel'))
    conn.execute('UPDATE admins SET password_hash=? WHERE id=?', (generate_password_hash(new_password), admin_id))
    conn.commit()
    conn.close()
    add_log('تغيير رمز مشرف', target['username'], None, 'تم تغيير الرمز السري للمشرف بواسطة ' + user['name'])
    flash('تم تغيير الرمز السري للمشرف: ' + target['username'])
    return redirect(url_for('admin_panel'))


@app.route('/admin/<int:admin_id>/delete', methods=['POST'])
def delete_admin(admin_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'manage_admins'):
        flash('لا تملك صلاحية حذف المشرفين.')
        return redirect(url_for('admin_panel'))
    conn = db()
    target = conn.execute('SELECT * FROM admins WHERE id=?', (admin_id,)).fetchone()
    if not target:
        conn.close()
        flash('المشرف غير موجود.')
        return redirect(url_for('admin_panel'))
    if target['is_owner']:
        conn.close()
        flash('لا يمكن حذف المشرف الأساسي.')
        return redirect(url_for('admin_panel'))
    conn.execute('DELETE FROM admins WHERE id=?', (admin_id,))
    conn.commit()
    conn.close()
    flash('تم حذف المشرف.')
    return redirect(url_for('admin_panel'))



@app.route('/members/<int:member_id>/make-admin', methods=['POST'])
def make_member_admin(member_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'manage_admins'):
        flash('لا تملك صلاحية إنشاء مشرفين.')
        return redirect(request.referrer or url_for('admin_panel'))

    conn = db()
    member = conn.execute('SELECT rm.*, sr.name AS room_name, sr.province_slug FROM room_members rm JOIN subrooms sr ON sr.id=rm.room_id WHERE rm.id=?', (member_id,)).fetchone()
    if not member:
        conn.close()
        flash('العضو غير موجود داخل الغرفة.')
        return redirect(request.referrer or url_for('admin_panel'))
    if member['role'] == 'owner':
        conn.close()
        flash('لا يمكن تعديل صاحب البرنامج.')
        return redirect(request.referrer or url_for('admin_panel'))

    username = request.form.get('username', '').strip() or member['display_name'].strip()
    password = request.form.get('password', '')
    requested = request.form.getlist('permissions')
    allowed = set(permissions_for_form(user))
    selected = [p for p in requested if p in allowed]

    if not username or not password:
        conn.close()
        flash('اكتب اسم المشرف والرمز السري.')
        return redirect(request.referrer or url_for('admin_panel'))
    if not selected:
        conn.close()
        flash('اختَر صلاحية واحدة على الأقل للمشرف الجديد.')
        return redirect(request.referrer or url_for('admin_panel'))
    if username == OWNER_NAME:
        conn.close()
        flash('هذا الاسم مخصص لصاحب البرنامج.')
        return redirect(request.referrer or url_for('admin_panel'))

    exists = conn.execute('SELECT id FROM admins WHERE username=?', (username,)).fetchone()
    if exists:
        conn.close()
        flash('هذا الاسم موجود مسبقًا كمشرف. اختَر اسمًا آخر.')
        return redirect(request.referrer or url_for('admin_panel'))

    conn.execute('INSERT INTO admins (username, password_hash, is_owner, permissions, created_by, created_at) VALUES (?, ?, 0, ?, ?, ?)',
                 (username, generate_password_hash(password), ','.join(selected), user['name'], now()))
    # تحديث العضو الحالي في الغرفة حتى يظهر كمشرف فورًا.
    conn.execute('UPDATE room_members SET display_name=?, role=? WHERE id=?', (username, 'admin', member_id))
    conn.commit()
    conn.close()
    add_log('ترقية عضو إلى مشرف', username, member['room_id'], 'الغرفة: ' + member['room_name'])
    flash('تم إنشاء مشرف من العضو: ' + username)
    return redirect(request.referrer or url_for('admin_panel'))


@app.route('/members/<int:member_id>/kick', methods=['POST'])
def kick_member(member_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'kick_members'):
        flash('لا تملك صلاحية الطرد.')
        return redirect(url_for('admin_panel'))
    conn = db()
    member = conn.execute('SELECT * FROM room_members WHERE id=?', (member_id,)).fetchone()
    if not member:
        conn.close()
        flash('العضو غير موجود.')
        return redirect(url_for('admin_panel'))
    room_id = member['room_id']
    target = member['display_name']
    conn.execute('DELETE FROM room_members WHERE id=?', (member_id,))
    conn.commit()
    conn.close()
    add_log('طرد عضو', target, room_id, 'تم طرده من الغرفة')
    flash('تم طرد العضو: ' + target)
    return redirect(request.referrer or url_for('admin_panel'))


@app.route('/members/<int:member_id>/mute', methods=['POST'])
def mute_member(member_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'mute_members'):
        flash('لا تملك صلاحية الكتم.')
        return redirect(url_for('admin_panel'))
    minutes = parse_minutes(request.form.get('minutes'), 60)
    conn = db()
    member = conn.execute('SELECT * FROM room_members WHERE id=?', (member_id,)).fetchone()
    if not member:
        conn.close()
        flash('العضو غير موجود.')
        return redirect(url_for('admin_panel'))
    expires = expires_after_minutes(minutes)
    conn.execute('INSERT OR REPLACE INTO muted_members (room_id, session_id, display_name, reason, expires_at, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (member['room_id'], member['session_id'], member['display_name'], 'كتم بواسطة مشرف', expires, user['name'], now()))
    conn.commit()
    conn.close()
    add_log('كتم عضو', member['display_name'], member['room_id'], f'لمدة {minutes} دقيقة')
    flash('تم كتم العضو لمدة ' + str(minutes) + ' دقيقة.')
    return redirect(request.referrer or url_for('admin_panel'))


@app.route('/members/<int:member_id>/ban', methods=['POST'])
def ban_member(member_id):
    user, resp = require_entry()
    if resp:
        return resp
    ban_type = request.form.get('ban_type', 'temporary')
    if ban_type == 'permanent' and not has_perm(user, 'permanent_ban'):
        flash('لا تملك صلاحية الحظر الدائم.')
        return redirect(url_for('admin_panel'))
    if ban_type == 'temporary' and not has_perm(user, 'temp_ban'):
        flash('لا تملك صلاحية الحظر المؤقت.')
        return redirect(url_for('admin_panel'))
    if ban_type == 'ip' and not has_perm(user, 'ip_ban'):
        flash('لا تملك صلاحية حظر IP.')
        return redirect(url_for('admin_panel'))
    conn = db()
    member = conn.execute('SELECT * FROM room_members WHERE id=?', (member_id,)).fetchone()
    if not member:
        conn.close()
        flash('العضو غير موجود.')
        return redirect(url_for('admin_panel'))
    minutes = parse_minutes(request.form.get('minutes'), 1440)
    expires = '' if ban_type == 'permanent' else expires_after_minutes(minutes)
    if ban_type == 'ip':
        expires_ip = expires_after_minutes(minutes)
        ip = member['ip_address'] or ''
        if not ip:
            conn.close()
            flash('لا يوجد IP مسجل لهذا العضو.')
            return redirect(url_for('admin_panel'))
        conn.execute('INSERT INTO ip_bans (ip_address, reason, expires_at, created_by, created_at) VALUES (?, ?, ?, ?, ?)',
                     (ip, 'حظر IP بواسطة مشرف', expires_ip, user['name'], now()))
        action_note = f'IP {ip} لمدة {minutes} دقيقة'
    else:
        conn.execute('INSERT INTO user_bans (display_name, session_id, ip_address, ban_type, reason, expires_at, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                     (member['display_name'], member['session_id'], member['ip_address'] or '', ban_type, 'حظر بواسطة مشرف', expires, user['name'], now()))
        action_note = 'حظر دائم' if ban_type == 'permanent' else f'حظر مؤقت لمدة {minutes} دقيقة'
    conn.execute('DELETE FROM room_members WHERE session_id=?', (member['session_id'],))
    conn.commit()
    conn.close()
    add_log('حظر عضو', member['display_name'], member['room_id'], action_note)
    flash('تم تنفيذ الحظر على: ' + member['display_name'])
    return redirect(request.referrer or url_for('admin_panel'))


@app.route('/messages/<int:message_id>/delete', methods=['POST'])
def delete_message(message_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'delete_messages'):
        flash('لا تملك صلاحية حذف الرسائل.')
        return redirect(url_for('dashboard'))
    conn = db()
    msg = conn.execute('SELECT * FROM room_messages WHERE id=?', (message_id,)).fetchone()
    if not msg:
        conn.close()
        flash('الرسالة غير موجودة.')
        return redirect(request.referrer or url_for('dashboard'))
    room_id = msg['room_id']
    target = msg['display_name']
    conn.execute('DELETE FROM room_messages WHERE id=?', (message_id,))
    conn.commit()
    conn.close()
    add_log('حذف رسالة', target, room_id, 'تم حذف رسالة من الغرفة')
    flash('تم حذف الرسالة.')
    return redirect(request.referrer or url_for('room_chat', room_id=room_id))


@app.route('/rooms/<int:room_id>/clear', methods=['POST'])
def clear_room(room_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'clear_rooms'):
        flash('لا تملك صلاحية إفراغ الغرفة.')
        return redirect(url_for('room_chat', room_id=room_id))
    conn = db()
    room = conn.execute('SELECT * FROM subrooms WHERE id=?', (room_id,)).fetchone()
    if not room:
        conn.close()
        flash('الغرفة غير موجودة.')
        return redirect(url_for('provinces'))
    conn.execute('DELETE FROM room_messages WHERE room_id=?', (room_id,))
    conn.execute('DELETE FROM room_members WHERE room_id=? AND session_id != ?', (room_id, user['sid']))
    conn.execute('DELETE FROM muted_members WHERE room_id=?', (room_id,))
    conn.commit()
    conn.close()
    add_log('إفراغ غرفة', room['name'], room_id, 'حذف الرسائل وطرد الأعضاء الآخرين')
    flash('تم إفراغ الغرفة من الرسائل والأعضاء الآخرين.')
    return redirect(url_for('room_chat', room_id=room_id))


@app.route('/bans/user/<int:ban_id>/delete', methods=['POST'])
def unban_user(ban_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'unban_users'):
        flash('لا تملك صلاحية فك الحظر.')
        return redirect(url_for('admin_panel'))
    conn = db()
    target = conn.execute('SELECT * FROM user_bans WHERE id=?', (ban_id,)).fetchone()
    conn.execute('DELETE FROM user_bans WHERE id=?', (ban_id,))
    conn.commit()
    conn.close()
    add_log('فك حظر', target['display_name'] if target else '', None, 'فك حظر مستخدم')
    flash('تم فك الحظر.')
    return redirect(url_for('admin_panel'))


@app.route('/bans/ip/<int:ban_id>/delete', methods=['POST'])
def unban_ip(ban_id):
    user, resp = require_entry()
    if resp:
        return resp
    if not has_perm(user, 'unban_users'):
        flash('لا تملك صلاحية فك حظر IP.')
        return redirect(url_for('admin_panel'))
    conn = db()
    target = conn.execute('SELECT * FROM ip_bans WHERE id=?', (ban_id,)).fetchone()
    conn.execute('DELETE FROM ip_bans WHERE id=?', (ban_id,))
    conn.commit()
    conn.close()
    add_log('فك حظر IP', target['ip_address'] if target else '', None, 'فك حظر IP')
    flash('تم فك حظر IP.')
    return redirect(url_for('admin_panel'))


@app.route('/logout')
def logout():
    # خروج كامل: حذف العضوية من الغرف ومسح كل بيانات الجلسة.
    sid = session.get('sid')
    if sid:
        conn = db()
        conn.execute('DELETE FROM room_members WHERE session_id=?', (sid,))
        conn.commit()
        conn.close()
    session.clear()
    flash('تم تسجيل الخروج أو تغيير الاسم بنجاح.')
    return redirect(url_for('provinces'))


# تهيئة قاعدة البيانات عند تشغيل Render عبر gunicorn app:app
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
