from flask import Flask, request, jsonify, render_template_string, send_from_directory
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename
import json, os

app = Flask(__name__)
LICENSES_FILE = "licenses.json"
CONFIG_FILE   = "config.json"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'zip'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Timezone UTC+7 ────────────────────────────────────────────────────────────
TZ_VN = timezone(timedelta(hours=7))

def now_vn():
    return datetime.now(TZ_VN)

def today():
    return now_vn().replace(hour=0, minute=0, second=0, microsecond=0)

def parse_date(iso_str):
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_VN)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

def load_licenses():
    if not os.path.exists(LICENSES_FILE):
        return []
    with open(LICENSES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_licenses(licenses):
    with open(LICENSES_FILE, 'w', encoding='utf-8') as f:
        json.dump(licenses, f, ensure_ascii=False, indent=2)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {'room_name': ''}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_files_info():
    files = []
    for fname in os.listdir(UPLOAD_FOLDER):
        fpath = os.path.join(UPLOAD_FOLDER, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            size_kb = round(stat.st_size / 1024, 1)
            files.append({
                'name': fname,
                'size': size_kb,
                'uploaded_at': datetime.fromtimestamp(stat.st_mtime, tz=TZ_VN).strftime('%Y-%m-%d %H:%M')
            })
    return sorted(files, key=lambda x: x['uploaded_at'], reverse=True)

HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GZF License Manager</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root{--bg:#0a0a0f;--card:#111118;--card2:#16161f;--border:#2a2a3a;
    --orange:#ff7a00;--orange2:#e06800;--green:#00e676;--red:#ff3d3d;
    --amber:#ffab00;--cyan:#00e5ff;--text:#f0f0f0;--sub:#666688;}
  *{margin:0;padding:0;box-sizing:border-box;}
  body{background:var(--bg);color:var(--text);font-family:'Rajdhani',sans-serif;min-height:100vh;
    background-image:radial-gradient(ellipse at 20% 20%,rgba(255,122,0,.04) 0%,transparent 60%),
    radial-gradient(ellipse at 80% 80%,rgba(0,229,255,.03) 0%,transparent 60%);}
  .header{background:var(--card);border-bottom:1px solid var(--border);padding:0 32px;
    display:flex;align-items:center;justify-content:space-between;height:64px;
    position:sticky;top:0;z-index:100;}
  .header::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
    background:linear-gradient(90deg,var(--orange),var(--cyan));}
  .logo{font-family:'Share Tech Mono',monospace;font-size:20px;color:var(--orange);letter-spacing:2px;}
  .logo span{color:var(--sub);font-size:13px;margin-left:8px;}
  .logo-room{font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--cyan);
    margin-left:12px;padding:3px 10px;border:1px solid rgba(0,229,255,.3);
    border-radius:4px;background:rgba(0,229,255,.06);}
  .nav-tabs{display:flex;gap:4px;margin-left:24px;}
  .nav-tab{padding:8px 20px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:700;
    letter-spacing:1px;border:1px solid transparent;transition:all .2s;color:var(--sub);}
  .nav-tab.active{background:var(--orange);color:#000;border-color:var(--orange);}
  .nav-tab:not(.active):hover{border-color:var(--border);color:var(--text);}
  .header-right{display:flex;gap:10px;align-items:center;}
  .badge{font-family:'Share Tech Mono',monospace;font-size:11px;padding:4px 10px;border-radius:4px;border:1px solid;}
  .badge-green{color:var(--green);border-color:var(--green);background:rgba(0,230,118,.08);}
  .badge-red{color:var(--red);border-color:var(--red);background:rgba(255,61,61,.08);}
  .badge-amber{color:var(--amber);border-color:var(--amber);background:rgba(255,171,0,.08);}
  .main{max-width:1200px;margin:0 auto;padding:32px 24px;}
  .tab-page{display:none;}.tab-page.active{display:block;}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px;}
  .stat-card{background:var(--card);border:1px solid var(--border);border-radius:10px;
    padding:20px;position:relative;overflow:hidden;}
  .stat-card::after{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;}
  .stat-card.s-total::after{background:var(--cyan);}
  .stat-card.s-active::after{background:var(--green);}
  .stat-card.s-expired::after{background:var(--red);}
  .stat-card.s-warn::after{background:var(--amber);}
  .stat-label{font-size:12px;color:var(--sub);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;}
  .stat-num{font-family:'Share Tech Mono',monospace;font-size:36px;}
  .stat-card.s-total .stat-num{color:var(--cyan);}
  .stat-card.s-active .stat-num{color:var(--green);}
  .stat-card.s-expired .stat-num{color:var(--red);}
  .stat-card.s-warn .stat-num{color:var(--amber);}
  .section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}
  .section-title{font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--orange);}
  .card-box{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:24px;margin-bottom:24px;}
  .form-grid{display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:12px;align-items:end;}
  .form-group{display:flex;flex-direction:column;gap:6px;}
  .form-label{font-size:11px;color:var(--sub);text-transform:uppercase;letter-spacing:1px;}
  .form-input{background:var(--card2);border:1px solid var(--border);border-radius:6px;
    padding:10px 14px;color:var(--text);font-family:'Share Tech Mono',monospace;
    font-size:13px;outline:none;transition:border-color .2s;width:100%;}
  .form-input:focus{border-color:var(--orange);}
  .btn{padding:10px 20px;border-radius:6px;border:none;cursor:pointer;
    font-family:'Rajdhani',sans-serif;font-size:14px;font-weight:700;
    letter-spacing:1px;transition:all .2s;white-space:nowrap;}
  .btn-orange{background:var(--orange);color:#000;}
  .btn-orange:hover{background:var(--orange2);transform:translateY(-1px);}
  .btn-red{background:transparent;border:1px solid var(--red);color:var(--red);padding:6px 12px;font-size:12px;}
  .btn-red:hover{background:rgba(255,61,61,.15);}
  .btn-green{background:transparent;border:1px solid var(--green);color:var(--green);padding:6px 12px;font-size:12px;}
  .btn-green:hover{background:rgba(0,230,118,.15);}
  .btn-cyan{background:transparent;border:1px solid var(--cyan);color:var(--cyan);padding:6px 12px;font-size:12px;}
  .btn-cyan:hover{background:rgba(0,229,255,.15);}
  .table-wrap{background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:24px;}
  table{width:100%;border-collapse:collapse;}
  thead{background:var(--card2);}
  th{padding:12px 16px;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--sub);text-align:left;font-weight:600;}
  td{padding:14px 16px;border-top:1px solid var(--border);font-size:14px;}
  tr:hover td{background:rgba(255,122,0,.03);}
  .mono{font-family:'Share Tech Mono',monospace;font-size:13px;color:var(--orange);}
  .actions{display:flex;gap:8px;}
  .status{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;}
  .status::before{content:'●';font-size:8px;}
  .status-active{color:var(--green);background:rgba(0,230,118,.1);}
  .status-expired{color:var(--red);background:rgba(255,61,61,.1);}
  .status-warn{color:var(--amber);background:rgba(255,171,0,.1);}
  .drop-zone{border:2px dashed var(--border);border-radius:10px;padding:48px;text-align:center;
    cursor:pointer;transition:all .2s;margin-bottom:16px;}
  .drop-zone:hover,.drop-zone.drag-over{border-color:var(--orange);background:rgba(255,122,0,.05);}
  .drop-zone-icon{font-size:48px;margin-bottom:12px;}
  .drop-zone-text{color:var(--sub);font-size:15px;line-height:1.8;}
  .drop-zone-text strong{color:var(--orange);}
  .upload-progress{display:none;margin-top:16px;}
  .progress-bar-wrap{background:var(--card2);border-radius:4px;height:8px;overflow:hidden;margin-top:8px;}
  .progress-bar-fill{height:100%;background:linear-gradient(90deg,var(--orange),var(--cyan));transition:width .3s;width:0%;}
  .file-url-box{background:var(--card2);border:1px solid var(--cyan);border-radius:6px;
    padding:12px 16px;font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--cyan);
    word-break:break-all;display:none;margin-top:12px;cursor:pointer;}
  .modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);
    backdrop-filter:blur(4px);z-index:200;align-items:center;justify-content:center;}
  .modal-overlay.active{display:flex;}
  .modal{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:32px;width:360px;}
  .modal-title{font-size:16px;font-weight:700;color:var(--orange);margin-bottom:20px;letter-spacing:1px;}
  .modal-btns{display:flex;gap:10px;margin-top:20px;}
  .btn-cancel{flex:1;padding:10px;border-radius:6px;background:transparent;
    border:1px solid var(--border);color:var(--sub);cursor:pointer;
    font-family:'Rajdhani',sans-serif;font-size:14px;font-weight:600;}
  .btn-confirm{flex:1;padding:10px;border-radius:6px;background:var(--orange);
    border:none;color:#000;cursor:pointer;font-family:'Rajdhani',sans-serif;font-size:14px;font-weight:700;}
  .toast{position:fixed;bottom:24px;right:24px;background:var(--card);border:1px solid var(--border);
    border-radius:8px;padding:14px 20px;font-size:14px;transform:translateY(80px);opacity:0;
    transition:all .3s;z-index:300;}
  .toast.show{transform:translateY(0);opacity:1;}
  .toast.success{border-color:var(--green);color:var(--green);}
  .toast.error{border-color:var(--red);color:var(--red);}
  .settings-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;}
  .setting-item{background:var(--card2);border:1px solid var(--border);border-radius:8px;padding:20px;}
  .setting-desc{font-size:13px;color:var(--sub);margin-bottom:16px;line-height:1.6;}
  .api-preview{background:var(--bg);border:1px solid var(--border);border-radius:6px;
    padding:12px 16px;font-family:'Share Tech Mono',monospace;font-size:12px;color:var(--cyan);
    margin-top:12px;line-height:1.8;}
  @media(max-width:768px){
    .stats{grid-template-columns:repeat(2,1fr);}
    .form-grid{grid-template-columns:1fr;}
    .settings-grid{grid-template-columns:1fr;}
  }
</style>
</head>
<body>
<div class="header">
  <div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px">
    <div class="logo">GZF<span>PANEL</span></div>
    <div id="header-room" class="logo-room" style="display:none"></div>
    <div class="nav-tabs">
      <div class="nav-tab active" id="tab-btn-licenses" onclick="switchTab('licenses',this)">🔑 LICENSE</div>
      <div class="nav-tab" id="tab-btn-files"    onclick="switchTab('files',this)">📦 FILES</div>
      <div class="nav-tab" id="tab-btn-settings" onclick="switchTab('settings',this)">⚙ SETTINGS</div>
    </div>
  </div>
  <div class="header-right">
    <span class="badge badge-green" id="badge-active">● 0 Active</span>
    <span class="badge badge-red"   id="badge-expired">● 0 Expired</span>
    <span class="badge badge-amber" id="badge-warn">⚠ 0 Expiring</span>
  </div>
</div>
<div class="main">
  <div class="tab-page active" id="tab-licenses">
    <div class="stats">
      <div class="stat-card s-total"><div class="stat-label">Tổng License</div><div class="stat-num" id="stat-total">0</div></div>
      <div class="stat-card s-active"><div class="stat-label">Hoạt Động</div><div class="stat-num" id="stat-active">0</div></div>
      <div class="stat-card s-expired"><div class="stat-label">Hết Hạn</div><div class="stat-num" id="stat-expired">0</div></div>
      <div class="stat-card s-warn"><div class="stat-label">Sắp Hết (7 ngày)</div><div class="stat-num" id="stat-warn">0</div></div>
    </div>
    <div class="card-box">
      <div class="section-title" style="margin-bottom:16px">Thêm License Mới</div>
      <div class="form-grid">
        <div class="form-group"><label class="form-label">Tên</label>
          <input class="form-input" id="inp-name" placeholder="Nguyen Van A"/></div>
        <div class="form-group"><label class="form-label">Machine ID</label>
          <input class="form-input" id="inp-mid" placeholder="GodZoneForce"/></div>
        <div class="form-group"><label class="form-label">Ngày hết hạn</label>
          <input class="form-input" id="inp-expire" type="date"/></div>
        <button class="btn btn-orange" onclick="addLicense()">+ THÊM</button>
      </div>
    </div>
    <div class="section-header">
      <div class="section-title">Danh Sách License</div>
      <span style="font-size:12px;color:var(--sub)" id="total-count">0 license</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>Tên</th><th>Machine ID</th><th>Hết Hạn</th><th>Còn Lại</th><th>Trạng Thái</th><th>Hành Động</th></tr></thead>
        <tbody id="license-tbody"><tr><td colspan="7" style="text-align:center;color:var(--sub);padding:40px">Đang tải...</td></tr></tbody>
      </table>
    </div>
  </div>
  <div class="tab-page" id="tab-files">
    <div class="card-box">
      <div class="section-title" style="margin-bottom:16px">📦 Upload File ZIP</div>
      <div class="drop-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
        <div class="drop-zone-icon">📦</div>
        <div class="drop-zone-text">Kéo thả file <strong>.ZIP</strong> vào đây<br>hoặc <strong>click để chọn file</strong></div>
        <input type="file" id="file-input" accept=".zip" style="display:none" onchange="uploadFile(this.files[0])">
      </div>
      <div class="upload-progress" id="upload-progress">
        <div style="font-size:13px;color:var(--sub)" id="upload-status">Đang upload...</div>
        <div class="progress-bar-wrap"><div class="progress-bar-fill" id="progress-fill"></div></div>
      </div>
      <div class="file-url-box" id="file-url-box" onclick="copyUrlBox()" title="Click để copy URL"></div>
    </div>
    <div class="section-header">
      <div class="section-title">Danh Sách File</div>
      <button class="btn btn-orange" style="padding:6px 16px;font-size:12px" onclick="loadFiles()">⟳ Refresh</button>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>Tên File</th><th>Dung Lượng</th><th>Upload Lúc</th><th>Download URL</th><th>Hành Động</th></tr></thead>
        <tbody id="files-tbody"><tr><td colspan="6" style="text-align:center;color:var(--sub);padding:40px">Chưa có file nào</td></tr></tbody>
      </table>
    </div>
  </div>
  <div class="tab-page" id="tab-settings">
    <div class="card-box">
      <div class="section-title" style="margin-bottom:20px">⚙ Cấu Hình Hệ Thống</div>
      <div class="settings-grid">
        <div class="setting-item">
          <div class="section-title" style="margin-bottom:8px">🏠 Tên Phòng</div>
          <div class="setting-desc">Tên phòng chung trả về khi client gọi <code style="color:var(--orange)">/check-key</code>.</div>
          <div class="form-group">
            <label class="form-label">Tên Phòng</label>
            <input class="form-input" id="inp-room-name" placeholder="Phòng 101 / Studio A / ..."/>
          </div>
          <button class="btn btn-orange" style="margin-top:12px;width:100%" onclick="saveRoomName()">💾 LƯU TÊN PHÒNG</button>
          <div class="api-preview">
            <div style="color:var(--sub);font-size:11px;margin-bottom:4px">▸ Response /check-key (UTC+7)</div>
            {<br>
            &nbsp;&nbsp;"name": "Nguyen Van A",<br>
            &nbsp;&nbsp;"room_name": "<span id="preview-room" style="color:var(--green)">...</span>",<br>
            &nbsp;&nbsp;"expire_in_days": 25.6,<br>
            &nbsp;&nbsp;"expires_at": "2026-07-05T23:59:59"<br>
            }
          </div>
        </div>
        <div class="setting-item">
          <div class="section-title" style="margin-bottom:8px">ℹ Thông Tin</div>
          <div class="setting-desc" style="line-height:2">
            Lưu trong <code style="color:var(--orange)">config.json</code>.<br>
            Hiệu lực ngay, không cần restart.<br>
            Múi giờ: <code style="color:var(--green)">UTC+7 (Việt Nam)</code>.
          </div>
          <div style="margin-top:16px;padding:12px;background:var(--bg);border-radius:6px;border:1px solid var(--border)">
            <div style="font-size:11px;color:var(--sub);margin-bottom:8px;letter-spacing:1px">TRẠNG THÁI</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:14px">
              Tên phòng: <span id="current-room-display" style="color:var(--cyan)">...</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="modal-overlay" id="modal-extend">
  <div class="modal">
    <div class="modal-title">⏱ GIA HẠN LICENSE</div>
    <div class="form-group">
      <label class="form-label">Số ngày gia hạn</label>
      <input class="form-input" id="extend-days" type="number" value="30" min="1" max="365"/>
    </div>
    <div style="font-size:12px;color:var(--sub);margin-top:8px" id="extend-info"></div>
    <div class="modal-btns">
      <button class="btn-cancel" onclick="closeModal()">Hủy</button>
      <button class="btn-confirm" onclick="confirmExtend()">Gia Hạn</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
let currentExtendId = null;
function switchTab(tab, el) {
  document.querySelectorAll('.tab-page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  el.classList.add('active');
  if (tab === 'files') loadFiles();
  if (tab === 'settings') loadConfig();
}
const d = new Date(); d.setDate(d.getDate()+30);
document.getElementById('inp-expire').value = d.toISOString().split('T')[0];
async function loadConfig() {
  const res = await fetch('/config');
  const cfg = await res.json();
  const room = cfg.room_name || '';
  document.getElementById('inp-room-name').value = room;
  document.getElementById('preview-room').textContent = room || '(chưa đặt)';
  document.getElementById('current-room-display').textContent = room || '(chưa đặt)';
  const hdr = document.getElementById('header-room');
  if (room) { hdr.textContent = '🏠 ' + room; hdr.style.display = ''; }
  else hdr.style.display = 'none';
}
async function saveRoomName() {
  const room = document.getElementById('inp-room-name').value.trim();
  const res = await fetch('/config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({room_name: room}) });
  if (res.ok) { showToast('✓ Đã lưu tên phòng', 'success'); loadConfig(); }
  else showToast('❌ Lỗi lưu config', 'error');
}
async function loadLicenses() {
  const res = await fetch('/licenses');
  const data = await res.json();
  renderLicenseTable(data);
  updateStats(data);
}
function updateStats(data) {
  const total=data.length, active=data.filter(l=>l.days_left>0).length,
    expired=data.filter(l=>l.days_left<=0).length, warn=data.filter(l=>l.days_left>0&&l.days_left<=7).length;
  document.getElementById('stat-total').textContent=total;
  document.getElementById('stat-active').textContent=active;
  document.getElementById('stat-expired').textContent=expired;
  document.getElementById('stat-warn').textContent=warn;
  document.getElementById('total-count').textContent=total+' license';
  document.getElementById('badge-active').textContent='● '+active+' Active';
  document.getElementById('badge-expired').textContent='● '+expired+' Expired';
  document.getElementById('badge-warn').textContent='⚠ '+warn+' Expiring';
}
function renderLicenseTable(data) {
  const tbody = document.getElementById('license-tbody');
  if (!data.length) { tbody.innerHTML='<tr><td colspan="7" style="text-align:center;color:var(--sub);padding:40px">Chưa có license nào</td></tr>'; return; }
  tbody.innerHTML = data.map((l,i) => {
    const days=l.days_left, expireDate=l.expires_at.split('T')[0];
    let st,dh;
    if(days<=0){st='<span class="status status-expired">Hết hạn</span>';dh='<span style="color:var(--red);font-family:Share Tech Mono,monospace">Hết hạn</span>';}
    else if(days<=7){st='<span class="status status-warn">Sắp hết</span>';dh='<span style="color:var(--amber);font-family:Share Tech Mono,monospace">'+days+' ngày</span>';}
    else{st='<span class="status status-active">Hoạt động</span>';dh='<span style="color:var(--green);font-family:Share Tech Mono,monospace">'+days+' ngày</span>';}
    return `<tr><td style="color:var(--sub);font-family:Share Tech Mono,monospace">${i+1}</td><td style="font-weight:600">${l.name}</td><td><span class="mono">${l.machine_id}</span></td><td style="color:var(--sub);font-family:Share Tech Mono,monospace;font-size:12px">${expireDate}</td><td>${dh}</td><td>${st}</td><td><div class="actions"><button class="btn btn-green" onclick="openExtend('${l.machine_id}',${days})">Gia Hạn</button><button class="btn btn-red" onclick="deleteLicense('${l.machine_id}','${l.name}')">Xóa</button></div></td></tr>`;
  }).join('');
}
async function addLicense() {
  const name=document.getElementById('inp-name').value.trim(), mid=document.getElementById('inp-mid').value.trim(), expire=document.getElementById('inp-expire').value;
  if(!name||!mid||!expire){showToast('Điền đầy đủ thông tin!','error');return;}
  const res=await fetch('/licenses',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,machine_id:mid,expires_at:expire})});
  const data=await res.json();
  if(res.ok){showToast('✓ Đã thêm: '+name,'success');document.getElementById('inp-name').value='';document.getElementById('inp-mid').value='';loadLicenses();}
  else showToast('❌ '+(data.error||'Lỗi'),'error');
}
async function deleteLicense(mid,name){
  if(!confirm('Xóa license của '+name+'?'))return;
  await fetch('/licenses/'+mid,{method:'DELETE'});
  showToast('✓ Đã xóa: '+name,'success');loadLicenses();
}
function openExtend(mid,daysLeft){currentExtendId=mid;document.getElementById('extend-info').textContent='Machine ID: '+mid+' · Còn '+daysLeft+' ngày';document.getElementById('modal-extend').classList.add('active');}
function closeModal(){document.getElementById('modal-extend').classList.remove('active');currentExtendId=null;}
async function confirmExtend(){
  const days=parseInt(document.getElementById('extend-days').value);
  if(!days||days<1){showToast('Nhập số ngày hợp lệ','error');return;}
  const res=await fetch('/licenses/'+currentExtendId+'/extend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({days})});
  if(res.ok){showToast('✓ Đã gia hạn '+days+' ngày','success');closeModal();loadLicenses();}
}
async function loadFiles() {
  const res=await fetch('/files'), data=await res.json(), tbody=document.getElementById('files-tbody');
  if(!data.length){tbody.innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--sub);padding:40px">Chưa có file nào</td></tr>';return;}
  const base=window.location.origin;
  tbody.innerHTML=data.map((f,i)=>`<tr><td style="color:var(--sub);font-family:Share Tech Mono,monospace">${i+1}</td><td style="font-weight:600">📦 ${f.name}</td><td style="font-family:Share Tech Mono,monospace;color:var(--sub)">${f.size} KB</td><td style="font-family:Share Tech Mono,monospace;color:var(--sub);font-size:12px">${f.uploaded_at}</td><td><span class="mono" style="font-size:11px;cursor:pointer" onclick="copyUrl('${base}/files/${f.name}/download')" title="Click để copy">/files/${f.name}/download ✎</span></td><td><div class="actions"><a href="/files/${f.name}/download" class="btn btn-cyan" style="text-decoration:none">⬇ Tải</a><button class="btn btn-red" onclick="deleteFile('${f.name}')">Xóa</button></div></td></tr>`).join('');
}
async function uploadFile(file) {
  if(!file)return;
  if(!file.name.endsWith('.zip')){showToast('Chỉ chấp nhận file .zip','error');return;}
  const progress=document.getElementById('upload-progress'),fill=document.getElementById('progress-fill'),status=document.getElementById('upload-status'),urlBox=document.getElementById('file-url-box');
  progress.style.display='block';urlBox.style.display='none';fill.style.width='0%';status.textContent='Đang upload '+file.name+'...';
  const formData=new FormData();formData.append('file',file);
  const xhr=new XMLHttpRequest();
  xhr.upload.onprogress=e=>{if(e.lengthComputable){const pct=Math.round(e.loaded/e.total*100);fill.style.width=pct+'%';status.textContent='Đang upload... '+pct+'%';}};
  xhr.onload=()=>{if(xhr.status===200){const res=JSON.parse(xhr.responseText);status.textContent='✓ Upload thành công!';fill.style.width='100%';const fullUrl=window.location.origin+res.url;urlBox.style.display='block';urlBox.textContent='📋 Click để copy: '+fullUrl;urlBox._url=fullUrl;showToast('✓ Upload thành công: '+file.name,'success');loadFiles();}else{status.textContent='❌ Upload thất bại';showToast('❌ Upload thất bại','error');}};
  xhr.open('POST','/files/upload');xhr.send(formData);
}
async function deleteFile(name){if(!confirm('Xóa file '+name+'?'))return;const res=await fetch('/files/'+name,{method:'DELETE'});if(res.ok){showToast('✓ Đã xóa: '+name,'success');loadFiles();}}
function copyUrl(url){navigator.clipboard.writeText(url).then(()=>showToast('✓ Đã copy URL','success'));}
function copyUrlBox(){const box=document.getElementById('file-url-box');if(box._url)navigator.clipboard.writeText(box._url).then(()=>showToast('✓ Đã copy URL','success'));}
const dz=document.getElementById('drop-zone');
dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag-over');});
dz.addEventListener('dragleave',()=>dz.classList.remove('drag-over'));
dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('drag-over');const file=e.dataTransfer.files[0];if(file)uploadFile(file);});
function showToast(msg,type='success'){const t=document.getElementById('toast');t.textContent=msg;t.className='toast '+type+' show';setTimeout(()=>t.className='toast',3000);}
document.getElementById('modal-extend').addEventListener('click',function(e){if(e.target===this)closeModal();});
loadLicenses();loadConfig();setInterval(loadLicenses,30000);
</script>
</body>
</html>
"""

@app.route('/config', methods=['GET'])
def get_config():
    return jsonify(load_config())

@app.route('/config', methods=['POST'])
def set_config():
    data = request.json
    cfg = load_config()
    cfg['room_name'] = data.get('room_name', '')
    save_config(cfg)
    return jsonify({'success': True, 'room_name': cfg['room_name']})

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/check-key', methods=['GET'])
def check_key():
    machine_id = request.args.get('machine_id') or request.args.get('id')
    if not machine_id:
        return jsonify({'error': 'missing_machine_id'}), 400
    licenses = load_licenses()
    lic = next((l for l in licenses if l['machine_id'] == machine_id), None)
    if not lic:
        return jsonify({'error': 'not_found'}), 404
    now    = now_vn()
    expire = datetime.fromisoformat(lic['expires_at'])
    if expire.tzinfo is None:
        expire = expire.replace(tzinfo=TZ_VN)
    diff = expire - now
    if diff.total_seconds() < 0:
        return jsonify({'error': 'expired'}), 403
    expire_in_days = diff.total_seconds() / 86400
    cfg = load_config()
    return jsonify({
        'name':           lic['name'],
        'room_name':      cfg.get('room_name', ''),
        'expire_in_days': expire_in_days,
        'expires_at':     lic['expires_at']
    }), 200

@app.route('/licenses', methods=['GET'])
def list_licenses():
    licenses = load_licenses()
    now = today()
    result = []
    for l in licenses:
        expire    = parse_date(l['expires_at'])
        days_left = (expire - now).days
        result.append({**l, 'days_left': days_left, 'status': 'active' if days_left > 0 else 'expired'})
    return jsonify(result)

@app.route('/licenses', methods=['POST'])
def add_license():
    data = request.json
    licenses = load_licenses()
    if any(l['machine_id'] == data['machine_id'] for l in licenses):
        return jsonify({'error': 'machine_id đã tồn tại'}), 400
    new_lic = {
        'id':         len(licenses) + 1,
        'name':       data['name'],
        'machine_id': data['machine_id'],
        'expires_at': data['expires_at'] + 'T23:59:59',
        'created_at': now_vn().isoformat()
    }
    licenses.append(new_lic)
    save_licenses(licenses)
    return jsonify(new_lic), 201

@app.route('/licenses/<machine_id>', methods=['DELETE'])
def delete_license(machine_id):
    licenses = load_licenses()
    licenses = [l for l in licenses if l['machine_id'] != machine_id]
    save_licenses(licenses)
    return jsonify({'success': True})

@app.route('/licenses/<machine_id>/extend', methods=['POST'])
def extend_license(machine_id):
    data = request.json
    days = int(data.get('days', 30))
    licenses = load_licenses()
    for l in licenses:
        if l['machine_id'] == machine_id:
            expire = datetime.fromisoformat(l['expires_at'])
            if expire.tzinfo is None:
                expire = expire.replace(tzinfo=TZ_VN)
            now  = now_vn()
            base = expire if expire > now else now
            l['expires_at'] = (base + timedelta(days=days)).strftime('%Y-%m-%dT23:59:59')
            save_licenses(licenses)
            return jsonify({'success': True, 'new_expire': l['expires_at']})
    return jsonify({'error': 'not_found'}), 404

@app.route('/files', methods=['GET'])
def list_files():
    return jsonify(get_files_info())

@app.route('/files/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Không có file'}), 400
    file = request.files['file']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'error': 'Chỉ chấp nhận file .zip'}), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return jsonify({'success': True, 'filename': filename, 'url': f'/files/{filename}/download'}), 200

@app.route('/files/<filename>/download', methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True})
    return jsonify({'error': 'Không tìm thấy file'}), 404

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
