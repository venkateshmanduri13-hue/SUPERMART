import http.server
import socketserver
import sqlite3
import json
import urllib.parse
import urllib.request
import uuid
import hashlib
import os
import random
from http import cookies

DB_FILE = "supermart.db"
SECRET_KEY = "SUPERMART_SECRET_KEY_PRO_2026"
ADMIN_WHATSAPP = "917670912836"
ADMIN_PIN = "630528"

# INTEGRATED FAST2SMS API KEY FOR REAL SMS OTP
FAST2SMS_API_KEY = "Fg9wyaCS8sRbiGeX1WpU6zVqAjc2m4TNLI5PuQOYHtrDfv0K3h5eT8MqEkZ0WnoCVRpwGh6xNufXBi29"

SESSIONS = {}
PENDING_REGISTRATIONS = {}

def hash_pw(pw):
    return hashlib.sha256((pw + SECRET_KEY).encode()).hexdigest()

def send_real_sms_otp(phone, otp):
    """Sends real OTP SMS automatically to customer phone via Fast2SMS API"""
    try:
        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {
            "authorization": FAST2SMS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "route": "otp",
            "variables_values": str(otp),
            "numbers": str(phone)
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as resp:
            res_body = resp.read().decode('utf-8')
            print("Fast2SMS API Response:", res_body)
            return True
    except Exception as e:
        print("SMS Dispatch Error:", e)
        return False

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        address TEXT,
        pincode TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        brand TEXT NOT NULL,
        price REAL NOT NULL,
        orig_price REAL NOT NULL,
        specs TEXT,
        image TEXT NOT NULL,
        rating REAL DEFAULT 4.5,
        reviews_count INTEGER DEFAULT 85
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        UNIQUE(user_id, product_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS wishlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        UNIQUE(user_id, product_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        pincode TEXT NOT NULL,
        address TEXT NOT NULL,
        subtotal REAL NOT NULL,
        delivery_charge REAL NOT NULL,
        total REAL NOT NULL,
        status TEXT DEFAULT 'Day 1: Packed & Ready',
        items TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        samples = [
            ("Aashirvaad Sharbati Whole Wheat Atta 5kg", "Groceries", "Aashirvaad", 240, 290, "100% Pure MP Sharbati Wheat, Stone Ground, High Dietary Fibre", "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80"),
            ("Fortune Sunlite Refined Sunflower Cooking Oil 1L", "Groceries", "Fortune", 135, 170, "Fortified with Vitamin A & D, Triple Refined Light Oil", "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=600&q=80"),
            ("India Gate Classic Aged Basmati Rice 1kg", "Groceries", "India Gate", 175, 230, "Extra Long Grain Basmati, Aged 2 Years, Non-Sticky Fragrance", "https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=600&q=80"),
            ("Fresh Organic Farm Red Tomatoes 1kg", "Vegetables", "FreshFarm", 35, 45, "Naturally Ripened, Rich in Lycopene, Direct From Local Farmers", "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=600&q=80"),
            ("Farm Fresh Green Capsicum / Shimla Mirch 500g", "Vegetables", "FreshFarm", 40, 55, "Crispy, Pesticide-Free, Packed With Vitamin C", "https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?auto=format&fit=crop&w=600&q=80"),
            ("Farm Fresh Organic Potatoes (Aloo) 1kg", "Vegetables", "FreshFarm", 30, 40, "Handpicked Clean Skin Potatoes, Ideal for Daily Curries & Fries", "https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=600&q=80"),
            ("Amul Pure Clarified Cow Ghee Jar 1L", "Dairy", "Amul", 595, 680, "Traditional Granular Texture, Rich Aromatic Cow Clarified Butter", "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=600&q=80"),
            ("Apple iPhone 15 (Blue, 128 GB)", "Electronics", "Apple", 65999, 79900, "128 GB ROM | 6.1 inch Super Retina XDR Display | 48MP Dual Camera", "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=600&q=80"),
            ("boAt Airdopes 141 Bluetooth Wireless Earbuds", "Electronics", "boAt", 1199, 4490, "42 Hours Battery, Low Latency Beast Mode, IPX4 Water Resistance", "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=600&q=80"),
            ("Surf Excel Quick Wash Front & Top Detergent 1kg", "Household", "Surf Excel", 155, 190, "Removes Tough Stains in 1 Wash, Safe for Color & Fabric", "https://images.unsplash.com/photo-1584813470613-5b1c1cad3d69?auto=format&fit=crop&w=600&q=80")
        ]
        c.executemany("INSERT INTO products (name, category, brand, price, orig_price, specs, image) VALUES (?, ?, ?, ?, ?, ?, ?)", samples)
        conn.commit()
    conn.close()

PWA_MANIFEST = {
    "name": "Supermart Online Store",
    "short_name": "Supermart",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#f8fafc",
    "theme_color": "#9333ea",
    "orientation": "portrait",
    "icons": [
        {"src": "https://cdn-icons-png.flaticon.com/512/3081/3081840.png", "sizes": "192x192", "type": "image/png"},
        {"src": "https://cdn-icons-png.flaticon.com/512/3081/3081840.png", "sizes": "512x512", "type": "image/png"}
    ]
}

PWA_SW_JS = """
const CACHE_NAME = 'supermart-cache-v16';
const ASSETS = ['/', '/manifest.json'];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.map((k) => k !== CACHE_NAME && caches.delete(k)))));
  return self.clients.claim();
});
self.addEventListener('fetch', (e) => {
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
"""

CUSTOMER_HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>SUPERMART - Online Smart Shopping</title>
  
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#9333ea">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/3081/3081840.png">

  <style>
    :root {{
      --primary: #9333ea;
      --primary-dark: #7e22ce;
      --accent: #ec4899;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --border: #e2e8f0;
      --text: #0f172a;
      --muted: #64748b;
      --whatsapp: #25d366;
      --shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }}

    body.dark-mode {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: Roboto, -apple-system, sans-serif; -webkit-tap-highlight-color: transparent; }}
    
    body {{
      background: var(--bg);
      color: var(--text);
      padding-bottom: 75px;
      min-height: 100vh;
      transition: background 0.3s ease, color 0.3s ease;
    }}

    .top-bar {{
      position: sticky; top: 0; z-index: 1000;
      background: var(--card-bg);
      backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--border);
      padding: 10px 14px;
      transition: background 0.3s ease;
    }}
    .header-row1 {{ display: flex; justify-content: space-between; align-items: center; }}
    .brand-logo {{ font-size: 20px; font-weight: 900; color: var(--primary); display: flex; align-items: center; gap: 6px; cursor: pointer; }}
    .brand-logo span {{ background: linear-gradient(135deg, #9333ea, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    
    .top-icons {{ display: flex; gap: 10px; align-items: center; }}
    
    .icon-2d-btn {{
      width: 38px; height: 38px; border-radius: 50%;
      background: var(--card-bg); border: 1px solid var(--border);
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 2px 5px rgba(0,0,0,0.04); position: relative; cursor: pointer;
      transition: transform 0.15s ease;
    }}
    .icon-2d-btn:active {{ transform: scale(0.92); }}
    body.dark-mode .icon-2d-btn svg {{ stroke: #f8fafc; fill: #f8fafc; }}
    
    .icon-badge-num {{
      position: absolute; top: -3px; right: -3px;
      background: #ef4444; color: #fff; font-size: 10px; font-weight: bold;
      width: 17px; height: 17px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
    }}
    
    .search-container {{ margin-top: 8px; position: relative; }}
    .search-input {{
      width: 100%; height: 42px; border: 1px solid var(--border);
      border-radius: 24px; padding: 0 42px 0 38px; font-size: 13px;
      outline: none; background: var(--card-bg); color: var(--text);
      box-shadow: inset 0 1px 2px rgba(0,0,0,0.03);
    }}
    .search-left-icon {{ position: absolute; left: 14px; top: 11px; color: var(--muted); font-size: 15px; }}
    .search-right-icon {{ position: absolute; right: 14px; top: 10px; color: var(--muted); font-size: 16px; cursor: pointer; }}

    .delivery-strip {{
      background: var(--card-bg); padding: 9px 14px; font-size: 12px; font-weight: bold; color: var(--text);
      display: none; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border);
      cursor: pointer;
    }}

    .circles-strip {{
      display: flex; gap: 14px; overflow-x: auto; padding: 12px 14px;
      background: var(--card-bg); border-bottom: 1px solid var(--border);
    }}
    .circles-strip::-webkit-scrollbar {{ display: none; }}
    .circle-item {{ display: flex; flex-direction: column; align-items: center; min-width: 66px; cursor: pointer; }}
    .circle-2d-box {{
      width: 52px; height: 52px; border-radius: 50%;
      background: var(--bg); border: 1.5px solid var(--border);
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 2px 5px rgba(0,0,0,0.03); transition: transform 0.15s, border-color 0.15s;
    }}
    body.dark-mode .circle-2d-box svg {{ stroke: #cbd5e1; }}
    .circle-item.active .circle-2d-box {{ border-color: var(--primary); background: #fdf4ff; transform: scale(1.06); }}
    .circle-label {{ font-size: 11px; font-weight: bold; margin-top: 5px; color: var(--text); text-align: center; white-space: nowrap; }}

    .sort-filter-bar {{
      display: flex; justify-content: space-between; align-items: center;
      background: var(--card-bg); padding: 8px 14px; border-bottom: 1px solid var(--border);
      font-size: 13px; font-weight: 700; color: var(--muted);
    }}
    .sort-select {{ border: none; background: transparent; font-weight: bold; color: var(--primary); outline: none; font-size: 13px; cursor: pointer; }}

    .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; padding: 10px; }}
    .card {{
      background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px;
      padding: 10px; display: flex; flex-direction: column; position: relative;
      box-shadow: var(--shadow); cursor: pointer;
    }}
    .card-heart {{
      position: absolute; top: 8px; right: 8px; background: var(--card-bg);
      border: 1px solid var(--border); width: 30px; height: 30px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 2;
    }}
    
    .card-img-wrap {{
      width: 100%; height: 155px; border-radius: 8px; overflow: hidden;
      margin-bottom: 8px; background: var(--bg);
    }}
    .card-img-wrap img {{
      width: 100%; height: 100%; object-fit: cover; object-position: center;
      transition: transform 0.2s ease;
    }}
    .card:hover .card-img-wrap img {{ transform: scale(1.04); }}
    
    .mall-tag {{
      background: #6b21a8; color: #fff; font-size: 10px; font-weight: 900; padding: 2px 6px; border-radius: 4px; width: fit-content; margin-bottom: 4px;
    }}
    .card-name {{ font-size: 13px; font-weight: 700; height: 34px; overflow: hidden; line-height: 1.3; margin-bottom: 4px; color: var(--text); }}
    .price-row {{ display: flex; align-items: baseline; gap: 6px; }}
    .price-now {{ font-size: 16px; font-weight: 900; color: var(--text); }}
    .price-mrp {{ font-size: 12px; color: var(--muted); text-decoration: line-through; }}
    .price-off {{ font-size: 12px; color: #16a34a; font-weight: 800; }}
    
    .rating-pill {{
      background: #15803d; color: #fff; font-size: 11px; font-weight: 800;
      padding: 1px 6px; border-radius: 12px; display: inline-flex; align-items: center; gap: 2px; width: fit-content; margin: 4px 0 8px 0;
    }}

    .btn-cart {{
      background: linear-gradient(135deg, var(--primary), var(--primary-dark));
      color: #fff; border: none; border-radius: 8px; padding: 10px 0;
      font-size: 13px; font-weight: 800; cursor: pointer; width: 100%; margin-top: auto;
    }}

    .product-view-sheet {{
      background: var(--card-bg); border-radius: 12px; padding: 16px; margin-bottom: 75px; box-shadow: var(--shadow);
    }}
    .pdp-img-box {{
      width: 100%; height: 260px; display: flex; align-items: center; justify-content: center; position: relative;
      background: var(--bg); border-radius: 10px; margin-bottom: 14px; overflow:hidden;
    }}
    .pdp-img-box img {{ width: 100%; height: 100%; object-fit: contain; }}
    .offer-box {{ background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2); border-radius: 8px; padding: 12px; margin: 14px 0; }}
    .trust-badges {{
      display: flex; justify-content: space-around; background: var(--bg); border: 1px solid var(--border);
      border-radius: 8px; padding: 12px; margin: 14px 0; text-align: center; font-size: 11px; font-weight: bold;
    }}
    .related-scroll {{ display: flex; gap: 10px; overflow-x: auto; padding: 10px 0; }}
    .related-scroll::-webkit-scrollbar {{ display: none; }}
    .related-card {{
      min-width: 140px; max-width: 140px; background: var(--card-bg); border: 1px solid var(--border);
      border-radius: 8px; padding: 8px; cursor: pointer; flex-shrink: 0;
    }}

    .pdp-bottom-bar {{
      position: fixed; bottom: 0; left: 0; right: 0; height: 60px;
      background: var(--card-bg); border-top: 1px solid var(--border); display: flex; z-index: 1000;
    }}
    .btn-pdp-cart {{ flex: 1; background: var(--card-bg); color: var(--text); border: none; font-weight: bold; font-size: 14px; cursor: pointer; }}
    .btn-pdp-buy {{ flex: 1; background: #ff9f00; color: #fff; border: none; font-weight: bold; font-size: 14px; cursor: pointer; }}

    .timeline {{ margin: 14px 0 10px 0; padding-left: 10px; border-left: 2px solid var(--border); }}
    .timeline-step {{ position: relative; padding-bottom: 12px; padding-left: 16px; font-size: 12px; }}
    .timeline-step::before {{
      content: ''; position: absolute; left: -6px; top: 2px; width: 10px; height: 10px;
      border-radius: 50%; background: var(--muted);
    }}
    .timeline-step.done {{ color: #16a34a; font-weight: bold; }}
    .timeline-step.done::before {{ background: #16a34a; }}
    .timeline-step.current {{ color: #2563eb; font-weight: 900; }}
    .timeline-step.current::before {{ background: #2563eb; box-shadow: 0 0 0 3px #bfdbfe; }}

    .meesho-item-row {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 15px 12px; border-bottom: 1px solid var(--border); cursor: pointer;
      background: var(--card-bg); text-decoration: none; color: var(--text);
    }}
    .meesho-item-row:active {{ background: var(--bg); }}
    .meesho-item-left {{ display: flex; align-items: center; gap: 12px; font-size: 14px; font-weight: 500; }}

    .btn-big {{
      width: 100%; min-height: 46px; border: none; border-radius: 8px;
      font-size: 14px; font-weight: 800; cursor: pointer; display: flex;
      align-items: center; justify-content: center; gap: 6px; text-decoration: none;
    }}
    .btn-primary {{ background: var(--primary); color: #fff; }}
    .btn-orange {{ background: #ea580c; color: #fff; }}
    .btn-whatsapp {{ background: var(--whatsapp); color: #fff; }}
    .btn-outline-red {{ background: transparent; border: 1px solid #ef4444; color: #ef4444; }}

    .screen {{ display: none; padding: 12px; }}
    .screen.active {{ display: block; }}
    .sheet {{
      background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px;
      padding: 16px; margin-bottom: 12px; box-shadow: var(--shadow);
    }}

    .modal {{
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);
      z-index: 2000; display: none; align-items: center; justify-content: center; padding: 14px;
    }}
    .modal-box {{
      background: var(--card-bg); color: var(--text); width: 100%; max-width: 440px; max-height: 90vh;
      border-radius: 14px; overflow-y: auto; padding: 20px; position: relative;
    }}
    .modal-close {{ position: absolute; top: 12px; right: 16px; font-size: 24px; font-weight: bold; cursor: pointer; border: none; background: transparent; color: var(--text); }}

    #locationModal .modal-box {{
      position: fixed; bottom: 0; left: 0; right: 0; max-width: 100%;
      border-radius: 16px 16px 0 0; padding: 20px 16px 30px 16px;
    }}

    .bottom-nav {{
      position: fixed; bottom: 0; left: 0; right: 0; height: 60px;
      background: var(--card-bg); border-top: 1px solid var(--border);
      display: flex; justify-content: space-around; align-items: center; z-index: 1000;
      transition: background 0.3s ease;
    }}
    .nav-btn {{
      background: none; border: none; font-size: 11px; font-weight: 700;
      color: var(--muted); display: flex; flex-direction: column; align-items: center; gap: 3px; flex: 1; cursor: pointer;
    }}
    .nav-btn.active {{ color: var(--primary); }}
    .nav-btn svg {{ stroke: var(--muted); }}
    .nav-btn.active svg {{ stroke: var(--primary); fill: rgba(147,51,234,0.12); }}

    .toast {{
      position: fixed; top: 75px; left: 50%; transform: translateX(-50%);
      background: #0f172a; color: #fff; padding: 10px 20px; border-radius: 30px;
      font-size: 13px; font-weight: 700; z-index: 9999; display: none; box-shadow: var(--shadow);
    }}

    #offlineOverlay {{
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(255, 255, 255, 0.96); z-index: 999999;
      display: none; flex-direction: column; align-items: center; justify-content: center; padding: 24px; text-align: center;
    }}
    .offline-dog-img {{
      width: 220px; height: 220px; border-radius: 20px; object-fit: cover;
      box-shadow: 0 10px 25px rgba(0,0,0,0.15); margin-bottom: 20px; border: 3px solid #e9d5ff;
    }}

    #pwaInstallBanner {{
      background: linear-gradient(135deg, #1e1b4b, #312e81); color: #fff;
      padding: 10px 14px; display: none; justify-content: space-between; align-items: center;
      font-size: 13px; font-weight: bold;
    }}
  </style>
</head>
<body>

  <div id="pwaInstallBanner">
    <span>📲 Install Supermart App for faster shopping!</span>
    <button onclick="triggerPWAInstall()" style="background:#22c55e; color:#fff; border:none; padding:6px 12px; border-radius:6px; font-weight:bold; cursor:pointer;">INSTALL</button>
  </div>

  <div id="offlineOverlay">
    <img class="offline-dog-img" src="https://cdn.phototourl.com/free/2026-09-11-91ddede7-9160-4e0a-885b-2f1f0256fb17.jpg" alt="No Connection Dog">
    <h2 style="color:var(--text); font-size: 20px; margin-bottom: 8px;">Waiting for Connection...</h2>
    <p style="color:var(--muted); font-size: 14px; max-width: 280px; line-height: 1.4; margin-bottom: 20px;">
      Looks like your internet connection took a walk! Please turn on Wi-Fi or Mobile Data.
    </p>
    <button class="btn-big btn-primary" onclick="window.location.reload()" style="max-width:200px;">🔄 Try Reconnecting</button>
  </div>

  <div id="toast" class="toast"></div>

  <header class="top-bar" id="mainHeader">
    <div class="header-row1">
      <div class="brand-logo" onclick="switchView('shop')">
        <span>🛍️ SUPERMART</span>
      </div>
      <div class="top-icons">
        <div class="icon-2d-btn" onclick="switchView('wishlist')" title="Wishlist">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1e1b4b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
          </svg>
          <span class="icon-badge-num" id="wishCount">0</span>
        </div>

        <div class="icon-2d-btn" onclick="switchView('cart')" title="Cart">
          <svg width="19" height="19" viewBox="0 0 24 24" fill="#1e1b4b">
            <path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49c.08-.14.12-.31.12-.48 0-.55-.45-1-1-1H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/>
          </svg>
          <span class="icon-badge-num" id="cartCount">0</span>
        </div>

        <div class="icon-2d-btn" id="userAuthBtn" onclick="handleAuthClick()" title="Profile" style="width:auto; padding:0 10px; border-radius:20px; font-size:12px; font-weight:bold;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1e1b4b" stroke-width="2" style="margin-right:4px;">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <span id="userAuthText">Login</span>
        </div>
      </div>
    </div>
    
    <div class="search-container" id="mainSearchBar">
      <span class="search-left-icon">🔍</span>
      <input type="text" id="searchInput" class="search-input" placeholder="Search Atta, Oil, Tomato, Phone..." onkeyup="filterAndSortItems()">
      <span class="search-right-icon" onclick="clearSearch()">✖</span>
    </div>
  </header>

  <div class="delivery-strip" id="pincodeStrip" onclick="openLocationModal()">
    <div style="display:flex; align-items:center; gap:6px;">
      <span>📍</span>
      <span id="deliveringToText">Delivering to: Select delivery location</span>
    </div>
    <span>❯</span>
  </div>

  <section id="shopScreen" class="screen active" style="padding:0;">
    <div class="circles-strip">
      <div class="circle-item active" onclick="selectCircleCategory('All', this)">
        <div class="circle-2d-box">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#9333ea" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
        </div>
        <span class="circle-label" id="catAll">All Items</span>
      </div>

      <div class="circle-item" onclick="selectCircleCategory('Groceries', this)">
        <div class="circle-2d-box">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>
        </div>
        <span class="circle-label">Groceries</span>
      </div>

      <div class="circle-item" onclick="selectCircleCategory('Vegetables', this)">
        <div class="circle-2d-box">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2"><path d="M12 2a9 9 0 0 1 9 9c0 7-9 11-9 11S3 18 3 11a9 9 0 0 1 9-9z"></path></svg>
        </div>
        <span class="circle-label">Veggies</span>
      </div>

      <div class="circle-item" onclick="selectCircleCategory('Dairy', this)">
        <div class="circle-2d-box">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2"><path d="M8 2h8l2 5v13a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V7l2-5z"></path></svg>
        </div>
        <span class="circle-label">Dairy</span>
      </div>

      <div class="circle-item" onclick="selectCircleCategory('Electronics', this)">
        <div class="circle-2d-box">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>
        </div>
        <span class="circle-label">Gadgets</span>
      </div>

      <div class="circle-item" onclick="selectCircleCategory('Household', this)">
        <div class="circle-2d-box">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>
        </div>
        <span class="circle-label">Home</span>
      </div>
    </div>

    <div class="sort-filter-bar">
      <span>Showing: <strong id="currentCatLabel" style="color:var(--primary);">All Products</strong></span>
      <div>
        <span>Sort: </span>
        <select id="sortSelect" class="sort-select" onchange="filterAndSortItems()">
          <option value="default">Relevance</option>
          <option value="low">Price: Low to High</option>
          <option value="high">Price: High to Low</option>
          <option value="rating">Top Rated</option>
        </select>
      </div>
    </div>

    <div class="grid" id="productGrid"></div>
  </section>

  <section id="pdpScreen" class="screen" style="padding:10px;">
    <button onclick="switchView('shop')" style="background:none; border:none; color:var(--primary); font-size:14px; font-weight:bold; margin-bottom:10px; cursor:pointer;">
      ⬅ Back to Products
    </button>
    
    <div class="product-view-sheet">
      <div class="pdp-img-box">
        <img id="pdpImg" src="">
        <div class="card-heart" id="pdpHeart" style="top:10px; right:10px;">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="#ef4444" stroke="#ef4444"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
        </div>
      </div>
      
      <span id="pdpBrand" style="color:var(--muted); font-size:12px; font-weight:800; text-transform:uppercase;"></span>
      <h2 id="pdpTitle" style="font-size:16px; margin:4px 0 8px 0;"></h2>
      
      <div style="display:flex; align-items:center; gap:8px;">
        <span id="pdpRating" class="rating-pill"></span>
        <span id="pdpReviews" style="font-size:12px; color:var(--muted);"></span>
      </div>

      <div class="price-row" style="margin: 10px 0;">
        <span id="pdpPrice" class="price-now" style="font-size:24px;"></span>
        <span id="pdpMvp" class="price-mrp" style="font-size:16px;"></span>
        <span id="pdpOff" class="price-off" style="font-size:16px;"></span>
      </div>

      <div class="offer-box">
        <div style="font-weight:bold; color:#1e40af; font-size:13px; margin-bottom:4px;">🏷️ Special Delivery Timeline</div>
        <p style="font-size:12px; color:#3b82f6;">Standard items: Fast delivery | Electronics & combos: 3-4 days procurement to doorstep.</p>
      </div>

      <div class="trust-badges">
        <div>🚚<br>Doorstep Delivery</div>
        <div>💵<br>Cash on Delivery</div>
        <div>🛡️<br>Supermart Assured</div>
      </div>

      <h4 style="margin-top:16px;">Product Specifications:</h4>
      <p id="pdpSpecs" style="color:#475569; font-size:13px; line-height:1.5; margin:6px 0 16px 0;"></p>

      <hr style="border:none; border-top:1px solid #e2e8f0; margin:16px 0;">

      <h3 style="font-size:15px; margin-bottom:8px;">Similar & Related Products</h3>
      <div class="related-scroll" id="relatedGrid"></div>
    </div>

    <div class="pdp-bottom-bar" id="pdpBottomBar">
      <button class="btn-pdp-cart" id="pdpAddToCartBtn">ADD TO CART</button>
      <button class="btn-pdp-buy" id="pdpBuyNowBtn">BUY NOW</button>
    </div>
  </section>

  <section id="cartScreen" class="screen">
    <div class="sheet">
      <h3>Shopping Basket (<span id="cartCountTitle">0</span>)</h3>
      <div id="cartListHolder" style="margin: 14px 0;"></div>

      <div style="border-top: 1px solid var(--border); padding-top: 12px; font-size: 14px;">
        <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
          <span>Items Subtotal:</span>
          <strong>₹<span id="cartSubtotal">0</span></strong>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom: 8px; color: #ea580c;">
          <span>Delivery Charges:</span>
          <strong>₹<span id="cartDelivery">0</span></strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size: 18px; font-weight: 900; border-top: 1px dashed var(--border); padding-top: 8px;">
          <span>Total Payable:</span>
          <span style="color: var(--primary);">₹<span id="cartTotal">0</span></span>
        </div>
      </div>

      <button class="btn-big btn-orange" style="margin-top: 16px;" onclick="goToCheckout()">PROCEED TO CHECKOUT ➔</button>
    </div>
  </section>

  <section id="checkoutScreen" class="screen">
    <div class="sheet">
      <h3>Confirm Delivery Address</h3>
      <form onsubmit="handlePlaceOrder(event)" style="display: grid; gap: 10px; margin-top: 14px;">
        <input type="text" id="chkName" placeholder="Full Receiver Name" required style="padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background:var(--card-bg); color:var(--text);">
        <input type="tel" id="chkPhone" placeholder="10-digit Phone Number" pattern="[0-9]{{10}}" required style="padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background:var(--card-bg); color:var(--text);">
        
        <div style="display:grid; grid-template-columns: 1fr auto; gap: 8px; align-items:center;">
          <input type="text" id="chkPincode" placeholder="6-digit Pincode" pattern="[0-9]{{6}}" required oninput="handlePincodeLookup(this.value)" style="padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background:var(--card-bg); color:var(--text);">
          <button type="button" onclick="detectGPSLocation()" style="background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; padding:10px; border-radius:6px; font-size:12px; font-weight:bold; cursor:pointer;">🎯 Auto GPS</button>
        </div>
        <div id="pincodeStatus" style="font-size:11px; color:var(--muted); font-weight:bold;"></div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px;">
          <input type="text" id="chkMandal" placeholder="Mandal / City" required style="padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background:var(--bg); color:var(--text);">
          <input type="text" id="chkDistrict" placeholder="District & State" required style="padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background:var(--bg); color:var(--text);">
        </div>

        <textarea id="chkAddress" placeholder="Complete Street, Flat/Door No, Landmark" required style="padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; height: 65px; background:var(--card-bg); color:var(--text);"></textarea>

        <div style="background: rgba(236,72,153,0.1); border: 1px solid rgba(236,72,153,0.3); padding: 12px; border-radius: 6px; font-size: 13px; font-weight: 700; color: #db2777;">
          💵 Cash / UPI On Delivery Available (Safe & Verified)
        </div>

        <button type="submit" class="btn-big btn-primary">CONFIRM & PLACE ORDER NOW</button>
      </form>
    </div>
  </section>

  <section id="orderSuccessScreen" class="screen">
    <div class="sheet" style="text-align: center; padding: 30px 16px;">
      <div style="font-size: 55px; margin-bottom: 12px;">🎉</div>
      <h2 style="color: var(--primary); margin-bottom: 6px;">Congrats!</h2>
      <h3 style="margin-bottom: 12px;">Your order has been placed successfully!</h3>
      <p style="color: var(--muted); font-size: 14px; margin-bottom: 20px;">Order ID: <strong id="successOrderId">#</strong><br>Our partner will deliver to your doorstep as per the live timeline.</p>
      
      <a id="waSupportLink" href="https://wa.me/{ADMIN_WHATSAPP}" target="_blank" class="btn-big btn-whatsapp" style="margin-bottom:10px;">
        💬 Chat on WhatsApp with Store
      </a>

      <button class="btn-big btn-primary" onclick="switchView('orders')">TRACK MY LIVE ORDER 📦</button>
    </div>
  </section>

  <section id="ordersScreen" class="screen">
    <div class="sheet">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
        <h3>My Orders & Live Timeline</h3>
        <button onclick="loadOrders()" style="background:var(--bg); border:1px solid var(--border); color:var(--text); padding:6px 12px; border-radius:4px; font-weight:bold; cursor:pointer;">🔄 Refresh</button>
      </div>
      <div id="ordersFeed"></div>
    </div>
  </section>

  <section id="wishlistScreen" class="screen">
    <div class="sheet">
      <h3>My Wishlist ❤️</h3>
      <div id="wishlistFeed" style="margin-top: 12px;"></div>
    </div>
  </section>

  <section id="profileScreen" class="screen" style="padding:10px 12px;">
    <div style="display:flex; justify-content:space-between; align-items:center; background:var(--card-bg); padding:16px; border-radius:12px; margin-bottom:12px; box-shadow:var(--shadow); border:1px solid var(--border);">
      <div style="display:flex; align-items:center; gap:12px;">
        <div style="width:50px; height:50px; border-radius:50%; background:#f3e8ff; border:2px solid #e9d5ff; display:flex; align-items:center; justify-content:center; font-size:24px;">
          🧑‍💼
        </div>
        <div>
          <strong style="font-size:16px;" id="accUserName">+91 Mobile User</strong><br>
          <span style="font-size:12px; color:var(--muted);" id="accUserPhone">Supermart Member</span>
        </div>
      </div>
      <span style="color:var(--muted); font-size:18px;">❯</span>
    </div>

    <div style="display:flex; gap:10px; margin-bottom:14px;">
      <a href="https://wa.me/{ADMIN_WHATSAPP}?text=Hello%20Supermart%20Support" target="_blank" style="flex:1; background:var(--card-bg); border:1px solid var(--border); border-radius:10px; padding:14px; text-align:center; text-decoration:none; color:var(--text); box-shadow:0 1px 3px rgba(0,0,0,0.03);">
        <div style="font-size:20px; margin-bottom:4px;">📞</div>
        <strong style="font-size:13px;">Help Centre</strong>
      </a>
      <div onclick="openLangModal()" style="flex:1; background:var(--card-bg); border:1px solid var(--border); border-radius:10px; padding:14px; text-align:center; cursor:pointer; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
        <div style="font-size:20px; margin-bottom:4px;">🌐</div>
        <strong style="font-size:13px;">Change Language</strong>
      </div>
    </div>

    <div style="background:var(--card-bg); border:1px solid var(--border); border-radius:12px; overflow:hidden; box-shadow:var(--shadow); margin-bottom:14px;">
      <div style="padding:12px 14px 6px 14px; font-size:12px; font-weight:bold; color:var(--muted); text-transform:uppercase;">
        Account Settings & Activity
      </div>

      <div class="meesho-item-row" onclick="toggleDarkMode()">
        <div class="meesho-item-left">
          <span id="darkModeIcon">🌙</span>
          <span id="darkModeText">Switch to Dark / Light Mode</span>
        </div>
        <span style="font-size:12px; font-weight:bold; background:var(--bg); padding:4px 8px; border-radius:6px; border:1px solid var(--border);" id="darkModeStatus">Auto</span>
      </div>

      <div class="meesho-item-row" onclick="openEditProfileModal()">
        <div class="meesho-item-left">
          <span>📍</span>
          <span>Delivery Address & Profile Details</span>
        </div>
        <span style="color:var(--muted);">❯</span>
      </div>

      <div class="meesho-item-row" onclick="openPasswordModal()">
        <div class="meesho-item-left">
          <span>🔐</span>
          <span>Update Account Password</span>
        </div>
        <span style="color:var(--muted);">❯</span>
      </div>

      <div class="meesho-item-row" onclick="switchView('orders')">
        <div class="meesho-item-left">
          <span>📦</span>
          <span>My Orders & Live Timeline</span>
        </div>
        <span style="color:var(--muted);">❯</span>
      </div>

      <div class="meesho-item-row" onclick="switchView('wishlist')">
        <div class="meesho-item-left">
          <span>❤️</span>
          <span>Wishlisted Products</span>
        </div>
        <span style="color:var(--muted);">❯</span>
      </div>

      <div class="meesho-item-row" onclick="openLangModal()">
        <div class="meesho-item-left">
          <span>🌐</span>
          <span>Change App Language</span>
        </div>
        <span style="color:var(--muted);">❯</span>
      </div>

      <a href="https://wa.me/{ADMIN_WHATSAPP}?text=Hello%20Supermart%20Support" target="_blank" class="meesho-item-row">
        <div class="meesho-item-left">
          <span>💬</span>
          <span>WhatsApp Customer Support</span>
        </div>
        <span style="color:var(--muted);">❯</span>
      </a>
    </div>

    <button class="btn-big btn-outline-red" style="border-radius:10px; background:var(--card-bg);" onclick="logout()">LOGOUT ACCOUNT</button>
  </section>

  <!-- PASSWORD MODAL -->
  <div class="modal" id="passwordModal">
    <div class="modal-box">
      <button class="modal-close" onclick="closePasswordModal()">&times;</button>
      <h3 style="margin-bottom: 14px;">🔐 Update Account Password</h3>
      <form onsubmit="handleChangePassword(event)" style="display:grid; gap:10px;">
        <input type="password" id="newPassInput" placeholder="Enter New Password" required style="padding:10px; border:1px solid var(--border); border-radius:6px; font-size:14px; background:var(--bg); color:var(--text);">
        <button type="submit" class="btn-big btn-primary">SAVE NEW PASSWORD</button>
      </form>
    </div>
  </div>

  <!-- LANGUAGE MODAL -->
  <div class="modal" id="langModal">
    <div class="modal-box">
      <button class="modal-close" onclick="closeLangModal()">&times;</button>
      <h3 style="margin-bottom: 14px;">🌐 Select App Language</h3>
      <div style="display:grid; gap:10px;">
        <button class="btn-big" style="background:var(--bg); border:1px solid var(--border); color:var(--text);" onclick="changeLanguage('en'); closeLangModal();">English (Default)</button>
        <button class="btn-big" style="background:#fdf4ff; border:1px solid #e9d5ff; color:#9333ea; font-weight:bold;" onclick="changeLanguage('te'); closeLangModal();">తెలుగు (Telugu)</button>
        <button class="btn-big" style="background:#f0fdf4; border:1px solid #bbf7d0; color:#16a34a; font-weight:bold;" onclick="changeLanguage('hi'); closeLangModal();">हिन्दी (Hindi)</button>
      </div>
    </div>
  </div>

  <!-- EDIT PROFILE MODAL -->
  <div class="modal" id="editProfileModal">
    <div class="modal-box">
      <button class="modal-close" onclick="closeEditProfileModal()">&times;</button>
      <h3 style="margin-bottom: 14px;">✏️ Edit Delivery Address</h3>
      <form onsubmit="handleSaveProfile(event)" style="display:grid; gap:10px;">
        <label style="font-size:12px; font-weight:bold;">Your Name:</label>
        <input type="text" id="epName" placeholder="Full Name" required style="padding:10px; border:1px solid var(--border); border-radius:6px; font-size:14px; background:var(--bg); color:var(--text);">
        
        <label style="font-size:12px; font-weight:bold;">Postal Pincode:</label>
        <input type="text" id="epPincode" placeholder="6-digit Pincode" pattern="[0-9]{{6}}" required style="padding:10px; border:1px solid var(--border); border-radius:6px; font-size:14px; background:var(--bg); color:var(--text);">
        
        <label style="font-size:12px; font-weight:bold;">Complete Address (Door No, Street, Village/City):</label>
        <textarea id="epAddress" placeholder="Street, Flat/Door No, Landmark" required style="padding:10px; border:1px solid var(--border); border-radius:6px; font-size:14px; height:75px; background:var(--bg); color:var(--text);"></textarea>

        <button type="submit" class="btn-big btn-primary" style="margin-top:6px;">SAVE ADDRESS</button>
      </form>
    </div>
  </div>

  <!-- LOCATION SHEET -->
  <div class="modal" id="locationModal">
    <div class="modal-box">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <h3 style="font-size:16px;">Select delivery address</h3>
        <button class="modal-close" onclick="closeLocationModal()" style="position:static; font-size:20px;">&times;</button>
      </div>

      <div style="position:relative; margin-bottom:14px;">
        <span style="position:absolute; left:12px; top:11px; color:var(--muted);">🔍</span>
        <input type="text" id="locSearchPincode" placeholder="Search by pincode (e.g. 532427)" onkeyup="if(event.key==='Enter') quickSetPincode(this.value)" style="width:100%; padding:10px 10px 10px 34px; border:1px solid var(--border); border-radius:8px; font-size:13px; background:var(--bg); color:var(--text);">
      </div>

      <div onclick="detectGPSLocation()" style="display:flex; gap:12px; align-items:center; padding:12px; background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.3); border-radius:8px; cursor:pointer; margin-bottom:14px;">
        <div style="background:#22c55e; color:#fff; width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:16px;">🎯</div>
        <div>
          <strong style="color:#15803d; font-size:13px;">Use my current location</strong><br>
          <small style="color:var(--muted); font-size:11px;">Tap to fetch GPS location automatically</small>
        </div>
      </div>

      <hr style="border:none; border-top:1px dashed var(--border); margin:14px 0;">
      
      <div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:8px;">Saved Address:</div>
      <div id="savedAddressInModal" style="font-size:13px; color:var(--text); line-height:1.4;">
        No address saved yet. Sign In or enter pincode above.
      </div>
    </div>
  </div>

  <!-- AUTH MODAL WITH FAST2SMS OTP -->
  <div class="modal" id="authModal">
    <div class="modal-box" style="max-width: 380px;">
      <button class="modal-close" onclick="closeAuthModal()">&times;</button>
      <h2 id="authTitle" style="margin-bottom: 14px;">Sign In with Mobile</h2>
      
      <form id="authMainForm" onsubmit="handleAuthSubmit(event)" style="display:grid; gap:10px;">
        <input type="tel" id="authPhone" placeholder="10-digit Mobile Number" pattern="[0-9]{{10}}" required style="width:100%; padding:10px; border:1px solid var(--border); border-radius:6px; font-size:14px; background:var(--bg); color:var(--text);">
        <input type="password" id="authPassword" placeholder="Enter Password" required style="width:100%; padding:10px; border:1px solid var(--border); border-radius:6px; font-size:14px; background:var(--bg); color:var(--text);">
        
        <div id="confirmPwGroup" style="display:none;">
          <input type="password" id="authConfirmPassword" placeholder="Confirm Password" style="width:100%; padding:10px; border:1px solid var(--border); border-radius:6px; font-size:14px; background:var(--bg); color:var(--text);">
        </div>

        <div id="forgotPwLink" style="text-align:right; font-size:12px;">
          <a href="https://wa.me/{ADMIN_WHATSAPP}?text=Hello%20Supermart,%20I%20forgot%20my%20login%20password.%20Please%20help%20me%20reset%20it." target="_blank" style="color:var(--primary); font-weight:bold; text-decoration:none;">Forgot Password?</a>
        </div>

        <button type="submit" class="btn-big btn-primary" id="authSubmitBtn">SIGN IN</button>
      </form>

      <div id="otpBox" style="display:none; text-align:center; margin-top:14px;">
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; padding:12px; border-radius:8px; margin-bottom:12px;">
          <strong style="color:#15803d; font-size:13px;">📩 SMS OTP Dispatched via Fast2SMS!</strong><br>
          <p style="font-size:11px; color:var(--muted); margin-top:4px;">Check your phone's SMS Messenger app for the 4-digit code.</p>
        </div>
        <input type="number" id="otpInput" placeholder="Enter 4-digit SMS OTP" style="width:100%; padding:12px; border:2px solid var(--primary); border-radius:6px; text-align:center; font-size:18px; letter-spacing:6px; margin-bottom:10px; background:var(--bg); color:var(--text);">
        <button class="btn-big btn-primary" onclick="verifyMobileOtp()">VERIFY & CREATE ACCOUNT</button>
      </div>

      <p style="margin-top: 14px; font-size: 13px; text-align: center; color: var(--muted);">
        <a href="javascript:void(0)" onclick="toggleAuthMode()" id="authSwitchLink" style="color: var(--primary); font-weight: bold; text-decoration:none;">New customer? Sign Up here</a>
      </p>
    </div>
  </div>

  <nav class="bottom-nav" id="mainBottomNav">
    <button class="nav-btn active" id="bShop" onclick="switchView('shop')">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>
      <span id="navHome">Home</span>
    </button>
    <button class="nav-btn" id="bCart" onclick="switchView('cart')">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
      <span id="navCart">Cart</span>
    </button>
    <button class="nav-btn" id="bOrders" onclick="switchView('orders')">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
      <span id="navOrders">Orders</span>
    </button>
    <button class="nav-btn" id="bProfile" onclick="switchView('profile')">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
      <span id="navAccount">Account</span>
    </button>
  </nav>

  <script>
    let products = [];
    let currentCategory = 'All';
    let currentUser = null;
    let isRegister = false;
    let activeProduct = null;
    let currentRegPhone = "";
    let currentLang = "en";

    const LANG_DATA = {{
      en: {{
        home: "Home", cart: "Cart", orders: "Orders", account: "Account",
        catAll: "All Items", searchPlace: "Search Atta, Oil, Tomato, Phone..."
      }},
      te: {{
        home: "హోమ్", cart: "కార్ట్", orders: "ఆర్డర్లు", account: "ఖాతా",
        catAll: "అన్నీ", searchPlace: "నూనె, బియ్యం, కూరగాయలు, ఫోన్ వెతకండి..."
      }},
      hi: {{
        home: "होम", cart: "कार्ट", orders: "ऑर्डर्स", account: "खाता",
        catAll: "सभी सामान", searchPlace: "आटा, तेल, सब्जियां, फोन खोजें..."
      }}
    }};

    function changeLanguage(lang) {{
      currentLang = lang;
      const d = LANG_DATA[lang] || LANG_DATA.en;
      document.getElementById('navHome').innerText = d.home;
      document.getElementById('navCart').innerText = d.cart;
      document.getElementById('navOrders').innerText = d.orders;
      document.getElementById('navAccount').innerText = d.account;
      document.getElementById('catAll').innerText = d.catAll;
      document.getElementById('searchInput').placeholder = d.searchPlace;
      localStorage.setItem('sm_lang', lang);
      toast("Language set to: " + (lang === 'te' ? "తెలుగు" : (lang === 'hi' ? "हिन्दी" : "English")));
    }}

    function toggleDarkMode() {{
      const isDark = document.body.classList.toggle('dark-mode');
      localStorage.setItem('sm_dark', isDark ? '1' : '0');
      updateDarkModeUI(isDark);
      toast(isDark ? "Dark Mode Enabled 🌙" : "Light Mode Enabled ☀️");
    }}

    function updateDarkModeUI(isDark) {{
      const icon = document.getElementById('darkModeIcon');
      const stat = document.getElementById('darkModeStatus');
      if(isDark) {{
        icon.innerText = "☀️";
        stat.innerText = "Dark";
      }} else {{
        icon.innerText = "🌙";
        stat.innerText = "Light";
      }}
    }}

    if(localStorage.getItem('sm_dark') === '1') {{
      document.body.classList.add('dark-mode');
      updateDarkModeUI(true);
    }}

    function openLangModal() {{ document.getElementById('langModal').style.display = 'flex'; }}
    function closeLangModal() {{ document.getElementById('langModal').style.display = 'none'; }}
    function openPasswordModal() {{ document.getElementById('passwordModal').style.display = 'flex'; }}
    function closePasswordModal() {{ document.getElementById('passwordModal').style.display = 'none'; }}

    let deferredPrompt;
    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.register('/sw.js').then(() => {{}});
    }}
    window.addEventListener('beforeinstallprompt', (e) => {{
      e.preventDefault();
      deferredPrompt = e;
      document.getElementById('pwaInstallBanner').style.display = 'flex';
    }});
    function triggerPWAInstall() {{
      if (deferredPrompt) {{
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((r) => {{
          if (r.outcome === 'accepted') document.getElementById('pwaInstallBanner').style.display = 'none';
          deferredPrompt = null;
        }});
      }} else {{
        alert("To install, tap browser menu (⋮) and select 'Add to Home screen'.");
      }}
    }}

    let audioCtx = null;
    function playTouchSound() {{
      try {{
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(800, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(400, audioCtx.currentTime + 0.04);
        gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.04);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.04);
      }} catch(e) {{}}
    }}
    document.addEventListener('click', function(e) {{
      if (e.target.closest('button') || e.target.closest('.card') || e.target.closest('.circle-item') || e.target.closest('.nav-btn') || e.target.closest('.icon-2d-btn')) {{
        playTouchSound();
      }}
    }}, true);

    function checkNetworkStatus() {{
      const overlay = document.getElementById('offlineOverlay');
      if (!navigator.onLine) overlay.style.display = 'flex';
      else overlay.style.display = 'none';
    }}
    window.addEventListener('online', checkNetworkStatus);
    window.addEventListener('offline', checkNetworkStatus);
    checkNetworkStatus();

    function toast(msg) {{
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.style.display = 'block';
      setTimeout(() => {{ t.style.display = 'none'; }}, 2800);
    }}

    async function handlePincodeLookup(pin) {{
      pin = pin.trim();
      const status = document.getElementById('pincodeStatus');
      if(pin.length === 6 && /^[0-9]+$/.test(pin)) {{
        status.innerText = "🔍 Checking Post Office & Mandal...";
        try {{
          const res = await fetch(`https://api.postalpincode.in/pincode/${{pin}}`);
          const data = await res.json();
          if(data && data[0].Status === "Success") {{
            const details = data[0].PostOffice[0];
            const mandal = details.Taluk || details.Block || details.Name;
            const dist = `${{details.District}}, ${{details.State}}`;
            
            document.getElementById('chkMandal').value = mandal;
            document.getElementById('chkDistrict').value = dist;
            status.innerText = `✓ Verified: ${{details.Name}}, ${{details.District}}`;
            status.style.color = "#16a34a";

            if(currentUser) {{
              syncLocationToProfile(pin, `${{details.Name}}, ${{mandal}}, ${{dist}}`);
            }}
          }} else {{
            status.innerText = "Pincode not found. Enter city manually.";
            status.style.color = "#ea580c";
          }}
        }} catch(e) {{ status.innerText = ""; }}
      }} else {{ status.innerText = ""; }}
    }}

    function detectGPSLocation() {{
      if(!navigator.geolocation) return toast("Geolocation not supported.");
      toast("Fetching live GPS coordinates...");
      navigator.geolocation.getCurrentPosition(async (pos) => {{
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        try {{
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{lat}}&lon=${{lon}}`);
          const data = await res.json();
          if(data && data.address) {{
            const addr = data.address;
            const place = addr.suburb || addr.town || addr.village || addr.city || "My Location";
            const pin = addr.postcode || "";

            const fullLoc = `Delivering to: ${{place}} ${{pin ? ('- ' + pin) : ''}}`;
            document.getElementById('deliveringToText').innerText = fullLoc;

            if(document.getElementById('chkPincode')) {{
              document.getElementById('chkPincode').value = pin;
              document.getElementById('chkMandal').value = place;
              document.getElementById('chkDistrict').value = `${{addr.state_district || ''}}, ${{addr.state || ''}}`;
            }}

            if(currentUser) {{
              const fullAddr = `${{place}}, ${{addr.state_district || ''}}, ${{addr.state || ''}}`;
              syncLocationToProfile(pin, fullAddr);
            }}

            toast(`Location set: ${{place}}`);
            closeLocationModal();
          }}
        }} catch(err) {{ toast("GPS fetched, but reverse address timed out."); }}
      }}, () => {{ toast("GPS Permission denied."); }});
    }}

    async function syncLocationToProfile(pin, addressStr) {{
      await fetch('/api/user/update-profile', {{
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({{
          name: currentUser.name || "Customer",
          pincode: pin,
          address: addressStr
        }})
      }});
      checkUserSession();
    }}

    function openLocationModal() {{
      if(currentUser && currentUser.address) {{
        document.getElementById('savedAddressInModal').innerText = `${{currentUser.name ? (currentUser.name + ' - ') : ''}}${{currentUser.address}} - PIN: ${{currentUser.pincode}}`;
      }}
      document.getElementById('locationModal').style.display = 'flex';
    }}
    function closeLocationModal() {{ document.getElementById('locationModal').style.display = 'none'; }}

    function quickSetPincode(pin) {{
      pin = pin.trim();
      if(pin.length === 6) {{
        document.getElementById('deliveringToText').innerText = `Delivering to: PIN - ${{pin}}`;
        handlePincodeLookup(pin);
        closeLocationModal();
        toast("Delivery location updated!");
      }} else {{ toast("Enter 6-digit valid pincode."); }}
    }}

    function openEditProfileModal() {{
      if(!currentUser) {{
        toast("Please Sign In first!");
        return openAuthModal();
      }}
      document.getElementById('epName').value = currentUser.name || '';
      document.getElementById('epPincode').value = currentUser.pincode || '';
      document.getElementById('epAddress').value = currentUser.address || '';
      document.getElementById('editProfileModal').style.display = 'flex';
    }}
    function closeEditProfileModal() {{ document.getElementById('editProfileModal').style.display = 'none'; }}

    async function handleSaveProfile(e) {{
      e.preventDefault();
      const payload = {{
        name: document.getElementById('epName').value.trim(),
        pincode: document.getElementById('epPincode').value.trim(),
        address: document.getElementById('epAddress').value.trim()
      }};

      const res = await fetch('/api/user/update-profile', {{
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      }});
      const d = await res.json();
      if(d.success) {{
        toast("Profile & Address saved successfully!");
        closeEditProfileModal();
        checkUserSession();
      }} else {{
        toast(d.message || "Failed to update address.");
      }}
    }}

    async function checkUserSession() {{
      const res = await fetch('/api/me');
      const data = await res.json();
      if(data.authenticated) {{
        currentUser = data.user;
        document.getElementById('userAuthText').innerText = currentUser.name ? currentUser.name.split(' ')[0] : currentUser.phone;
        document.getElementById('accUserName').innerText = currentUser.name || ("User: " + currentUser.phone);
        document.getElementById('accUserPhone').innerText = "+91 " + currentUser.phone;

        if(currentUser.address && currentUser.pincode) {{
          document.getElementById('deliveringToText').innerText = `Delivering to: ${{currentUser.address.slice(0, 18)}}... - ${{currentUser.pincode}}`;
        }}
      }} else {{
        currentUser = null;
        document.getElementById('userAuthText').innerText = "Login";
        document.getElementById('accUserName').innerText = "Guest User";
        document.getElementById('accUserPhone').innerText = "Click to Sign In";
        document.getElementById('deliveringToText').innerText = "Delivering to: Select delivery location";
      }}
      refreshCounts();
    }}

    async function loadCatalog() {{
      const res = await fetch('/api/products');
      products = await res.json();
      filterAndSortItems();
    }}

    function selectCircleCategory(cat, el) {{
      currentCategory = cat;
      document.querySelectorAll('.circle-item').forEach(c => c.classList.remove('active'));
      el.classList.add('active');
      document.getElementById('currentCatLabel').innerText = cat === 'All' ? 'All Products' : cat;
      filterAndSortItems();
    }}

    function clearSearch() {{
      document.getElementById('searchInput').value = '';
      filterAndSortItems();
    }}

    function calcLevenshtein(a, b) {{
      const m = a.length, n = b.length;
      const dp = Array.from({{ length: m + 1 }}, () => Array(n + 1).fill(0));
      for (let i = 0; i <= m; i++) dp[i][0] = i;
      for (let j = 0; j <= n; j++) dp[0][j] = j;
      for (let i = 1; i <= m; i++) {{
        for (let j = 1; j <= n; j++) {{
          if (a[i - 1] === b[j - 1]) dp[i][j] = dp[i - 1][j - 1];
          else dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
        }}
      }}
      return dp[m][n];
    }}

    function isFuzzyMatch(targetText, query) {{
      if (!query) return true;
      targetText = targetText.toLowerCase();
      query = query.toLowerCase();

      if (targetText.includes(query)) return true;

      const targetWords = targetText.split(/\\s+/);
      const queryWords = query.split(/\\s+/);

      return queryWords.every(qWord => {{
        if (qWord.length <= 2) return targetText.includes(qWord);
        return targetWords.some(tWord => {{
          if (tWord.includes(qWord) || qWord.includes(tWord)) return true;
          const maxAllowedErrors = qWord.length <= 4 ? 1 : 2;
          const dist = calcLevenshtein(qWord, tWord.slice(0, qWord.length + 1));
          return dist <= maxAllowedErrors;
        }});
      }});
    }}

    function filterAndSortItems() {{
      const q = document.getElementById('searchInput').value.trim();
      const sortType = document.getElementById('sortSelect').value;

      let filtered = products.filter(p => {{
        const catMatch = (currentCategory === 'All' || p.category === currentCategory);
        const searchPool = `${{p.name}} ${{p.brand}} ${{p.category}} ${{p.specs || ''}}`;
        const textMatch = isFuzzyMatch(searchPool, q);
        return catMatch && textMatch;
      }});

      if (sortType === 'low') filtered.sort((a, b) => a.price - b.price);
      else if (sortType === 'high') filtered.sort((a, b) => b.price - a.price);
      else if (sortType === 'rating') filtered.sort((a, b) => b.rating - a.rating);

      renderFeed(filtered);
    }}

    function renderFeed(items) {{
      const grid = document.getElementById('productGrid');
      if (items.length === 0) {{
        grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--muted);">No matching products found.</div>';
        return;
      }}

      grid.innerHTML = items.map(p => {{
        const discount = p.orig_price > p.price ? Math.round(((p.orig_price - p.price) / p.orig_price) * 100) : 0;
        return `
          <div class="card" onclick="openProductPage(${{p.id}})">
            <div class="card-heart" onclick="event.stopPropagation(); toggleWishlist(${{p.id}})">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="#ef4444" stroke="#ef4444"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
            </div>
            <div class="card-img-wrap">
              <img src="${{p.image}}" onerror="this.src='https://images.unsplash.com/photo-1542838132-92c53300491e?w=600'">
            </div>
            <div class="mall-tag">✓ Mall</div>
            <div class="card-name">${{p.name}}</div>
            <div class="price-row">
              <span class="price-now">₹${{p.price.toLocaleString()}}</span>
              <span class="price-mrp">₹${{p.orig_price.toLocaleString()}}</span>
              ${{discount > 0 ? `<span class="price-off">${{discount}}% off</span>` : ''}}
            </div>
            <div class="rating-pill">★ ${{p.rating}}</div>
            <button class="btn-cart" onclick="event.stopPropagation(); addToCart(${{p.id}})">+ Add to Cart</button>
          </div>
        `;
      }}).join('');
    }}

    function openProductPage(id) {{
      const p = products.find(x => x.id === id);
      if(!p) return;
      activeProduct = p;

      const discount = p.orig_price > p.price ? Math.round(((p.orig_price - p.price) / p.orig_price) * 100) : 0;
      document.getElementById('pdpImg').src = p.image;
      document.getElementById('pdpBrand').innerText = p.brand;
      document.getElementById('pdpTitle').innerText = p.name;
      document.getElementById('pdpRating').innerText = '★ ' + p.rating;
      document.getElementById('pdpReviews').innerText = '(' + p.reviews_count + ' reviews)';
      document.getElementById('pdpPrice').innerText = '₹' + p.price.toLocaleString();
      document.getElementById('pdpMvp').innerText = '₹' + p.orig_price.toLocaleString();
      document.getElementById('pdpOff').innerText = discount > 0 ? (discount + '% off') : '';
      document.getElementById('pdpSpecs').innerText = p.specs || 'Supermart Assured Genuine Quality Product with Fast Doorstep Delivery.';

      document.getElementById('pdpHeart').onclick = () => toggleWishlist(p.id);
      document.getElementById('pdpAddToCartBtn').onclick = () => addToCart(p.id);
      document.getElementById('pdpBuyNowBtn').onclick = () => buyNow(p.id);

      const related = products.filter(item => item.category === p.category && item.id !== p.id);
      const relGrid = document.getElementById('relatedGrid');
      
      if (related.length === 0) {{
        relGrid.innerHTML = '<div style="font-size:12px; color:var(--muted); padding:10px 0;">No other items in this category.</div>';
      }} else {{
        relGrid.innerHTML = related.map(r => `
          <div class="related-card" onclick="openProductPage(${{r.id}})">
            <img src="${{r.image}}" style="width:100%; height:90px; object-fit:cover; border-radius:6px; margin-bottom:4px;">
            <div style="font-size:11px; font-weight:bold; height:28px; overflow:hidden;">${{r.name}}</div>
            <div style="font-size:12px; font-weight:bold; color:var(--text); margin-top:4px;">₹${{r.price.toLocaleString()}}</div>
          </div>
        `).join('');
      }}

      switchView('pdp');
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    async function buyNow(id) {{
      await addToCart(id);
      switchView('cart');
    }}

    function switchView(name) {{
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

      const isPdp = (name === 'pdp');
      const isHome = (name === 'shop');
      const showLocation = (name === 'orders' || name === 'profile');

      document.getElementById('mainHeader').style.display = isPdp ? 'none' : 'block';
      document.getElementById('mainBottomNav').style.display = isPdp ? 'none' : 'flex';

      document.getElementById('mainSearchBar').style.display = isHome ? 'block' : 'none';
      document.getElementById('pincodeStrip').style.display = showLocation ? 'flex' : 'none';

      document.getElementById(name + 'Screen').classList.add('active');
      if(name === 'shop') document.getElementById('bShop').classList.add('active');
      if(name === 'cart') {{ document.getElementById('bCart').classList.add('active'); renderCart(); }}
      if(name === 'orders') {{ document.getElementById('bOrders').classList.add('active'); loadOrders(); }}
      if(name === 'profile') {{ document.getElementById('bProfile').classList.add('active'); checkUserSession(); }}
      if(name === 'wishlist') renderWishlist();
    }}

    async function addToCart(id) {{
      if(!currentUser) {{ toast("Please Sign In to add items!"); openAuthModal(); return; }}
      const res = await fetch('/api/cart/add', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ product_id: id }})
      }});
      const d = await res.json();
      if(d.success) {{
        toast("Added to Cart!");
        refreshCounts();
      }}
    }}

    async function toggleWishlist(id) {{
      if(!currentUser) {{ toast("Please Sign In first!"); openAuthModal(); return; }}
      const res = await fetch('/api/wishlist/toggle', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{ product_id: id }})
      }});
      const d = await res.json();
      toast(d.message);
      refreshCounts();
    }}

    async function refreshCounts() {{
      if(!currentUser) {{
        document.getElementById('cartCount').innerText = '0';
        document.getElementById('wishCount').innerText = '0';
        return;
      }}
      const [cRes, wRes] = await Promise.all([fetch('/api/cart'), fetch('/api/wishlist')]);
      const cData = await cRes.json();
      const wData = await wRes.json();
      document.getElementById('cartCount').innerText = cData.items ? cData.items.length : 0;
      document.getElementById('cartCountTitle').innerText = cData.items ? cData.items.length : 0;
      document.getElementById('wishCount').innerText = wData.items ? wData.items.length : 0;
    }}

    async function renderCart() {{
      if(!currentUser) {{
        document.getElementById('cartListHolder').innerHTML = '<p style="padding:20px 0; text-align:center;">Please Sign In to view basket.</p>';
        return;
      }}
      const res = await fetch('/api/cart');
      const d = await res.json();
      const items = d.items || [];
      const cont = document.getElementById('cartListHolder');

      if(items.length === 0) {{
        cont.innerHTML = '<p style="padding:20px 0; text-align:center; color:var(--muted);">Basket is empty!</p>';
        document.getElementById('cartSubtotal').innerText = '0';
        document.getElementById('cartDelivery').innerText = '0';
        document.getElementById('cartTotal').innerText = '0';
        return;
      }}

      let subtotal = 0;
      cont.innerHTML = items.map(i => {{
        subtotal += i.price * i.quantity;
        return `
          <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid var(--border);">
            <div>
              <strong>${{i.name}}</strong><br>
              <span style="color:var(--primary); font-weight:800;">₹${{i.price}} &times; ${{i.quantity}}</span>
            </div>
            <button onclick="removeCart(${{i.cart_id}})" style="background:#fee2e2; color:#ef4444; border:none; padding:6px 12px; border-radius:4px; font-weight:bold; cursor:pointer;">Remove</button>
          </div>
        `;
      }}).join('');

      let delivery = 0;
      if (subtotal > 0 && subtotal <= 50) delivery = Math.round((subtotal / 10) * 3);
      else if (subtotal > 50 && subtotal <= 100) delivery = Math.round((subtotal / 10) * 2);
      else if (subtotal > 100) delivery = 30;

      document.getElementById('cartSubtotal').innerText = subtotal.toLocaleString();
      document.getElementById('cartDelivery').innerText = delivery.toLocaleString();
      document.getElementById('cartTotal').innerText = (subtotal + delivery).toLocaleString();
    }}

    async function removeCart(id) {{
      await fetch('/api/cart/remove', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{cart_id:id}}) }});
      renderCart();
      refreshCounts();
    }}

    function goToCheckout() {{
      const total = parseFloat(document.getElementById('cartTotal').innerText.replace(/,/g,''));
      if(total <= 0) return toast("Your basket is empty!");
      if(currentUser) {{
        document.getElementById('chkName').value = currentUser.name || '';
        document.getElementById('chkPhone').value = currentUser.phone || '';
        if(currentUser.pincode) {{
          document.getElementById('chkPincode').value = currentUser.pincode;
          handlePincodeLookup(currentUser.pincode);
        }}
        document.getElementById('chkAddress').value = currentUser.address || '';
      }}
      switchView('checkout');
    }}

    async function handlePlaceOrder(e) {{
      e.preventDefault();
      const mandal = document.getElementById('chkMandal').value.trim();
      const district = document.getElementById('chkDistrict').value.trim();
      const street = document.getElementById('chkAddress').value.trim();

      const combinedAddress = `${{street}}, ${{mandal}}, ${{district}}`;

      const payload = {{
        name: document.getElementById('chkName').value,
        phone: document.getElementById('chkPhone').value,
        pincode: document.getElementById('chkPincode').value,
        address: combinedAddress
      }};

      const res = await fetch('/api/order/place', {{
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      }});
      const d = await res.json();
      if(d.success) {{
        document.getElementById('successOrderId').innerText = '#' + d.order_id;
        const waMsg = encodeURIComponent(`Hi Supermart, I placed order #${{d.order_id}}. Receiver: ${{payload.name}}, Phone: ${{payload.phone}}, Address: ${{payload.address}}`);
        document.getElementById('waSupportLink').href = `https://wa.me/{ADMIN_WHATSAPP}?text=${{waMsg}}`;
        refreshCounts();
        checkUserSession();
        switchView('orderSuccess');
      }} else {{
        toast(d.message || "Failed to place order.");
      }}
    }}

    function getTimelineHTML(status) {{
      const steps = [
        "Day 1: Packed & Ready",
        "Day 2: In Transit",
        "Day 3: Reached Srikakulam Store",
        "Day 4: Reached Komanapalli Store",
        "Out for Delivery (Arriving Today)",
        "Delivered Successfully"
      ];
      let currentIndex = steps.findIndex(s => s.toLowerCase() === status.toLowerCase());
      if (currentIndex === -1) currentIndex = 0;

      return `
        <div class="timeline">
          ${{steps.map((step, idx) => {{
            let cls = '';
            if (idx < currentIndex) cls = 'done';
            else if (idx === currentIndex) cls = 'current';
            return `<div class="timeline-step ${{cls}}">${{step}}</div>`;
          }}).join('')}}
        </div>
      `;
    }}

    async function loadOrders() {{
      if(!currentUser) {{
        document.getElementById('ordersFeed').innerHTML = '<p style="padding:20px 0; text-align:center;">Sign In to view orders.</p>';
        return;
      }}
      const res = await fetch('/api/orders');
      const orders = await res.json();
      const cont = document.getElementById('ordersFeed');

      if(orders.length === 0) {{
        cont.innerHTML = '<p style="padding:20px 0; text-align:center; color:var(--muted);">No orders placed yet.</p>';
        return;
      }}

      cont.innerHTML = orders.map(o => `
        <div style="border:1px solid var(--border); border-radius:8px; padding:12px; margin-bottom:12px; background:var(--card-bg);">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong>Order #${{o.order_id}}</strong>
            <span style="color:var(--primary); font-weight:800; font-size:12px;">${{o.status}}</span>
          </div>
          <div style="font-size:13px; color:var(--muted); margin:6px 0;">Items: ${{o.items}}</div>
          <div style="font-size:12px; color:var(--muted);">Delivery: ${{o.name}} (${{o.phone}}), ${{o.address}} - PIN: ${{o.pincode}}</div>
          
          ${{getTimelineHTML(o.status)}}

          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
            <strong style="font-size:15px;">Total: ₹${{o.total.toLocaleString()}}</strong>
            ${{o.status.includes('Day 1') ? `<button onclick="cancelOrder(${{o.id}})" style="background:#fee2e2; color:#dc2626; border:none; padding:6px 10px; border-radius:4px; font-weight:bold; cursor:pointer;">Cancel Order</button>` : ''}}
          </div>
        </div>
      `).join('');
    }}

    async function cancelOrder(id) {{
      if(!confirm("Are you sure you want to cancel this order?")) return;
      const res = await fetch('/api/order/cancel', {{
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({order_id: id})
      }});
      const d = await res.json();
      toast(d.message);
      loadOrders();
    }}

    async function renderWishlist() {{
      if(!currentUser) {{
        document.getElementById('wishlistFeed').innerHTML = '<p style="padding:20px 0; text-align:center;">Sign In to see wishlist.</p>';
        return;
      }}
      const res = await fetch('/api/wishlist');
      const d = await res.json();
      const items = d.items || [];
      const cont = document.getElementById('wishlistFeed');

      if(items.length === 0) {{
        cont.innerHTML = '<p style="padding:20px 0; text-align:center; color:var(--muted);">Your wishlist is empty!</p>';
        return;
      }}

      cont.innerHTML = items.map(i => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid var(--border);">
          <div>
            <strong>${{i.name}}</strong><br>
            <span style="font-weight:bold; color:var(--primary);">₹${{i.price}}</span>
          </div>
          <button onclick="addToCart(${{i.id}})" class="btn-big btn-primary" style="min-height:36px; padding:0 12px; font-size:12px; width:auto;">Move to Cart</button>
        </div>
      `).join('');
    }}

    async function handleChangePassword(e) {{
      e.preventDefault();
      const newPw = document.getElementById('newPassInput').value;
      const res = await fetch('/api/user/change-password', {{
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ password: newPw })
      }});
      const d = await res.json();
      if(d.success) {{
        toast("Password updated successfully!");
        document.getElementById('newPassInput').value = '';
        closePasswordModal();
      }} else {{
        toast(d.message || "Failed to update password.");
      }}
    }}

    function handleAuthClick() {{
      if(currentUser) switchView('profile');
      else openAuthModal();
    }}
    function openAuthModal() {{ 
      isRegister = false;
      document.getElementById('confirmPwGroup').style.display = 'none';
      document.getElementById('forgotPwLink').style.display = 'block';
      document.getElementById('authTitle').innerText = 'Sign In with Mobile';
      document.getElementById('authSubmitBtn').innerText = 'SIGN IN';
      document.getElementById('authSwitchLink').innerText = 'New customer? Sign Up here';
      document.getElementById('authMainForm').style.display = 'grid';
      document.getElementById('otpBox').style.display = 'none';
      document.getElementById('authModal').style.display = 'flex'; 
    }}
    function closeAuthModal() {{ document.getElementById('authModal').style.display = 'none'; }}
    function toggleAuthMode() {{
      isRegister = !isRegister;
      document.getElementById('confirmPwGroup').style.display = isRegister ? 'block' : 'none';
      document.getElementById('forgotPwLink').style.display = isRegister ? 'none' : 'block';
      document.getElementById('authTitle').innerText = isRegister ? 'Create Supermart Account' : 'Sign In with Mobile';
      document.getElementById('authSubmitBtn').innerText = isRegister ? 'SEND SMS OTP ➔' : 'SIGN IN';
      document.getElementById('authSwitchLink').innerText = isRegister ? 'Already registered? Sign In' : 'New customer? Sign Up here';
      document.getElementById('authMainForm').style.display = 'grid';
      document.getElementById('otpBox').style.display = 'none';
    }}

    async function handleAuthSubmit(e) {{
      e.preventDefault();
      const phone = document.getElementById('authPhone').value.trim();
      const password = document.getElementById('authPassword').value;

      if(isRegister) {{
        const confirmPw = document.getElementById('authConfirmPassword').value;
        if(password !== confirmPw) return toast("Passwords do not match!");

        const res = await fetch('/api/register/request-otp', {{
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ phone: phone, password: password })
        }});
        const d = await res.json();
        if(d.success) {{
          currentRegPhone = phone;
          document.getElementById('authMainForm').style.display = 'none';
          document.getElementById('otpBox').style.display = 'block';
          toast("SMS OTP dispatched to your mobile!");
        }} else {{
          toast(d.message || "Registration error.");
        }}
      }} else {{
        const res = await fetch('/api/login', {{
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ phone: phone, password: password })
        }});
        const d = await res.json();
        if(d.success) {{
          toast("Welcome to Supermart!");
          closeAuthModal();
          checkUserSession();
        }} else {{
          toast(d.message || "Invalid Mobile Number or Password.");
        }}
      }}
    }}

    async function verifyMobileOtp() {{
      const otp = document.getElementById('otpInput').value.trim();
      if(!otp || otp.length !== 4) return toast("Enter valid 4-digit code!");

      const res = await fetch('/api/register/verify-otp', {{
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ phone: currentRegPhone, otp: otp })
      }});
      const d = await res.json();
      if(d.success) {{
        toast("Mobile verified & Account created!");
        closeAuthModal();
        checkUserSession();
      }} else {{
        toast(d.message || "Invalid verification code!");
      }}
    }}

    async function logout() {{
      await fetch('/api/logout', {{method:'POST'}});
      currentUser = null;
      checkUserSession();
      switchView('shop');
      toast("Logged out successfully.");
    }}

    const savedLang = localStorage.getItem('sm_lang') || 'en';
    changeLanguage(savedLang);

    checkUserSession();
    loadCatalog();
  </script>
</body>
</html>
"""

# ==============================================================================
# 3. SELLER / ADMIN FRONTEND WITH FROSTED GLASS UI & PIN 630528
# ==============================================================================
SELLER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SUPERMART - Seller Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: Roboto, -apple-system, sans-serif; }
    body {
      background: linear-gradient(135deg, #f3e8ff 0%, #fdf2f8 50%, #f1f5f9 100%);
      background-attachment: fixed;
      padding: 14px; color: #1e293b; padding-bottom: 60px; min-height: 100vh;
    }
    .header-bar {
      background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px); color: #fff;
      padding: 16px 20px; border-radius: 14px; display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 16px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); border: 1px solid rgba(255,255,255,0.1);
    }
    .box {
      background: rgba(255, 255, 255, 0.88); backdrop-filter: blur(12px);
      border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 14px;
      padding: 18px; margin-bottom: 16px; box-shadow: 0 8px 24px rgba(149, 157, 165, 0.1);
    }
    input, textarea, select {
      width: 100%; min-height: 44px; border: 1px solid #cbd5e1;
      border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; font-size: 14px; outline: none; background: #fff;
    }
    .btn {
      min-height: 44px; border: none; border-radius: 8px; font-weight: 800; cursor: pointer;
      width: 100%; font-size: 13px; text-decoration: none; display: flex; align-items: center; justify-content: center;
    }
    .btn-blue { background: #2563eb; color: #fff; }
    .btn-green { background: #16a34a; color: #fff; flex: 1; }
    .btn-yellow { background: #d97706; color: #fff; flex: 1; }
    .btn-red { background: #ef4444; color: #fff; }
    .btn-gray { background: #64748b; color: #fff; }
    .btn-whatsapp { background: #25d366; color: #fff; margin-top: 8px; font-weight: bold; }
    
    .order-card, .prod-row {
      background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .order-card { border-left: 6px solid #9333ea; }

    .modal { position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center; z-index:9999; padding:12px; }
    .modal-box { background:#fff; width:100%; max-width:480px; border-radius:14px; padding:20px; max-height:90vh; overflow-y:auto; position:relative; }
    
    #adminLockOverlay {
      position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(15, 23, 42, 0.92); backdrop-filter:blur(8px); z-index:10000;
      display: flex; align-items: center; justify-content: center; padding: 16px;
    }
  </style>
</head>
<body>

  <div id="adminLockOverlay">
    <div style="background:#fff; padding:28px; border-radius:16px; width:100%; max-width:340px; text-align:center; box-shadow:0 12px 30px rgba(0,0,0,0.2);">
      <h3 style="margin-bottom:8px; color:#1e1b4b;">🔒 Seller Hub Login</h3>
      <p style="color:#64748b; font-size:12px; margin-bottom:16px;">Enter your Master Admin PIN (630528)</p>
      <input type="password" id="pinInput" placeholder="••••••" style="text-align:center; letter-spacing:6px; font-size:20px;">
      <button class="btn btn-blue" onclick="checkPin()">UNLOCK DASHBOARD</button>
    </div>
  </div>

  <div class="header-bar">
    <div>
      <h2>SUPERMART SELLER HUB</h2>
      <small style="color: #cbd5e1;">Professional Inventory & Live Orders Management</small>
    </div>
    <button onclick="refreshAll()" style="background:#334155; color:#fff; border:none; padding:8px 16px; border-radius:6px; font-weight:bold; cursor:pointer;">🔄 REFRESH</button>
  </div>

  <div class="box">
    <h3>+ Add New Product to Supermart</h3>
    <form onsubmit="handleUpload(event)" style="margin-top: 10px;">
      <input type="text" id="pName" placeholder="Product Title (e.g. Fortune Pure Besan 1kg)" required>
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <select id="pCat">
          <option value="Groceries">Groceries</option>
          <option value="Vegetables">Vegetables</option>
          <option value="Dairy">Dairy</option>
          <option value="Electronics">Electronics</option>
          <option value="Household">Household</option>
        </select>
        <input type="text" id="pBrand" placeholder="Brand Name" required>
      </div>
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <input type="number" id="pPrice" placeholder="Selling Price (₹)" required>
        <input type="number" id="pOrig" placeholder="MRP Price (₹)" required>
      </div>
      <input type="url" id="pImg" placeholder="Direct Image URL (https://...)" required>
      <textarea id="pSpecs" placeholder="Product Specifications & Features" style="height: 60px;"></textarea>
      <button type="submit" class="btn btn-blue">UPLOAD LIVE TO STORE</button>
    </form>
  </div>

  <div class="box">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
      <h3>Manage Inventory (<span id="prodCount">0</span> Items)</h3>
      <button onclick="loadInventory()" style="background:#e2e8f0; border:none; padding:4px 10px; border-radius:4px; font-weight:bold; cursor:pointer;">Reload</button>
    </div>
    <div id="inventoryHolder">Loading inventory...</div>
  </div>

  <div class="box">
    <h3>Live Customer Orders & Timeline Updates</h3>
    <div id="ordersHolder" style="margin-top: 12px;"></div>
  </div>

  <div class="modal" id="editModal">
    <div class="modal-box">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h3>✏️ Edit Product Details</h3>
        <button onclick="closeEditModal()" style="border:none; background:none; font-size:22px; cursor:pointer;">&times;</button>
      </div>
      <form onsubmit="handleSaveEdit(event)">
        <input type="hidden" id="editId">
        <label style="font-size:12px; font-weight:bold;">Product Title:</label>
        <input type="text" id="editName" required>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
          <div>
            <label style="font-size:12px; font-weight:bold;">Category:</label>
            <select id="editCat">
              <option value="Groceries">Groceries</option>
              <option value="Vegetables">Vegetables</option>
              <option value="Dairy">Dairy</option>
              <option value="Electronics">Electronics</option>
              <option value="Household">Household</option>
            </select>
          </div>
          <div>
            <label style="font-size:12px; font-weight:bold;">Brand:</label>
            <input type="text" id="editBrand" required>
          </div>
        </div>

        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
          <div>
            <label style="font-size:12px; font-weight:bold;">Selling Price (₹):</label>
            <input type="number" id="editPrice" required>
          </div>
          <div>
            <label style="font-size:12px; font-weight:bold;">MRP Price (₹):</label>
            <input type="number" id="editOrig" required>
          </div>
        </div>

        <label style="font-size:12px; font-weight:bold;">Image URL:</label>
        <input type="url" id="editImg" required>

        <label style="font-size:12px; font-weight:bold;">Specifications:</label>
        <textarea id="editSpecs" style="height:60px;"></textarea>

        <div style="display:flex; gap:8px; margin-top:8px;">
          <button type="button" class="btn btn-gray" onclick="closeEditModal()" style="flex:1;">Cancel</button>
          <button type="submit" class="btn btn-green" style="flex:2;">SAVE CHANGES</button>
        </div>
      </form>
    </div>
  </div>

  <script>
    let currentProducts = [];

    function checkPin() {
      const pin = document.getElementById('pinInput').value;
      if (pin === "630528") {
        document.getElementById('adminLockOverlay').style.display = 'none';
        refreshAll();
      } else {
        alert("Invalid PIN! Access Denied.");
      }
    }

    function refreshAll() {
      loadOrders();
      loadInventory();
    }

    async function loadInventory() {
      const res = await fetch('/api/products');
      currentProducts = await res.json();
      document.getElementById('prodCount').innerText = currentProducts.length;
      const cont = document.getElementById('inventoryHolder');

      if (currentProducts.length === 0) {
        cont.innerHTML = '<p style="color:#64748b; padding:10px 0;">No products in store.</p>';
        return;
      }

      cont.innerHTML = currentProducts.map(p => `
        <div class="prod-row" style="display:flex; gap:12px; align-items:center;">
          <img src="${p.image}" style="width:50px; height:50px; object-fit:cover; border-radius:6px; border:1px solid #e2e8f0;">
          <div style="flex:1;">
            <strong style="font-size:14px;">${p.name}</strong><br>
            <span style="font-size:12px; color:#64748b;">${p.category} | ${p.brand}</span><br>
            <span style="color:#16a34a; font-weight:bold; font-size:14px;">₹${p.price}</span> 
            <span style="color:#94a3b8; font-size:12px; text-decoration:line-through;">₹${p.orig_price}</span>
          </div>
          <div style="display:flex; gap:6px;">
            <button onclick="openEditModal(${p.id})" style="background:#2563eb; color:#fff; border:none; padding:8px 12px; border-radius:6px; font-weight:bold; cursor:pointer;">✏️ Edit</button>
            <button onclick="handleDeleteProduct(${p.id})" style="background:#fee2e2; color:#ef4444; border:none; padding:8px 12px; border-radius:6px; font-weight:bold; cursor:pointer;">🗑️</button>
          </div>
        </div>
      `).join('');
    }

    function openEditModal(id) {
      const p = currentProducts.find(x => x.id === id);
      if(!p) return;
      document.getElementById('editId').value = p.id;
      document.getElementById('editName').value = p.name;
      document.getElementById('editCat').value = p.category;
      document.getElementById('editBrand').value = p.brand;
      document.getElementById('editPrice').value = p.price;
      document.getElementById('editOrig').value = p.orig_price;
      document.getElementById('editImg').value = p.image;
      document.getElementById('editSpecs').value = p.specs || '';
      document.getElementById('editModal').style.display = 'flex';
    }

    function closeEditModal() { document.getElementById('editModal').style.display = 'none'; }

    async function handleSaveEdit(e) {
      e.preventDefault();
      const payload = {
        id: parseInt(document.getElementById('editId').value),
        name: document.getElementById('editName').value,
        category: document.getElementById('editCat').value,
        brand: document.getElementById('editBrand').value,
        price: parseFloat(document.getElementById('editPrice').value),
        orig_price: parseFloat(document.getElementById('editOrig').value),
        image: document.getElementById('editImg').value,
        specs: document.getElementById('editSpecs').value
      };

      const res = await fetch('/api/seller/product/update', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const d = await res.json();
      if (d.success) {
        alert("Product updated successfully!");
        closeEditModal();
        loadInventory();
      } else {
        alert(d.message || "Failed to update product.");
      }
    }

    async function handleDeleteProduct(id) {
      if(!confirm("Are you sure you want to remove this product from store?")) return;
      const res = await fetch('/api/seller/product/delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: id})
      });
      const d = await res.json();
      if(d.success) {
        alert("Product removed from store.");
        loadInventory();
      }
    }

    async function handleUpload(e) {
      e.preventDefault();
      const payload = {
        name: document.getElementById('pName').value,
        category: document.getElementById('pCat').value,
        brand: document.getElementById('pBrand').value,
        price: parseFloat(document.getElementById('pPrice').value),
        orig_price: parseFloat(document.getElementById('pOrig').value),
        image: document.getElementById('pImg').value,
        specs: document.getElementById('pSpecs').value
      };

      const res = await fetch('/api/seller/product/add', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      const d = await res.json();
      if(d.success) {
        alert("Product added live to Supermart customer app!");
        e.target.reset();
        loadInventory();
      }
    }

    async function loadOrders() {
      const res = await fetch('/api/seller/orders');
      const orders = await res.json();
      const cont = document.getElementById('ordersHolder');

      if(orders.length === 0) {
        cont.innerHTML = '<p style="color:#64748b; padding:12px 0;">No active orders yet.</p>';
        return;
      }

      cont.innerHTML = orders.map(o => {
        const cleanPhone = (o.phone || '').replace(/[^0-9]/g, '');
        const targetPhone = cleanPhone.length === 10 ? ('91' + cleanPhone) : cleanPhone;
        const waMsg = encodeURIComponent(`Hi ${o.name}, update on your Supermart Order #${o.order_id}. Total: ₹${o.total}. Current Stage: ${o.status}.`);
        const waUrl = `https://wa.me/${targetPhone}?text=${waMsg}`;

        return `
          <div class="order-card">
            <div style="display:flex; justify-content:space-between; font-weight:bold;">
              <span>Order #${o.order_id}</span>
              <span style="background:#e0e7ff; color:#3730a3; padding:3px 8px; border-radius:4px; font-size:12px;">${o.status}</span>
            </div>
            <div style="margin: 10px 0; font-size:14px; line-height:1.5;">
              <p><strong>Customer:</strong> ${o.name} (📞 <a href="tel:${o.phone}" style="color:#2563eb; font-weight:bold;">${o.phone}</a>)</p>
              <p><strong>Address:</strong> ${o.address} - PIN: ${o.pincode}</p>
              <p><strong>Items:</strong> ${o.items}</p>
              <p style="font-weight:bold; font-size:15px; margin-top:6px; color:#16a34a;">Collect Cash: ₹${o.total.toLocaleString()} (incl. Delivery)</p>
            </div>
            
            <a href="${waUrl}" target="_blank" class="btn btn-whatsapp">
              💬 WhatsApp Customer (${o.phone})
            </a>

            <div style="margin-top: 10px; background:#f8fafc; padding:8px; border-radius:6px;">
              <label style="font-size:12px; font-weight:bold;">Update Delivery Step Timeline:</label>
              <select onchange="updateStatus(${o.id}, this.value)" style="margin-top:4px; margin-bottom:0;">
                <option value="" disabled selected>-- Change Order Stage --</option>
                <option value="Day 1: Packed & Ready">Day 1: Packed & Ready</option>
                <option value="Day 2: In Transit">Day 2: In Transit</option>
                <option value="Day 3: Reached Srikakulam Store">Day 3: Reached Srikakulam Store</option>
                <option value="Day 4: Reached Komanapalli Store">Day 4: Reached Komanapalli Store</option>
                <option value="Out for Delivery (Arriving Today)">Out for Delivery (Arriving Today)</option>
                <option value="Delivered Successfully">Delivered Successfully</option>
              </select>
            </div>
          </div>
        `;
      }).join('');
    }

    async function updateStatus(id, st) {
      await fetch('/api/seller/order/update', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({status: st, order_id: id})
      });
      alert('Updated Order Stage: ' + st);
      loadOrders();
    }
  </script>
</body>
</html>
"""

# ==============================================================================
# 4. HTTP REQUEST HANDLERS & BACKEND APIS
# ==============================================================================
class UnifiedHandler(http.server.BaseHTTPRequestHandler):

    def _get_user(self):
        cookie_header = self.headers.get('Cookie')
        if not cookie_header: return None
        c = cookies.SimpleCookie(cookie_header)
        if 'sm_session' in c:
            return SESSIONS.get(c['sm_session'].value)
        return None

    def _json(self, data, status=200, set_cookie=None):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        if set_cookie:
            self.send_header('Set-Cookie', set_cookie)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        user = self._get_user()

        if url.path == '/manifest.json':
            self.send_response(200)
            self.send_header('Content-Type', 'application/manifest+json')
            self.end_headers()
            self.wfile.write(json.dumps(PWA_MANIFEST).encode('utf-8'))
            return

        if url.path == '/sw.js':
            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript')
            self.end_headers()
            self.wfile.write(PWA_SW_JS.encode('utf-8'))
            return

        if url.path in ['/', '/shop']:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(CUSTOMER_HTML.encode('utf-8'))
            return

        if url.path in ['/seller', '/admin', '/seller/']:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(SELLER_HTML.encode('utf-8'))
            return

        if url.path == '/api/me':
            if user: self._json({"authenticated": True, "user": user})
            else: self._json({"authenticated": False})
            return

        if url.path == '/api/products':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, name, category, brand, price, orig_price, specs, image, rating, reviews_count FROM products ORDER BY id DESC")
            rows = c.fetchall()
            conn.close()
            result = [{
                "id": r[0], "name": r[1], "category": r[2], "brand": r[3], "price": r[4],
                "orig_price": r[5], "specs": r[6], "image": r[7], "rating": r[8], "reviews_count": r[9]
            } for r in rows]
            self._json(result)
            return

        if url.path == '/api/cart':
            if not user: return self._json({"items": []})
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
                SELECT c.id, p.id, p.name, p.price, p.image, c.quantity
                FROM cart c JOIN products p ON c.product_id = p.id
                WHERE c.user_id = ?
            """, (user['id'],))
            rows = c.fetchall()
            conn.close()
            self._json({"items": [{"cart_id": r[0], "product_id": r[1], "name": r[2], "price": r[3], "image": r[4], "quantity": r[5]} for r in rows]})
            return

        if url.path == '/api/wishlist':
            if not user: return self._json({"items": []})
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
                SELECT p.id, p.name, p.price, p.image
                FROM wishlist w JOIN products p ON w.product_id = p.id
                WHERE w.user_id = ?
            """, (user['id'],))
            rows = c.fetchall()
            conn.close()
            self._json({"items": [{"id": r[0], "name": r[1], "price": r[2], "image": r[3]} for r in rows]})
            return

        if url.path == '/api/orders':
            if not user: return self._json([])
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, order_id, name, phone, pincode, address, total, status, items FROM orders WHERE user_id = ? ORDER BY id DESC", (user['id'],))
            rows = c.fetchall()
            conn.close()
            self._json([{"id": r[0], "order_id": r[1], "name": r[2], "phone": r[3], "pincode": r[4], "address": r[5], "total": r[6], "status": r[7], "items": r[8]} for r in rows])
            return

        if url.path == '/api/seller/orders':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, order_id, name, phone, pincode, address, total, status, items FROM orders ORDER BY id DESC")
            rows = c.fetchall()
            conn.close()
            self._json([{"id": r[0], "order_id": r[1], "name": r[2], "phone": r[3], "pincode": r[4], "address": r[5], "total": r[6], "status": r[7], "items": r[8]} for r in rows])
            return

        self.send_error(404)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        user = self._get_user()
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length)
        data = json.loads(body.decode('utf-8')) if length else {}

        if url.path == '/api/user/update-profile':
            if not user: return self._json({"success": False, "message": "Login required"})
            name = data.get('name', '').strip()
            pincode = data.get('pincode', '').strip()
            address = data.get('address', '').strip()

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE users SET name = ?, pincode = ?, address = ? WHERE id = ?", (name, pincode, address, user['id']))
            conn.commit()
            conn.close()

            user['name'] = name
            user['pincode'] = pincode
            user['address'] = address
            return self._json({"success": True})

        if url.path == '/api/register/request-otp':
            phone = data.get('phone', '').strip().replace(' ', '')
            password = data.get('password', '')

            if len(phone) != 10 or not phone.isdigit():
                return self._json({"success": False, "message": "Enter valid 10-digit mobile number."})

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            exists = c.fetchone()
            conn.close()

            if exists:
                return self._json({"success": False, "message": "This mobile number is already registered! Please Sign In."})

            generated_otp = str(random.randint(1000, 9999))
            PENDING_REGISTRATIONS[phone] = {
                "password": hash_pw(password),
                "otp": generated_otp
            }

            send_real_sms_otp(phone, generated_otp)
            return self._json({"success": True, "message": "SMS OTP sent to mobile phone."})

        if url.path == '/api/register/verify-otp':
            phone = data.get('phone', '').strip()
            user_otp = data.get('otp', '').strip()

            pending = PENDING_REGISTRATIONS.get(phone)
            if not pending or pending['otp'] != user_otp:
                return self._json({"success": False, "message": "Invalid SMS OTP code."})

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (phone, password) VALUES (?, ?)", (phone, pending['password']))
                uid = c.lastrowid
                conn.commit()
                conn.close()
                del PENDING_REGISTRATIONS[phone]

                token = str(uuid.uuid4())
                u_obj = {"id": uid, "phone": phone, "name": "", "address": "", "pincode": ""}
                SESSIONS[token] = u_obj
                self._json({"success": True}, set_cookie=f"sm_session={token}; Path=/; HttpOnly")
            except sqlite3.IntegrityError:
                conn.close()
                self._json({"success": False, "message": "Mobile number already registered."})
            return

        if url.path == '/api/login':
            phone = data.get('phone', '').strip()
            pw = hash_pw(data.get('password', ''))

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, phone, name, address, pincode FROM users WHERE phone = ? AND password = ?", (phone, pw))
            row = c.fetchone()
            conn.close()

            if row:
                token = str(uuid.uuid4())
                u_obj = {"id": row[0], "phone": row[1], "name": row[2] or "", "address": row[3] or "", "pincode": row[4] or ""}
                SESSIONS[token] = u_obj
                self._json({"success": True}, set_cookie=f"sm_session={token}; Path=/; HttpOnly")
            else:
                self._json({"success": False, "message": "Invalid Mobile Number or Password."})
            return

        if url.path == '/api/user/change-password':
            if not user: return self._json({"success": False, "message": "Login required"})
            new_pw = hash_pw(data.get('password', ''))
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE users SET password = ? WHERE id = ?", (new_pw, user['id']))
            conn.commit()
            conn.close()
            self._json({"success": True})
            return

        if url.path == '/api/logout':
            self._json({"success": True}, set_cookie="sm_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT")
            return

        if url.path == '/api/cart/add':
            if not user: return self._json({"success": False, "message": "Login required"}, status=401)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
                INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)
                ON CONFLICT(user_id, product_id) DO UPDATE SET quantity = quantity + 1
            """, (user['id'], data.get('product_id')))
            conn.commit()
            conn.close()
            self._json({"success": True})
            return

        if url.path == '/api/cart/remove':
            if not user: return self._json({"success": False})
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM cart WHERE id = ? AND user_id = ?", (data.get('cart_id'), user['id']))
            conn.commit()
            conn.close()
            self._json({"success": True})
            return

        if url.path == '/api/wishlist/toggle':
            if not user: return self._json({"success": False, "message": "Login required"})
            pid = data.get('product_id')
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM wishlist WHERE user_id = ? AND product_id = ?", (user['id'], pid))
            exists = c.fetchone()
            if exists:
                c.execute("DELETE FROM wishlist WHERE id = ?", (exists[0],))
                msg = "Removed from wishlist"
            else:
                c.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)", (user['id'], pid))
                msg = "Added to wishlist ❤️"
            conn.commit()
            conn.close()
            self._json({"success": True, "message": msg})
            return

        if url.path == '/api/order/place':
            if not user: return self._json({"success": False, "message": "Login required"})
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
                SELECT p.name, p.price, c.quantity
                FROM cart c JOIN products p ON c.product_id = p.id
                WHERE c.user_id = ?
            """, (user['id'],))
            items = c.fetchall()
            if not items:
                conn.close()
                return self._json({"success": False, "message": "Basket is empty"})

            subtotal = sum(r[1] * r[2] for r in items)
            if subtotal <= 50: delivery_charge = round((subtotal / 10.0) * 3.0, 2)
            elif subtotal <= 100: delivery_charge = round((subtotal / 10.0) * 2.0, 2)
            else: delivery_charge = 30.0

            total = subtotal + delivery_charge
            items_str = ", ".join([f"{r[0]} (x{r[2]})" for r in items])
            order_id = "SM" + str(uuid.uuid4().hex[:6]).upper()

            c.execute("UPDATE users SET name = ?, address = ?, pincode = ? WHERE id = ?",
                      (data['name'], data['address'], data['pincode'], user['id']))
            user['name'] = data['name']
            user['address'] = data['address']
            user['pincode'] = data['pincode']

            c.execute("""
                INSERT INTO orders (order_id, user_id, name, phone, pincode, address, subtotal, delivery_charge, total, status, items)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Day 1: Packed & Ready', ?)
            """, (order_id, user['id'], data['name'], data['phone'], data['pincode'], data['address'], subtotal, delivery_charge, total, items_str))

            c.execute("DELETE FROM cart WHERE user_id = ?", (user['id'],))
            conn.commit()
            conn.close()
            self._json({"success": True, "order_id": order_id})
            return

        if url.path == '/api/order/cancel':
            if not user: return self._json({"success": False})
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT status FROM orders WHERE id = ? AND user_id = ?", (data['order_id'], user['id']))
            od = c.fetchone()
            if od and 'Day 1' in od[0]:
                c.execute("UPDATE orders SET status = 'Cancelled by Customer' WHERE id = ?", (data['order_id'],))
                conn.commit()
                conn.close()
                self._json({"success": True, "message": "Order cancelled successfully."})
            else:
                conn.close()
                self._json({"success": False, "message": "Order already in transit / cannot cancel."})
            return

        if url.path == '/api/seller/product/add':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
                INSERT INTO products (name, category, brand, price, orig_price, specs, image)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data['name'], data['category'], data['brand'], data['price'], data['orig_price'], data.get('specs', ''), data['image']))
            conn.commit()
            conn.close()
            self._json({"success": True})
            return

        if url.path == '/api/seller/product/update':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
                UPDATE products SET name = ?, category = ?, brand = ?, price = ?, orig_price = ?, specs = ?, image = ?
                WHERE id = ?
            """, (data['name'], data['category'], data['brand'], data['price'], data['orig_price'], data.get('specs', ''), data['image'], data['id']))
            conn.commit()
            conn.close()
            self._json({"success": True})
            return

        if url.path == '/api/seller/product/delete':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM products WHERE id = ?", (data['id'],))
            conn.commit()
            conn.close()
            self._json({"success": True})
            return

        if url.path == '/api/seller/order/update':
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE orders SET status = ? WHERE id = ?", (data['status'], data['order_id']))
            conn.commit()
            conn.close()
            self._json({"success": True})
            return

        self.send_error(404)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Unified SUPERMART Server running on port {port}...")
    with socketserver.TCPServer(("", port), UnifiedHandler) as httpd:
        httpd.serve_forever()
