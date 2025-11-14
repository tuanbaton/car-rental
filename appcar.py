# appcar.py 
import os
import sqlite3
import bcrypt
import secrets
import webbrowser
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
app.secret_key = 'your-super-secret-key-2025-car-rental'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

# === CẤU HÌNH ===
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'rental_system.db')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Tạo thư mục
os.makedirs(os.path.join(BASE_DIR, 'templates', 'admin'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static', 'css'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'static', 'js'), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === ẢNH MẶC ĐỊNH ĐẸP ===
default_img = os.path.join(UPLOAD_FOLDER, 'default.jpg')
if not os.path.exists(default_img):
    try:
        img = Image.new('RGB', (800, 600), color=(240, 244, 248))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
        text = "No Image"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((800 - text_width) // 2, (600 - text_height) // 2)
        draw.text(position, text, fill=(150, 150, 150), font=font)
        img.save(default_img)
        print("Tạo ảnh mặc định thành công!")
    except Exception as e:
        print(f"Không tạo được ảnh mặc định: {e}")

# === HÀM HỖ TRỢ ===
def format_vnd(amount):
    return f"{int(amount):,}".replace(",", ".") + " VND"

def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode('utf-8')

def check_password(h, p):
    return bcrypt.checkpw(p.encode(), h.encode('utf-8') if isinstance(h, str) else h)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# === CSRF ===
@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.get('_csrf_token')
        if not token or token != request.form.get('csrf_token'):
            abort(403)

def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(16)
    return session["_csrf_token"]

app.jinja_env.globals['csrf_token'] = generate_csrf_token

# === TOÀN CỤC ===
@app.context_processor
def utility_processor():
    return dict(format_vnd=format_vnd)

# === TẠO HTML TỰ ĐỘNG ===
HTML_FILES = {
    'templates/base.html': '''<!DOCTYPE html>
<html lang="vi"><head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}CarRental{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background:#f8f9fa; padding-top:80px; }
        .navbar { box-shadow:0 2px 4px rgba(0,0,0,.1); }
        .card { border:none; box-shadow:0 .5rem 1rem rgba(0,0,0,.15); transition:.2s; }
        .card:hover { transform:translateY(-5px); }
        .btn { border-radius:25px; padding:.375rem 1.5rem; }
        .quick-back { position: fixed; right: 20px; bottom: 20px; z-index: 1050; box-shadow: 0 .5rem 1rem rgba(0,0,0,.15); border-radius: 50px; padding: .5rem .8rem; }
        .quick-back .label { display: none; margin-left: 8px; vertical-align: middle; }
        @media (min-width: 576px) { .quick-back .label { display: inline-block; } }
    </style>
</head><body>
<nav class="navbar fixed-top navbar-expand-lg navbar-dark bg-primary">
    <div class="container">
        <a class="navbar-brand" href="/"><i class="fas fa-car me-2"></i>CarRental</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav ms-auto">
                {% if session.user_id %}
                    <li class="nav-item"><a href="/cart" class="nav-link"><i class="fas fa-shopping-cart me-1"></i>Giỏ ({{ session.cart|length|default(0) }})</a></li>
                    <li class="nav-item"><a href="/bookings" class="nav-link"><i class="fas fa-list me-1"></i>Đơn hàng</a></li>
                    {% if session.role == 'admin' %}
                        <li class="nav-item"><a href="/admin" class="nav-link"><i class="fas fa-user-shield me-1"></i>ADMIN</a></li>
                    {% endif %}
                    <li class="nav-item"><a href="/logout" class="nav-link"><i class="fas fa-sign-out-alt me-1"></i>Đăng xuất</a></li>
                {% else %}
                    <li class="nav-item"><a href="/login" class="nav-link"><i class="fas fa-sign-in-alt me-1"></i>Đăng nhập</a></li>
                    <li class="nav-item"><a href="/register" class="nav-link"><i class="fas fa-user-plus me-1"></i>Đăng ký</a></li>
                {% endif %}
            </ul>
        </div>
    </div>
</nav>
<div class="container mt-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }} alert-dismissible fade show">
                    <i class="fas fa-{{ 'check-circle' if category == 'success' else 'exclamation-circle' }} me-2"></i>
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>
<a href="/" class="btn btn-success quick-back" title="Quay lại xem xe">
    <i class="fas fa-car"></i> <span class="label">Quay lại xem xe</span>
</a>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>''',

    'templates/index.html': '''{% extends "base.html" %}{% block title %}Tìm kiếm xe{% endblock %}
{% block content %}
<h1>Tìm kiếm xe</h1>
<form method="get" action="/" class="mb-4">
    <input type="text" name="q" class="form-control w-50 d-inline" placeholder="Nhập tên xe, hãng..." value="{{ request.args.get('q','') }}">
    <button class="btn btn-primary">Tìm</button>
</form>
<div class="row">
    {% for v in vehicles %}
    <div class="col-md-4 mb-3">
        <div class="card h-100">
            <div class="position-relative">
                <img src="/static/uploads/{{ v.image_path }}" class="card-img-top" style="height:180px; object-fit:cover;" onerror="this.src='/static/uploads/default.jpg'">
                {% if v.status == 'rented' %}
                    <div class="position-absolute top-0 end-0 m-2"><span class="badge bg-danger">Đã cho thuê</span></div>
                {% endif %}
            </div>
            <div class="card-body">
                <h5>{{ v.brand }} {{ v.model }}</h5>
                <p><strong>{{ v.type_name }}</strong> | {{ format_vnd(v.daily_rate) }}/ngày<br>
                <span class="badge bg-{{ 'success' if v.status == 'available' else 'danger' }}">{{ 'Có sẵn' if v.status == 'available' else 'Đã thuê' }}</span></p>
                <a href="/vehicle/{{ v.vehicle_id }}" class="btn btn-primary btn-sm">Chi tiết</a>
            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}''',

    'templates/vehicle_detail.html': '''{% extends "base.html" %}
{% block title %}{{ vehicle.brand }} {{ vehicle.model }}{% endblock %}
{% block content %}
<div class="row">
    <div class="col-md-6">
        <img src="/static/uploads/{{ vehicle.image_path }}" class="img-fluid rounded" style="max-height:400px; object-fit:cover;" onerror="this.src='/static/uploads/default.jpg'">
    </div>
    <div class="col-md-6">
        <h2>{{ vehicle.brand }} {{ vehicle.model }} <span class="badge bg-{{ 'success' if vehicle.status == 'available' else 'danger' }}">{{ 'Có sẵn' if vehicle.status == 'available' else 'Đã thuê' }}</span></h2>
        <table class="table">
            <tr><th>Biển số</th><td>{{ vehicle.registration_no }}</td></tr>
            <tr><th>Loại</th><td>{{ vehicle.type_name }} - {{ vehicle.seats }} chỗ</td></tr>
            <tr><th>Năm SX</th><td>{{ vehicle.year }}</td></tr>
            <tr><th>Giá/ngày</th><td><strong class="text-danger">{{ format_vnd(vehicle.daily_rate) }}</strong></td></tr>
            <tr><th>Mô tả</th><td>{{ vehicle.description or 'Không có' }}</td></tr>
        </table>
        {% if session.user_id %}
            {% if vehicle.status == 'available' %}
                <form action="/cart/add" method="post">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <input type="hidden" name="vehicle_id" value="{{ vehicle.vehicle_id }}">
                    <input type="number" name="days" class="form-control d-inline w-25" value="1" min="1" required> ngày
                    <button type="submit" class="btn btn-success">Thêm vào giỏ</button>
                </form>
            {% else %}
                <div class="alert alert-danger">Xe đang được thuê</div>
            {% endif %}
        {% else %}
            <p><a href="/login">Đăng nhập</a> để đặt xe</p>
        {% endif %}
    </div>
</div>
{% endblock %}''',

    'templates/login.html': '''{% extends "base.html" %}{% block title %}Đăng nhập{% endblock %}
{% block content %}
<h2>Đăng nhập</h2>
<form method="post">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="mb-3">
        <input type="email" name="email" class="form-control" placeholder="Email" required>
        <input type="password" name="password" class="form-control mt-2" placeholder="Mật khẩu" required>
        <button class="btn btn-primary mt-3">Đăng nhập</button>
    </div>
</form>
{% endblock %}''',

    'templates/register.html': '''{% extends "base.html" %}
{% block title %}Đăng ký{% endblock %}
{% block content %}
<h2 class="mb-4">Đăng ký tài khoản</h2>
<form method="post" id="registerForm">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="row g-3">
        <div class="col-md-6"><input type="text" name="name" class="form-control" placeholder="Họ tên" required></div>
        <div class="col-md-6"><input type="email" name="email" class="form-control" placeholder="Email" required></div>
        <div class="col-md-6"><input type="password" name="password" class="form-control" placeholder="Mật khẩu (tối thiểu 6 ký tự)" required minlength="6"></div>
        <div class="col-md-6"><input type="text" name="phone" class="form-control" placeholder="SĐT (10-11 số)" required pattern="[0-9]{10,11}"></div>
        <div class="col-md-6"><input type="text" name="address" class="form-control" placeholder="Địa chỉ" required></div>
        <div class="col-md-6"><input type="text" name="cccd" class="form-control" placeholder="CCCD (12 số)" required pattern="[0-9]{12}" maxlength="12"></div>
        <div class="col-md-6"><input type="text" name="license" class="form-control" placeholder="Số bằng lái" required></div>
        <div class="col-12">
            <button type="submit" class="btn btn-success btn-lg">Đăng ký ngay</button>
            <a href="/login" class="btn btn-link">Đã có tài khoản? Đăng nhập</a>
        </div>
    </div>
</form>
<script>
document.getElementById('registerForm').addEventListener('submit', function(e) {
    const cccd = document.querySelector('[name="cccd"]').value;
    const phone = document.querySelector('[name="phone"]').value;
    const pass = document.querySelector('[name="password"]').value;
    if (!/^\d{12}$/.test(cccd)) { alert('CCCD phải đúng 12 số!'); e.preventDefault(); }
    if (!/^\d{10,11}$/.test(phone)) { alert('SĐT phải 10 hoặc 11 số!'); e.preventDefault(); }
    if (pass.length < 6) { alert('Mật khẩu phải ít nhất 6 ký tự!'); e.preventDefault(); }
});
</script>
{% endblock %}''',

    'templates/cart.html': '''{% extends "base.html" %}{% block title %}Giỏ hàng{% endblock %}
{% block content %}
<h2>Giỏ hàng</h2>
{% if cart %}
<table class="table"><thead><tr><th>Xe</th><th>Ngày</th><th>Thành tiền</th><th></th></tr></thead>
<tbody>
    {% for item in cart %}
    <tr>
        <td>{{ item.vehicle.brand }} {{ item.model }}</td>
        <td><input type="number" class="form-control w-50" value="{{ item.days }}" onchange="updateDays({{ loop.index0 }}, this.value)"></td>
        <td>{{ format_vnd(item.subtotal) }}</td>
        <td><a href="/cart/remove/{{ loop.index0 }}" class="btn btn-danger btn-sm">Xóa</a></td>
    </tr>
    {% endfor %}
</tbody></table>
<div class="d-flex justify-content-between align-items-center">
    <div>
        <h5>Tổng: {{ format_vnd(total) }}</h5>
        <p class="mb-0">Tổng số ngày thuê: <strong>{{ days_total }}</strong> ngày</p>
    </div>
    <div>
        <a href="/checkout" class="btn btn-success">Thanh toán</a>
    </div>
</div>
<script>function updateDays(i, days) { fetch('/cart/update/' + i + '/' + days); }</script>
{% else %}
<p>Giỏ hàng trống</p>
{% endif %}
{% endblock %}''',

    'templates/checkout.html': '''{% extends "base.html" %}
{% block title %}Thanh toán{% endblock %}
{% block content %}
<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card shadow">
                <div class="card-header bg-primary text-white">
                    <h3 class="card-title mb-0">Xác nhận đặt xe</h3>
                </div>
                <div class="card-body">
                    <form method="post" id="checkoutForm">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        <div class="row g-3">
                            <div class="col-12">
                                <label class="form-label">Địa điểm nhận xe <span class="text-danger">*</span></label>
                                <input type="text" name="pickup" class="form-control" required>
                            </div>
                            <div class="col-12">
                                <label class="form-label">Địa điểm trả xe <span class="text-danger">*</span></label>
                                <input type="text" name="dropoff" class="form-control" required>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Ngày nhận xe <span class="text-danger">*</span></label>
                                <input type="date" name="start" id="start" class="form-control" required>
                                <small class="text-muted">Từ hôm nay trở đi</small>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Ngày trả xe</label>
                                <input type="date" name="end" id="end" class="form-control" readonly>
                            </div>
                            <div class="col-12">
                                <div class="alert alert-info">
                                    Thời gian thuê: <strong><span id="daysCount">0</span> ngày</strong>
                                </div>
                            </div>
                            <div class="col-12">
                                <div class="alert alert-warning">
                                    Phương thức: <strong>Thanh toán khi nhận xe (COD)</strong>
                                </div>
                            </div>
                            <div class="col-12 text-center">
                                <button type="submit" class="btn btn-primary btn-lg px-5">Xác nhận đặt xe</button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
<script>
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('start').min = today;
    document.getElementById('start').value = today;
    const startInput = document.getElementById('start');
    const endInput = document.getElementById('end');
    const daysCount = document.getElementById('daysCount');
    function updateEndDate() {
        const start = new Date(startInput.value);
        const days = {{ cart|map(attribute='days')|sum|default(0) }};
        const end = new Date(start); end.setDate(start.getDate() + days);
        endInput.value = end.toISOString().split('T')[0];
        daysCount.textContent = days;
    }
    startInput.addEventListener('change', updateEndDate);
    updateEndDate();
</script>
{% endblock %}''',

    'templates/bookings.html': '''{% extends "base.html" %}
{% block title %}Đơn thuê{% endblock %}
{% block content %}
<h2>Đơn thuê của bạn</h2>
<table class="table">
    <thead>
        <tr>
            <th>Mã</th><th>Xe</th><th>Thời gian</th><th>Tổng</th><th>Trạng thái</th><th></th>
        </tr>
    </thead>
    <tbody>
        {% for b in bookings %}
        <tr>
            <td>{{ b.rental_id }}</td>
            <td>{{ b.brand }} {{ b.model }}</td>
            <td>Giao: {{ b.start_datetime }} → Trả: {{ b.end_datetime }}</td>
            <td>{{ format_vnd(b.total_amount) }}</td>
            <td>
                <span class="badge bg-{%
                    if b.status=='pending' %}warning{% 
                    elif b.status=='confirmed' %}success{% 
                    elif b.status=='rejected' %}danger{% 
                    elif b.status=='completed' %}info{% 
                    else %}secondary{% endif %}">
                    {{ {'pending':'Chờ duyệt','confirmed':'Đã duyệt','rejected':'Từ chối','cancelled':'Đã hủy','completed':'Hoàn thành'}.get(b.status, b.status) }}
                </span>
            </td>
            <td>
                {% if b.status == 'pending' %}
                <form method="post" action="/bookings/cancel/{{ b.rental_id }}" class="d-inline">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button class="btn btn-danger btn-sm">Hủy</button>
                </form>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}''',

    'templates/admin/dashboard.html': '''{% extends "base.html" %}
{% block title %}Admin Dashboard{% endblock %}
{% block content %}
<div class="row">
    <div class="col-md-6 mb-3">
        <div class="card text-white bg-primary">
            <div class="card-body">
                <h5>Quản lý xe</h5>
                <a href="/admin/vehicles" class="btn btn-light">Xem danh sách xe</a>
            </div>
        </div>
    </div>
    <div class="col-md-6 mb-3">
        <div class="card text-white bg-success">
            <div class="card-body">
                <h5>Quản lý thành viên</h5>
                <a href="/admin/users" class="btn btn-light">Xem tài khoản</a>
            </div>
        </div>
    </div>
    <div class="col-md-6 mb-3">
        <div class="card text-white bg-info">
            <div class="card-body">
                <h5>Quản lý đơn thuê</h5>
                <a href="/admin/orders" class="btn btn-light">Xem đơn thuê</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}''',

    'templates/admin/vehicles.html': '''{% extends "base.html" %}
{% block title %}Quản lý xe{% endblock %}
{% block content %}
<h1>Quản lý xe</h1>
<div class="mb-3">
    <a href="/admin/vehicles/add" class="btn btn-success">+ Thêm xe</a>
    <a href="/admin" class="btn btn-secondary">Dashboard</a>
</div>
<form method="get" class="mb-3">
    <input type="text" name="q" class="form-control w-25 d-inline" placeholder="Tìm biển số, hãng..." value="{{ search }}">
    <button class="btn btn-primary">Tìm</button>
</form>
<table class="table table-hover">
    <thead class="table-dark"><tr><th>Ảnh</th><th>Biển số</th><th>Xe</th><th>Loại</th><th>Giá/ngày</th><th></th></tr></thead>
    <tbody>
        {% for v in vehicles %}
        <tr>
            <td><img src="/static/uploads/{{ v.image_path }}" width="60" class="rounded" onerror="this.src='/static/uploads/default.jpg'"></td>
            <td>{{ v.registration_no }}</td>
            <td>{{ v.brand }} {{ v.model }} ({{ v.year }})</td>
            <td>{{ v.type_name }} - {{ v.seats }} chỗ</td>
            <td>{{ format_vnd(v.daily_rate) }}</td>
            <td>
                <form method="post" action="/admin/vehicles/toggle/{{ v.vehicle_id }}" class="d-inline">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button class="btn btn-{{ 'warning' if v.status == 'available' else 'success' }} btn-sm">
                        {{ 'Khóa xe' if v.status == 'available' else 'Mở khóa' }}
                    </button>
                </form>
                <form method="post" action="/admin/vehicles/delete/{{ v.vehicle_id }}" class="d-inline">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button class="btn btn-danger btn-sm" onclick="return confirm('Xóa xe này?')">Xóa</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<nav>
    <ul class="pagination">
        {% if page > 1 %}<li class="page-item"><a class="page-link" href="?q={{ search }}&page={{ page-1 }}">Trước</a></li>{% endif %}
        <li class="page-item disabled"><span class="page-link">Trang {{ page }}/{{ total_pages }}</span></li>
        {% if page < total_pages %}<li class="page-item"><a class="page-link" href="?q={{ search }}&page={{ page+1 }}">Sau</a></li>{% endif %}
    </ul>
</nav>
{% endblock %}''',

    'templates/admin/add_vehicle.html': '''{% extends "base.html" %}
{% block title %}Thêm xe{% endblock %}
{% block content %}
<h1>Thêm xe mới</h1>
<form method="post" enctype="multipart/form-data">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="mb-3"><input type="text" name="reg_no" placeholder="Biển số" class="form-control" required></div>
    <div class="mb-3"><input type="text" name="brand" placeholder="Hãng" class="form-control" required></div>
    <div class="mb-3"><input type="text" name="model" placeholder="Tên xe" class="form-control" required></div>
    <div class="mb-3">
        <select name="type_id" class="form-control" required>
            {% for t in types %}<option value="{{ t.type_id }}">{{ t.type_name }}</option>{% endfor %}
        </select>
    </div>
    <div class="mb-3"><input type="number" name="year" placeholder="Năm SX" class="form-control" value="2020"></div>
    <div class="mb-3"><input type="number" name="daily_rate" placeholder="Giá/ngày (VNĐ)" class="form-control" required></div>
    <div class="mb-3"><input type="number" name="seats" placeholder="Số chỗ" class="form-control" value="4"></div>
    <div class="mb-3"><textarea name="description" placeholder="Mô tả" class="form-control"></textarea></div>
    <div class="mb-3"><input type="file" name="image" class="form-control" accept="image/*"></div>
    <button type="submit" class="btn btn-success">Thêm xe</button>
    <a href="/admin/vehicles" class="btn btn-secondary">Hủy</a>
</form>
{% endblock %}''',

    'templates/admin/users.html': '''{% extends "base.html" %}
{% block title %}Quản lý thành viên{% endblock %}
{% block content %}
<h1>Quản lý thành viên</h1>
<div class="mb-3">
    <a href="/admin" class="btn btn-secondary">Dashboard</a>
</div>
<form method="get" class="mb-3">
    <input type="text" name="q" class="form-control w-25 d-inline" placeholder="Tìm tên, email, CCCD..." value="{{ search }}">
    <button class="btn btn-primary">Tìm</button>
</form>
<table class="table table-hover">
    <thead class="table-dark"><tr><th>ID</th><th>Họ tên</th><th>Email</th><th>SĐT</th><th>CCCD</th><th>Trạng thái</th><th></th></tr></thead>
    <tbody>
        {% for u in users %}
        <tr>
            <td>{{ u.user_id }}</td>
            <td>{{ u.name }}</td>
            <td>{{ u.email }}</td>
            <td>{{ u.phone }}</td>
            <td>{{ u.cccd }}</td>
            <td><span class="badge bg-{{ 'success' if not u.is_locked else 'danger' }}">{{ 'Hoạt động' if not u.is_locked else 'Bị khóa' }}</span></td>
            <td>
                <form method="post" action="/admin/users/toggle/{{ u.user_id }}" class="d-inline">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button class="btn btn-{{ 'warning' if not u.is_locked else 'success' }} btn-sm">
                        {{ 'Khóa' if not u.is_locked else 'Mở khóa' }}
                    </button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<nav>
    <ul class="pagination">
        {% if page > 1 %}<li class="page-item"><a class="page-link" href="?q={{ search }}&page={{ page-1 }}">Trước</a></li>{% endif %}
        <li class="page-item disabled"><span class="page-link">Trang {{ page }}/{{ total_pages }}</span></li>
        {% if page < total_pages %}<li class="page-item"><a class="page-link" href="?q={{ search }}&page={{ page+1 }}">Sau</a></li>{% endif %}
    </ul>
</nav>
{% endblock %}''',

    'templates/admin/orders.html': '''{% extends "base.html" %}
{% block title %}Quản lý đơn thuê{% endblock %}
{% block content %}
<h1>Quản lý đơn thuê</h1>
<div class="mb-3">
    <a href="/admin" class="btn btn-secondary">Dashboard</a>
</div>
<form method="get" class="mb-3">
    <select name="status" class="form-select w-auto d-inline" onchange="this.form.submit()">
        <option value="all" {% if status_filter=='all' %}selected{% endif %}>Tất cả</option>
        <option value="pending" {% if status_filter=='pending' %}selected{% endif %}>Chờ duyệt</option>
        <option value="confirmed" {% if status_filter=='confirmed' %}selected{% endif %}>Đã duyệt</option>
        <option value="rejected" {% if status_filter=='rejected' %}selected{% endif %}>Từ chối</option>
    </select>
</form>
<table class="table table-sm table-hover">
    <thead class="table-dark">
        <tr><th>Mã</th><th>Khách</th><th>Xe</th><th>Thời gian</th><th>Địa điểm</th><th>Tổng</th><th>Trạng thái</th><th>Hành động</th></tr>
    </thead>
    <tbody>
        {% for o in orders %}
        <tr>
            <td><strong>#{{ o.rental_id }}</strong></td>
            <td><small><b>{{ o.user_name }}</b><br>{{ o.email }}<br>{{ o.phone }} | CCCD: {{ o.cccd }}</small></td>
            <td><small>{{ o.brand }} {{ o.model }}<br>Biển: {{ o.registration_no }}</small></td>
            <td><small>Giao: {{ o.start_datetime }}<br>Trả: {{ o.end_datetime }}</small></td>
            <td><small>Nhận: {{ o.pickup_location }}<br>Trả: {{ o.dropoff_location }}</small></td>
            <td><strong>{{ format_vnd(o.total_amount) }}</strong></td>
            <td>
                <span class="badge bg-{% if o.status=='pending' %}warning{% elif o.status=='confirmed' %}success{% else %}danger{% endif %}">
                    {{ {'pending':'Chờ duyệt','confirmed':'Đã duyệt','rejected':'Từ chối'}[o.status] }}
                </span>
            </td>
            <td>
                {% if o.status == 'pending' %}
                    <form method="post" action="/admin/orders/approve/{{ o.rental_id }}" class="d-inline">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        <button class="btn btn-success btn-sm">Duyệt</button>
                    </form>
                    <form method="post" action="/admin/orders/reject/{{ o.rental_id }}" class="d-inline">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        <button class="btn btn-danger btn-sm">Từ chối</button>
                    </form>
                {% elif o.status == 'confirmed' %}
                    <form method="post" action="/admin/orders/return/{{ o.rental_id }}" class="d-inline">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        <button class="btn btn-info btn-sm">Đánh dấu đã trả</button>
                    </form>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
<nav>
    <ul class="pagination">
        {% if page > 1 %}<li class="page-item"><a class="page-link" href="?status={{ status_filter }}&page={{ page-1 }}">Trước</a></li>{% endif %}
        <li class="page-item disabled"><span class="page-link">Trang {{ page }}/{{ total_pages }}</span></li>
        {% if page < total_pages %}<li class="page-item"><a class="page-link" href="?status={{ status_filter }}&page={{ page+1 }}">Sau</a></li>{% endif %}
    </ul>
</nav>
{% endblock %}''',
}

# Ghi file HTML
for path, content in HTML_FILES.items():
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip())

# === KHỞI TẠO DB ===
def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY, name TEXT, address TEXT, phone TEXT, cccd TEXT UNIQUE,
            email TEXT UNIQUE, password_hash TEXT, license TEXT, is_locked INTEGER DEFAULT 0, role TEXT DEFAULT 'member'
        );
        CREATE TABLE IF NOT EXISTS VehicleTypes (type_id INTEGER PRIMARY KEY, type_name TEXT);
        CREATE TABLE IF NOT EXISTS Vehicles (
            vehicle_id INTEGER PRIMARY KEY, registration_no TEXT UNIQUE, model TEXT, brand TEXT,
            type_id INTEGER, year INTEGER, daily_rate REAL, seats INTEGER, description TEXT,
            image_path TEXT DEFAULT 'default.jpg', status TEXT DEFAULT 'available'
        );
        CREATE TABLE IF NOT EXISTS Rentals (
            rental_id INTEGER PRIMARY KEY, user_id INTEGER, vehicle_id INTEGER,
            start_datetime TEXT, end_datetime TEXT, pickup_location TEXT, dropoff_location TEXT,
            total_amount REAL, payment_method TEXT, status TEXT DEFAULT 'pending'
        );
    ''')
    if cur.execute("SELECT COUNT(*) FROM VehicleTypes").fetchone()[0] == 0:
        cur.executemany("INSERT INTO VehicleTypes (type_name) VALUES (?)", [('Car',), ('Motorcycle',), ('Van',)])
        cur.executemany("""INSERT OR IGNORE INTO Vehicles
            (registration_no, model, brand, type_id, year, daily_rate, seats, image_path, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            ('51H-12345', 'Vios', 'Toyota', 1, 2022, 800000, 5, 'default.jpg', 'Xe sedan 5 chỗ, tiết kiệm nhiên liệu'),
            ('29A-67890', 'Wave Alpha', 'Honda', 2, 2023, 150000, 2, 'default.jpg', 'Xe máy phổ thông, bền bỉ'),
            ('30E-55555', 'Hiace', 'Toyota', 3, 2021, 1500000, 16, 'default.jpg', 'Xe 16 chỗ, rộng rãi cho đoàn'),
        ])
    if not cur.execute("SELECT * FROM Users WHERE email='admin@gmail.com'").fetchone():
        cur.execute("INSERT INTO Users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                    ('Admin', 'admin@gmail.com', hash_password('admin123')))
    conn.commit()
    conn.close()
init_db()

# === KIỂM TRA XUNG ĐỘT ===
def is_vehicle_booked(conn, vehicle_id, start_dt, end_dt):
    return conn.execute("SELECT 1 FROM Rentals WHERE vehicle_id = ? AND status IN ('pending', 'confirmed') AND ? < end_datetime AND ? > start_datetime",
                        (vehicle_id, start_dt, end_dt)).fetchone() is not None

# === ROUTES ===
@app.route('/')
def index():
    conn = get_db()
    q = request.args.get('q', '')
    sql = '''SELECT v.*, t.type_name FROM Vehicles v JOIN VehicleTypes t ON v.type_id = t.type_id'''
    params = []
    if q:
        sql += " WHERE v.brand LIKE ? OR v.model LIKE ? OR t.type_name LIKE ?"
        like = f'%{q}%'
        params = [like, like, like]
    vehicles = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('index.html', vehicles=vehicles)

@app.route('/vehicle/<int:vid>')
def vehicle_detail(vid):
    conn = get_db()
    v = conn.execute('SELECT v.*, t.type_name FROM Vehicles v JOIN VehicleTypes t ON v.type_id = t.type_id WHERE vehicle_id=?', (vid,)).fetchone()
    conn.close()
    if not v:
        flash('Xe không tồn tại!', 'danger')
        return redirect('/')
    return render_template('vehicle_detail.html', vehicle=v)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        user = conn.execute("SELECT * FROM Users WHERE email=?", (request.form['email'],)).fetchone()
        conn.close()
        if user and check_password(user['password_hash'], request.form['password']) and not user['is_locked']:
            session.update(user_id=user['user_id'], role=user['role'], name=user['name'])
            flash('Đăng nhập thành công!', 'success')
            return redirect('/')
        flash('Sai thông tin hoặc tài khoản bị khóa', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        required = ['name', 'email', 'password', 'phone', 'address', 'cccd', 'license']
        for field in required:
            if not request.form.get(field):
                flash(f'Vui lòng nhập: {field}', 'danger')
                return render_template('register.html')
        if len(request.form['password']) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự!', 'danger')
            return render_template('register.html')
        cccd, phone = request.form['cccd'], request.form['phone']
        if not (cccd.isdigit() and len(cccd) == 12):
            flash('CCCD phải đúng 12 số!', 'danger')
            return render_template('register.html')
        if not (phone.isdigit() and len(phone) in [10, 11]):
            flash('Số điện thoại phải 10 hoặc 11 số!', 'danger')
            return render_template('register.html')
        conn = get_db()
        try:
            conn.execute("""INSERT INTO Users (name, address, phone, cccd, email, password_hash, license)
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                         (request.form['name'], request.form['address'], phone, cccd,
                          request.form['email'], hash_password(request.form['password']), request.form['license']))
            conn.commit()
            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('Email hoặc CCCD đã được sử dụng!', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# === GIỎ HÀNG ===
@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect('/login')
    try:
        vehicle_id = int(request.form['vehicle_id'])
        days = max(1, int(request.form.get('days', 1)))
    except:
        flash('Dữ liệu không hợp lệ!', 'danger')
        return redirect('/')
    conn = get_db()
    vehicle = conn.execute("SELECT status FROM Vehicles WHERE vehicle_id=?", (vehicle_id,)).fetchone()
    conn.close()
    if not vehicle or vehicle['status'] != 'available':
        flash('Xe không khả dụng!', 'danger')
        return redirect('/')
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append({'vehicle_id': vehicle_id, 'days': days})
    session.modified = True
    flash('Đã thêm vào giỏ!', 'success')
    return redirect('/vehicle/' + str(vehicle_id))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    items, total = [], 0
    total_days = 0
    for item in session.get('cart', []):
        v = conn.execute("SELECT * FROM Vehicles WHERE vehicle_id=?", (item['vehicle_id'],)).fetchone()
        if v:
            subtotal = v['daily_rate'] * item['days']
            total += subtotal
            total_days += item['days']
            items.append({'vehicle': v, 'days': item['days'], 'subtotal': subtotal})
    conn.close()
    return render_template('cart.html', cart=items, total=total, days_total=total_days)

@app.route('/cart/remove/<int:i>')
def remove_from_cart(i):
    if 'cart' in session and 0 <= i < len(session['cart']):
        session['cart'].pop(i)
        session.modified = True
    return redirect('/cart')

@app.route('/cart/update/<int:i>/<int:days>')
def update_cart_days(i, days):
    if 'cart' in session and 0 <= i < len(session['cart']):
        session['cart'][i]['days'] = max(1, days)
        session.modified = True
    return '', 204

# === CHECKOUT ===
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session or not session.get('cart'):
        return redirect('/')
    if request.method == 'POST':
        start_str = request.form.get('start')
        end_str = request.form.get('end')
        pickup = request.form.get('pickup')
        dropoff = request.form.get('dropoff')
        if not all([start_str, end_str, pickup, dropoff]):
            flash('Vui lòng điền đầy đủ!', 'danger')
            return redirect('/checkout')
        try:
            start_dt = datetime.strptime(start_str, '%Y-%m-%d')
            end_dt = datetime.strptime(end_str, '%Y-%m-%d')
        except:
            flash('Ngày không hợp lệ!', 'danger')
            return redirect('/checkout')
        if start_dt.date() < datetime.now().date():
            flash('Ngày nhận xe không được trong quá khứ!', 'danger')
            return redirect('/checkout')
        total_days = sum(item['days'] for item in session['cart'])
        expected_end = start_dt + timedelta(days=total_days)
        if end_dt.date() != expected_end.date():
            flash('Ngày trả xe không khớp! (Phải là ngày nhận + số ngày thuê)', 'danger')
            return redirect('/checkout')
        conn = get_db()
        try:
            for item in session['cart']:
                if is_vehicle_booked(conn, item['vehicle_id'], start_str, end_str):
                    flash(f'Xe ID {item["vehicle_id"]} đã được đặt!', 'danger')
                    return redirect('/cart')
            for item in session['cart']:
                v = conn.execute("SELECT daily_rate FROM Vehicles WHERE vehicle_id=?", (item['vehicle_id'],)).fetchone()
                total = v['daily_rate'] * item['days']
                conn.execute("""INSERT INTO Rentals
                    (user_id, vehicle_id, start_datetime, end_datetime, pickup_location, dropoff_location, total_amount, payment_method, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'cod', 'pending')""",
                    (session['user_id'], item['vehicle_id'], start_str, end_str, pickup, dropoff, total))
            conn.commit()
            session['cart'] = []
            session.modified = True
            flash('Đặt xe thành công! Chờ duyệt.', 'success')
            return redirect('/bookings')
        except Exception as e:
            conn.rollback()
            flash(f'Lỗi: {str(e)}', 'danger')
        finally:
            conn.close()
    return render_template('checkout.html', cart=session.get('cart', []))

# === BOOKINGS ===
@app.route('/bookings')
def bookings():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    bookings = conn.execute('''SELECT r.*, v.brand, v.model FROM Rentals r
                               JOIN Vehicles v ON r.vehicle_id = v.vehicle_id
                               WHERE r.user_id = ? ORDER BY r.rental_id DESC''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('bookings.html', bookings=bookings)

@app.route('/bookings/cancel/<int:rid>', methods=['POST'])
def cancel_booking(rid):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    booking = conn.execute("SELECT status, vehicle_id FROM Rentals WHERE rental_id=? AND user_id=?", (rid, session['user_id'])).fetchone()
    if not booking:
        flash('Đơn không tồn tại!', 'danger')
    elif booking['status'] != 'pending':
        flash('Chỉ có thể hủy đơn đang chờ duyệt!', 'danger')
    else:
        conn.execute("UPDATE Rentals SET status='cancelled' WHERE rental_id=?", (rid,))
        conn.commit()
        flash('Đã hủy đơn!', 'success')
    conn.close()
    return redirect('/bookings')

# === ADMIN ===
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/')
    return render_template('admin/dashboard.html')

@app.route('/admin/vehicles')
def admin_vehicles():
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    q = request.args.get('q', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = 10
    offset = (page - 1) * per_page
    sql = '''SELECT v.*, t.type_name FROM Vehicles v JOIN VehicleTypes t ON v.type_id = t.type_id'''
    params = []
    if q:
        sql += " WHERE v.registration_no LIKE ? OR v.brand LIKE ? OR v.model LIKE ?"
        like = f'%{q}%'
        params = [like, like, like]
    total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page
    sql += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    vehicles = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('admin/vehicles.html', vehicles=vehicles, search=q, page=page, total_pages=total_pages)

@app.route('/admin/vehicles/add', methods=['GET', 'POST'])
def admin_add_vehicle():
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    types = conn.execute("SELECT * FROM VehicleTypes").fetchall()
    if request.method == 'POST':
        try:
            reg_no = request.form['reg_no'].strip()
            brand = request.form['brand'].strip()
            model = request.form['model'].strip()
            type_id = int(request.form['type_id'])
            year = int(request.form['year'])
            daily_rate = float(request.form['daily_rate'])
            seats = int(request.form['seats'])
            description = request.form.get('description', '').strip()

            image_path = 'default.jpg'
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    name, ext = os.path.splitext(filename)
                    filename = f"{secrets.token_hex(8)}{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    try:
                        with Image.open(filepath) as img:
                            img.thumbnail((800, 600))
                            img.save(filepath)
                    except Exception as e:
                        print(f"Resize error: {e}")
                    image_path = filename

            conn.execute("""INSERT INTO Vehicles 
                (registration_no, brand, model, type_id, year, daily_rate, seats, description, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (reg_no, brand, model, type_id, year, daily_rate, seats, description, image_path))
            conn.commit()
            flash('Thêm xe thành công!', 'success')
            return redirect('/admin/vehicles')
        except Exception as e:
            conn.rollback()
            flash(f'Lỗi: {str(e)}', 'danger')
        finally:
            conn.close()
    conn.close()
    return render_template('admin/add_vehicle.html', types=types)

@app.route('/admin/vehicles/toggle/<int:vid>', methods=['POST'])
def admin_toggle_vehicle(vid):
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    try:
        vehicle = conn.execute("SELECT status FROM Vehicles WHERE vehicle_id=?", (vid,)).fetchone()
        if vehicle:
            new_status = 'rented' if vehicle['status'] == 'available' else 'available'
            conn.execute("UPDATE Vehicles SET status=? WHERE vehicle_id=?", (new_status, vid))
            conn.commit()
            flash(f'Đã {"khóa" if new_status == "rented" else "mở khóa"} xe!', 'success')
    except:
        flash('Lỗi!', 'danger')
    finally:
        conn.close()
    return redirect('/admin/vehicles')

@app.route('/admin/vehicles/delete/<int:vid>', methods=['POST'])
def admin_delete_vehicle(vid):
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    try:
        vehicle = conn.execute("SELECT image_path FROM Vehicles WHERE vehicle_id=?", (vid,)).fetchone()
        conn.execute("DELETE FROM Vehicles WHERE vehicle_id=?", (vid,))
        if vehicle and vehicle['image_path'] != 'default.jpg':
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], vehicle['image_path'])
            if os.path.exists(img_path):
                os.remove(img_path)
        conn.commit()
        flash('Xóa xe thành công!', 'success')
    except:
        flash('Lỗi khi xóa xe!', 'danger')
    finally:
        conn.close()
    return redirect('/admin/vehicles')

@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    q = request.args.get('q', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = 10
    offset = (page - 1) * per_page
    sql = "SELECT * FROM Users WHERE role='member'"
    params = []
    if q:
        sql += " AND (name LIKE ? OR email LIKE ? OR cccd LIKE ?)"
        like = f'%{q}%'
        params = [like, like, like]
    total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page
    sql += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    users = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('admin/users.html', users=users, search=q, page=page, total_pages=total_pages)

@app.route('/admin/users/toggle/<int:uid>', methods=['POST'])
def admin_toggle_user(uid):
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    try:
        user = conn.execute("SELECT is_locked FROM Users WHERE user_id=?", (uid,)).fetchone()
        if user:
            new_lock = 0 if user['is_locked'] else 1
            conn.execute("UPDATE Users SET is_locked=? WHERE user_id=?", (new_lock, uid))
            conn.commit()
            flash(f'Đã {"mở khóa" if new_lock == 0 else "khóa"} tài khoản!', 'success')
    except:
        flash('Lỗi!', 'danger')
    finally:
        conn.close()
    return redirect('/admin/users')

@app.route('/admin/orders')
def admin_orders():
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    status_filter = request.args.get('status', 'all')
    page = max(1, int(request.args.get('page', 1)))
    per_page = 10
    offset = (page - 1) * per_page
    sql = '''SELECT r.*, u.name AS user_name, u.email, u.phone, u.cccd, v.brand, v.model, v.registration_no
             FROM Rentals r JOIN Users u ON r.user_id = u.user_id JOIN Vehicles v ON r.vehicle_id = v.vehicle_id'''
    params = []
    if status_filter != 'all':
        sql += " WHERE r.status = ?"
        params.append(status_filter)
    total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page
    sql += " ORDER BY r.rental_id DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    orders = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('admin/orders.html', orders=orders, status_filter=status_filter, page=page, total_pages=total_pages)

@app.route('/admin/orders/approve/<int:rid>', methods=['POST'])
def admin_approve_order(rid):
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    try:
        conn.execute("UPDATE Rentals SET status='confirmed' WHERE rental_id=? AND status='pending'", (rid,))
        conn.execute("UPDATE Vehicles SET status='rented' WHERE vehicle_id=(SELECT vehicle_id FROM Rentals WHERE rental_id=?)", (rid,))
        conn.commit()
        flash('Đã duyệt đơn!', 'success')
    except:
        flash('Lỗi duyệt đơn!', 'danger')
    finally:
        conn.close()
    return redirect('/admin/orders')

@app.route('/admin/orders/reject/<int:rid>', methods=['POST'])
def admin_reject_order(rid):
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    try:
        conn.execute("UPDATE Rentals SET status='rejected' WHERE rental_id=? AND status='pending'", (rid,))
        conn.commit()
        flash('Đã từ chối đơn!', 'danger')
    except:
        flash('Lỗi!', 'danger')
    finally:
        conn.close()
    return redirect('/admin/orders')

@app.route('/admin/orders/return/<int:rid>', methods=['POST'])
def admin_return_order(rid):
    if session.get('role') != 'admin':
        return redirect('/')
    conn = get_db()
    try:
        conn.execute("UPDATE Rentals SET status='completed' WHERE rental_id=? AND status='confirmed'", (rid,))
        conn.execute("UPDATE Vehicles SET status='available' WHERE vehicle_id=(SELECT vehicle_id FROM Rentals WHERE rental_id=?)", (rid,))
        conn.commit()
        flash('Đã xác nhận trả xe!', 'info')
    except:
        flash('Lỗi!', 'danger')
    finally:
        conn.close()
    return redirect('/admin/orders')

# === KHỞI ĐỘNG ===
def open_browser():
    time.sleep(2)
    webbrowser.open('http://localhost:5000')

threading.Thread(target=open_browser, daemon=True).start()

print("="*60)
print("HỆ THỐNG CHO THUÊ XE ĐÃ SẴN SÀNG!")
print("MỞ: http://localhost:5000")
print("ADMIN: admin@gmail.com / admin123")
print("="*60)

if __name__ == '__main__':
    app.run(debug=False, port=5000)