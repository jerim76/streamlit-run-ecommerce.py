# app.py - Complete Flask Backend and Streamlit Frontend
import os
import sqlite3
import hashlib
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, make_response, g
from flask_cors import CORS
import streamlit as st
from PIL import Image

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = 'javashop_secret_key'

# Database setup
DATABASE = 'ecommerce.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                price REAL,
                category TEXT,
                stock INTEGER,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                product_id TEXT,
                quantity INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                total_price REAL,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id TEXT PRIMARY KEY,
                order_id TEXT,
                product_id TEXT,
                quantity INTEGER,
                price REAL
            )
        ''')
        
        # Insert sample products
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        
        if count == 0:
            sample_products = [
                ("Ultimate Java IDE 2023", "Professional IDE with advanced debugging tools", 89.99, "Development Tools", 100, "https://images.unsplash.com/photo-1555066931-4365d14bab8c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1770&q=80"),
                ("Mastering Java 17", "Comprehensive guide to Java 17 features", 34.99, "Books & Courses", 50, "https://images.unsplash.com/photo-1542831371-29b0f74f9713?ixlib=rb-4.0.3&auto=format&fit=crop&w=1770&q=80"),
                ("Spring Framework Pro", "Enterprise-grade Spring framework", 149.99, "Frameworks", 30, "https://images.unsplash.com/photo-1581094794329-16d1f2b6b9a5?ixlib=rb-4.0.3&auto=format&fit=crop&w=1770&q=80"),
                ("Enterprise Java Server", "High-performance server for Java applications", 249.99, "Server Solutions", 20, "https://images.unsplash.com/photo-1551650975-87deedd944c3?ixlib=rb-4.0.3&auto=format&fit=crop&w=1674&q=80"),
                ("Java Performance Toolkit", "Optimize your Java applications", 79.99, "Development Tools", 40, "https://images.unsplash.com/photo-1586769852836-bc069f19e1b6?ixlib=rb-4.0.3&auto=format&fit=crop&w=1770&q=80"),
                ("Java Security Essentials", "Learn to secure Java applications", 44.99, "Books & Courses", 60, "https://images.unsplash.com/photo-1495640388908-05fa85288e61?ixlib=rb-4.0.3&auto=format&fit=crop&w=1770&q=80")
            ]
            
            for product in sample_products:
                product_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO products (id, name, description, price, category, stock, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (product_id, *product)
                )
        
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Helper functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# API Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    if not username or not password or not email:
        return jsonify({'error': 'Missing required fields'}), 400
    
    hashed_password = hash_password(password)
    user_id = str(uuid.uuid4())
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (id, username, password, email) VALUES (?, ?, ?, ?)",
            (user_id, username, hashed_password, email)
        )
        db.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400
    
    hashed_password = hash_password(password)
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, username FROM users WHERE username = ? AND password = ?",
        (username, hashed_password)
    )
    user = cursor.fetchone()
    
    if user:
        # Create a simple token (in a real app, use JWT)
        token = str(uuid.uuid4())
        return jsonify({
            'token': token,
            'user_id': user['id'],
            'username': user['username']
        }), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/products', methods=['GET'])
def get_products():
    category = request.args.get('category')
    search = request.args.get('search')
    
    db = get_db()
    cursor = db.cursor()
    
    if category and category != "All":
        cursor.execute("SELECT * FROM products WHERE category = ?", (category,))
    elif search:
        cursor.execute(
            "SELECT * FROM products WHERE name LIKE ? OR description LIKE ?",
            (f'%{search}%', f'%{search}%')
        )
    else:
        cursor.execute("SELECT * FROM products")
    
    products = cursor.fetchall()
    products_list = [dict(product) for product in products]
    return jsonify(products_list), 200

@app.route('/api/products/<product_id>', methods=['GET'])
def get_product(product_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    
    if product:
        return jsonify(dict(product)), 200
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/cart', methods=['GET'])
def get_cart():
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        SELECT cart.id, products.id as product_id, products.name, products.price, 
               cart.quantity, products.image_url, products.stock
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
        """,
        (user_id,)
    )
    cart_items = cursor.fetchall()
    cart_list = [dict(item) for item in cart_items]
    return jsonify(cart_list), 200

@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if not product_id:
        return jsonify({'error': 'Missing product ID'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if product exists
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    # Check if item already in cart
    cursor.execute(
        "SELECT * FROM cart WHERE user_id = ? AND product_id = ?",
        (user_id, product_id)
    )
    existing_item = cursor.fetchone()
    
    if existing_item:
        new_quantity = existing_item['quantity'] + quantity
        cursor.execute(
            "UPDATE cart SET quantity = ? WHERE id = ?",
            (new_quantity, existing_item['id'])
        )
    else:
        cart_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO cart (id, user_id, product_id, quantity) VALUES (?, ?, ?, ?)",
            (cart_id, user_id, product_id, quantity)
        )
    
    db.commit()
    return jsonify({'message': 'Product added to cart'}), 200

@app.route('/api/cart/update/<cart_id>', methods=['PUT'])
def update_cart_item(cart_id):
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    data = request.json
    quantity = data.get('quantity')
    
    if quantity is None:
        return jsonify({'error': 'Missing quantity'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify cart item belongs to user
    cursor.execute(
        "SELECT * FROM cart WHERE id = ? AND user_id = ?",
        (cart_id, user_id)
    )
    cart_item = cursor.fetchone()
    
    if not cart_item:
        return jsonify({'error': 'Cart item not found'}), 404
    
    cursor.execute(
        "UPDATE cart SET quantity = ? WHERE id = ?",
        (quantity, cart_id)
    )
    db.commit()
    return jsonify({'message': 'Cart item updated'}), 200

@app.route('/api/cart/remove/<cart_id>', methods=['DELETE'])
def remove_cart_item(cart_id):
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    db = get_db()
    cursor = db.cursor()
    
    # Verify cart item belongs to user
    cursor.execute(
        "SELECT * FROM cart WHERE id = ? AND user_id = ?",
        (cart_id, user_id)
    )
    cart_item = cursor.fetchone()
    
    if not cart_item:
        return jsonify({'error': 'Cart item not found'}), 404
    
    cursor.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
    db.commit()
    return jsonify({'message': 'Cart item removed'}), 200

@app.route('/api/cart/clear', methods=['DELETE'])
def clear_cart():
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    db.commit()
    return jsonify({'message': 'Cart cleared'}), 200

@app.route('/api/orders/checkout', methods=['POST'])
def checkout():
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    db = get_db()
    cursor = db.cursor()
    
    # Get cart items
    cursor.execute(
        """
        SELECT cart.id, cart.product_id, cart.quantity, products.price, products.stock
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
        """,
        (user_id,)
    )
    cart_items = cursor.fetchall()
    
    if not cart_items:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Calculate total price
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Create order
    order_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO orders (id, user_id, total_price, status) VALUES (?, ?, ?, ?)",
        (order_id, user_id, total_price, 'Processing')
    )
    
    # Create order items and update stock
    for item in cart_items:
        # Create order item
        order_item_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO order_items (id, order_id, product_id, quantity, price) VALUES (?, ?, ?, ?, ?)",
            (order_item_id, order_id, item['product_id'], item['quantity'], item['price'])
        )
        
        # Update product stock
        new_stock = item['stock'] - item['quantity']
        cursor.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (new_stock, item['product_id'])
        )
    
    # Clear cart
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    
    db.commit()
    return jsonify({
        'message': 'Order placed successfully',
        'order_id': order_id,
        'total_price': total_price
    }), 200

@app.route('/api/orders', methods=['GET'])
def get_orders():
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    orders = cursor.fetchall()
    orders_list = [dict(order) for order in orders]
    return jsonify(orders_list), 200

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order_details(order_id):
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    db = get_db()
    cursor = db.cursor()
    
    # Get order
    cursor.execute(
        "SELECT * FROM orders WHERE id = ? AND user_id = ?",
        (order_id, user_id)
    )
    order = cursor.fetchone()
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    # Get order items
    cursor.execute(
        """
        SELECT order_items.quantity, order_items.price, 
               products.name, products.image_url
        FROM order_items
        JOIN products ON order_items.product_id = products.id
        WHERE order_items.order_id = ?
        """,
        (order_id,)
    )
    items = cursor.fetchall()
    items_list = [dict(item) for item in items]
    
    order_details = dict(order)
    order_details['items'] = items_list
    return jsonify(order_details), 200

# Streamlit Frontend
def run_streamlit():
    # Initialize session state
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'cart_count' not in st.session_state:
        st.session_state.cart_count = 0
    if 'page' not in st.session_state:
        st.session_state.page = "home"
    if 'view_product' not in st.session_state:
        st.session_state.view_product = None
    if 'order_placed' not in st.session_state:
        st.session_state.order_placed = False
    if 'order_id' not in st.session_state:
        st.session_state.order_id = None

    # Custom CSS for Java-themed styling
    st.markdown("""
    <style>
        :root {
            --java-blue: #007396;
            --java-dark-blue: #004d73;
            --java-light-blue: #4da6ff;
            --java-orange: #ff8c00;
            --java-light: #f0f8ff;
            --java-dark: #002233;
            --gray-light: #f5f5f5;
            --gray-medium: #e0e0e0;
            --gray-dark: #333;
        }
        
        .stApp {
            background-color: var(--java-light);
            color: var(--java-dark);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        /* Header styles */
        header {
            background: linear-gradient(135deg, var(--java-blue), var(--java-dark-blue));
            color: white;
            padding: 15px 0;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        .logo {
            display: flex;
            align-items: center;
            font-size: 1.8rem;
            font-weight: 700;
            cursor: pointer;
        }
        
        .logo span {
            color: var(--java-orange);
        }
        
        .nav-icons {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .nav-icon {
            color: white;
            font-size: 1.3rem;
            cursor: pointer;
        }
        
        .cart-count {
            background-color: var(--java-orange);
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 0.8rem;
            display: inline-flex;
            justify-content: center;
            align-items: center;
            position: absolute;
            top: -5px;
            right: -5px;
        }
        
        /* Button styles */
        .stButton>button {
            background-color: var(--java-orange);
            color: white;
            border-radius: 30px;
            padding: 12px 30px;
            font-weight: 600;
            font-size: 1.1rem;
            border: none;
            transition: all 0.3s ease;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        
        .stButton>button:hover {
            background-color: #e67e00;
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
        }
        
        /* Section titles */
        .section-title {
            text-align: center;
            margin-bottom: 40px;
            position: relative;
            font-size: 2.2rem;
            color: var(--java-dark-blue);
        }
        
        .section-title:after {
            content: '';
            display: block;
            width: 80px;
            height: 4px;
            background: var(--java-orange);
            margin: 15px auto;
            border-radius: 2px;
        }
        
        /* Product cards */
        .product-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 30px;
            margin-bottom: 50px;
        }
        
        .product-card {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            transition: transform 0.3s ease;
        }
        
        .product-card:hover {
            transform: translateY(-10px);
        }
        
        .product-image {
            height: 220px;
            background-color: var(--gray-medium);
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        
        .product-image img {
            max-width: 80%;
            max-height: 80%;
            transition: transform 0.5s ease;
        }
        
        .product-info {
            padding: 20px;
        }
        
        .product-title {
            font-size: 1.2rem;
            margin-bottom: 10px;
            color: var(--java-dark);
        }
        
        .product-price {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--java-dark-blue);
            margin-bottom: 15px;
        }
        
        /* Form styles */
        .stTextInput>div>div>input, .stTextArea>div>div>textarea {
            border-radius: 10px !important;
            padding: 10px 15px !important;
        }
        
        /* Cart styles */
        .cart-item {
            display: flex;
            padding: 15px;
            border-bottom: 1px solid var(--gray-medium);
        }
        
        .cart-item-image {
            width: 100px;
            height: 100px;
            object-fit: contain;
            margin-right: 20px;
            border-radius: 10px;
        }
        
        .cart-item-details {
            flex: 1;
        }
        
        .cart-item-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .cart-summary {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            margin-top: 30px;
        }
        
        /* Order history */
        .order-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
        }
        
        .order-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--gray-medium);
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .section-title {
                font-size: 1.8rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    # API Functions
    def api_request(method, endpoint, data=None, headers=None):
        backend_url = "http://localhost:5000"  # Flask runs on port 5000
        url = f"{backend_url}{endpoint}"
        
        headers = headers or {}
        if st.session_state.token:
            headers["X-User-ID"] = st.session_state.user_id
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=data)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                return None
                
            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.RequestException:
            return None

    # Render header with navigation
    def render_header():
        cart_count = st.session_state.cart_count
        
        st.markdown(f"""
        <header>
            <div class="header-container">
                <div class="logo" onclick="window.location.href='#'">
                    <span>☕</span> Java<span>Shop</span>
                </div>
                <div class="nav-icons">
                    <a class="nav-icon" onclick="window.location.href='#'">🔍</a>
                    {"<a class='nav-icon' onclick='window.location.href=\"#account\"'>👤</a>" if st.session_state.token else ""}
                    <a class="nav-icon" onclick="window.location.href='#cart'" style="position:relative">
                        🛒
                        <span class="cart-count">{cart_count}</span>
                    </a>
                </div>
            </div>
        </header>
        """, unsafe_allow_html=True)

    # Render hero section
    def render_hero():
        st.markdown("""
        <div style="background: linear-gradient(rgba(0, 115, 150, 0.8), rgba(0, 77, 115, 0.8), 
                    url('https://images.unsplash.com/photo-1550439062-609e1531270e?ixlib=rb-4.0.3&auto=format&fit=crop&w=1770&q=80');
                    background-size: cover;
                    background-position: center;
                    height: 400px;
                    display: flex;
                    align-items: center;
                    text-align: center;
                    color: white;
                    margin-bottom: 50px;
                    border-radius: 0 0 20px 20px;">
            <div style="max-width: 800px; margin: 0 auto; padding: 0 20px;">
                <h1 style="font-size: 3rem; margin-bottom: 20px; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);">Premium Java Development Tools</h1>
                <p style="font-size: 1.2rem; margin-bottom: 30px;">Discover the best Java products, frameworks, and libraries for developers</p>
                <button class="stButton">Shop Now</button>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Render products
    def render_products(category=None, search_query=None):
        title = "Search Results" if search_query else "Featured Products"
        st.markdown(f'<h2 class="section-title">{title}</h2>', unsafe_allow_html=True)
        
        params = {}
        if category and category != "All":
            params["category"] = category
        if search_query:
            params["search"] = search_query
            
        products = api_request("GET", "/api/products", params)
        
        if not products:
            st.warning("No products found matching your search.")
            return
        
        cols = st.columns(3)
        for i, product in enumerate(products):
            col = cols[i % 3]
            
            with col:
                # Product card
                with st.container():
                    # Product image
                    st.markdown(f"""
                    <div style="height: 200px; background-color: #e0e0e0; 
                                display: flex; align-items: center; justify-content: center; 
                                border-radius: 10px 10px 0 0; overflow: hidden;">
                        <img src="{product.get('image_url', '')}" style="max-height: 80%; max-width: 80%;">
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 0 0 10px 10px; 
                                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);">
                        <h3 style="margin-bottom: 10px;">{product.get('name', '')}</h3>
                        <div style="color: var(--java-blue); margin-bottom: 10px;">{product.get('category', '')}</div>
                        <div style="font-size: 1.4rem; font-weight: 700; color: var(--java-dark-blue); margin-bottom: 15px;">
                            ${product.get('price', 0):.2f}
                        </div>
                        <div style="margin-bottom: 15px; color: #666; font-size: 0.9rem;">
                            {product.get('description', '')[:100]}{'...' if len(product.get('description', '')) > 100 else ''}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # View Details button
                    if st.button("View Details", key=f"view_{product.get('id')}", use_container_width=True):
                        st.session_state.view_product = product.get('id')
                    
                    # Add to Cart button
                    if st.session_state.token:
                        if st.button("Add to Cart", key=f"add_{product.get('id')}", use_container_width=True):
                            data = {"product_id": product.get('id')}
                            if api_request("POST", "/api/cart/add", data):
                                st.success(f"{product.get('name')} added to cart!")
                                # Update cart count
                                cart_items = api_request("GET", "/api/cart") or []
                                st.session_state.cart_count = len(cart_items)
                                st.experimental_rerun()

    # Render product details
    def render_product_details(product_id):
        product = api_request("GET", f"/api/products/{product_id}")
        if not product:
            st.error("Product not found")
            return
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image(product.get('image_url', ''), use_column_width=True)
        
        with col2:
            st.markdown(f"<h2>{product.get('name', '')}</h2>", unsafe_allow_html=True)
            st.markdown(f"<div style='color: var(--java-blue); font-size: 1.2rem; margin-bottom: 20px;'>{product.get('category', '')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 2rem; font-weight: 700; color: var(--java-dark-blue); margin-bottom: 20px;'>${product.get('price', 0):.2f}</div>", unsafe_allow_html=True)
            
            st.markdown("### Description")
            st.markdown(f"<div style='margin-bottom: 30px;'>{product.get('description', '')}</div>", unsafe_allow_html=True)
            
            stock = product.get('stock', 0)
            stock_status = f"In Stock ({stock} available)" if stock > 0 else "Out of Stock"
            st.markdown(f"**Availability:** {stock_status}")
            
            if st.session_state.token and stock > 0:
                quantity = st.number_input("Quantity", min_value=1, max_value=stock, value=1)
                if st.button("Add to Cart", use_container_width=True):
                    data = {"product_id": product_id, "quantity": quantity}
                    if api_request("POST", "/api/cart/add", data):
                        st.success(f"{product.get('name')} added to cart!")
                        # Update cart count
                        cart_items = api_request("GET", "/api/cart") or []
                        st.session_state.cart_count = len(cart_items)
                        st.experimental_rerun()
        
        st.button("Back to Products", on_click=lambda: st.session_state.pop("view_product"))

    # Render shopping cart
    def render_cart():
        if not st.session_state.token:
            st.warning("Please log in to view your cart")
            return
        
        cart_items = api_request("GET", "/api/cart") or []
        
        if not cart_items:
            st.info("Your cart is empty")
            return
        
        total_price = 0
        for item in cart_items:
            with st.container():
                col1, col2 = st.columns([1, 4])
                
                with col1:
                    st.image(item.get('image_url', ''), width=100)
                
                with col2:
                    st.markdown(f"**{item.get('name', '')}**")
                    st.markdown(f"Price: ${item.get('price', 0):.2f}")
                    
                    col21, col22 = st.columns([2, 1])
                    with col21:
                        new_quantity = st.number_input(
                            "Quantity", 
                            min_value=1, 
                            max_value=item.get('stock', 1), 
                            value=item.get('quantity', 1),
                            key=f"qty_{item.get('id')}"
                        )
                        if new_quantity != item.get('quantity', 1):
                            data = {"quantity": new_quantity}
                            if api_request("PUT", f"/api/cart/update/{item.get('id')}", data):
                                st.experimental_rerun()
                    
                    with col22:
                        if st.button("❌", key=f"remove_{item.get('id')}"):
                            if api_request("DELETE", f"/api/cart/remove/{item.get('id')}"):
                                st.experimental_rerun()
                    
                    item_total = item.get('price', 0) * item.get('quantity', 1)
                    total_price += item_total
                    st.markdown(f"**Total: ${item_total:.2f}**")
        
        # Cart summary
        with st.container():
            st.markdown("### Order Summary")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Subtotal**")
                st.markdown("**Shipping**")
                st.markdown("**Tax (10%)**")
                st.markdown("---")
                st.markdown("**Total**")
                
            with col2:
                st.markdown(f"${total_price:.2f}")
                st.markdown("$5.99")
                tax = total_price * 0.1
                st.markdown(f"${tax:.2f}")
                st.markdown("---")
                grand_total = total_price + 5.99 + tax
                st.session_state.order_total = grand_total
                st.markdown(f"**${grand_total:.2f}**")
        
        # Checkout button
        if st.button("Proceed to Checkout", use_container_width=True):
            response = api_request("POST", "/api/orders/checkout")
            if response:
                st.session_state.order_placed = True
                st.session_state.order_id = response.get('order_id')
                st.session_state.cart_count = 0
                st.experimental_rerun()

    # Render order confirmation
    def render_order_confirmation():
        order_id = st.session_state.get('order_id')
        if not order_id:
            st.error("Order not found")
            return
        
        order = api_request("GET", f"/api/orders/{order_id}")
        if not order:
            st.error("Order details not found")
            return
        
        items = order.get('items', [])
        
        st.success(f"## 🎉 Order #{order_id} Placed Successfully!")
        st.markdown(f"**Order Date:** {order.get('created_at', '')}")
        st.markdown(f"**Total Amount:** ${order.get('total_price', 0):.2f}")
        st.markdown(f"**Status:** {order.get('status', '')}")
        
        st.markdown("### Order Details")
        for item in items:
            col1, col2 = st.columns([1, 5])
            with col1:
                st.image(item.get('image_url', ''), width=80)
            with col2:
                st.markdown(f"**{item.get('name', '')}**")
                st.markdown(f"Quantity: {item.get('quantity', 0)} × ${item.get('price', 0):.2f} = ${item.get('quantity', 0) * item.get('price', 0):.2f}")
        
        st.button("Continue Shopping", on_click=lambda: st.session_state.pop("order_placed"))

    # Render order history
    def render_order_history():
        if not st.session_state.token:
            st.warning("Please log in to view your order history")
            return
        
        orders = api_request("GET", "/api/orders") or []
        
        if not orders:
            st.info("You have no orders yet")
            return
        
        st.markdown("### Your Orders")
        
        for order in orders:
            with st.expander(f"Order #{order.get('id')} - ${order.get('total_price', 0):.2f} - {order.get('status', '')} - {order.get('created_at', '')}"):
                order_details = api_request("GET", f"/api/orders/{order.get('id')}")
                if not order_details:
                    continue
                    
                items = order_details.get('items', [])
                
                col1, col2 = st.columns(2)
                col1.markdown(f"**Order Date:** {order_details.get('created_at', '')}")
                col1.markdown(f"**Status:** {order_details.get('status', '')}")
                col2.markdown(f"**Total:** ${order_details.get('total_price', 0):.2f}")
                
                st.markdown("---")
                st.markdown("**Items:**")
                
                for item in items:
                    col3, col4 = st.columns([1, 5])
                    with col3:
                        st.image(item.get('image_url', ''), width=60)
                    with col4:
                        st.markdown(f"**{item.get('name', '')}**")
                        st.markdown(f"Quantity: {item.get('quantity', 0)} × ${item.get('price', 0):.2f}")

    # Render login form
    def render_login():
        with st.form("login_form"):
            st.markdown("### Login to Your Account")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            submitted = st.form_submit_button("Login")
            if submitted:
                data = {"username": username, "password": password}
                response = api_request("POST", "/api/auth/login", data)
                if response:
                    st.session_state.token = response.get('token')
                    st.session_state.user_id = response.get('user_id')
                    st.session_state.username = response.get('username')
                    # Get cart count
                    cart_items = api_request("GET", "/api/cart") or []
                    st.session_state.cart_count = len(cart_items)
                    st.success("Login successful!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")

    # Render registration form
    def render_register():
        with st.form("register_form"):
            st.markdown("### Create an Account")
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            submitted = st.form_submit_button("Register")
            if submitted:
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    data = {"username": username, "password": password, "email": email}
                    if api_request("POST", "/api/auth/register", data):
                        st.success("Account created successfully! Please log in.")
                    else:
                        st.error("Username already exists")

    # Render account page
    def render_account():
        if not st.session_state.token:
            st.warning("Please log in to view your account")
            return
        
        st.markdown(f"# Welcome, {st.session_state.username}!")
        
        tabs = st.tabs(["Profile", "Order History", "Logout"])
        
        with tabs[0]:
            st.markdown("### Your Profile")
            st.markdown(f"**Username:** {st.session_state.username}")
            # In a real app, you would show more profile information here
        
        with tabs[1]:
            render_order_history()
        
        with tabs[2]:
            st.markdown("### Are you sure you want to log out?")
            if st.button("Logout", use_container_width=True):
                st.session_state.clear()
                run_session_state()
                st.success("You have been logged out")
                st.experimental_rerun()

    # Render header
    render_header()
    
    # Page routing
    if st.session_state.get("order_placed", False):
        render_order_confirmation()
    elif st.session_state.get("view_product", None):
        render_product_details(st.session_state.view_product)
    elif st.session_state.page == "login":
        render_login()
        st.markdown("Don't have an account? [Register here](#register)")
    elif st.session_state.page == "register":
        render_register()
        st.markdown("Already have an account? [Login here](#login)")
    elif st.session_state.page == "account":
        render_account()
    elif st.session_state.page == "cart":
        render_cart()
    else:
        render_hero()
        
        # Search bar
        search_query = st.text_input("Search products...", key="search")
        
        # Category filter
        categories = ["All", "Development Tools", "Books & Courses", "Frameworks", "Server Solutions"]
        selected_category = st.selectbox("Filter by Category", categories, key="category")
        
        # Show products
        render_products(selected_category if selected_category != "All" else None, 
                        search_query if search_query else None)
    
    # Sidebar for login/register
    if not st.session_state.token and st.session_state.page not in ["login", "register"]:
        with st.sidebar:
            st.markdown("### Account")
            if st.button("Login", use_container_width=True):
                st.session_state.page = "login"
            if st.button("Register", use_container_width=True):
                st.session_state.page = "register"
    elif st.session_state.token:
        with st.sidebar:
            st.markdown(f"### Welcome, {st.session_state.username}")
            if st.button("View Account", key="view_account", use_container_width=True):
                st.session_state.page = "account"
            if st.button("View Cart", key="view_cart", use_container_width=True):
                st.session_state.page = "cart"
            if st.button("Order History", key="order_history", use_container_width=True):
                st.session_state.page = "account"

# Initialize and run the app
if __name__ == "__main__":
    import threading
    import requests
    import time
    
    # Initialize database
    init_db()
    
    # Start Flask in a separate thread
    def run_flask():
        app.run(port=5000, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Wait for Flask to start
    time.sleep(2)
    
    # Run Streamlit
    run_streamlit()
