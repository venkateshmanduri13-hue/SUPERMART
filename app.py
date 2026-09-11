import http.server
import socketserver
import sqlite3
import json
import urllib.parse
import uuid
import hashlib
import os
from http import cookies

DB_FILE = "supermart.db"
SECRET_KEY = "SUPERMART_SECRET_KEY_PRO_2026"
ADMIN_WHATSAPP = "917670912836"

SESSIONS = {}

def hash_pw(pw):
    return hashlib.sha256((pw + SECRET_KEY).encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
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
        status TEXT DEFAULT 'Confirmed (Packing)',
        items TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        samples = [
            ("Aashirvaad Sharbati Whole Wheat Atta 5kg", "Groceries", "Aashirvaad", 240, 290, "100% Pure MP Sharbati Wheat, Stone Ground, High Dietary Fibre", "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=500&q=80"),
            ("Fortune Sunlite Refined Sunflower Cooking Oil 1L", "Groceries", "Fortune", 135, 170, "Fortified with Vitamin A & D, Triple Refined Light Oil", "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?auto=format&fit=crop&w=500&q=80"),
            ("India Gate Classic Aged Basmati Rice 1kg", "Groceries", "India Gate", 175, 230, "Extra Long Grain Basmati, Aged 2 Years, Non-Sticky Fragrance", "https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=500&q=80"),
            ("Fresh Organic Farm Red Tomatoes 1kg", "Vegetables", "FreshFarm", 35, 45, "Naturally Ripened, Rich in Lycopene, Direct From Local Farmers", "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=500&q=80"),
            ("Farm Fresh Green Capsicum / Shimla Mirch 500g", "Vegetables", "FreshFarm", 40, 55, "Crispy, Pesticide-Free, Packed With Vitamin C", "https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?auto=format&fit=crop&w=500&q=80"),
            ("Farm Fresh Organic Potatoes (Aloo) 1kg", "Vegetables", "FreshFarm", 30, 40, "Handpicked Clean Skin Potatoes, Ideal for Daily Curries & Fries", "https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=500&q=80"),
            ("Amul Pure Clarified Cow Ghee Jar 1L", "Dairy", "Amul", 595, 680, "Traditional Granular Texture, Rich Aromatic Cow Clarified Butter", "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=500&q=80"),
            ("Apple iPhone 15 (Blue, 128 GB)", "Electronics", "Apple", 65999, 79900, "128 GB ROM | 6.1 inch Super Retina XDR Display | 48MP Dual Camera", "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=500&q=80"),
            ("boAt Airdopes 141 Bluetooth Wireless Earbuds", "Electronics", "boAt", 1199, 4490, "42 Hours Battery, Low Latency Beast Mode, IPX4 Water Resistance", "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=500&q=80"),
            ("Surf Excel Quick Wash Front & Top Detergent 1kg", "Household", "Surf Excel", 155, 190, "Removes Tough Stains in 1 Wash, Safe for Color & Fabric", "https://images.unsplash.com/photo-1584813470613-5b1c1cad3d69?auto=format&fit=crop&w=500&q=80")
        ]
        c.executemany("INSERT INTO products (name, category, brand, price, orig_price, specs, image) VALUES (?, ?, ?, ?, ?, ?, ?)", samples)
        conn.commit()
    conn.close()

# ==============================================================================
# 2. CUSTOMER FRONTEND (WITH FLIPKART STYLE PRODUCT DETAILS & RELATED ITEMS)
# ==============================================================================
CUSTOMER_HTML = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>SUPERMART - Online Smart Shopping</title>
  <style>
    :root {{
      --primary: #9333ea;
      --primary-dark: #7e22ce;
      --accent: #ec4899;
      --glass-bg: rgba(255, 255, 255, 0.85);
      --glass-card: rgba(255, 255, 255, 0.90);
      --glass-border: rgba(226, 232, 240, 0.8);
      --text: #1e1b4b;
      --muted: #64748b;
      --whatsapp: #25d366;
      --shadow: 0 8px 24px rgba(149, 157, 165, 0.12);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: Roboto, -apple-system, sans-serif; -webkit-tap-highlight-color: transparent; }}
    
    body {{
      background: linear-gradient(135deg, #f3e8ff 0%, #fdf2f8 50%, #f1f5f9 100%);
      background-attachment: fixed;
      color: var(--text);
      padding-bottom: 75px;
      min-height: 100vh;
    }}

    .top-bar {{
      position: sticky; top: 0; z-index: 1000;
      background: var(--glass-bg);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--glass-border);
      padding: 10px 14px;
    }}
    .header-row1 {{ display: flex; justify-content: space-between; align-items: center; }}
    .brand-logo {{ font-size: 20px; font-weight: 900; color: var(--primary); display: flex; align-items: center; gap: 6px; cursor: pointer; }}
    .brand-logo span {{ background: linear-gradient(135deg, #9333ea, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .top-icons {{ display: flex; gap: 8px; align-items: center; }}
    .icon-bubble {{
      background: rgba(255,255,255,0.75); border: 1px solid var(--glass-border);
      padding: 6px 10px; border-radius: 20px; font-size: 13px; font-weight: bold;
      cursor: pointer; display: flex; align-items: center; gap: 4px; box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }}

    .search-container {{ margin-top: 8px; position: relative; }}
    .search-input {{
      width: 100%; height: 42px; border: 1px solid #cbd5e1;
      border-radius: 24px; padding: 0 42px 0 38px; font-size: 13px;
      outline: none; background: #ffffff; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
    }}
    .search-left-icon {{ position: absolute; left: 14px; top: 11px; color: #94a3b8; font-size: 15px; }}
    .search-right-icon {{ position: absolute; right: 14px; top: 10px; color: #94a3b8; font-size: 16px; cursor: pointer; }}

    .delivery-strip {{
      background: rgba(243, 232, 255, 0.7); backdrop-filter: blur(6px);
      padding: 7px 14px; font-size: 12px; font-weight: bold; color: #6b21a8;
      display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(216, 180, 254, 0.5);
      cursor: pointer;
    }}

    .circles-strip {{
      display: flex; gap: 14px; overflow-x: auto; padding: 12px 14px;
      background: var(--glass-bg); backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--glass-border);
    }}
    .circles-strip::-webkit-scrollbar {{ display: none; }}
    .circle-item {{
      display: flex; flex-direction: column; align-items: center;
      min-width: 64px; cursor: pointer; text-decoration: none;
    }}
    .circle-img {{
      width: 54px; height: 54px; border-radius: 50%; object-fit: cover;
      border: 2px solid #e9d5ff; box-shadow: 0 2px 6px rgba(147, 51, 234, 0.15);
      transition: transform 0.2s;
    }}
    .circle-item.active .circle-img {{ border-color: var(--primary); transform: scale(1.08); box-shadow: 0 4px 10px rgba(147,51,234,0.3); }}
    .circle-label {{ font-size: 11px; font-weight: bold; margin-top: 5px; color: var(--text); text-align: center; white-space: nowrap; }}

    .sort-filter-bar {{
      display: flex; justify-content: space-between; align-items: center;
      background: #ffffff; padding: 8px 14px; border-bottom: 1px solid var(--glass-border);
      font-size: 13px; font-weight: 700; color: #475569;
    }}
    .sort-select {{
      border: none; background: transparent; font-weight: bold; color: var(--primary);
      outline: none; font-size: 13px; cursor: pointer;
    }}

    .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; padding: 10px; }}
    .card {{
      background: var(--glass-card); backdrop-filter: blur(10px);
      border: 1px solid var(--glass-border); border-radius: 12px;
      padding: 10px; display: flex; flex-direction: column; position: relative;
      box-shadow: var(--shadow); transition: transform 0.2s; cursor: pointer;
    }}
    .card:active {{ transform: scale(0.98); }}
    .card-heart {{
      position: absolute; top: 8px; right: 8px; background: rgba(255,255,255,0.85);
      border: 1px solid #e2e8f0; width: 30px; height: 30px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center; font-size: 14px; cursor: pointer; z-index: 2;
    }}
    .card-img-wrap {{ width: 100%; height: 130px; display: flex; align-items: center; justify-content: center; margin-bottom: 8px; }}
    .card-img-wrap img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
    
    .mall-tag {{
      display: inline-flex; align-items: center; gap: 3px; background: #6b21a8;
      color: #fff; font-size: 10px; font-weight: 900; padding: 2px 6px; border-radius: 4px; width: fit-content; margin-bottom: 4px;
    }}
    .card-name {{ font-size: 13px; font-weight: 700; height: 34px; overflow: hidden; line-height: 1.3; margin-bottom: 4px; }}
    .price-row {{ display: flex; align-items: baseline; gap: 6px; }}
    .price-now {{ font-size: 16px; font-weight: 900; color: #000; }}
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

    /* Flipkart Style Full View Layout */
    .product-view-sheet {{
      background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 75px; box-shadow: var(--shadow);
    }}
    .pdp-img-box {{
      width: 100%; height: 260px; display: flex; align-items: center; justify-content: center; position: relative;
      background: #fafafa; border-radius: 10px; margin-bottom: 14px;
    }}
    .pdp-img-box img {{ max-width: 90%; max-height: 240px; object-fit: contain; }}
    .offer-box {{
      background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px; margin: 14px 0;
    }}
    .trust-badges {{
      display: flex; justify-content: space-around; background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 12px; margin: 14px 0; text-align: center; font-size: 11px; font-weight: bold;
    }}
    .related-scroll {{
      display: flex; gap: 10px; overflow-x: auto; padding: 10px 0;
    }}
    .related-scroll::-webkit-scrollbar {{ display: none; }}
    .related-card {{
      min-width: 140px; max-width: 140px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 8px; cursor: pointer; flex-shrink: 0;
    }}

    .pdp-bottom-bar {{
      position: fixed; bottom: 0; left: 0; right: 0; height: 60px;
      background: #fff; border-top: 1px solid #e2e8f0; display: flex; z-index: 1000;
    }}
    .btn-pdp-cart {{
      flex: 1; background: #fff; color: #000; border: none; font-weight: bold; font-size: 14px; cursor: pointer;
    }}
    .btn-pdp-buy {{
      flex: 1; background: #ff9f00; color: #fff; border: none; font-weight: bold; font-size: 14px; cursor: pointer;
    }}

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
      background: var(--glass-card); backdrop-filter: blur(12px);
      border: 1px solid var(--glass-border); border-radius: 12px;
      padding: 16px; margin-bottom: 12px; box-shadow: var(--shadow);
    }}

    .modal {{
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);
      z-index: 2000; display: none; align-items: center; justify-content: center; padding: 14px;
    }}
    .modal-box {{
      background: #ffffff; width: 100%; max-width: 440px; max-height: 90vh;
      border-radius: 14px; overflow-y: auto; padding: 20px; position: relative;
    }}
    .modal-close {{ position: absolute; top: 12px; right: 16px; font-size: 24px; font-weight: bold; cursor: pointer; border: none; background: transparent; }}

    .bottom-nav {{
      position: fixed; bottom: 0; left: 0; right: 0; height: 60px;
      background: var(--glass-bg); backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px); border-top: 1px solid var(--glass-border);
      display: flex; justify-content: space-around; align-items: center; z-index: 1000;
    }}
    .nav-btn {{
      background: none; border: none; font-size: 11px; font-weight: 700;
      color: var(--muted); display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1; cursor: pointer;
    }}
    .nav-btn.active {{ color: var(--primary); }}

    .toast {{
      position: fixed; top: 75px; left: 50%; transform: translateX(-50%);
      background: #0f172a; color: #fff; padding: 10px 20px; border-radius: 30px;
      font-size: 13px; font-weight: 700; z-index: 9999; display: none; box-shadow: var(--shadow);
    }}
  </style>
</head>
<body>

  <div id="toast" class="toast"></div>

  <header class="top-bar" id="mainHeader">
    <div class="header-row1">
      <div class="brand-logo" onclick="switchView('shop')">
        <span>🛍️ SUPERMART</span>
      </div>
      <div class="top-icons">
        <div class="icon-bubble" onclick="switchView('wishlist')">❤️ <span id="wishCount">0</span></div>
        <div class="icon-bubble" onclick="switchView('cart')">🛒 <span id="cartCount">0</span></div>
        <div class="icon-bubble" id="userAuthBtn" onclick="handleAuthClick()">👤 Login</div>
      </div>
    </div>
    
    <div class="search-container">
      <span class="search-left-icon">🔍</span>
      <input type="text" id="searchInput" class="search-input" placeholder="Search by Product Name, Atta, Oil, iPhone..." onkeyup="filterAndSortItems()">
      <span class="search-right-icon" onclick="clearSearch()">✖</span>
    </div>
  </header>

  <div class="delivery-strip" id="pincodeStrip" onclick="switchView('profile')">
    <div style="display:flex; align-items:center; gap:6px;">
      <span>📍</span>
      <span id="deliveringToText">Delivering to: Click to set address</span>
    </div>
    <span>❯</span>
  </div>

  <!-- 1. PRODUCT STORE VIEW -->
  <section id="shopScreen" class="screen active" style="padding:0;">
    <div class="circles-strip">
      <div class="circle-item active" onclick="selectCircleCategory('All', this)">
        <img class="circle-img" src="https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=150&q=80">
        <span class="circle-label">All Items</span>
      </div>
      <div class="circle-item" onclick="selectCircleCategory('Groceries', this)">
        <img class="circle-img" src="https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=150&q=80">
        <span class="circle-label">🌾 Groceries</span>
      </div>
      <div class="circle-item" onclick="selectCircleCategory('Vegetables', this)">
        <img class="circle-img" src="https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=150&q=80">
        <span class="circle-label">🥦 Veggies</span>
      </div>
      <div class="circle-item" onclick="selectCircleCategory('Dairy', this)">
        <img class="circle-img" src="https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=150&q=80">
        <span class="circle-label">🥛 Dairy</span>
      </div>
      <div class="circle-item" onclick="selectCircleCategory('Electronics', this)">
        <img class="circle-img" src="https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=150&q=80">
        <span class="circle-label">📱 Gadgets</span>
      </div>
      <div class="circle-item" onclick="selectCircleCategory('Household', this)">
        <img class="circle-img" src="https://images.unsplash.com/photo-1584813470613-5b1c1cad3d69?auto=format&fit=crop&w=150&q=80">
        <span class="circle-label">🧼 Home</span>
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

  <!-- 2. FLIPKART STYLE PRODUCT DETAILS SCREEN WITH RELATED PRODUCTS -->
  <section id="pdpScreen" class="screen" style="padding:10px;">
    <button onclick="switchView('shop')" style="background:none; border:none; color:var(--primary); font-size:14px; font-weight:bold; margin-bottom:10px; cursor:pointer;">
      ⬅ Back to Products
    </button>
    
    <div class="product-view-sheet">
      <div class="pdp-img-box">
        <img id="pdpImg" src="">
        <div class="card-heart" id="pdpHeart" style="top:10px; right:10px;">❤️</div>
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
        <div style="font-weight:bold; color:#1e40af; font-size:13px; margin-bottom:4px;">🏷️ Special Offers Available</div>
        <p style="font-size:12px; color:#3b82f6;">Get tiered delivery charges & UPI discounts on final checkout.</p>
      </div>

      <div class="trust-badges">
        <div>🚚<br>Fast Delivery</div>
        <div>💵<br>Cash on Delivery</div>
        <div>🛡️<br>Supermart Assured</div>
      </div>

      <h4 style="margin-top:16px;">Product Specifications:</h4>
      <p id="pdpSpecs" style="color:#475569; font-size:13px; line-height:1.5; margin:6px 0 16px 0;"></p>

      <hr style="border:none; border-top:1px solid #e2e8f0; margin:16px 0;">

      <!-- SIMILAR / RELATED PRODUCTS SECTION -->
      <h3 style="font-size:15px; margin-bottom:8px;">Similar & Related Products</h3>
      <div class="related-scroll" id="relatedGrid"></div>
    </div>

    <!-- Fixed Bottom Buy Bar -->
    <div class="pdp-bottom-bar" id="pdpBottomBar">
      <button class="btn-pdp-cart" id="pdpAddToCartBtn">ADD TO CART</button>
      <button class="btn-pdp-buy" id="pdpBuyNowBtn">BUY NOW</button>
    </div>
  </section>

  <!-- 3. CART VIEW -->
  <section id="cartScreen" class="screen">
    <div class="sheet">
      <h3>Shopping Basket (<span id="cartCountTitle">0</span>)</h3>
      <div id="cartListHolder" style="margin: 14px 0;"></div>

      <div style="border-top: 1px solid var(--glass-border); padding-top: 12px; font-size: 14px;">
        <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
          <span>Items Subtotal:</span>
          <strong>₹<span id="cartSubtotal">0</span></strong>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom: 8px; color: #ea580c;">
          <span>Delivery Charges:</span>
          <strong>₹<span id="cartDelivery">0</span></strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size: 18px; font-weight: 900; border-top: 1px dashed var(--glass-border); padding-top: 8px;">
          <span>Total Payable:</span>
          <span style="color: var(--primary);">₹<span id="cartTotal">0</span></span>
        </div>
      </div>

      <button class="btn-big btn-orange" style="margin-top: 16px;" onclick="goToCheckout()">PROCEED TO CHECKOUT ➔</button>
    </div>
  </section>

  <!-- 4. CHECKOUT VIEW -->
  <section id="checkoutScreen" class="screen">
    <div class="sheet">
      <h3>Confirm Delivery Address</h3>
      <form onsubmit="handlePlaceOrder(event)" style="display: grid; gap: 12px; margin-top: 14px;">
        <input type="text" id="chkName" placeholder="Full Receiver Name" required style="padding: 12px; border: 1px solid var(--glass-border); border-radius: 6px; font-size: 14px;">
        <input type="tel" id="chkPhone" placeholder="10-digit Phone Number" pattern="[0-9]{{10}}" required style="padding: 12px; border: 1px solid var(--glass-border); border-radius: 6px; font-size: 14px;">
        <input type="text" id="chkPincode" placeholder="Postal Pincode" required style="padding: 12px; border: 1px solid var(--glass-border); border-radius: 6px; font-size: 14px;">
        <textarea id="chkAddress" placeholder="Complete Street, Flat/Door No, Landmark" required style="padding: 12px; border: 1px solid var(--glass-border); border-radius: 6px; font-size: 14px; height: 75px;"></textarea>

        <div style="background: #fdf2f8; border: 1px solid #fbcfe8; padding: 12px; border-radius: 6px; font-size: 13px; font-weight: 700; color: #9d174d;">
          💵 Cash / UPI On Delivery Available (Safe & Verified)
        </div>

        <button type="submit" class="btn-big btn-primary">CONFIRM & PLACE ORDER NOW</button>
      </form>
    </div>
  </section>

  <!-- 5. ORDER SUCCESS VIEW -->
  <section id="orderSuccessScreen" class="screen">
    <div class="sheet" style="text-align: center; padding: 30px 16px;">
      <div style="font-size: 55px; margin-bottom: 12px;">🎉</div>
      <h2 style="color: var(--primary); margin-bottom: 6px;">Congrats!</h2>
      <h3 style="margin-bottom: 12px;">Your order has been placed successfully!</h3>
      <p style="color: var(--muted); font-size: 14px; margin-bottom: 20px;">Order ID: <strong id="successOrderId">#</strong><br>Our delivery partner will reach you shortly.</p>
      
      <a id="waSupportLink" href="https://wa.me/{ADMIN_WHATSAPP}" target="_blank" class="btn-big btn-whatsapp" style="margin-bottom:10px;">
        💬 Chat on WhatsApp with Store
      </a>

      <button class="btn-big btn-primary" onclick="switchView('orders')">TRACK MY ORDER 📦</button>
    </div>
  </section>

  <!-- 6. ORDERS VIEW -->
  <section id="ordersScreen" class="screen">
    <div class="sheet">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
        <h3>My Orders & Live Delivery</h3>
        <button onclick="loadOrders()" style="background:#f1f5f9; border:none; padding:6px 12px; border-radius:4px; font-weight:bold; cursor:pointer;">🔄 Refresh</button>
      </div>
      <div id="ordersFeed"></div>
    </div>
  </section>

  <!-- 7. WISHLIST VIEW -->
  <section id="wishlistScreen" class="screen">
    <div class="sheet">
      <h3>My Wishlist ❤️</h3>
      <div id="wishlistFeed" style="margin-top: 12px;"></div>
    </div>
  </section>

  <!-- 8. PROFILE & ADDRESS VIEW -->
  <section id="profileScreen" class="screen">
    <div class="sheet">
      <h3>Customer Account</h3>
      <div id="profileDetails" style="margin-top: 14px;"></div>
      
      <a href="https://wa.me/{ADMIN_WHATSAPP}?text=Hello%20Supermart%20Support" target="_blank" class="btn-big btn-whatsapp" style="margin-top:14px;">
        💬 WhatsApp Store Owner
      </a>

      <button class="btn-big btn-outline-red" style="margin-top: 14px;" onclick="logout()">LOGOUT ACCOUNT</button>
    </div>
  </section>

  <!-- AUTH MODAL -->
  <div class="modal" id="authModal">
    <div class="modal-box" style="max-width: 380px;">
      <button class="modal-close" onclick="closeAuthModal()">&times;</button>
      <h2 id="authTitle" style="margin-bottom: 14px;">Customer Login</h2>
      
      <form onsubmit="handleAuthSubmit(event)" style="display:grid; gap:10px;">
        <div id="nameInputGroup" style="display:none;">
          <input type="text" id="authName" placeholder="Your Full Name" style="width:100%; padding:10px; border:1px solid var(--glass-border); border-radius:6px;">
        </div>
        <input type="email" id="authEmail" placeholder="Email Address" required style="width:100%; padding:10px; border:1px solid var(--glass-border); border-radius:6px;">
        <input type="password" id="authPassword" placeholder="Password" required style="width:100%; padding:10px; border:1px solid var(--glass-border); border-radius:6px;">
        <button type="submit" class="btn-big btn-primary" id="authSubmitBtn">SIGN IN</button>
      </form>

      <p style="margin-top: 14px; font-size: 13px; text-align: center; color: var(--muted);">
        <a href="javascript:void(0)" onclick="toggleAuthMode()" id="authSwitchLink" style="color: var(--primary); font-weight: bold; text-decoration:none;">New here? Create an account</a>
      </p>
    </div>
  </div>

  <!-- Bottom Navigation -->
  <nav class="bottom-nav" id="mainBottomNav">
    <button class="nav-btn active" id="bShop" onclick="switchView('shop')">
      <span style="font-size: 18px;">🏠</span>
      <span>Home</span>
    </button>
    <button class="nav-btn" id="bCart" onclick="switchView('cart')">
      <span style="font-size: 18px;">🛒</span>
      <span>Cart</span>
    </button>
    <button class="nav-btn" id="bOrders" onclick="switchView('orders')">
      <span style="font-size: 18px;">📦</span>
      <span>My Orders</span>
    </button>
    <button class="nav-btn" id="bProfile" onclick="switchView('profile')">
      <span style="font-size: 18px;">👤</span>
      <span>Account</span>
    </button>
  </nav>

  <script>
    let products = [];
    let currentCategory = 'All';
    let currentUser = null;
    let isRegister = false;
    let activeProduct = null;

    function toast(msg) {{
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.style.display = 'block';
      setTimeout(() => {{ t.style.display = 'none'; }}, 2500);
    }}

    async function checkUserSession() {{
      const res = await fetch('/api/me');
      const data = await res.json();
      if(data.authenticated) {{
        currentUser = data.user;
        document.getElementById('userAuthBtn').innerText = '👤 ' + currentUser.name.split(' ')[0];
        if(currentUser.address && currentUser.pincode) {{
          document.getElementById('deliveringToText').innerText = `Delivering to: ${{currentUser.address.slice(0, 18)}}... - ${{currentUser.pincode}}`;
        }}
      }} else {{
        currentUser = null;
        document.getElementById('userAuthBtn').innerText = '👤 Login';
        document.getElementById('deliveringToText').innerText = "Delivering to: Click to set address";
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

    function filterAndSortItems() {{
      const q = document.getElementById('searchInput').value.toLowerCase().trim();
      const sortType = document.getElementById('sortSelect').value;

      let filtered = products.filter(p => {{
        const catMatch = (currentCategory === 'All' || p.category === currentCategory);
        const textMatch = p.name.toLowerCase().includes(q) || p.brand.toLowerCase().includes(q);
        return catMatch && textMatch;
      }});

      if (sortType === 'low') {{
        filtered.sort((a, b) => a.price - b.price);
      }} else if (sortType === 'high') {{
        filtered.sort((a, b) => b.price - a.price);
      }} else if (sortType === 'rating') {{
        filtered.sort((a, b) => b.rating - a.rating);
      }}

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
            <div class="card-heart" onclick="event.stopPropagation(); toggleWishlist(${{p.id}})">❤️</div>
            <div class="card-img-wrap">
              <img src="${{p.image}}" onerror="this.src='https://images.unsplash.com/photo-1542838132-92c53300491e?w=400'">
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

    /* Open Flipkart Style Product Details Page with Related Items */
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

      // Render Related Products (same category, excluding current product)
      const related = products.filter(item => item.category === p.category && item.id !== p.id);
      const relGrid = document.getElementById('relatedGrid');
      
      if (related.length === 0) {{
        relGrid.innerHTML = '<div style="font-size:12px; color:var(--muted); padding:10px 0;">No related items in this category.</div>';
      }} else {{
        relGrid.innerHTML = related.map(r => `
          <div class="related-card" onclick="openProductPage(${{r.id}})">
            <img src="${{r.image}}" style="width:100%; height:90px; object-fit:contain; margin-bottom:4px;">
            <div style="font-size:11px; font-weight:bold; height:28px; overflow:hidden;">${{r.name}}</div>
            <div style="font-size:12px; font-weight:bold; color:#000; margin-top:4px;">₹${{r.price.toLocaleString()}}</div>
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
      document.getElementById('mainHeader').style.display = isPdp ? 'none' : 'block';
      document.getElementById('pincodeStrip').style.display = isPdp ? 'none' : 'flex';
      document.getElementById('mainBottomNav').style.display = isPdp ? 'none' : 'flex';

      document.getElementById(name + 'Screen').classList.add('active');
      if(name === 'shop') document.getElementById('bShop').classList.add('active');
      if(name === 'cart') {{ document.getElementById('bCart').classList.add('active'); renderCart(); }}
      if(name === 'orders') {{ document.getElementById('bOrders').classList.add('active'); loadOrders(); }}
      if(name === 'profile') {{ document.getElementById('bProfile').classList.add('active'); renderProfile(); }}
      if(name === 'wishlist') renderWishlist();
    }}

    async function addToCart(id) {{
      if(!currentUser) {{ toast("Please Login to add items!"); openAuthModal(); return; }}
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
      if(!currentUser) {{ toast("Please Login first!"); openAuthModal(); return; }}
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
        document.getElementById('cartListHolder').innerHTML = '<p style="padding:20px 0; text-align:center;">Please login to view basket.</p>';
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
          <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid var(--glass-border);">
            <div>
              <strong>${{i.name}}</strong><br>
              <span style="color:var(--primary); font-weight:800;">₹${{i.price}} &times; ${{i.quantity}}</span>
            </div>
            <button onclick="removeCart(${{i.cart_id}})" style="background:#fee2e2; color:#ef4444; border:none; padding:6px 12px; border-radius:4px; font-weight:bold; cursor:pointer;">Remove</button>
          </div>
        `;
      }}).join('');

      let delivery = 0;
      if (subtotal > 0 && subtotal <= 50) {{
        delivery = Math.round((subtotal / 10) * 3);
      }} else if (subtotal > 50 && subtotal <= 100) {{
        delivery = Math.round((subtotal / 10) * 2);
      }} else if (subtotal > 100) {{
        delivery = 30;
      }}

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
      if(currentUser && currentUser.address) {{
        document.getElementById('chkName').value = currentUser.name || '';
        document.getElementById('chkPhone').value = currentUser.phone || '';
        document.getElementById('chkPincode').value = currentUser.pincode || '';
        document.getElementById('chkAddress').value = currentUser.address || '';
      }}
      switchView('checkout');
    }}

    async function handlePlaceOrder(e) {{
      e.preventDefault();
      const payload = {{
        name: document.getElementById('chkName').value,
        phone: document.getElementById('chkPhone').value,
        pincode: document.getElementById('chkPincode').value,
        address: document.getElementById('chkAddress').value
      }};

      const res = await fetch('/api/order/place', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(payload)
      }});
      const d = await res.json();
      if(d.success) {{
        document.getElementById('successOrderId').innerText = '#' + d.order_id;
        const waMsg = encodeURIComponent(`Hi Supermart, I placed order #${{d.order_id}}. Receiver: ${{payload.name}}, Phone: ${{payload.phone}}`);
        document.getElementById('waSupportLink').href = `https://wa.me/{ADMIN_WHATSAPP}?text=${{waMsg}}`;
        refreshCounts();
        checkUserSession();
        switchView('orderSuccess');
      }} else {{
        toast(d.message || "Failed to place order.");
      }}
    }}

    async function loadOrders() {{
      if(!currentUser) {{
        document.getElementById('ordersFeed').innerHTML = '<p style="padding:20px 0; text-align:center;">Login to view orders.</p>';
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
        <div style="border:1px solid var(--glass-border); border-radius:8px; padding:12px; margin-bottom:10px; background:#fff;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong>Order #${{o.order_id}}</strong>
            <span style="color:var(--primary); font-weight:800; font-size:12px;">${{o.status}}</span>
          </div>
          <div style="font-size:13px; color:#475569; margin:6px 0;">Items: ${{o.items}}</div>
          <div style="font-size:12px; color:var(--muted);">Delivery: ${{o.name}} (${{o.phone}}), ${{o.address}} - PIN: ${{o.pincode}}</div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
            <strong style="font-size:15px;">Total: ₹${{o.total.toLocaleString()}}</strong>
            ${{o.status.includes('Confirmed') ? `<button onclick="cancelOrder(${{o.id}})" style="background:#fee2e2; color:#dc2626; border:none; padding:6px 10px; border-radius:4px; font-weight:bold; cursor:pointer;">Cancel Order</button>` : ''}}
          </div>
        </div>
      `).join('');
    }}

    async function cancelOrder(id) {{
      if(!confirm("Are you sure you want to cancel this order?")) return;
      const res = await fetch('/api/order/cancel', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{order_id: id}})
      }});
      const d = await res.json();
      toast(d.message);
      loadOrders();
    }}

    async function renderWishlist() {{
      if(!currentUser) {{
        document.getElementById('wishlistFeed').innerHTML = '<p style="padding:20px 0; text-align:center;">Login to see wishlist.</p>';
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
        <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid var(--glass-border);">
          <div>
            <strong>${{i.name}}</strong><br>
            <span style="font-weight:bold; color:var(--primary);">₹${{i.price}}</span>
          </div>
          <button onclick="addToCart(${{i.id}})" class="btn-big btn-primary" style="min-height:36px; padding:0 12px; font-size:12px; width:auto;">Move to Cart</button>
        </div>
      `).join('');
    }}

    function renderProfile() {{
      const cont = document.getElementById('profileDetails');
      if(!currentUser) {{
        cont.innerHTML = '<p>You are not logged in. <a href="javascript:openAuthModal()" style="color:var(--primary); font-weight:bold;">Click here to Login</a></p>';
        return;
      }}
      cont.innerHTML = `
        <div style="line-height: 1.8; font-size: 14px;">
          <p><strong>Name:</strong> ${{currentUser.name}}</p>
          <p><strong>Email:</strong> ${{currentUser.email}}</p>
          <p><strong>Saved Phone:</strong> ${{currentUser.phone || 'Not Saved'}}</p>
          <p><strong>Delivery Address:</strong> ${{currentUser.address ? (currentUser.address + ' - PIN: ' + currentUser.pincode) : 'No address saved yet. (Auto-saves upon checkout)'}}</p>
        </div>
      `;
    }}

    function handleAuthClick() {{
      if(currentUser) switchView('profile');
      else openAuthModal();
    }}
    function openAuthModal() {{ 
      isRegister = false;
      document.getElementById('nameInputGroup').style.display = 'none';
      document.getElementById('authTitle').innerText = 'Customer Login';
      document.getElementById('authSubmitBtn').innerText = 'SIGN IN';
      document.getElementById('authSwitchLink').innerText = 'New here? Create an account';
      document.getElementById('authModal').style.display = 'flex'; 
    }}
    function closeAuthModal() {{ document.getElementById('authModal').style.display = 'none'; }}
    function toggleAuthMode() {{
      isRegister = !isRegister;
      document.getElementById('nameInputGroup').style.display = isRegister ? 'block' : 'none';
      document.getElementById('authTitle').innerText = isRegister ? 'Create Supermart Account' : 'Customer Login';
      document.getElementById('authSubmitBtn').innerText = isRegister ? 'REGISTER & SIGN IN' : 'SIGN IN';
      document.getElementById('authSwitchLink').innerText = isRegister ? 'Already registered? Login here' : 'New here? Create an account';
    }}

    async function handleAuthSubmit(e) {{
      e.preventDefault();
      const endpoint = isRegister ? '/api/register' : '/api/login';
      const payload = {{
        email: document.getElementById('authEmail').value,
        password: document.getElementById('authPassword').value,
        name: document.getElementById('authName').value
      }};
      const res = await fetch(endpoint, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(payload)
      }});
      const d = await res.json();
      if(d.success) {{
        toast("Welcome to Supermart!");
        closeAuthModal();
        checkUserSession();
      }} else {{
        if(isRegister && d.message && d.message.includes("already registered")) {{
          toast("Account exists! Switched to Login mode. Enter password to sign in.");
          toggleAuthMode();
        }} else {{
          toast(d.message || "Authentication error.");
        }}
      }}
    }}

    async function logout() {{
      await fetch('/api/logout', {{method:'POST'}});
      currentUser = null;
      checkUserSession();
      switchView('shop');
      toast("Logged out successfully.");
    }}

    checkUserSession();
    loadCatalog();
  </script>
</body>
</html>
"""

# ==============================================================================
# 3. SELLER / ADMIN FRONTEND (WITH EDIT & DELETE)
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
    body { background: #f1f5f9; padding: 14px; color: #1e293b; padding-bottom: 50px; }
    .header-bar { background: #0f172a; color: #fff; padding: 14px 18px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
    .box { background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; margin-bottom: 14px; }
    input, textarea, select { width: 100%; min-height: 44px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; font-size: 14px; }
    .btn { min-height: 42px; border: none; border-radius: 6px; font-weight: 800; cursor: pointer; width: 100%; font-size: 13px; text-decoration: none; display: flex; align-items: center; justify-content: center; }
    .btn-blue { background: #2563eb; color: #fff; }
    .btn-green { background: #16a34a; color: #fff; flex: 1; }
    .btn-yellow { background: #d97706; color: #fff; flex: 1; }
    .btn-red { background: #ef4444; color: #fff; }
    .btn-gray { background: #64748b; color: #fff; }
    .btn-whatsapp { background: #25d366; color: #fff; margin-top: 8px; font-weight: bold; }
    
    .order-card, .prod-row { background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; margin-bottom: 10px; }
    .order-card { border-left: 6px solid #2563eb; }

    .modal { position: fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); display:none; align-items:center; justify-content:center; z-index:9999; padding:12px; }
    .modal-box { background:#fff; width:100%; max-width:480px; border-radius:8px; padding:18px; max-height:90vh; overflow-y:auto; position:relative; }
  </style>
</head>
<body>
  <div class="header-bar">
    <div>
      <h2>SUPERMART SELLER HUB</h2>
      <small style="color: #94a3b8;">Inventory & Live Orders Fulfillment</small>
    </div>
    <button onclick="refreshAll()" style="background:#334155; color:#fff; border:none; padding:8px 16px; border-radius:4px; font-weight:bold; cursor:pointer;">🔄 REFRESH</button>
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
    <h3>Live Customer Orders Received</h3>
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
          <img src="${p.image}" style="width:50px; height:50px; object-fit:contain; border-radius:4px; border:1px solid #e2e8f0;">
          <div style="flex:1;">
            <strong style="font-size:14px;">${p.name}</strong><br>
            <span style="font-size:12px; color:#64748b;">${p.category} | ${p.brand}</span><br>
            <span style="color:#16a34a; font-weight:bold; font-size:14px;">₹${p.price}</span> 
            <span style="color:#94a3b8; font-size:12px; text-decoration:line-through;">₹${p.orig_price}</span>
          </div>
          <div style="display:flex; gap:6px;">
            <button onclick="openEditModal(${p.id})" style="background:#2563eb; color:#fff; border:none; padding:8px 12px; border-radius:4px; font-weight:bold; cursor:pointer;">✏️ Edit</button>
            <button onclick="handleDeleteProduct(${p.id})" style="background:#fee2e2; color:#ef4444; border:none; padding:8px 12px; border-radius:4px; font-weight:bold; cursor:pointer;">🗑️</button>
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

    function closeEditModal() {
      document.getElementById('editModal').style.display = 'none';
    }

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
        const waMsg = encodeURIComponent(`Hi ${o.name}, update regarding your Supermart Order #${o.order_id}. Total: ₹${o.total}. Status: ${o.status}.`);
        const waUrl = `https://wa.me/${targetPhone}?text=${waMsg}`;

        return `
          <div class="order-card">
            <div style="display:flex; justify-content:space-between; font-weight:bold;">
              <span>Order #${o.order_id}</span>
              <span style="background:#e2e8f0; padding:2px 8px; border-radius:4px;">${o.status}</span>
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

            <div style="display:flex; gap:8px; margin-top:8px;">
              <button class="btn btn-yellow" onclick="updateStatus(${o.id}, 'Out for Delivery')">Mark Out for Delivery</button>
              <button class="btn btn-green" onclick="updateStatus(${o.id}, 'Delivered Successfully')">Mark Delivered</button>
            </div>
          </div>
        `;
      }).join('');
    }

    async function updateStatus(id, st) {
      await fetch('/api/seller/order/update', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({order_id: id, status: st})
      });
      alert('Status updated to: ' + st);
      loadOrders();
    }

    refreshAll();
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

        if url.path == '/api/register':
            email = data.get('email', '').strip().lower()
            name = data.get('name', '').strip()
            pw = hash_pw(data.get('password', ''))
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, pw))
                uid = c.lastrowid
                conn.commit()
                conn.close()
                token = str(uuid.uuid4())
                u_obj = {"id": uid, "name": name, "email": email, "phone": "", "address": "", "pincode": ""}
                SESSIONS[token] = u_obj
                self._json({"success": True}, set_cookie=f"sm_session={token}; Path=/; HttpOnly")
            except sqlite3.IntegrityError:
                conn.close()
                self._json({"success": False, "message": "Email already registered."})
            return

        if url.path == '/api/login':
            email = data.get('email', '').strip().lower()
            pw = hash_pw(data.get('password', ''))
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id, name, email, phone, address, pincode FROM users WHERE email = ? AND password = ?", (email, pw))
            row = c.fetchone()
            conn.close()
            if row:
                token = str(uuid.uuid4())
                u_obj = {"id": row[0], "name": row[1], "email": row[2], "phone": row[3], "address": row[4], "pincode": row[5]}
                SESSIONS[token] = u_obj
                self._json({"success": True}, set_cookie=f"sm_session={token}; Path=/; HttpOnly")
            else:
                self._json({"success": False, "message": "Invalid email or password."})
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
            if subtotal <= 50:
                delivery_charge = round((subtotal / 10.0) * 3.0, 2)
            elif subtotal <= 100:
                delivery_charge = round((subtotal / 10.0) * 2.0, 2)
            else:
                delivery_charge = 30.0

            total = subtotal + delivery_charge
            items_str = ", ".join([f"{r[0]} (x{r[2]})" for r in items])
            order_id = "SM" + str(uuid.uuid4().hex[:6]).upper()

            c.execute("UPDATE users SET phone = ?, address = ?, pincode = ? WHERE id = ?",
                      (data['phone'], data['address'], data['pincode'], user['id']))
            user['phone'] = data['phone']
            user['address'] = data['address']
            user['pincode'] = data['pincode']

            c.execute("""
                INSERT INTO orders (order_id, user_id, name, phone, pincode, address, subtotal, delivery_charge, total, items)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            if od and 'Confirmed' in od[0]:
                c.execute("UPDATE orders SET status = 'Cancelled by Customer' WHERE id = ?", (data['order_id'],))
                conn.commit()
                conn.close()
                self._json({"success": True, "message": "Order cancelled successfully."})
            else:
                conn.close()
                self._json({"success": False, "message": "Order already processed / cannot cancel."})
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
