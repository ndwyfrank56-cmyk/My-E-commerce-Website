from flask import Flask, render_template, request, url_for, flash, redirect, session, jsonify
from flask_mysqldb import MySQL
from flask_compress import Compress
# from flask_session import Session  # Disabled due to compatibility issues
import redis
# Using XAMPP MySQL - no SQLite fallback needed
USE_SQLITE = False
from collections import defaultdict
from functools import wraps
from datetime import datetime, timedelta
import os
import uuid
import hashlib
import secrets
import requests
import json
import base64
import bcrypt
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from threading import Lock, Thread
# from pay import PayClass as ExternalPayClass
# Google OAuth imports
import pathlib
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests

load_dotenv()

# Production mode detection
PRODUCTION_MODE = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('PRODUCTION', 'False').lower() == 'true'

app = Flask(__name__)
# Enforce SECRET_KEY in production
if PRODUCTION_MODE and not os.environ.get('SECRET_KEY'):
    raise RuntimeError("SECRET_KEY must be set in production environment")
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # Reduced from 24h to 2h
app.config['SESSION_COOKIE_SECURE'] = PRODUCTION_MODE  # True in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Performance: Enable GZIP Compression
compress = Compress()
compress.init_app(app)

# ============================================
# Email Sending Function (Gmail SMTP - Production)
# ============================================
def send_email_async(recipient_email, subject, html_content):
    """
    Log email to console (for testing/development).
    In production, you can replace this with a real email service.
    
    Args:
        recipient_email: Email address to send to
        subject: Email subject
        html_content: HTML content of the email
    
    Returns:
        True if successful, False otherwise
    """
    print(f"[THREAD] Email thread started for {recipient_email}")
    try:
        print(f"\n{'='*80}")
        print(f"[EMAIL] Order Confirmation Email")
        print(f"{'='*80}")
        print(f"TO: {recipient_email}")
        print(f"SUBJECT: {subject}")
        print(f"{'='*80}")
        print(f"CONTENT:")
        print(f"{html_content}")
        print(f"{'='*80}\n")
        
        print(f"[OK] Email logged to console for {recipient_email}")
        return True
            
    except Exception as e:
        print(f"[ERROR] Failed to log email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def send_email(recipient_email, subject, html_content):
    """
    Send an email asynchronously (non-blocking).
    Spawns a background thread to avoid blocking the main request.
    """
    thread = Thread(target=send_email_async, args=(recipient_email, subject, html_content), daemon=True)
    thread.start()
    return True  # Return immediately, email sends in background

def send_welcome_email(email, first_name):
    """Send a welcome email to a new user."""
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #333; text-align: center;">Welcome to CiTi🛒Plug!</h1>
                <p style="color: #666; font-size: 16px;">Hi {first_name},</p>
                <p style="color: #666; font-size: 16px;">Thank you for signing up with us! We're excited to have you as part of the CiTiPlug family.</p>
                <p style="color: #666; font-size: 16px;">You can now:</p>
                <ul style="color: #666; font-size: 16px;">
                    <li>Browse our amazing products</li>
                    <li>Add items to your wishlist</li>
                    <li>Place orders and track them</li>
                    <li>Manage your profile</li>
                </ul>
                <p style="color: #666; font-size: 16px;">If you have any questions, feel free to reach out to us.</p>
                <p style="color: #666; font-size: 16px;">Happy shopping!<br><strong>The CiTiPlug Team</strong></p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
    </html>
    """
    return send_email(email, "Welcome to CiTi🛒Plug!", html_content)

def send_order_confirmation_email(email, order_id, full_name, total_amount, items):
    """Send an order confirmation email."""
    items_html = "".join([
        f"<tr><td style='padding: 8px; border-bottom: 1px solid #ddd;'>{item['name']}</td><td style='padding: 8px; border-bottom: 1px solid #ddd; text-align: center;'>{item['quantity']}</td><td style='padding: 8px; border-bottom: 1px solid #ddd; text-align: right;'>RWF {item['price']:,.0f}</td></tr>"
        for item in items
    ])
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #333; text-align: center;">Order Confirmation</h1>
                <p style="color: #666; font-size: 16px;">Hi {full_name},</p>
                <p style="color: #666; font-size: 16px;">Thank you for your order! Here are your order details:</p>
                <p style="color: #333; font-size: 14px; font-weight: bold;">Order ID: #{order_id}</p>
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <thead>
                        <tr style="background-color: #f0f0f0;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Product</th>
                            <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Qty</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                <div style="text-align: right; margin: 20px 0;">
                    <p style="color: #333; font-size: 18px; font-weight: bold;">Total: RWF {total_amount:,.0f}</p>
                </div>
                <p style="color: #666; font-size: 16px;">We'll keep you updated on your order status. You can track your order anytime on your profile.</p>
                <p style="color: #666; font-size: 16px;">Thank you for shopping with CiTiPlug!<br><strong>The CiTiPlug Team</strong></p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
    </html>
    """
    return send_email(email, f"Order Confirmation - Order #{order_id}", html_content)

def send_order_status_email(email, full_name, order_id, status, tracking_info=None):
    """Send order status update email."""
    status_messages = {
        'processing': 'Your order is being prepared for shipment.',
        'shipped': 'Your order has been shipped! Track it with the information below.',
        'delivered': 'Your order has been delivered. Thank you for shopping with us!',
        'cancelled': 'Your order has been cancelled. A refund will be processed shortly.'
    }
    
    status_colors = {
        'processing': '#3b82f6',
        'shipped': '#f59e0b',
        'delivered': '#10b981',
        'cancelled': '#ef4444'
    }
    
    status_message = status_messages.get(status, 'Your order status has been updated.')
    status_color = status_colors.get(status, '#3b82f6')
    
    tracking_html = ''
    if tracking_info:
        tracking_html = f"""
        <div style="background: #f0f9ff; border-left: 4px solid {status_color}; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="color: #333; font-weight: bold; margin: 0 0 10px 0;">Tracking Information:</p>
            <p style="color: #666; margin: 5px 0;"><strong>Tracking Number:</strong> {tracking_info.get('tracking_number', 'N/A')}</p>
            <p style="color: #666; margin: 5px 0;"><strong>Carrier:</strong> {tracking_info.get('carrier', 'N/A')}</p>
        </div>
        """
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: {status_color}; text-align: center;">Order {status.upper()}</h1>
                <p style="color: #666; font-size: 16px;">Hi {full_name},</p>
                <p style="color: #666; font-size: 16px;">{status_message}</p>
                <p style="color: #333; font-size: 14px; font-weight: bold;">Order ID: #{order_id}</p>
                {tracking_html}
                <p style="color: #666; font-size: 16px;">You can view your order details anytime on your profile.</p>
                <p style="color: #666; font-size: 16px;">Thank you for shopping with CiTiPlug!<br><strong>The CiTiPlug Team</strong></p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
    </html>
    """
    return send_email(email, f"Order {status.upper()} - Order #{order_id}", html_content)

def send_order_cancellation_email(email, full_name, order_id, reason=None):
    """Send order cancellation email."""
    reason_text = f"<p style='color: #666; font-size: 16px;'><strong>Reason:</strong> {reason}</p>" if reason else ""
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #ef4444; text-align: center;">Order Cancelled</h1>
                <p style="color: #666; font-size: 16px;">Hi {full_name},</p>
                <p style="color: #666; font-size: 16px;">Your order has been cancelled.</p>
                <p style="color: #333; font-size: 14px; font-weight: bold;">Order ID: #{order_id}</p>
                {reason_text}
                <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="color: #333; margin: 0;"><strong>Refund Status:</strong> A refund will be processed to your original payment method within 5-7 business days.</p>
                </div>
                <p style="color: #666; font-size: 16px;">If you have any questions, please contact our support team.</p>
                <p style="color: #666; font-size: 16px;">Thank you for your understanding!<br><strong>The CiTiPlug Team</strong></p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
    </html>
    """
    return send_email(email, f"Order Cancelled - Order #{order_id}", html_content)

def send_admin_notification_email(admin_email, order_id, customer_name, customer_email, total_amount, items_count):
    """Send notification to admin when new order is placed."""
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #10b981; text-align: center;">🎉 New Order Received!</h1>
                <p style="color: #666; font-size: 16px;">A new order has been placed on CiTiPlug.</p>
                <div style="background: #f0fdf4; border-left: 4px solid #10b981; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <p style="color: #333; margin: 5px 0;"><strong>Order ID:</strong> #{order_id}</p>
                    <p style="color: #333; margin: 5px 0;"><strong>Customer:</strong> {customer_name}</p>
                    <p style="color: #333; margin: 5px 0;"><strong>Email:</strong> {customer_email}</p>
                    <p style="color: #333; margin: 5px 0;"><strong>Total Amount:</strong> RWF {total_amount:,.0f}</p>
                    <p style="color: #333; margin: 5px 0;"><strong>Items:</strong> {items_count}</p>
                </div>
                <p style="color: #666; font-size: 16px;"><a href="https://my-e-commerce-website.onrender.com/admin/orders" style="color: #10b981; text-decoration: none; font-weight: bold;">View Order Details →</a></p>
                <p style="color: #666; font-size: 16px;">Please process this order as soon as possible.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
    </html>
    """
    return send_email(admin_email, f"🎉 New Order #{order_id} - CiTiPlug", html_content)

def send_promotional_email(recipient_emails, subject, promo_title, promo_description, promo_code=None, discount_percent=None, valid_until=None):
    """Send promotional/newsletter email to multiple users."""
    promo_code_html = f"<p style='color: #333; font-size: 18px; font-weight: bold; text-align: center; background: #f0f0f0; padding: 15px; border-radius: 8px; margin: 20px 0;'>Use Code: <span style='color: #10b981;'>{promo_code}</span></p>" if promo_code else ""
    discount_html = f"<p style='color: #ef4444; font-size: 24px; font-weight: bold; text-align: center;'>{discount_percent}% OFF</p>" if discount_percent else ""
    valid_until_html = f"<p style='color: #999; font-size: 12px; text-align: center;'>Valid until: {valid_until}</p>" if valid_until else ""
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #10b981; text-align: center;">{promo_title}</h1>
                {discount_html}
                <p style="color: #666; font-size: 16px; text-align: center;">{promo_description}</p>
                {promo_code_html}
                {valid_until_html}
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://my-e-commerce-website.onrender.com" style="background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Shop Now</a>
                </div>
                <p style="color: #666; font-size: 14px;">Don't miss out on this amazing offer!</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
    </html>
    """
    
    # Send to all recipients
    success_count = 0
    for email in recipient_emails:
        if send_email(email, subject, html_content):
            success_count += 1
    
    return success_count == len(recipient_emails)

# ============================================
# WhatsApp Link Generator (Simple & Free)
# ============================================
def generate_whatsapp_link(phone_number, message_text):
    """
    Generate WhatsApp link for sending messages.
    User clicks link to send message via their WhatsApp.
    
    Args:
        phone_number: Phone number with country code (e.g., +250788123456)
        message_text: Message to send
    
    Returns:
        WhatsApp link URL
    """
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    # Remove + for URL encoding
    phone_clean = phone_number.replace('+', '')
    
    # URL encode the message
    import urllib.parse
    message_encoded = urllib.parse.quote(message_text)
    
    # Generate WhatsApp link
    whatsapp_link = f'https://wa.me/{phone_clean}?text={message_encoded}'
    
    return whatsapp_link

# Performance: Add caching headers for static files
@app.after_request
def add_caching_headers(response):
    if request.endpoint == 'static':
        # Cache static files for 30 days
        response.cache_control.max_age = 30 * 24 * 60 * 60
        response.cache_control.public = True
    return response
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'ecommerce')
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', 3306))

# Force MySQL usage (disable SQLite fallback for XAMPP)
USE_SQLITE = False
mysql = MySQL(app)

# Redis Configuration for Sessions and Caching
# In production, set REDIS_HOST, REDIS_PORT, REDIS_PASSWORD in environment variables
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
REDIS_DB = int(os.environ.get('REDIS_DB', 0))

# Configure Redis connection
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True
    )
    # Test Redis connection
    redis_client.ping()
    print(f"[OK] Redis connected successfully to {REDIS_HOST}:{REDIS_PORT}")
    REDIS_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] Redis connection failed: {e}")
    print("[INFO] Falling back to Flask default sessions")
    REDIS_AVAILABLE = False

# Note: Flask-Session disabled due to compatibility issues
# Using Redis only for cart storage and caching
# Sessions handled by Flask's default secure cookie-based sessions
if REDIS_AVAILABLE:
    print("[OK] Redis available for cart storage and caching")
    print("[INFO] Using Flask secure cookie-based sessions")
else:
    print("[INFO] Using Flask default sessions and in-memory storage")

# ============================================
# Google OAuth Configuration
# ============================================
# Allow HTTP ONLY in development mode (NEVER in production!)
if not PRODUCTION_MODE:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    print("[WARNING] OAUTHLIB_INSECURE_TRANSPORT enabled - DEVELOPMENT MODE ONLY")
else:
    # In production, enforce HTTPS
    if os.environ.get("OAUTHLIB_INSECURE_TRANSPORT"):
        del os.environ["OAUTHLIB_INSECURE_TRANSPORT"]
    print("[OK] HTTPS required for OAuth - PRODUCTION MODE")

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

# Determine redirect URI based on environment
if PRODUCTION_MODE:
    # Production: Use your actual domain with HTTPS
    default_redirect = os.environ.get('GOOGLE_REDIRECT_URI', 'https://yourdomain.com/google/callback')
else:
    # Development: Use localhost
    default_redirect = os.environ.get('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:5000/google/callback')

# Initialize Google OAuth - try environment variables first, then client_secret.json
GOOGLE_AUTH_ENABLED = False
flow = None

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        # Use environment variables
        from google_auth_oauthlib.flow import Flow as GoogleFlow
        flow = GoogleFlow.from_client_config(
            {
                "installed": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [default_redirect]
                }
            },
            scopes=[
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid"
            ],
            redirect_uri=default_redirect
        )
        GOOGLE_AUTH_ENABLED = True
        print(f"[OK] Google OAuth initialized from environment variables: {default_redirect}")
    except Exception as e:
        print(f"[WARNING] Google OAuth from env vars failed: {e}")
elif os.path.exists(client_secrets_file):
    try:
        # Fallback to client_secret.json
        flow = Flow.from_client_secrets_file(
            client_secrets_file=client_secrets_file,
            scopes=[
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid"
            ],
            redirect_uri=default_redirect
        )
        GOOGLE_AUTH_ENABLED = True
        print(f"[OK] Google OAuth initialized from client_secret.json: {default_redirect}")
    except Exception as e:
        print(f"[WARNING] Google OAuth from client_secret.json failed: {e}")
else:
    print("[INFO] Google OAuth not configured - set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables")

def get_db_cursor():
    """Get database cursor with error handling"""
    try:
        return mysql.connection.cursor()
    except Exception as e:
        print(f"Database connection error: {e}")
        print("Please ensure XAMPP MySQL is running.")
        return None


# Redis Helper Functions
def get_redis_cart_key(user_id=None):
    """Generate Redis key for cart storage"""
    if user_id:
        return f"cart:user:{user_id}"
    else:
        # Use session ID for guest users
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session.modified = True  # Important: save session_id to cookie
        return f"cart:guest:{session['session_id']}"


def save_cart_to_redis(cart_data, user_id=None):
    """Save cart data to Redis with fallback to Flask session"""
    if not REDIS_AVAILABLE:
        session['cart'] = cart_data
        return True
    
    try:
        cart_key = get_redis_cart_key(user_id)
        redis_client.setex(cart_key, 7200, json.dumps(cart_data))  # 2 hours TTL
        return True
    except Exception as e:
        print(f"Redis cart save error: {e}")
        # Fallback to session
        session['cart'] = cart_data
        return False


def get_cart_from_redis(user_id=None):
    """Get cart data from Redis with fallback to Flask session"""
    if not REDIS_AVAILABLE:
        return session.get('cart', {})
    
    try:
        cart_key = get_redis_cart_key(user_id)
        cart_data = redis_client.get(cart_key)
        if cart_data:
            return json.loads(cart_data)
        return {}
    except Exception as e:
        print(f"Redis cart get error: {e}")
        # Fallback to session
        return session.get('cart', {})


def clear_cart_from_redis(user_id=None):
    """Clear cart data from Redis with fallback to Flask session"""
    if not REDIS_AVAILABLE:
        session.pop('cart', None)
        return True
    
    try:
        cart_key = get_redis_cart_key(user_id)
        redis_client.delete(cart_key)
        return True
    except Exception as e:
        print(f"Redis cart clear error: {e}")
        # Fallback to session
        session.pop('cart', None)
        return False


def cache_data(key, data, ttl=3600):
    """Cache data in Redis with TTL (default 1 hour)"""
    if not REDIS_AVAILABLE:
        return False
    
    try:
        redis_client.setex(f"cache:{key}", ttl, json.dumps(data))
        return True
    except Exception as e:
        print(f"Redis cache set error: {e}")
        return False


def get_cached_data(key):
    """Get cached data from Redis"""
    if not REDIS_AVAILABLE:
        return None
    
    try:
        cached_data = redis_client.get(f"cache:{key}")
        if cached_data:
            return json.loads(cached_data)
        return None
    except Exception as e:
        print(f"Redis cache get error: {e}")
        return None


def clear_cache(pattern="*"):
    """Clear cache with optional pattern"""
    if not REDIS_AVAILABLE:
        return False
    
    try:
        keys = redis_client.keys(f"cache:{pattern}")
        if keys:
            redis_client.delete(*keys)
        return True
    except Exception as e:
        print(f"Redis cache clear error: {e}")
        return False


def get_cached_categories():
    """Get categories from cache or database"""
    cache_key = "categories"
    cached_categories = get_cached_data(cache_key)
    
    if cached_categories:
        return cached_categories
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM categories")
        categories_data = cur.fetchall()
        categories = [{'id': cat[0], 'name': cat[1]} for cat in categories_data]
        cur.close()
        
        # Cache for 1 hour
        cache_data(cache_key, categories, 3600)
        return categories
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []


def get_cached_products(category_id=None, limit=None):
    """Get products from cache or database"""
    cache_key = f"products_cat_{category_id}_limit_{limit}"
    cached_products = get_cached_data(cache_key)
    
    if cached_products:
        return cached_products
    
    try:
        cur = mysql.connection.cursor()
        if category_id:
            if limit:
                cur.execute("SELECT * FROM products WHERE category_id = %s LIMIT %s", (category_id, limit))
            else:
                cur.execute("SELECT * FROM products WHERE category_id = %s", (category_id,))
        else:
            if limit:
                cur.execute("SELECT * FROM products LIMIT %s", (limit,))
            else:
                cur.execute("SELECT * FROM products")
        
        products_data = cur.fetchall()
        products = []
        for product_data in products_data:
            product = get_product_with_discount(product_data)
            if product:
                products.append(product)
        cur.close()
        
        # Cache for 30 minutes
        cache_data(cache_key, products, 1800)
        return products
    except Exception as e:
        print(f"Error fetching products: {e}")
        return []


def deduct_stock_smartly(cur, product_id, quantity, variations_string):
    """
    Deduct stock from the appropriate level based on variations.
    Uses the hierarchy: dropdown_variation -> image_variation -> product
    Your triggers will cascade the updates automatically.
    """
    try:
        print(f"STOCK DEDUCTION: product_id={product_id}, qty={quantity}, variations='{variations_string}'")
        
        if not variations_string or variations_string.strip() == '':
            # No variations - deduct from product directly
            print("STOCK DEDUCTION: No variations, updating product stock")
            cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, product_id))
            return "product"
        
        # Parse variations string (format: "color:Red, size:41" or "color:Red")
        variations = {}
        for part in variations_string.split(','):
            if ':' in part:
                key, value = part.split(':', 1)
                variations[key.strip().lower()] = value.strip()
        
        print(f"STOCK DEDUCTION: Parsed variations: {variations}")
        
        # Check if we have both color/style AND size (dropdown variation)
        has_color_or_style = any(k in variations for k in ['color', 'style'])
        has_size = 'size' in variations
        
        if has_color_or_style and has_size:
            # Try to find specific dropdown variation
            color_or_style = variations.get('color') or variations.get('style')
            size_value = variations.get('size')
            
            # First find the image_variation ID
            cur.execute("""
                SELECT id FROM image_variations 
                WHERE prod_id = %s AND (
                    (type = 'color' AND name = %s) OR 
                    (type = 'style' AND name = %s)
                )
            """, (product_id, color_or_style, color_or_style))
            
            img_var_result = cur.fetchone()
            if img_var_result:
                img_var_id = img_var_result[0]
                
                # Now find the dropdown variation
                cur.execute("""
                    SELECT id FROM dropdown_variation 
                    WHERE prod_id = %s AND img_var_id = %s AND attr_value = %s
                """, (product_id, img_var_id, size_value))
                
                dropdown_result = cur.fetchone()
                if dropdown_result:
                    dropdown_id = dropdown_result[0]
                    print(f"STOCK DEDUCTION: Updating dropdown_variation id={dropdown_id}")
                    cur.execute("UPDATE dropdown_variation SET stock = stock - %s WHERE id = %s", (quantity, dropdown_id))
                    return "dropdown"
        
        # If no dropdown found, try image variation only
        if has_color_or_style:
            color_or_style = variations.get('color') or variations.get('style')
            cur.execute("""
                SELECT id FROM image_variations 
                WHERE prod_id = %s AND (
                    (type = 'color' AND name = %s) OR 
                    (type = 'style' AND name = %s)
                )
            """, (product_id, color_or_style, color_or_style))
            
            img_var_result = cur.fetchone()
            if img_var_result:
                img_var_id = img_var_result[0]
                print(f"STOCK DEDUCTION: Updating image_variation id={img_var_id}")
                cur.execute("UPDATE image_variations SET stock = stock - %s WHERE id = %s", (quantity, img_var_id))
                return "image"
        
        # Fallback to product level
        print("STOCK DEDUCTION: Fallback to product stock")
        cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, product_id))
        return "product"
        
    except Exception as e:
        print(f"STOCK DEDUCTION ERROR: {e}")
        # Fallback to product level on any error
        cur.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, product_id))
        return "product_fallback"


def restore_stock_smartly(cur, product_id, quantity, variations_string):
    """
    Restore stock to the appropriate level based on variations (opposite of deduct_stock_smartly).
    Uses the hierarchy: dropdown_variation -> image_variation -> product
    Your triggers will cascade the updates automatically.
    """
    try:
        print(f"STOCK RESTORATION: product_id={product_id}, qty={quantity}, variations='{variations_string}'")
        
        if not variations_string or variations_string.strip() == '':
            # No variations - restore to product directly
            print("STOCK RESTORATION: No variations, updating product stock")
            cur.execute("UPDATE products SET stock = stock + %s WHERE id = %s", (quantity, product_id))
            return "product"
        
        # Parse variations string (format: "color:Red, size:41" or "color:Red")
        variations = {}
        for part in variations_string.split(','):
            if ':' in part:
                key, value = part.split(':', 1)
                variations[key.strip().lower()] = value.strip()
        
        print(f"STOCK RESTORATION: Parsed variations: {variations}")
        
        # Check if we have both color/style AND size (dropdown variation)
        has_color_or_style = any(k in variations for k in ['color', 'style'])
        has_size = 'size' in variations
        
        if has_color_or_style and has_size:
            # Try to find specific dropdown variation
            color_or_style = variations.get('color') or variations.get('style')
            size_value = variations.get('size')
            
            # First find the image_variation ID
            cur.execute("""
                SELECT id FROM image_variations 
                WHERE prod_id = %s AND (
                    (type = 'color' AND name = %s) OR 
                    (type = 'style' AND name = %s)
                )
            """, (product_id, color_or_style, color_or_style))
            
            img_var_result = cur.fetchone()
            if img_var_result:
                img_var_id = img_var_result[0]
                
                # Now find the dropdown variation
                cur.execute("""
                    SELECT id FROM dropdown_variation 
                    WHERE prod_id = %s AND img_var_id = %s AND attr_value = %s
                """, (product_id, img_var_id, size_value))
                
                dropdown_result = cur.fetchone()
                if dropdown_result:
                    dropdown_id = dropdown_result[0]
                    print(f"STOCK RESTORATION: Updating dropdown_variation id={dropdown_id}")
                    cur.execute("UPDATE dropdown_variation SET stock = stock + %s WHERE id = %s", (quantity, dropdown_id))
                    return "dropdown"
        
        # If no dropdown found, try image variation only
        if has_color_or_style:
            color_or_style = variations.get('color') or variations.get('style')
            cur.execute("""
                SELECT id FROM image_variations 
                WHERE prod_id = %s AND (
                    (type = 'color' AND name = %s) OR 
                    (type = 'style' AND name = %s)
                )
            """, (product_id, color_or_style, color_or_style))
            
            img_var_result = cur.fetchone()
            if img_var_result:
                img_var_id = img_var_result[0]
                print(f"STOCK RESTORATION: Updating image_variation id={img_var_id}")
                cur.execute("UPDATE image_variations SET stock = stock + %s WHERE id = %s", (quantity, img_var_id))
                return "image"
        
        # Fallback to product level
        print("STOCK RESTORATION: Fallback to product stock")
        cur.execute("UPDATE products SET stock = stock + %s WHERE id = %s", (quantity, product_id))
        return "product"
        
    except Exception as e:
        print(f"STOCK RESTORATION ERROR: {e}")
        # Fallback to product level on any error
        cur.execute("UPDATE products SET stock = stock + %s WHERE id = %s", (quantity, product_id))
        return "product_fallback"

# MTN MoMo PayClass
class PayClass:
    # Enforce API keys from environment variables only
    collections_subkey = os.environ.get('MOMO_COLLECTIONS_SUBKEY')
    if not collections_subkey:
        raise RuntimeError("MOMO_COLLECTIONS_SUBKEY must be set in environment variables")
    environment_mode = os.environ.get('MOMO_ENV_MODE', 'sandbox')
    accurl = "https://sandbox.momodeveloper.mtn.com" if environment_mode == "sandbox" else "https://proxy.momoapi.mtn.com"
    collections_apiuser = None
    api_key_collections = None
    basic_authorisation_collections = None

    @classmethod
    def initialize_api_user(cls):
        print(f"DEBUG: Initializing API user with subkey: {bool(cls.collections_subkey)}")
        if cls.collections_apiuser and cls.api_key_collections:
            print("DEBUG: Using existing credentials from environment")
            return
        try:
            # Use existing credentials from environment if available
            cls.collections_apiuser = os.environ.get('MOMO_API_USER')
            cls.api_key_collections = os.environ.get('MOMO_API_KEY')
            
            if cls.collections_apiuser and cls.api_key_collections:
                print(f"Using existing MTN MoMo credentials from environment")
                # Build HTTP Basic auth header value: Base64(apiUser:apiKey)
                basic_raw = f"{cls.collections_apiuser}:{cls.api_key_collections}".encode("utf-8")
                cls.basic_authorisation_collections = "Basic " + base64.b64encode(basic_raw).decode("utf-8")
                return
            
            # Fallback: Create new API user and key if not in environment
            print("Creating new MTN MoMo API user...")
            cls.collections_apiuser = str(uuid.uuid4())
            url = f"{cls.accurl}/v1_0/apiuser"
            payload = json.dumps({"providerCallbackHost": "example.com"})
            headers = {
                'X-Reference-Id': cls.collections_apiuser,
                'Content-Type': 'application/json',
                'Ocp-Apim-Subscription-Key': cls.collections_subkey
            }
            response = requests.post(url, headers=headers, data=payload)
            print(f"DEBUG: API user creation response: {response.status_code}")
            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to create API user: {response.text}")

            url = f"{cls.accurl}/v1_0/apiuser/{cls.collections_apiuser}/apikey"
            headers = {'Ocp-Apim-Subscription-Key': cls.collections_subkey}
            response = requests.post(url, headers=headers)
            print(f"DEBUG: API key creation response: {response.status_code}")
            if response.status_code != 201:
                raise Exception(f"Failed to create API key: {response.text}")
            cls.api_key_collections = response.json().get("apiKey")
            
            print(f"New API user created: {cls.collections_apiuser}")
            print(f"Add these to your .env file:")
            print(f"MOMO_API_USER={cls.collections_apiuser}")
            print(f"MOMO_API_KEY={cls.api_key_collections}")
            
            # Build HTTP Basic auth header value: Base64(apiUser:apiKey)
            basic_raw = f"{cls.collections_apiuser}:{cls.api_key_collections}".encode("utf-8")
            cls.basic_authorisation_collections = "Basic " + base64.b64encode(basic_raw).decode("utf-8")
        except Exception as e:
            print(f"DEBUG: API user initialization failed: {e}")
            raise

    @classmethod
    def momotoken(cls):
        try:
            url = f"{cls.accurl}/collection/token/"
            headers = {
                'Ocp-Apim-Subscription-Key': cls.collections_subkey,
                'Authorization': cls.basic_authorisation_collections
            }
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            print(f"Token error: {response.text}")
            return {"access_token": None}
        except Exception as e:
            print(f"Token generation error: {e}")
            return {"access_token": None}

    @classmethod
    def momopay(cls, amount, currency, txt_ref, phone_number, payermessage):
        print(f"DEBUG: momopay called with amount={amount}, phone={phone_number}, currency={currency}")
        try:
            # Test API connectivity first
            test_url = f"{cls.accurl}/collection/v1_0/requesttopay"
            print(f"DEBUG: Testing connection to {test_url}")
            
            token = cls.momotoken().get('access_token')
            print(f"DEBUG: Token obtained: {bool(token)}")
            if not token:
                return {
                    "response": 500, 
                    "ref": None, 
                    "error": "Failed to obtain access token",
                    "error_code": "TOKEN_FAILED",
                    "user_messagfe": "Payment service temporarily unavailable. Please try again later."
                }
            uuidgen = str(uuid.uuid4())
            url = f"{cls.accurl}/collection/v1_0/requesttopay"
            payload = json.dumps({
                "amount": str(int(amount)),
                "currency": currency,
                "externalId": txt_ref,
                "payer": {"partyIdType": "MSISDN", "partyId": phone_number},
                "payerMessage": payermessage,
                "payeeNote": payermessage
            })
            headers = {
                'X-Reference-Id': uuidgen,
                'X-Target-Environment': cls.environment_mode,
                'Ocp-Apim-Subscription-Key': cls.collections_subkey,
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {token}"
            }
            response = requests.post(url, headers=headers, data=payload)
            
            if response.status_code in [200, 202]:
                return {"response": response.status_code, "ref": uuidgen, "error": None}
            else:
                # Parse error response for detailed information
                error_details = cls._parse_payment_error(response)
                return {
                    "response": response.status_code, 
                    "ref": uuidgen, 
                    "error": error_details["technical_error"],
                    "error_code": error_details["error_code"],
                    "user_message": error_details["user_message"]
                }
        except requests.exceptions.Timeout:
            return {
                "response": 408, 
                "ref": None, 
                "error": "Request timeout",
                "error_code": "TIMEOUT",
                "user_message": "Payment request timed out. Please check your network connection and try again."
            }
        except requests.exceptions.ConnectionError:
            return {
                "response": 503, 
                "ref": None, 
                "error": "Connection error",
                "error_code": "CONNECTION_ERROR",
                "user_message": "Unable to connect to payment service. Please check your internet connection."
            }
        except Exception as e:
            print(f"MoMo pay error: {e}")
            return {
                "response": 500, 
                "ref": None, 
                "error": str(e),
                "error_code": "UNKNOWN_ERROR",
                "user_message": "An unexpected error occurred. Please try again or contact support."
            }

    @classmethod
    def _parse_payment_error(cls, response):
        """Parse payment error response and return user-friendly messages"""
        try:
            error_data = response.json() if response.content else {}
        except:
            error_data = {}
        
        status_code = response.status_code
        error_code = error_data.get('code', 'UNKNOWN_ERROR')
        error_message = error_data.get('message', response.text)
        
        # Map common errors to user-friendly messages
        user_messages = {
            400: "Invalid payment request. Please check your details and try again.",
            401: "Payment service authentication failed. Please try again later.",
            403: "Payment not authorized. Please check your mobile money account.",
            404: "Payment service not found. Please try again later.",
            409: "Duplicate payment request. Please wait and try again.",
            500: "Payment service temporarily unavailable. Please try again later.",
            502: "Payment gateway error. Please try again later.",
            503: "Payment service maintenance. Please try again later.",
            504: "Payment request timeout. Please try again."
        }
        
        return {
            "technical_error": f"HTTP {status_code}: {error_message}",
            "error_code": error_code,
            "user_message": user_messages.get(status_code, "Payment failed. Please try again or contact support.")
        }

    @classmethod
    def verifymomo(cls, txn):
        try:
            token = cls.momotoken().get('access_token')
            if not token:
                return {"status": "ERROR", "reason": "Failed to obtain access token"}
            url = f"{cls.accurl}/collection/v1_0/requesttopay/{txn}"
            headers = {
                'Ocp-Apim-Subscription-Key': cls.collections_subkey,
                'Authorization': f"Bearer {token}",
                'X-Target-Environment': cls.environment_mode
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            return {"status": "ERROR", "reason": response.text}
        except Exception as e:
            print(f"Verify MoMo error: {e}")
            return {"status": "ERROR", "reason": str(e)}

# Initialize PayClass (use internal implementation with better error handling)
try:
    # Use the internal PayClass implementation which has superior error handling
    PayClass.initialize_api_user()
    print("MTN MoMo PayClass initialized successfully")
except Exception as e:
    print(f"PayClass initialization failed: {e}")
    print("Warning: Payment functionality may be limited")

# HTTPS redirect middleware
@app.before_request
def redirect_to_https():
    """Force HTTPS in production"""
    if PRODUCTION_MODE:
        if not request.is_secure and request.headers.get('X-Forwarded-Proto', 'http') != 'https':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

# Security headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if PRODUCTION_MODE:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Content Security Policy for XSS protection - Allow Font Awesome icons & OpenStreetMap
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "frame-src 'self' https://www.openstreetmap.org; "
        "connect-src 'self';"
    )
    return response

@app.get('/api/geocode')
def geocode_proxy():
    try:
        q = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 8))
        country = (request.args.get('country') or '').strip().lower()
        if not q:
            return jsonify([])

        # Nominatim primary
        params = {
            'format': 'jsonv2',
            'addressdetails': 1,
            'q': q,
            'limit': limit,
        }
        if country:
            params['countrycodes'] = country
        headers = {
            'User-Agent': 'eMarket/1.0 (contact: support@example.com)'
        }
        try:
            r = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, timeout=5)
            if r.ok:
                items = r.json()
                if isinstance(items, list) and len(items) > 0:
                    return jsonify(items)
        except Exception:
            pass

        # Photon fallback
        try:
            r2 = requests.get('https://photon.komoot.io/api/', params={'q': q, 'limit': limit}, timeout=5)
            if r2.ok:
                data = r2.json()
                features = data.get('features', []) if isinstance(data, dict) else []
                items = []
                for f in features:
                    try:
                        lon, lat = f['geometry']['coordinates']
                        props = f.get('properties', {})
                        display = ', '.join([
                            str(props.get('name') or ''),
                            str(props.get('street') or ''),
                            str(props.get('city') or ''),
                            str(props.get('country') or ''),
                        ])
                        display = ', '.join([p for p in [s.strip() for s in display.split(',')] if p])
                        items.append({'lat': lat, 'lon': lon, 'display_name': display})
                    except Exception:
                        continue
                return jsonify(items)
        except Exception:
            pass
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# CSRF protection
def _ensure_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
        session.modified = True

def validate_csrf():
    """Validate CSRF token"""
    token = session.get('csrf_token')
    form_token = request.form.get('csrf_token')
    return token and form_token and token == form_token

def calculate_discounted_price(original_price, discount_percent):
    """Calculate discounted price"""
    if discount_percent and discount_percent > 0:
        return original_price * (1 - discount_percent / 100)
    return original_price

def build_cart_items_from_session(cur, session_cart):
    """Build cart items list from session, fetching variation images from database"""
    cart_items = []
    for cart_key, item in session_cart.items():
        # Extract actual product_id from cart item
        actual_product_id = item.get('product_id', cart_key.split('_')[0] if '_' in cart_key else cart_key)
        img_var_id = item.get('img_var_id', '')
        
        cur.execute("SELECT * FROM products WHERE id = %s", (actual_product_id,))
        product_data = cur.fetchone()
        if product_data:
            product = get_product_with_discount(product_data)
            if product:
                qty = min(item['quantity'], product['stock'])
                if qty > 0:
                    # Fetch image from database based on variation
                    image_url = product['image']
                    img_var_name = ''
                    img_var_description = ''
                    if img_var_id and str(img_var_id).strip():
                        try:
                            cur.execute("SELECT img_url, name, description FROM image_variations WHERE id = %s", (img_var_id,))
                            result = cur.fetchone()
                            if result and result[0]:
                                image_url = resolve_image_url(result[0])
                                img_var_name = result[1] if len(result) > 1 else ''
                                img_var_description = result[2] if len(result) > 2 else ''
                        except Exception:
                            pass
                    
                    cart_items.append({
                        'id': cart_key,
                        'product_id': actual_product_id,
                        'name': item['name'],
                        'price': item['price'],
                        'image': image_url,
                        'quantity': qty,
                        'stock': product['stock'],
                        'variations': item.get('variations', ''),
                        'is_new': False,
                        'img_var_name': img_var_name,
                        'img_var_description': img_var_description
                    })
    return cart_items

def resolve_image_url(image_value):
    """Normalize image path to the Flask static images folder or pass through Cloudinary URLs.
    Accepts values like:
    - 'cooler-bag-xxx.jpg' -> '/static/images/cooler-bag-xxx.jpg'
    - '/images/xyz.jpg'    -> '/static/images/xyz.jpg'
    - '/static/images/..'  -> kept as-is
    - 'https://res.cloudinary.com/...' -> kept as-is (Cloudinary URL)
    """
    try:
        if not image_value:
            return image_value
        s = str(image_value).strip()
        # Pass through Cloudinary URLs and any HTTPS URLs
        if s.startswith('https://') or s.startswith('http://'):
            return s
        if s.startswith('/static/'):
            return s
        if s.startswith('/images/'):
            return '/static' + s
        # assume it's a bare filename
        return '/static/images/' + s
    except Exception:
        return image_value

def fetch_image_variations(cur, product_id):
    """Fetch image variations for a product with resolved URLs"""
    image_variations = []
    try:
        cur.execute("""
            SELECT id, type, name, description, stock, img_url
            FROM image_variations
            WHERE prod_id = %s
            ORDER BY type, name
        """, (product_id,))
        for row in cur.fetchall():
            image_variations.append({
                'id': row[0],
                'type': row[1],
                'name': row[2],
                'description': row[3],
                'stock': row[4],
                'img_url': resolve_image_url(row[5])
            })
    except Exception as e:
        print(f"Error fetching image variations: {e}")
    return image_variations

def fetch_dropdown_variations(cur, product_id):
    """Fetch dropdown variations for a product"""
    dropdown_variations = {}
    try:
        cur.execute("""
            SELECT id, attr_name, attr_value, stock, img_var_id
            FROM dropdown_variation
            WHERE prod_id = %s
            ORDER BY attr_name, attr_value
        """, (product_id,))
        for row in cur.fetchall():
            attr_name = row[1]
            if attr_name not in dropdown_variations:
                dropdown_variations[attr_name] = []
            dropdown_variations[attr_name].append({
                'id': row[0],
                'value': row[2],
                'stock': row[3],
                'img_var_id': row[4]
            })
    except Exception as e:
        print(f"Error fetching dropdown variations: {e}")
    return dropdown_variations

def get_product_with_discount(product_data):
    """Get product data with discount calculations"""
    if not product_data:
        return None
    
    original_price = float(product_data[2]) if product_data[2] is not None else 0.0
    discount = float(product_data[7] if len(product_data) > 7 and product_data[7] is not None else 0)
    discounted_price = calculate_discounted_price(original_price, discount)
    
    return {
        'id': product_data[0],
        'name': product_data[1],
        'original_price': original_price,
        'price': discounted_price,  # Use discounted price as the main price
        'discount': discount,
        'image': resolve_image_url(product_data[3]),
        'category_id': product_data[4],
        'stock': product_data[5] if len(product_data) > 5 else 999,
        'description': product_data[6] if len(product_data) > 6 else '',
        # Rating from products.rate (index 8), provide both 'rate' and 'rating' keys for templates
        'rate': float(product_data[8]) if len(product_data) > 8 and product_data[8] is not None else 0.0,
        'rating': float(product_data[8]) if len(product_data) > 8 and product_data[8] is not None else 0.0,
    }

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'error': 'Please log in to access this feature.'}), 401
            flash('Please log in to access this feature.', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Password validation
def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

# Hash password
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Verify password
def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Rate limiting - expanded to multiple endpoints
login_attempts = {}
registration_attempts = {}
checkout_attempts = {}

# Jinja filter: floatformat
@app.template_filter('floatformat')
def floatformat(value, precision=1):
    """Format a number with a fixed number of decimal places.
    Usage: {{ value|floatformat(1) }}
    """
    try:
        p = int(precision)
        return f"{float(value):.{p}f}"
    except Exception:
        return value

@app.template_filter('fmtvars')
def fmtvars(value):
    """Format variations as 'attr:value, attr2:value2' with lowercase attr names and space after comma.
    Input: 'Size=41, Color=Red' or 'Size:41,Color:Red'
    Output: 'size:41, color:Red'
    """
    try:
        if not value:
            return ''
        s = str(value)
        parts = []
        for p in s.split(','):
            p = p.strip()
            if not p:
                continue
            # Split by = or :
            if '=' in p:
                k, v = p.split('=', 1)
            elif ':' in p:
                k, v = p.split(':', 1)
            else:
                continue
            k = k.strip().lower()
            v = v.strip()
            parts.append(f'{k}:{v}')
        return ', '.join(parts)  # Space after comma
    except Exception:
        return value

@app.template_filter('fmtdate')
def fmtdate(value, fmt='%b %d, %Y • %H:%M'):
    """Pretty-format a datetime or ISO string.
    Usage: {{ some_dt|fmtdate }} or {{ some_dt|fmtdate('%d %b %Y') }}
    """
    try:
        if isinstance(value, datetime):
            return value.strftime(fmt)
        s = str(value)
        try:
            # Handle values like '2025-10-30 16:53:46' or with timezone
            return datetime.fromisoformat(s.replace('Z', '+00:00')).strftime(fmt)
        except Exception:
            try:
                return datetime.strptime(s, '%Y-%m-%d %H:%M:%S').strftime(fmt)
            except Exception:
                return s
    except Exception:
        return value

def is_rate_limited(ip_address, attempt_dict=None, max_attempts=5, window_minutes=15):
    """Generic rate limiting function"""
    if attempt_dict is None:
        attempt_dict = login_attempts
    now = datetime.now()
    if ip_address in attempt_dict:
        attempts = attempt_dict[ip_address]
        attempts = [attempt for attempt in attempts if now - attempt < timedelta(minutes=window_minutes)]
        attempt_dict[ip_address] = attempts
        return len(attempts) >= max_attempts
    return False

def record_attempt(ip_address, attempt_dict=None):
    """Generic attempt recording"""
    if attempt_dict is None:
        attempt_dict = login_attempts
    now = datetime.now()
    if ip_address not in attempt_dict:
        attempt_dict[ip_address] = []
    attempt_dict[ip_address].append(now)

def regenerate_session():
    """Regenerate session ID to prevent session fixation attacks"""
    # Store data we want to keep
    user_id = session.get('user_id')
    username = session.get('username')
    cart = session.get('cart', {})  # Always preserve cart
    csrf_token = session.get('csrf_token')
    
    # Clear and regenerate
    session.clear()
    
    # Restore essential data
    if user_id:
        session['user_id'] = user_id
    if username:
        session['username'] = username
    if cart:
        session['cart'] = cart
    
    # Generate new CSRF token if none existed
    session['csrf_token'] = csrf_token or secrets.token_urlsafe(32)
    session.modified = True

def safe_error_log(error, context=""):
    """Log errors safely - verbose in dev, generic in production"""
    if PRODUCTION_MODE:
        # In production, log detailed error to server logs only
        app.logger.error(f"{context}: {str(error)}")
        return "An error occurred. Please try again or contact support."
    else:
        # In development, show detailed error
        print(f"{context}: {error}")
        return f"Error: {error}"

# Cached helper functions for performance # Cache for 10 minutes
def get_all_categories():
    """Cached category fetching - reduces DB load by 90%"""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories_data = cur.fetchall()
    cur.close()
    return [{'id': cat[0], 'name': cat[1]} for cat in categories_data]


def get_product_by_id(product_id):
    """Cached single product fetching"""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product_data = cur.fetchone()
    cur.close()
    return product_data

def get_cart_products_bulk(product_ids):
    """Fetch multiple cart products in ONE query - 10x faster than loops!"""
    if not product_ids:
        return {}
    
    cur = mysql.connection.cursor()
    placeholders = ','.join(['%s'] * len(product_ids))
    query = f"SELECT * FROM products WHERE id IN ({placeholders})"
    cur.execute(query, tuple(product_ids))
    products_data = cur.fetchall()
    cur.close()
    
    # Convert to dict for easy lookup
    products_dict = {}
    for prod in products_data:
        product = get_product_with_discount(prod)
        if product:
            products_dict[str(product['id'])] = product
    return products_dict

# DB initialization
_db_init_lock = Lock()
_db_init_done = False

def ensure_db_initialized():
    global _db_init_done
    if _db_init_done:
        return
    with _db_init_lock:
        if _db_init_done:
            return
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(50) NOT NULL,
                    last_name VARCHAR(50) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    address VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    failed_login_attempts INT DEFAULT 0,
                    locked_until DATETIME NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    image VARCHAR(255),
                    category_id INT,
                    stock INT DEFAULT 0,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            # Optional description column, safely added at the end to avoid breaking index-based reads
            try:
                cur.execute("ALTER TABLE products ADD COLUMN description TEXT NULL AFTER stock")
            except Exception:
                pass
            
            # Add OAuth columns to users table for Google login
            try:
                cur.execute("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50) NULL AFTER created_at")
            except Exception:
                pass
            try:
                cur.execute("ALTER TABLE users ADD COLUMN oauth_id VARCHAR(255) NULL AFTER oauth_provider")
            except Exception:
                pass
            # Optional discount column for percentage discounts
            try:
                cur.execute("ALTER TABLE products ADD COLUMN discount DECIMAL(5,2) DEFAULT 0.00 AFTER description")
            except Exception:
                pass
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL,
                    guest_email VARCHAR(120) NULL,
                    full_name VARCHAR(120) NOT NULL,
                    address_line VARCHAR(255) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    delivery_phone VARCHAR(20) NOT NULL,
                    provider VARCHAR(20),
                    momo_number VARCHAR(20),
                    notes VARCHAR(255),
                    latitude DECIMAL(10,7) NULL,
                    longitude DECIMAL(10,7) NULL,
                    total_amount DECIMAL(10,2) NOT NULL,
                    status VARCHAR(30) DEFAULT 'PENDING',
                    momo_transaction_id VARCHAR(36),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    product_id INT,
                    product_name VARCHAR(255) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    quantity INT NOT NULL,
                    subtotal DECIMAL(10,2) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            # Payments table for transaction logging
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NULL,
                    momo_transaction_id VARCHAR(64),
                    amount DECIMAL(10,2) NOT NULL,
                    currency VARCHAR(10) NOT NULL,
                    status VARCHAR(30) NOT NULL,
                    provider VARCHAR(30) NULL,
                    payer_number VARCHAR(32) NULL,
                    raw_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX (order_id),
                    INDEX (momo_transaction_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            # Wishlist table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wishlist (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    product_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_wishlist (user_id, product_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            # Best-effort: add uniqueness and FK constraints (ignore if already exist)
            try:
                cur.execute("ALTER TABLE orders ADD UNIQUE KEY uniq_orders_momo (momo_transaction_id)")
            except Exception as _:
                pass
            # Ensure latitude/longitude columns exist in orders (for map picker)
            try:
                cur.execute("ALTER TABLE orders ADD COLUMN latitude DECIMAL(10,7) NULL AFTER notes")
            except Exception as _:
                pass
            try:
                cur.execute("ALTER TABLE orders ADD COLUMN longitude DECIMAL(10,7) NULL AFTER latitude")
            except Exception as _:
                pass
            try:
                cur.execute("ALTER TABLE payments ADD UNIQUE KEY uniq_payments_momo (momo_transaction_id)")
            except Exception as _:
                pass
            try:
                cur.execute("ALTER TABLE payments ADD CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL")
            except Exception as _:
                pass
            mysql.connection.commit()
            cur.close()
        except Exception as e:
            print(f"DB init error: {e}")
        finally:
            _db_init_done = True

@app.before_request
def initialize_cart():
    ensure_db_initialized()
    _ensure_csrf_token()
    # Note: Cart is stored in Redis when available, otherwise in session
    # Session itself is always Flask's cookie-based session
    if not REDIS_AVAILABLE:
        # Fallback to session-based cart when Redis is not available
        if 'cart' not in session:
            session['cart'] = {}
            session.modified = True

# Provide a safe 'user' object to all templates
@app.context_processor
def inject_user():
    user = None
    try:
        if 'user_id' in session:
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT id, username, email, first_name, last_name, phone, city, address FROM users WHERE id = %s",
                (session['user_id'],)
            )
            row = cur.fetchone()
            cur.close()
            if row:
                user = {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'first_name': row[3],
                    'last_name': row[4],
                    'phone': row[5],
                    'city': row[6],
                    'address': row[7],
                }
    except Exception:
        user = None
    if user is None:
        user = {
            'id': None,
            'username': '',
            'email': '',
            'first_name': '',
            'last_name': '',
            'phone': '',
            'city': '',
            'address': '',
        }
    return {'user': user}

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    categories = []
    cart_items = []
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories_data = cur.fetchall()
    categories = [{'id': cat[0], 'name': cat[1]} for cat in categories_data]
    cart_items = build_cart_items_from_session(cur, session.get('cart', {}))
    cur.close()

    if request.method == 'POST':
        if not validate_csrf():
            flash('Invalid session. Please refresh and try again.', 'error')
            return render_template('login.html', categories=categories, cart_items=cart_items)
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        ip_address = request.remote_addr

        if is_rate_limited(ip_address, login_attempts):
            flash('Too many login attempts. Please try again in 15 minutes.', 'error')
            return render_template('login.html', categories=categories, cart_items=cart_items)

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html', categories=categories, cart_items=cart_items)

        cur = mysql.connection.cursor()
        if '@' in username:
            cur.execute("SELECT id, username, password_hash, is_active, failed_login_attempts, locked_until FROM users WHERE email = %s", (username,))
        else:
            cur.execute("SELECT id, username, password_hash, is_active, failed_login_attempts, locked_until FROM users WHERE username = %s", (username,))
        user = cur.fetchone()

        if user:
            user_id, db_username, password_hash, is_active, failed_attempts, locked_until = user
            if locked_until and datetime.now() < locked_until:
                flash('Account is temporarily locked. Please try again later.', 'error')
                cur.close()
                return render_template('login.html', categories=categories, cart_items=cart_items)
            if not is_active:
                flash('Account is deactivated. Please contact support.', 'error')
                cur.close()
                return render_template('login.html', categories=categories, cart_items=cart_items)

            if verify_password(password, password_hash):
                # Preserve cart before session regeneration
                old_cart = session.get('cart', {})
                
                # Regenerate session to prevent session fixation
                session['user_id'] = user_id
                session['username'] = db_username
                session.permanent = True
                regenerate_session()
                
                # Restore cart after session regeneration
                session['cart'] = old_cart
                session.modified = True
                
                cur.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = %s", (user_id,))
                mysql.connection.commit()
                flash(f'Welcome back, {db_username}!', 'success')
                next_page = request.args.get('next') or request.form.get('next')
                cur.close()
                return redirect(next_page or url_for('home'))
            else:
                record_attempt(ip_address, login_attempts)
                failed_attempts += 1
                if failed_attempts >= 5:
                    lock_time = datetime.now() + timedelta(minutes=30)
                    cur.execute("UPDATE users SET failed_login_attempts = %s, locked_until = %s WHERE id = %s", 
                               (failed_attempts, lock_time, user_id))
                    flash('Account locked due to too many failed attempts. Try again in 30 minutes.', 'error')
                else:
                    cur.execute("UPDATE users SET failed_login_attempts = %s WHERE id = %s", (failed_attempts, user_id))
                    flash(f'Invalid credentials. {5 - failed_attempts} attempts remaining.', 'error')
                mysql.connection.commit()
        else:
            record_attempt(ip_address, login_attempts)
            flash('Invalid username or password.', 'error')
        cur.close()
    return render_template('login.html', categories=categories, cart_items=cart_items)

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Fetch categories and cart items for template rendering
    categories = []
    cart_items = []
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM categories")
        categories_data = cur.fetchall()
        categories = [{'id': cat[0], 'name': cat[1]} for cat in categories_data]
        cart_items = build_cart_items_from_session(cur, session.get('cart', {}))
        cur.close()
    except Exception:
        pass

    if request.method == 'POST':
        if not validate_csrf():
            flash('Invalid session. Please refresh and try again.', 'error')
            return render_template('login.html', categories=categories, cart_items=cart_items)
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        ip_address = request.remote_addr

        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append('Username can only contain letters, numbers, and underscores.')
        if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errors.append('Please enter a valid email address.')
        if not first_name or not last_name:
            errors.append('First name and last name are required.')
        if not phone or not re.match(r'^\+2507[0-9]{8}$|^07[0-9]{8}$', phone):
            errors.append('Please enter a valid Rwandan phone number (+2507XXXXXXXX or 07XXXXXXXX).')
        if not city:
            errors.append('City is required.')
        is_valid, password_msg = validate_password(password)
        if not is_valid:
            errors.append(password_msg)
        if password != confirm_password:
            errors.append('Passwords do not match.')

        if errors:
            record_attempt(ip_address, registration_attempts)
            for error in errors:
                flash(error, 'error')
            return render_template('login.html', categories=categories, cart_items=cart_items)

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        if cur.fetchone():
            record_attempt(ip_address, registration_attempts)
            flash('Username or email already exists.', 'error')
            cur.close()
            return render_template('login.html', categories=categories, cart_items=cart_items)
        password_hash = hash_password(password)
        cur.execute("""
            INSERT INTO users (username, email, password_hash, first_name, last_name, phone, city, address, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (username, email, password_hash, first_name, last_name, phone, city, address, True))
        user_id = cur.lastrowid
        
        # Skip linking guest orders since guest_email column doesn't exist
        linked_orders = 0
        
        mysql.connection.commit()
        cur.close()
        
        # Send welcome email
        send_welcome_email(email, first_name)
        
        # Regenerate session after successful registration
        old_cart = session.get('cart', {})
        session['user_id'] = user_id
        session['username'] = username
        session.permanent = True
        regenerate_session()
        
        # Restore cart after session regeneration
        session['cart'] = old_cart
        session.modified = True
        
        if linked_orders > 0:
            flash(f'Account created successfully! Welcome, {first_name}! We\'ve linked {linked_orders} previous order(s) to your account.', 'success')
        else:
            flash(f'Account created successfully! Welcome, {first_name}!', 'success')
        return redirect(url_for('home'))
    return render_template('login.html', categories=categories, cart_items=cart_items)

@app.route('/logout')
def logout():
    username = session.get('username', 'User')
    cart = session.get('cart', {})  # Preserve cart on logout
    
    session.clear()
    
    # Restore cart for guest shopping
    session['cart'] = cart
    session['csrf_token'] = secrets.token_urlsafe(32)
    session.modified = True
    
    flash(f'Goodbye, {username}! You have been logged out.', 'info')
    return redirect(url_for('home'))

# ============================================
# Forgot Password Routes
# ============================================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset - sends code to email"""
    categories = get_all_categories()
    # Build cart items for template
    cur = mysql.connection.cursor()
    cart_items = build_cart_items_from_session(cur, session.get('cart', {}))
    cur.close()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address', 'error')
            return render_template('forgot_password.html', categories=categories, cart_items=cart_items)
        
        try:
            cur = mysql.connection.cursor()
            
            # Check if user exists
            cur.execute("SELECT id, username, first_name FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            
            if not user:
                # Email not found - show explicit error
                flash('No account found with this email address. Please check and try again.', 'error')
                cur.close()
                return render_template('forgot_password.html', categories=categories, cart_items=cart_items)
            
            user_id, username, first_name = user
            
            # Generate 6-digit code
            reset_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
            
            # Set expiration (15 minutes from now)
            from datetime import datetime, timedelta
            expires_at = datetime.now() + timedelta(minutes=15)
            
            # Delete any existing unused tokens for this user
            cur.execute("DELETE FROM password_resets WHERE user_id = %s AND used = FALSE", (user_id,))
            
            # Insert new reset token
            cur.execute("""
                INSERT INTO password_resets (user_id, email, reset_code, expires_at)
                VALUES (%s, %s, %s, %s)
            """, (user_id, email, reset_code, expires_at))
            mysql.connection.commit()
            cur.close()
            
            # Send email with reset code
            subject = "Password Reset Code - eMarket"
            body_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Inter', Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #2d5016 0%, #1e3a0f 100%); padding: 30px; text-align: center; }}
                    .header h1 {{ color: #fff; margin: 0; font-size: 24px; }}
                    .content {{ padding: 40px 30px; }}
                    .code-box {{ background: #f8f9fa; border: 2px dashed #2d5016; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }}
                    .code {{ font-size: 32px; font-weight: bold; color: #2d5016; letter-spacing: 8px; }}
                    .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                    .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Password Reset Request</h1>
                    </div>
                    <div class="content">
                        <p>Hello <strong>{first_name}</strong>,</p>
                        <p>We received a request to reset your password for your eMarket account (<strong>{username}</strong>).</p>
                        <p>Use the following code to reset your password:</p>
                        <div class="code-box">
                            <div class="code">{reset_code}</div>
                        </div>
                        <div class="warning">
                            <strong>This code expires in 15 minutes</strong><br>
                            If you didn't request this, you can safely ignore this email.
                        </div>
                        <p>For security reasons, never share this code with anyone.</p>
                    </div>
                    <div class="footer">
                        <p>eMarket - Your Trusted Online Shopping Platform</p>
                        <p>This is an automated email. Please do not reply.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            email_sent = send_email(email, subject, body_html)
            
            if email_sent:
                flash('A reset code has been sent to your email. Please check your inbox.', 'success')
                return redirect(url_for('reset_password'))
            else:
                flash('Failed to send reset email. Please try again later.', 'error')
                
        except Exception as e:
            print(f"Forgot password error: {e}")
            flash('An error occurred. Please try again.', 'error')
            
    return render_template('forgot_password.html', categories=categories, cart_items=cart_items)

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password using code from email"""
    categories = get_all_categories()
    # Build cart items for template
    cur = mysql.connection.cursor()
    cart_items = build_cart_items_from_session(cur, session.get('cart', {}))
    cur.close()
    
    if request.method == 'POST':
        reset_code = request.form.get('reset_code', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation
        if not reset_code or not new_password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('reset_password.html', categories=categories, cart_items=cart_items)
        
        if new_password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', categories=categories, cart_items=cart_items)
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('reset_password.html', categories=categories, cart_items=cart_items)
        
        try:
            cur = mysql.connection.cursor()
            
            # Find valid reset token
            from datetime import datetime
            cur.execute("""
                SELECT user_id, email FROM password_resets 
                WHERE reset_code = %s AND used = FALSE AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
            """, (reset_code,))
            
            token = cur.fetchone()
            
            if not token:
                flash('Invalid or expired reset code. Please request a new one.', 'error')
                cur.close()
                return render_template('reset_password.html', categories=categories, cart_items=cart_items)
            
            user_id, email = token
            
            # Hash new password
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update user password
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
            
            # Mark token as used
            cur.execute("UPDATE password_resets SET used = TRUE WHERE reset_code = %s", (reset_code,))
            
            mysql.connection.commit()
            cur.close()
            
            flash('Password reset successful! You can now login with your new password.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Reset password error: {e}")
            flash('An error occurred. Please try again.', 'error')
            
    return render_template('reset_password.html', categories=categories, cart_items=cart_items)

# ============================================
# Google OAuth Routes
# ============================================
@app.route('/google/login')
def google_login():
    """Initiate Google OAuth flow"""
    if not GOOGLE_AUTH_ENABLED:
        flash('Google login is not configured', 'error')
        return redirect(url_for('login'))
    
    try:
        authorization_url, state = flow.authorization_url()
        session["oauth_state"] = state
        session.modified = True
        return redirect(authorization_url)
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash('Error connecting to Google. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    if not GOOGLE_AUTH_ENABLED:
        flash('Google login is not configured', 'error')
        return redirect(url_for('login'))
    
    try:
        # Fetch the OAuth2 token
        flow.fetch_token(authorization_response=request.url)
        
        # Verify state to prevent CSRF
        if not session.get("oauth_state") == request.args.get("state"):
            flash('Invalid state parameter', 'error')
            return redirect(url_for('login'))
        
        # Get user credentials and info
        credentials = flow.credentials
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)
        
        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID
        )
        
        # Extract user info from Google
        google_id = id_info.get("sub")
        email = id_info.get("email")
        name = id_info.get("name", "")
        picture = id_info.get("picture", "")
        
        # Split name into first and last
        name_parts = name.split(' ', 1)
        first_name = name_parts[0] if name_parts else "User"
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Preserve cart before processing
        old_cart = session.get('cart', {})
        
        # Check if user exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, first_name, last_name FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if user:
            # Existing user - log them in
            user_id, username, db_first_name, db_last_name = user
            
            # Update OAuth info if not set
            cur.execute("""
                UPDATE users 
                SET oauth_provider = 'google', oauth_id = %s 
                WHERE id = %s AND oauth_provider IS NULL
            """, (google_id, user_id))
            mysql.connection.commit()
            
            # Set session
            session['user_id'] = user_id
            session['username'] = username
            session.permanent = True
            regenerate_session()
            
            # Restore cart
            session['cart'] = old_cart
            session.modified = True
            
            flash(f'Welcome back, {db_first_name}!', 'success')
            cur.close()
            return redirect(url_for('home'))
        else:
            # New user - create account
            username = email.split('@')[0]  # Use email prefix as username
            
            # Ensure username is unique
            base_username = username
            counter = 1
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            while cur.fetchone():
                username = f"{base_username}{counter}"
                counter += 1
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            
            # Generate random password (user won't need it since they use OAuth)
            random_password = secrets.token_urlsafe(32)
            password_hash = bcrypt.hashpw(random_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Insert new user
            cur.execute("""
                INSERT INTO users (username, email, password_hash, first_name, last_name, 
                                 phone, city, address, oauth_provider, oauth_id, is_active)
                VALUES (%s, %s, %s, %s, %s, '', '', '', 'google', %s, 1)
            """, (username, email, password_hash, first_name, last_name, google_id))
            mysql.connection.commit()
            
            user_id = cur.lastrowid
            
            # Send welcome email for new Google OAuth user
            send_welcome_email(email, first_name)
            
            # Set session
            session['user_id'] = user_id
            session['username'] = username
            session.permanent = True
            regenerate_session()
            
            # Restore cart
            session['cart'] = old_cart
            session.modified = True
            
            flash(f'Welcome to CiTiPlug, {first_name}! Your account has been created.', 'success')
            cur.close()
            return redirect(url_for('home'))
            
    except Exception as e:
        print(f"Google OAuth callback error: {e}")
        flash('Error during Google sign-in. Please try again.', 'error')
        return redirect(url_for('login'))

# Guest registration route removed - using existing login/register page instead

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories_data = cur.fetchall()
    categories = [{'id': cat[0], 'name': cat[1]} for cat in categories_data]
    cur.execute("SELECT id, username, email, password_hash, first_name, last_name, phone, city, address, is_active FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        flash('User not found.', 'error')
        return redirect(url_for('home'))
    # Build user object defensively in case some columns are missing in schema
    user = {
        'id': row[0] if len(row) > 0 else user_id,
        'username': row[1] if len(row) > 1 else '',
        'email': row[2] if len(row) > 2 else '',
        'password_hash': row[3] if len(row) > 3 else '',
        'first_name': row[4] if len(row) > 4 else '',
        'last_name': row[5] if len(row) > 5 else '',
        'phone': row[6] if len(row) > 6 else '',
        'city': row[7] if len(row) > 7 else '',
        'address': row[8] if len(row) > 8 else '',
        'is_active': row[9] if len(row) > 9 else 1
    }
    cart_items = []
    for product_id, item in session.get('cart', {}).items():
        # product_id in session is stored as string; cast to int for DB lookup
        pid = None
        try:
            pid = int(product_id)
        except Exception:
            pid = product_id
        cur.execute("SELECT * FROM products WHERE id = %s", (pid,))
        product_data = cur.fetchone()
        if product_data:
            product = {
                'id': product_data[0],
                'name': product_data[1],
                'price': float(product_data[2]),
                'image': product_data[3],
                'category_id': product_data[4],
                'stock': product_data[5] if len(product_data) > 5 else 999
            }
            item['quantity'] = min(item['quantity'], product['stock'])
            if item['quantity'] > 0:
                cart_items.append({
                    'id': product_id,
                    'name': item['name'],
                    'price': item['price'],
                    'image': product['image'],
                    'quantity': item['quantity'],
                    'stock': product['stock'],
                    'variations': item.get('variations', ''),  # Include variations
                    'is_new': False
                })
    
    # Fetch wishlist items (resilient)
    wishlist_items = []
    try:
        cur.execute("""
            SELECT p.* FROM products p
            INNER JOIN wishlist w ON p.id = w.product_id
            WHERE w.user_id = %s
            ORDER BY w.added_at DESC
        """, (user_id,))
        wishlist_data = cur.fetchall()
        for product_data in wishlist_data:
            product = get_product_with_discount(product_data)
            if product:
                wishlist_items.append(product)
    except Exception as _e:
        # If wishlist table/columns are missing or any error occurs, fail soft
        wishlist_items = []

    # Fetch this user's orders with items (resilient)
    user_orders = []
    try:
        cur.execute(
            """
            SELECT id, total_amount, status, provider, momo_number, created_at, payment_status, momo_transaction_id, address_line, city, delivered
            FROM orders
            WHERE user_id = %s
            ORDER BY id DESC, created_at DESC
            """,
            (user_id,)
        )
        order_rows = cur.fetchall()
        for o in order_rows:
            order = {
                'id': o[0],
                'total_amount': float(o[1]) if o[1] is not None else 0.0,
                'status': o[2],
                'provider': o[3],
                'momo_number': o[4],
                'created_at': o[5],
                'payment_status': o[6],
                'momo_transaction_id': o[7],
                'address_line': o[8] if len(o) > 8 else '',
                'city': o[9] if len(o) > 9 else '',
                'delivered': (o[10] if len(o) > 10 else None) or '',
                'items': []
            }
            try:
                cur2 = mysql.connection.cursor()
                cur2.execute(
                    """
                    SELECT oi.product_id, oi.product_name, oi.price, oi.quantity, oi.subtotal, p.image, oi.VARIATIONS
                    FROM order_items oi
                    LEFT JOIN products p ON p.id = oi.product_id
                    WHERE oi.order_id = %s
                    ORDER BY oi.id ASC
                    """,
                    (order['id'],)
                )
                for it in cur2.fetchall():
                    order['items'].append({
                        'product_id': it[0],
                        'name': it[1],
                        'price': float(it[2]) if it[2] is not None else 0.0,
                        'quantity': int(it[3]) if it[3] is not None else 0,
                        'subtotal': float(it[4]) if it[4] is not None else 0.0,
                        'image': resolve_image_url(it[5]) if len(it) > 5 else None,
                        'variations': it[6] if len(it) > 6 else ''
                    })
                cur2.close()
            except Exception:
                pass
            user_orders.append(order)
    except Exception:
        user_orders = []
    
    if request.method == 'POST':
        if not validate_csrf():
            flash('Invalid session. Please refresh and try again.', 'error')
            return render_template('profile.html', user=user, categories=categories, cart_items=cart_items, wishlist_items=wishlist_items, user_orders=user_orders)
        form_type = request.form.get('form_type')
        if form_type == 'info':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            city = request.form.get('city', '').strip()
            address = request.form.get('address', '').strip()
            errors = []
            if not username or len(username) < 3 or not re.match(r'^[a-zA-Z0-9_]+$', username):
                errors.append('Username must be at least 3 chars and contain only letters, numbers, and underscores.')
            if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                errors.append('Please enter a valid email address.')
            if not first_name or not last_name:
                errors.append('First name and last name are required.')
            if not phone or not re.match(r'^\+2507[0-9]{8}$|^07[0-9]{8}$', phone):
                errors.append('Please enter a valid Rwandan phone number (+2507XXXXXXXX or 07XXXXXXXX).')
            if not city:
                errors.append('City is required.')
            cur.execute("SELECT id FROM users WHERE (username = %s OR email = %s) AND id <> %s", (username, email, user_id))
            if cur.fetchone():
                errors.append('Username or email already in use by another account.')
            if errors:
                for err in errors:
                    flash(err, 'error')
                user.update({'username': username, 'email': email, 'first_name': first_name, 'last_name': last_name,
                                'phone': phone, 'city': city, 'address': address})
                return render_template('profile.html', user=user, categories=categories, cart_items=cart_items, wishlist_items=wishlist_items, user_orders=user_orders)
            cur.execute("""
                UPDATE users SET username=%s, email=%s, first_name=%s, last_name=%s, phone=%s, city=%s, address=%s
                WHERE id=%s
            """, (username, email, first_name, last_name, phone, city, address, user_id))
            mysql.connection.commit()
            session['username'] = username
            flash('Profile updated successfully.', 'success')
            cur.execute("SELECT id, username, email, password_hash, first_name, last_name, phone, city, address, is_active FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            user.update({'username': row[1], 'email': row[2], 'first_name': row[4], 'last_name': row[5], 'phone': row[6], 'city': row[7], 'address': row[8]})
            return render_template('profile.html', user=user, categories=categories, cart_items=cart_items, wishlist_items=wishlist_items, user_orders=user_orders)
        elif form_type == 'password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            if not verify_password(current_password, user['password_hash']):
                flash('Current password is incorrect.', 'error')
                return render_template('profile.html', user=user, categories=categories, cart_items=cart_items, wishlist_items=wishlist_items, user_orders=user_orders)
            ok, msg = validate_password(new_password)
            if not ok:
                flash(msg, 'error')
                return render_template('profile.html', user=user, categories=categories, cart_items=cart_items, wishlist_items=wishlist_items, user_orders=user_orders)
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return render_template('profile.html', user=user, categories=categories, cart_items=cart_items, wishlist_items=wishlist_items, user_orders=user_orders)
            new_hash = hash_password(new_password)
            cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user_id))
            mysql.connection.commit()
            flash('Password updated successfully.', 'success')
            return render_template('profile.html', user=user, categories=categories, cart_items=cart_items, wishlist_items=wishlist_items, user_orders=user_orders)
    cur.close()
    return render_template('profile.html', user=user, categories=categories, cart_items=cart_items, wishlist_items=wishlist_items, user_orders=user_orders)


@app.post('/orders/cancel/<int:order_id>')
@login_required
def cancel_order(order_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id, status, delivered FROM orders WHERE id=%s", (order_id,))
        row = cur.fetchone()
        if not row:
            flash('Order not found.', 'error')
            return redirect(url_for('profile') + '#orders')
        owner_id, status, delivered = row[0], (row[1] or ''), (row[2] or '')
        if owner_id != session.get('user_id'):
            flash('Not authorized for this order.', 'error')
            return redirect(url_for('profile') + '#orders')
        if str(status).lower() == 'cancelled' or str(delivered).lower() in ('yes', 'true', '1'):
            flash('Order cannot be cancelled.', 'info')
            return redirect(url_for('profile') + '#orders')
        if not validate_csrf():
            flash('Invalid session. Please refresh and try again.', 'error')
            return redirect(url_for('profile') + '#orders')
        
        # Fetch order items to restore stock
        cur.execute("""
            SELECT product_id, quantity, VARIATIONS 
            FROM order_items 
            WHERE order_id = %s
        """, (order_id,))
        order_items = cur.fetchall()
        
        # Restore stock for each item using smart hierarchy
        for item in order_items:
            product_id = item[0]
            quantity = int(item[1]) if item[1] else 0
            variations = item[2] if len(item) > 2 and item[2] else ''
            
            if quantity > 0:
                stock_level = restore_stock_smartly(cur, product_id, quantity, variations)
                print(f"ORDER CANCEL: Stock restored to {stock_level} level for product_id={product_id}, qty={quantity}")
        
        # Update order status, payment status, and delivered to cancelled
        cur.execute("""
            UPDATE orders 
            SET status = 'cancelled', payment_status = 'cancelled', delivered = 'false' 
            WHERE id = %s
        """, (order_id,))
        
        mysql.connection.commit()
        cur.close()
        flash('Order cancelled and stock restored.', 'success')
    except Exception as e:
        print(f"Cancel order error: {e}")
        flash('Failed to cancel order.', 'error')
    return redirect(url_for('profile') + '#orders')

@app.get('/api/debug/products')
def debug_products():
    """Debug endpoint to check if products exist"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM products")
        count = cur.fetchone()[0]
        
        cur.execute("SELECT id, name FROM products LIMIT 5")
        products = cur.fetchall()
        
        cur.close()
        return jsonify({
            'total_products': count,
            'products': products
        })
    except Exception as e:
        print(f"Error in /api/debug/products: {e}")
        return jsonify(error='server_error'), 500

@app.get('/api/product/<int:product_id>')
def api_product(product_id):
    try:
        cur = mysql.connection.cursor()
        # Try to fetch description if the column exists
        try:
            cur.execute(
                """
                SELECT id, name, price, image, category_id, stock, description
                FROM products WHERE id = %s
                """,
                (product_id,)
            )
            row = cur.fetchone()
            if row:
                data = {
                    'id': row[0], 'name': row[1], 'price': float(row[2]) if row[2] is not None else 0.0,
                    'image': resolve_image_url(row[3]), 'category_id': row[4], 'stock': row[5] if len(row) > 5 and row[5] is not None else 0,
                    'description': row[6] if len(row) > 6 else ''
                }
                cur.close()
                return jsonify(data)
        except Exception:
            # Fallback when description column doesn't exist
            cur.execute("SELECT id, name, price, image, category_id, stock FROM products WHERE id = %s", (product_id,))
            row = cur.fetchone()
            if row:
                data = {
                    'id': row[0], 'name': row[1], 'price': float(row[2]) if row[2] is not None else 0.0,
                    'image': resolve_image_url(row[3]), 'category_id': row[4], 'stock': row[5] if len(row) > 5 and row[5] is not None else 0,
                    'description': ''
                }
                cur.close()
                return jsonify(data)
        cur.close()
        return jsonify(error='not_found'), 404
    except Exception as e:
        print(f"/api/product error: {e}")
        return jsonify(error='server_error'), 500

@app.route('/')
def home():
    try:
        cur = get_db_cursor()
        if not cur:
            return "Database connection failed. Please check if MySQL is running and accessible.", 500
        # Get all categories for sidebar
        cur.execute("SELECT * FROM categories")
        categories_data = cur.fetchall()
        categories = [{'id': cat[0], 'name': cat[1]} for cat in categories_data]
        
        # Get curated product sections
        products_sections = {}
        
        # 1. Top Selling - 8 products (prioritize rated products, then show any products)
        cur.execute("""
            SELECT * FROM products 
            WHERE stock > 0
            ORDER BY COALESCE(rate, 0) DESC, id DESC
            LIMIT 8
        """)
        top_selling_data = cur.fetchall()
        top_selling = []
        for prod in top_selling_data:
            product_with_discount = get_product_with_discount(prod)
            if product_with_discount:
                top_selling.append(product_with_discount)
        
        # Always show Top Selling section, even if no rated products
        if top_selling:
            products_sections['top_selling'] = {
                'name': 'Top Selling',
                'products': top_selling,
                'order': 1
            }
        
        # 2. New Arrivals - 8 newest products
        cur.execute("""
            SELECT * FROM products 
            WHERE stock > 0
            ORDER BY id DESC
            LIMIT 8
        """)
        new_arrivals_data = cur.fetchall()
        new_arrivals = []
        for prod in new_arrivals_data:
            product_with_discount = get_product_with_discount(prod)
            if product_with_discount:
                new_arrivals.append(product_with_discount)
        if new_arrivals:
            products_sections['new_arrivals'] = {
                'name': 'New Arrivals',
                'products': new_arrivals,
                'order': 2
            }
        
        # 3. On Sale - 8 products with highest discount
        cur.execute("""
            SELECT * FROM products 
            WHERE discount > 0
            ORDER BY discount DESC
            LIMIT 8
        """)
        on_sale_data = cur.fetchall()
        on_sale = []
        for prod in on_sale_data:
            product_with_discount = get_product_with_discount(prod)
            if product_with_discount:
                on_sale.append(product_with_discount)
        if on_sale:
            products_sections['on_sale'] = {
                'name': 'On Sale',
                'products': on_sale,
                'order': 3
            }
        
        # 4. Explore More - 12 random products from different categories
        random_products = []
        try:
            # Get 12 random products, prioritizing diversity across categories
            cur.execute("""
                SELECT p.*, 
                       @cat_rank := IF(@current_cat = p.category_id, @cat_rank + 1, 1) AS cat_rank,
                       @current_cat := p.category_id
                FROM products p
                CROSS JOIN (SELECT @cat_rank := 0, @current_cat := NULL) vars
                ORDER BY RAND()
            """)
            seen_categories = set()
            for row in cur.fetchall():
                if len(random_products) >= 12:
                    break
                cat_id = row[4]  # category_id is at index 4
                # Prefer products from categories we haven't seen yet
                if cat_id not in seen_categories or len(random_products) < 12:
                    prod_obj = get_product_with_discount(row)
                    if prod_obj:
                        random_products.append(prod_obj)
                        seen_categories.add(cat_id)
        except Exception:
            random_products = []
        
        if random_products:
            products_sections['explore_more'] = {
                'name': 'Explore More',
                'products': random_products,
                'order': 99
            }
        
        # Get cart items using standardized function
        cart_items = build_cart_items_from_session(cur, session.get('cart', {}))
        # Build a safe 'user' object for the template to avoid UndefinedError
        user = None
        try:
            if 'user_id' in session:
                cur.execute(
                    "SELECT id, username, email, first_name, last_name, phone, city, address FROM users WHERE id = %s",
                    (session['user_id'],)
                )
                row = cur.fetchone()
                if row:
                    user = {
                        'id': row[0],
                        'username': row[1],
                        'email': row[2],
                        'first_name': row[3],
                        'last_name': row[4],
                        'phone': row[5],
                        'city': row[6],
                        'address': row[7],
                    }
        except Exception:
            # Non-fatal: if user lookup fails, fall back to empty defaults
            user = None
        if user is None:
            user = {
                'id': None,
                'username': '',
                'email': '',
                'first_name': '',
                'last_name': '',
                'phone': '',
                'city': '',
                'address': '',
            }
        
        # Sort sections by order field
        products_sections = dict(sorted(products_sections.items(), key=lambda x: x[1].get('order', 999)))
        
        cur.close()
        return render_template("home.html", categories=categories, products_sections=products_sections, cart_items=cart_items, user=user)
    except Exception as e:
        print(f"Error in /home: {e}")
        flash(f"Error loading homepage: {e}", 'error')
        # Avoid redirect loop by rendering a minimal safe page
        safe_user = {
            'id': None,
            'username': '',
            'email': '',
            'first_name': '',
            'last_name': '',
            'phone': '',
            'city': '',
            'address': '',
        }
        return render_template("home.html", categories=[], products_by_cat={}, products_sections={}, cart_items=[], user=safe_user), 500

@app.route('/viewall')
def viewall():
    category_id = request.args.get('category')
    page = request.args.get('page', 1, type=int)
    per_page = 30  # 30 products per page
    sort_by = request.args.get('sort_by', 'newest')  # newest, oldest, price_low, price_high, rating
    show_out_of_stock = request.args.get('show_oos', '0')  # Hide out-of-stock by default for better UX
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    selected_sizes = request.args.getlist('size')  # Multiple sizes
    
    if not category_id:
        flash('Category not specified', 'error')
        return redirect(url_for('home'))
    try:
        cur = mysql.connection.cursor()
        if not cur:
            flash("Database connection failed. Please try again.", 'error')
            return redirect(url_for('home'))
        
        # Handle "uncategorized" special case
        if category_id == 'uncategorized':
            category = {'id': 'uncategorized', 'name': 'Uncategorized'}
            # Build WHERE clause for uncategorized products (category_id IS NULL or category_id = 0 or not in categories)
            where_clause = "(category_id IS NULL OR category_id = 0 OR category_id NOT IN (SELECT id FROM categories))"
            where_params = []
        else:
            cur.execute("SELECT * FROM categories WHERE id = %s", (category_id,))
            category_data = cur.fetchone()
            if not category_data:
                flash('Category not found', 'error')
                return redirect(url_for('home'))
            category = {'id': category_data[0], 'name': category_data[1]}
            
            # Build WHERE clause for filters
            where_clause = "category_id = %s"
            where_params = [category_id]
        
        # Hide out of stock by default
        if show_out_of_stock == '0':
            where_clause += " AND stock > 0"
        
        # Price range filter
        if min_price is not None:
            where_clause += " AND price >= %s"
            where_params.append(min_price)
        if max_price is not None:
            where_clause += " AND price <= %s"
            where_params.append(max_price)
        
        # Get total count for pagination
        cur.execute(f"SELECT COUNT(*) FROM products WHERE {where_clause}", where_params)
        total_products = cur.fetchone()[0]
        
        # Calculate pagination
        total_pages = (total_products + per_page - 1) // per_page  # Ceiling division
        offset = (page - 1) * per_page
        
        # Build ORDER BY clause
        order_by = "id DESC"  # default: newest
        if sort_by == 'oldest':
            order_by = "id ASC"
        elif sort_by == 'price_low':
            order_by = "price ASC"
        elif sort_by == 'price_high':
            order_by = "price DESC"
        elif sort_by == 'rating':
            order_by = "rate DESC"
        
        # Get base products
        cur.execute(f"SELECT * FROM products WHERE {where_clause} ORDER BY {order_by} LIMIT %s OFFSET %s", 
                   where_params + [per_page, offset])
        products_data_raw = cur.fetchall()
        
        # Filter by size if specified (via variations)
        products_data = []
        for prod in products_data_raw:
            prod_id = prod[0]
            
            # Check size filter
            if selected_sizes:
                cur.execute(
                    "SELECT COUNT(*) FROM dropdown_variation WHERE prod_id = %s AND LOWER(attr_name) = 'size' AND LOWER(attr_value) IN (" + ",".join(['%s'] * len(selected_sizes)) + ")",
                    [prod_id] + [s.lower() for s in selected_sizes]
                )
                if cur.fetchone()[0] == 0:
                    continue
            
            products_data.append(prod)
        products = []
        for prod in products_data:
            original_price = float(prod[2]) if prod[2] is not None else 0.0
            discount = float(prod[7] if len(prod) > 7 and prod[7] is not None else 0)
            discounted_price = calculate_discounted_price(original_price, discount)
            
            products.append({
                'id': prod[0],
                'name': prod[1],
                'price': discounted_price,
                'original_price': original_price,
                'image': resolve_image_url(prod[3]),
                'category_id': prod[4],
                'stock': prod[5] if len(prod) > 5 else 0,
                'description': prod[6] if len(prod) > 6 else '',
                'discount': discount,
                'rate': float(prod[8]) if len(prod) > 8 and prod[8] is not None else 0.0
            })
        cur.execute("SELECT * FROM categories")
        categories_data = cur.fetchall()
        categories = [{'id': cat[0], 'name': cat[1]} for cat in categories_data]
        
        # Get cart items using standardized function
        cart_items = build_cart_items_from_session(cur, session.get('cart', {}))
        
        # Get available sizes for this category
        if category_id == 'uncategorized':
            cur.execute("""
                SELECT DISTINCT LOWER(dv.attr_value) 
                FROM dropdown_variation dv
                JOIN products p ON dv.prod_id = p.id
                WHERE (p.category_id IS NULL OR p.category_id = 0 OR p.category_id NOT IN (SELECT id FROM categories))
                AND LOWER(dv.attr_name) = 'size'
                ORDER BY LOWER(dv.attr_value)
            """)
        else:
            cur.execute("""
                SELECT DISTINCT LOWER(dv.attr_value) 
                FROM dropdown_variation dv
                JOIN products p ON dv.prod_id = p.id
                WHERE p.category_id = %s AND LOWER(dv.attr_name) = 'size'
                ORDER BY LOWER(dv.attr_value)
            """, (category_id,))
        available_sizes = [row[0] for row in cur.fetchall()]
        
        cur.close()
        return render_template('viewall_fixed.html', 
                              category=category, 
                              products=products, 
                              categories=categories, 
                              cart_items=cart_items,
                              current_page=page,
                              total_pages=total_pages,
                              total_products=total_products,
                              sort_by=sort_by,
                              show_out_of_stock=show_out_of_stock,
                              min_price=min_price,
                              max_price=max_price,
                              available_sizes=available_sizes,
                              selected_sizes=selected_sizes)
    except Exception as e:
        import traceback
        print(f"Error in /viewall: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        flash("Error loading category. Please try again.", 'error')
        return redirect(url_for('home'))

@app.route('/add-to-cart', methods=['GET'])
def add_to_cart():
    """Simple, reliable add-to-cart functionality using Flask sessions"""
    try:
        # Get parameters
        product_id = request.args.get('product_id')
        img_var_id = request.args.get('img_var_id', '')
        dropdown_var_id = request.args.get('dropdown_var_id', '')
        variation_image = request.args.get('variation_image', '')
        is_buy_now = request.args.get('buy_now') == '1'
        requested_quantity = int(request.args.get('quantity', '1'))
        
        # Debug logging
        print(f"ADD-TO-CART: product_id={product_id}, img_var_id={img_var_id}, variation_image={variation_image}")
        
        if not product_id:
            flash('Product ID not specified', 'error')
            return redirect(url_for('home'))
        
        # Initialize session cart
        if 'cart' not in session:
            session['cart'] = {}
        
        # Get product info
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product_data = cur.fetchone()
        
        if not product_data:
            flash('Product not found', 'error')
            cur.close()
            return redirect(url_for('home'))
        
        product = get_product_with_discount(product_data)
        
        # Build cart key and get stock
        cart_key = product_id
        actual_stock = product['stock']
        variation_display = ""
        
        # Handle variations
        variation_parts = []
        if img_var_id:
            cart_key += f"_img{img_var_id}"
            cur.execute("SELECT stock, name, type FROM image_variations WHERE id = %s", (img_var_id,))
            img_var = cur.fetchone()
            if img_var:
                actual_stock = img_var[0]
                # Store variation in parseable format: "color:Brown"
                img_type = (img_var[2] or 'color').lower()  # type field (e.g., "color", "style")
                img_name = img_var[1] or ''  # name field (e.g., "Brown")
                variation_parts.append(f"{img_type}:{img_name}")
        
        if dropdown_var_id:
            cart_key += f"_drop{dropdown_var_id}"
            cur.execute("SELECT stock, attr_name, attr_value FROM dropdown_variation WHERE id = %s", (dropdown_var_id,))
            drop_var = cur.fetchone()
            if drop_var:
                actual_stock = drop_var[0]
                # Store variation in parseable format: "size:41"
                attr_name = (drop_var[1] or 'size').lower()  # attr_name field (e.g., "size")
                attr_value = drop_var[2] or ''  # attr_value field (e.g., "41")
                variation_parts.append(f"{attr_name}:{attr_value}")
        
        # Join all variations with comma and space
        variation_display = ", ".join(variation_parts)
        
        # Check stock
        if actual_stock <= 0:
            flash('Out of stock', 'error')
            cur.close()
            return redirect(request.referrer or url_for('home'))
        
        # Add to cart with stock validation
        if cart_key in session['cart']:
            current_qty = session['cart'][cart_key]['quantity']
            new_total_qty = current_qty + requested_quantity
            
            if new_total_qty <= actual_stock:
                session['cart'][cart_key]['quantity'] = new_total_qty
                # Show stock warning if getting close to limit
                remaining = actual_stock - new_total_qty
                if remaining <= 0:
                    flash(f'Added to cart. No more {product["name"]} available in stock!', 'warning')
                elif remaining <= 2:
                    flash(f'Added to cart. Only {remaining} left in stock!', 'warning')
                else:
                    flash(f'Added {requested_quantity} to cart', 'success')
            else:
                # Can't add full requested quantity, add what we can
                max_can_add = actual_stock - current_qty
                if max_can_add > 0:
                    session['cart'][cart_key]['quantity'] = actual_stock
                    flash(f'Only {max_can_add} more available in stock. Added {max_can_add} to cart.', 'warning')
                else:
                    flash(f'Cannot add more - only {actual_stock} available in stock', 'error')
                    cur.close()
                    return redirect(request.referrer or url_for('home'))
        else:
            # Validate requested quantity doesn't exceed stock
            final_quantity = min(requested_quantity, actual_stock)
            
            session['cart'][cart_key] = {
                'product_id': product_id,
                'name': product['name'],
                'price': product['price'],
                'quantity': final_quantity,
                'variations': variation_display,
                'img_var_id': img_var_id,
                'dropdown_var_id': dropdown_var_id
            }
            
            # Debug logging
            print(f"STORED IN CART: cart_key={cart_key}, variations={variation_display}, img_var_id={img_var_id}")
            
            # Show appropriate message
            if final_quantity < requested_quantity:
                flash(f'Only {final_quantity} available in stock. Added {final_quantity} to cart.', 'warning')
            elif final_quantity > 1:
                flash(f'Added {final_quantity} items to cart', 'success')
            else:
                flash('Product added to cart', 'success')
        
        session.modified = True
        cur.close()
        
        # Success message already shown above based on quantity
        
        # Handle buy now - redirect to checkout
        if is_buy_now:
            print(f"Buy Now detected - redirecting to checkout for product {product_id}")
            return redirect(url_for('checkout'))
        
        # Handle AJAX requests
        if request.args.get('ajax') == '1':
            cart_count = sum(item['quantity'] for item in session['cart'].values())
            return jsonify(success=True, cart_count=cart_count, message='Product added to cart')
        
        # Regular redirect
        redirect_url = request.args.get('redirect')
        if redirect_url:
            return redirect(redirect_url)
        
        return redirect(url_for('addtocart', product_id=product_id))
        
    except Exception as e:
        print(f"Add to cart error: {e}")
        flash('Error adding to cart', 'error')
        return redirect(url_for('home'))

@app.route('/addtocart')
def addtocart():
    """Cart page using Flask sessions"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM categories")
        categories_data = cur.fetchall()
        categories = [{'id': cat[0], 'name': cat[1]} for cat in categories_data]
        
        # Get cart from session using standardized function
        current_cart = session.get('cart', {})
        cart_items = build_cart_items_from_session(cur, current_cart)
        
        # Calculate total
        total = 0
        newly_added_product_id = request.args.get('product_id')
        for item in cart_items:
            item['is_new'] = str(item['product_id']) == newly_added_product_id
            total += item['price'] * item['quantity']
        
        cur.close()
        return render_template('addtocart.html', cart_items=cart_items, categories=categories, total=total)
    except Exception as e:
        print(f"Error in /addtocart: {e}")
        flash(f"Error loading cart: {e}", 'error')
        return redirect(url_for('home'))

@app.route('/api/cart')
def get_cart():
    """Simple cart API using Flask sessions - fetch variation images from database"""
    try:
        # Get cart from session
        cart_data = session.get('cart', {})
        cart_items = []
        cur = mysql.connection.cursor()
        
        for cart_key, item in cart_data.items():
            # Extract product ID from cart key
            product_id = item.get('product_id', cart_key.split('_')[0])
            img_var_id = item.get('img_var_id', '')
            
            # Format variations
            variations = item.get('variations', '')
            if variations:
                variations = fmtvars(variations)
            
            # Fetch image from database based on variation
            image_url = ''
            if img_var_id and str(img_var_id).strip():
                try:
                    # Fetch variation image from database
                    cur.execute("SELECT img_url FROM image_variations WHERE id = %s", (img_var_id,))
                    result = cur.fetchone()
                    if result and result[0]:
                        image_url = resolve_image_url(result[0])
                except Exception as e:
                    print(f"Error fetching variation image: {e}")
            
            # Fallback to product image if no variation image
            if not image_url:
                try:
                    cur.execute("SELECT image FROM products WHERE id = %s", (product_id,))
                    result = cur.fetchone()
                    if result and result[0]:
                        image_url = resolve_image_url(result[0])
                except Exception as e:
                    print(f"Error fetching product image: {e}")
            
            print(f"Cart item {cart_key}: img_var_id={img_var_id}, image_url={image_url}")
            
            cart_items.append({
                'id': cart_key,
                'product_id': product_id,
                'name': item.get('name', ''),
                'price': item.get('price', 0),
                'image': image_url,
                'quantity': item.get('quantity', 1),
                'variations': variations
            })
        
        cur.close()
        return jsonify({'items': cart_items})
    except Exception as e:
        print(f"Cart API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'items': []})

@app.route('/cart-info')
def cart_info():
    try:
        product_id = request.args.get('product_id')
        dropdown_var_id = request.args.get('dropdown_var_id', '')
        
        if not product_id:
            return jsonify({'error': 'Product ID required'}), 400
        
        cur = mysql.connection.cursor()
        
        # Check if product has variations
        cur.execute("SELECT COUNT(*) FROM image_variations WHERE prod_id = %s", (product_id,))
        has_image_vars = cur.fetchone()[0] > 0
        
        cur.execute("SELECT COUNT(*) FROM dropdown_variation WHERE prod_id = %s", (product_id,))
        has_dropdown_vars = cur.fetchone()[0] > 0
        
        stock = 0
        needs_image_selection = False
        needs_dropdown_selection = False
        
        # Determine stock based on variation hierarchy
        if not has_image_vars and not has_dropdown_vars:
            # No variations - use product stock
            cur.execute("SELECT stock FROM products WHERE id = %s", (product_id,))
            result = cur.fetchone()
            stock = result[0] if result else 0
            
        elif has_image_vars and not has_dropdown_vars:
            # Only image variations
            if img_var_id:
                cur.execute("SELECT stock FROM image_variations WHERE id = %s AND prod_id = %s", (img_var_id, product_id))
                result = cur.fetchone()
                stock = result[0] if result else 0
            else:
                needs_image_selection = True
                
        elif has_image_vars and has_dropdown_vars:
            # Both variations
            if img_var_id and dropdown_var_id:
                cur.execute("""
                    SELECT stock FROM dropdown_variation 
                    WHERE id = %s AND prod_id = %s AND img_var_id = %s
                """, (dropdown_var_id, product_id, img_var_id))
                result = cur.fetchone()
                stock = result[0] if result else 0
            elif img_var_id and not dropdown_var_id:
                needs_dropdown_selection = True
            else:
                needs_image_selection = True
                
        elif not has_image_vars and has_dropdown_vars:
            # Only dropdown variations
            if dropdown_var_id:
                cur.execute("SELECT stock FROM dropdown_variation WHERE id = %s AND prod_id = %s", (dropdown_var_id, product_id))
                result = cur.fetchone()
                stock = result[0] if result else 0
            else:
                needs_dropdown_selection = True
        
        cur.close()
        
        return jsonify({
            'stock': stock,
            'needs_image_selection': needs_image_selection,
            'needs_dropdown_selection': needs_dropdown_selection,
            'has_stock': stock > 0
        })
        
    except Exception as e:
        print(f"Error in /api/product/stock: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/product/dropdown-variations', methods=['GET'])
def get_dropdown_variations():
    """Get dropdown variations for a product (optionally filtered by image variation)"""
    try:
        product_id = request.args.get('product_id')
        img_var_id = request.args.get('img_var_id', '')
        
        if not product_id:
            return jsonify({'error': 'Product ID required'}), 400
        
        cur = mysql.connection.cursor()
        
        # Check if dropdown variations are linked to image variations
        if img_var_id:
            # Get dropdowns for specific image variation
            cur.execute("""
                SELECT id, attr_name, attr_value, stock 
                FROM dropdown_variation 
                WHERE prod_id = %s AND img_var_id = %s
                ORDER BY attr_name, attr_value
            """, (product_id, img_var_id))
        else:
            # Get all dropdowns for product (not linked to image variation)
            cur.execute("""
                SELECT id, attr_name, attr_value, stock 
                FROM dropdown_variation 
                WHERE prod_id = %s AND img_var_id IS NULL
                ORDER BY attr_name, attr_value
            """, (product_id,))
        
        rows = cur.fetchall()
        cur.close()
        
        # Group by attribute name
        variations = {}
        for row in rows:
            attr_name = row[1]
            if attr_name not in variations:
                variations[attr_name] = []
            variations[attr_name].append({
                'id': row[0],
                'value': row[2],
                'stock': row[3]
            })
        
        return jsonify({'variations': variations})
        
    except Exception as e:
        print(f"Error in /api/product/dropdown-variations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/update-cart', methods=['GET', 'POST'])
def update_cart():
    """Update cart quantities using Flask sessions"""
    try:
        cart_key = request.args.get('product_id') if request.method == 'GET' else request.form.get('product_id')
        action = request.args.get('action') if request.method == 'GET' else request.form.get('action')
        quantity = request.args.get('quantity') if request.method == 'GET' else request.form.get('quantity')
        redirect_to = request.args.get('redirect_to') if request.method == 'GET' else request.form.get('redirect_to')
        
        # Debug logging (simplified)
        print(f"UPDATE CART: {request.method} - cart_key={cart_key}, action={action}, quantity={quantity}")
        
        # Get cart from session
        if 'cart' not in session:
            session['cart'] = {}
        
        current_cart = session['cart']
        
        if not cart_key:
            print(f"ERROR: No cart_key provided")
            if request.args.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, error="No cart key provided")
            flash('Invalid cart item', 'error')
            return redirect(url_for('addtocart'))
            
        if cart_key not in current_cart:
            print(f"ERROR: cart_key '{cart_key}' not found in cart. Available keys: {list(current_cart.keys())}")
            if request.args.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, error=f"Cart item not found: {cart_key}")
            flash('Invalid cart item', 'error')
            return redirect(url_for('addtocart'))
        
        cart_item = current_cart[cart_key]
        product_name = cart_item.get('name', 'Product')
        
        if action == 'remove':
            current_cart.pop(cart_key, None)
            success_message = f'{product_name} removed from cart'
            flash(success_message, 'success')
        elif action == 'update' and quantity:
            requested_qty = int(quantity)
            
            # Get actual stock for this variation
            product_id = cart_item.get('product_id')
            img_var_id = cart_item.get('img_var_id', '')
            dropdown_var_id = cart_item.get('dropdown_var_id', '')
            
            # Calculate actual stock based on variations
            max_stock = 999  # Default fallback
            cur = mysql.connection.cursor()
            
            if img_var_id and dropdown_var_id:
                cur.execute("SELECT stock FROM dropdown_variation WHERE id = %s", (dropdown_var_id,))
                stock_result = cur.fetchone()
                if stock_result:
                    max_stock = stock_result[0]
            elif img_var_id:
                cur.execute("SELECT stock FROM image_variations WHERE id = %s", (img_var_id,))
                stock_result = cur.fetchone()
                if stock_result:
                    max_stock = stock_result[0]
            elif dropdown_var_id:
                cur.execute("SELECT stock FROM dropdown_variation WHERE id = %s", (dropdown_var_id,))
                stock_result = cur.fetchone()
                if stock_result:
                    max_stock = stock_result[0]
            else:
                cur.execute("SELECT stock FROM products WHERE id = %s", (product_id,))
                stock_result = cur.fetchone()
                if stock_result:
                    max_stock = stock_result[0]
            
            cur.close()
            
            # Enforce stock limits
            actual_qty = max(1, min(requested_qty, max_stock))
            current_cart[cart_key]['quantity'] = actual_qty
            
            if requested_qty > max_stock:
                success_message = f'Only {max_stock} available in stock. Quantity set to maximum.'
                flash(success_message, 'warning')
            else:
                success_message = 'Cart updated successfully'
                flash(success_message, 'success')
        else:
            error_message = 'Invalid action or quantity'
            flash(error_message, 'error')
            
            # Handle AJAX error response for invalid action
            if request.args.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, error=error_message)
        
        # Save to session
        session['cart'] = current_cart
        session.modified = True
        
        # Handle AJAX requests (only if explicitly marked as AJAX)
        if request.args.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart_count = sum(item['quantity'] for item in current_cart.values())
            cart_total = sum(item['quantity'] * item['price'] for item in current_cart.values())
            
            # Include success message in response
            message = success_message if 'success_message' in locals() else 'Operation completed'
            return jsonify(success=True, cart_count=cart_count, cart_total=cart_total, message=message)
        
        # Redirect
        if redirect_to and redirect_to.startswith('/'):
            return redirect(redirect_to)
        return redirect(url_for('addtocart'))
        
    except Exception as e:
        print(f"Update cart error: {e}")
        import traceback
        traceback.print_exc()
        
        # Handle AJAX error response
        if request.args.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error=str(e))
        
        flash('Error updating cart', 'error')
        return redirect(url_for('addtocart'))

# Wishlist routes
@app.route('/api/wishlist/count')
def wishlist_count():
    """Get wishlist item count for badge"""
    try:
        if 'user_id' not in session:
            return jsonify({'count': 0})
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM wishlist WHERE user_id = %s", (session['user_id'],))
        count = cur.fetchone()[0]
        cur.close()
        return jsonify({'count': count})
    except Exception as e:
        print(f"Error getting wishlist count: {e}")
        return jsonify({'count': 0, 'error': str(e)}), 500

@app.route('/wishlist/get')
@login_required
def get_wishlist():
    """Get all wishlist items for the logged-in user"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT p.* FROM products p
            INNER JOIN wishlist w ON p.id = w.product_id
            WHERE w.user_id = %s
            ORDER BY w.added_at DESC
        """, (session['user_id'],))
        wishlist_data = cur.fetchall()
        cur.close()
        
        wishlist_items = []
        for product_data in wishlist_data:
            product = get_product_with_discount(product_data)
            if product:
                wishlist_items.append(product)
        
        return jsonify({'success': True, 'wishlist': wishlist_items})
    except Exception as e:
        print(f"Error getting wishlist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/wishlist/add', methods=['POST'])
def add_to_wishlist_json():
    """Add product to wishlist (JSON API)"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'You must be logged in to add items to wishlist'}), 401
        
        data = request.get_json(force=True, silent=True)
        if not data:
            data = {}
        
        product_id = data.get('product_id')
        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID required'}), 400
        
        cur = mysql.connection.cursor()
        
        # Check if product exists
        cur.execute("SELECT name FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        if not product:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
        
        product_name = product[0]
        
        # Try to add to wishlist
        try:
            cur.execute("INSERT INTO wishlist (user_id, product_id) VALUES (%s, %s)", 
                       (session['user_id'], product_id))
            mysql.connection.commit()
            cur.close()
            return jsonify({'success': True, 'message': f'{product_name} added to wishlist'})
        except Exception as e:
            cur.close()
            # Already in wishlist
            return jsonify({'success': True, 'message': f'{product_name} is already in your wishlist'})
    except Exception as e:
        print(f"Error adding to wishlist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/wishlist/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_wishlist(product_id):
    """Add product to wishlist (Form submission)"""
    try:
        cur = mysql.connection.cursor()
        
        # Check if product exists
        cur.execute("SELECT name FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        if not product:
            flash('Product not found', 'error')
            return redirect(request.referrer or url_for('home'))
        
        product_name = product[0]
        
        # Try to add to wishlist (will fail silently if already exists due to UNIQUE constraint)
        try:
            cur.execute("INSERT INTO wishlist (user_id, product_id) VALUES (%s, %s)", 
                       (session['user_id'], product_id))
            mysql.connection.commit()
            flash(f'{product_name} added to wishlist!', 'success')
        except Exception:
            flash(f'{product_name} is already in your wishlist', 'info')
        
        cur.close()
        return redirect(request.referrer or url_for('home'))
    except Exception as e:
        print(f"Error adding to wishlist: {e}")
        flash('Error adding to wishlist', 'error')
        return redirect(request.referrer or url_for('home'))

@app.route('/wishlist/remove', methods=['POST'])
def remove_from_wishlist():
    """Remove product from wishlist"""
    try:
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'You must be logged in to manage wishlist'}), 401
        
        # Get JSON data
        data = request.get_json(force=True, silent=True)
        if not data:
            data = {}
        
        # Get product_id from JSON body
        product_id = data.get('product_id')
        
        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID required'}), 400
        
        cur = mysql.connection.cursor()
        
        # Get product name before removing
        cur.execute("SELECT name FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        product_name = product[0] if product else 'Product'
        
        cur.execute("DELETE FROM wishlist WHERE user_id = %s AND product_id = %s", 
                   (session['user_id'], product_id))
        mysql.connection.commit()
        cur.close()
        
        # Add flash message for after reload
        flash(f'{product_name} removed from wishlist', 'info')
        
        return jsonify({'success': True, 'message': f'{product_name} removed from wishlist'})
    except Exception as e:
        print(f"Error removing from wishlist: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/wishlist/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def wishlist_add_to_cart(product_id):
    """Add product from wishlist to cart"""
    try:
        if 'cart' not in session:
            session['cart'] = {}
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product_data = cur.fetchone()
        
        if not product_data:
            flash('Product not found', 'error')
            cur.close()
            return redirect(url_for('profile'))
        
        product = get_product_with_discount(product_data)
        product_id_str = str(product_id)
        
        if product_id_str in session['cart']:
            session['cart'][product_id_str]['quantity'] += 1
        else:
            session['cart'][product_id_str] = {
                'product_id': product_id,
                'name': product['name'],
                'price': product['price'],
                'original_price': product.get('original_price', product['price']),
                'discount': product.get('discount', 0),
                'image': product['image'],
                'quantity': 1,
                'stock': product.get('stock', 999),
                'variations': ''
            }
        
        session.modified = True
        cur.close()
        flash(f"{product['name']} added to cart!", 'success')
        return redirect(url_for('profile') + '#wishlist')
    except Exception as e:
        print(f"Error adding wishlist item to cart: {e}")
        flash('Error adding to cart', 'error')
        return redirect(url_for('profile'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cur = None
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories_data = cur.fetchall()
    categories = [{'id': cat[0], 'name': cat[1]} for cat in categories_data]
    
    # Fetch logged-in user data for auto-fill
    user_data = None
    if 'user_id' in session:
        cur.execute("SELECT first_name, last_name, email, phone, address, city FROM users WHERE id = %s", (session['user_id'],))
        user_row = cur.fetchone()
        if user_row:
            # Combine first_name and last_name for full_name
            full_name = f"{user_row[0] or ''} {user_row[1] or ''}".strip()
            user_data = {
                'full_name': full_name if full_name else None,
                'email': user_row[2],
                'phone': user_row[3],
                'address': user_row[4],
                'city': user_row[5]
            }
    
    # Get cart items using standardized function
    cart_items = build_cart_items_from_session(cur, session.get('cart', {}))
    
    # Calculate total and add discount info
    total = 0.0
    for item in cart_items:
        # Fetch discount info for each item
        actual_product_id = item['product_id']
        cur.execute("SELECT * FROM products WHERE id = %s", (actual_product_id,))
        product_data = cur.fetchone()
        if product_data:
            product = get_product_with_discount(product_data)
            if product:
                item['original_price'] = product['original_price']
                item['discount'] = product['discount']
                item['is_new'] = False
                total += item['price'] * item['quantity']
    delivery_fee = 1500
    tax_rate = 0.18
    tax_amount = total * tax_rate
    final_total = total + delivery_fee + tax_amount
    payment_initiated = False
    payment_message = ''
    payment_ref = session.get('payment_ref')
    if request.method == 'POST':
        if not validate_csrf():
            flash('Invalid session. Please refresh and try again.', 'error')
        else:
            full_name = request.form.get('full_name', '').strip()
            address_line = request.form.get('address_line', '').strip()
            city = request.form.get('city', '').strip()
            delivery_phone = request.form.get('delivery_phone', '').strip()
            notes = request.form.get('notes', '').strip()
            payment_method = request.form.get('payment_method', 'cod').strip().lower()  # Default to COD
            provider = request.form.get('provider', 'MTN').strip().lower()  # Default to MTN
            momo_number = request.form.get('momo_number', '').strip()
            guest_email = request.form.get('guest_email', '').strip().lower() if 'user_id' not in session else None
            if not cart_items or total <= 0:
                flash('Your cart is empty', 'error')
            else:
                missing = []
                if not full_name: missing.append('Full Name')
                if not address_line: missing.append('Address')
                if not city: missing.append('City')
                if not delivery_phone: missing.append('Delivery Phone')
                # Only validate Mobile Money fields if Mobile Money payment is selected
                if payment_method == 'momo':
                    if not provider: missing.append('Mobile Money Provider')
                    if not momo_number: missing.append('Mobile Money Number')
                # For guest users, email is required
                if 'user_id' not in session and not guest_email:
                    missing.append('Email Address')
                elif 'user_id' not in session and guest_email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', guest_email):
                    missing.append('Valid Email Address')
                # Accept multiple formats:
                # - Rwandan: 07XXXXXXXX or +25007XXXXXXXX or 25007XXXXXXXX
                # - Any 10+ digit number (for sandbox testing)
                phone_regex = r'^(\+?[0-9]{10,15})$'
                if missing:
                    flash('Please fill: ' + ', '.join(missing), 'error')
                elif not re.match(phone_regex, delivery_phone):
                    flash('Enter a valid delivery phone number (10-15 digits)', 'error')
                elif payment_method == 'momo' and not re.match(phone_regex, momo_number):
                    flash('Enter a valid mobile money number (10-15 digits)', 'error')
                else:
                    # Preserve original MoMo number for storage; map separate API number if needed
                    original_momo_number = momo_number.strip()
                    # Normalize display/storage lightly (keep what user typed, just trim spaces)
                    # Build api_momo_number for MTN sandbox/prod rules
                    api_momo_number = original_momo_number.replace('+', '').replace(' ', '')
                    if getattr(PayClass, 'environment_mode', 'sandbox') == 'sandbox':
                        if api_momo_number.startswith('07') or api_momo_number.startswith('2507') or api_momo_number.startswith('+2507'):
                            api_momo_number = '56733123450'
                    else:
                        if api_momo_number.startswith('07') or api_momo_number.startswith('78'):
                            api_momo_number = f"250{api_momo_number.lstrip('0')}"
                    
                    delivery_phone = delivery_phone.replace('+', '').replace(' ', '')
                    if delivery_phone.startswith('07') or delivery_phone.startswith('78'):
                        delivery_phone = f"+250{delivery_phone.lstrip('0')}"
                    elif delivery_phone.startswith('250'):
                        delivery_phone = f"+{delivery_phone}"
                    # else: keep as-is for test numbers
                    external_id = str(uuid.uuid4())
                    try:
                        # Handle both logged-in users and guests
                        user_id = session.get('user_id', None)
                        # Geolocation from map picker
                        lat_raw = request.form.get('latitude')
                        lng_raw = request.form.get('longitude')
                        latitude = float(lat_raw) if lat_raw and lat_raw.strip() != '' else None
                        longitude = float(lng_raw) if lng_raw and lng_raw.strip() != '' else None
                        
                        # Handle different payment methods
                        if payment_method == 'momo':
                            # Note: Sandbox uses EUR, production uses RWF
                            currency = "EUR" if PayClass.environment_mode == "sandbox" else "RWF"
                            
                            # INITIATE PAYMENT FIRST - DO NOT CREATE ORDER YET
                            payment_result = PayClass.momopay(
                                amount=str(int(final_total)),
                                currency=currency,
                                txt_ref=external_id,
                                phone_number=api_momo_number,
                                payermessage=f"Payment from eMarket"
                            )
                        else:
                            # Cash on Delivery - no payment processing needed
                            currency = "RWF"  # Always RWF for COD
                            payment_result = {'response': 200, 'status': 'success', 'message': 'Cash on Delivery order'}
                        
                        if payment_result['response'] in [200, 202]:
                            # Payment initiated successfully - store pending order data in session
                            print(f"PAYMENT INITIATED - Storing pending_order with {len(cart_items)} items:")
                            for idx, ci in enumerate(cart_items):
                                print(f"   Item {idx+1}: {ci['name']} | Variations: '{ci.get('variations', 'KEY_MISSING')}'")
                            
                            session['pending_order'] = {
                                'user_id': user_id,
                                'guest_email': guest_email,
                                'full_name': full_name,
                                'address_line': address_line,
                                'city': city,
                                'delivery_phone': delivery_phone,
                                'payment_method': payment_method,
                                'provider': provider if payment_method == 'momo' else None,
                                'momo_number': original_momo_number if payment_method == 'momo' else None,
                                'notes': notes,
                                'latitude': latitude,
                                'longitude': longitude,
                                'total_amount': total,
                                'cart_items': cart_items,
                                'currency': currency if payment_method == 'momo' else 'RWF'
                            }
                            session['payment_ref'] = external_id
                            session['provider'] = provider if payment_method == 'momo' else None
                            session['momo_number'] = original_momo_number if payment_method == 'momo' else None
                            session['currency'] = currency if payment_method == 'momo' else 'RWF'
                            session['final_total'] = float(final_total)
                            session.modified = True
                            
                            if payment_method == 'cod':
                                # For Cash on Delivery, create order immediately
                                try:
                                    # Create the order directly
                                    from datetime import datetime
                                    cur = mysql.connection.cursor()
                                    
                                    # Insert order - match database schema exactly
                                    cur.execute("""
                                        INSERT INTO orders (user_id, full_name, address_line, city, 
                                                          delivery_phone, provider, momo_number, notes, latitude, 
                                                          longitude, total_amount, payment_status, status, 
                                                          created_at)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (
                                        user_id, full_name, address_line, city,
                                        delivery_phone, 'COD', None, notes, latitude,
                                        longitude, total, 'pending', 'pending',
                                        datetime.now()
                                    ))
                                    
                                    order_id = cur.lastrowid
                                    
                                    # Insert order items - match database schema exactly
                                    for item in cart_items:
                                        subtotal = item['quantity'] * item['price']
                                        variations = item.get('variations', '')
                                        cur.execute("""
                                            INSERT INTO order_items (order_id, product_id, product_name, price, quantity, subtotal, VARIATIONS)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                                        """, (order_id, item['product_id'], item['name'], item['price'], item['quantity'], subtotal, variations))
                                        
                                        # DEDUCT STOCK from appropriate level (triggers will cascade)
                                        stock_level = deduct_stock_smartly(cur, item['product_id'], int(item['quantity']), variations)
                                        print(f"CHECKOUT COD: Stock deducted from {stock_level} level for {item['name']}")
                                    
                                    mysql.connection.commit()
                                    
                                    # Send order confirmation email
                                    order_email = user_data['email'] if user_data else guest_email
                                    print(f"[DEBUG] COD Order email: user_data={bool(user_data)}, guest_email={guest_email}, final_email={order_email}")
                                    if order_email:
                                        print(f"[EMAIL] Sending COD order confirmation to {order_email}")
                                        send_order_confirmation_email(order_email, order_id, full_name, total, cart_items)
                                    else:
                                        print(f"[WARNING] No email found for COD order {order_id}")
                                    
                                    cur.close()
                                    
                                    # Clear cart and pending order
                                    session['cart'] = {}
                                    session.pop('pending_order', None)
                                    session.modified = True
                                    
                                    # Show success modal instead of redirect
                                    return render_template('checkout.html', 
                                                         categories=categories, 
                                                         cart_items=[], 
                                                         total=0, 
                                                         user_data=user_data,
                                                         show_success_modal=True,
                                                         order_id=order_id)
                                    
                                except Exception as e:
                                    print(f"Error creating COD order: {e}")
                                    flash('Error creating order. Please try again.', 'error')
                            else:
                                # Mobile Money payment
                                payment_initiated = True
                                payment_message = f'Payment requested! Check your phone ({original_momo_number}) to approve.'
                                flash(payment_message, 'success')
                        else:
                            # Payment initiation failed - do not create order
                            user_message = payment_result.get('user_message', 'Payment initiation failed. Please try again.')
                            error_code = payment_result.get('error_code', 'UNKNOWN')
                            flash(f"{user_message} (Error: {error_code})", 'error')
                    except Exception as e:
                        print(f"Payment initiation error: {e}")
                        flash('Error initiating payment. Try again.', 'error')
    if payment_ref and payment_initiated:
        payment_status = PayClass.verifymomo(payment_ref)
        if payment_status.get('status') == 'SUCCESSFUL':
            # Payment successful - NOW create the order
            pending_order = session.get('pending_order')
            if pending_order:
                try:
                    # Create order in database
                    cur.execute(
                        "INSERT INTO orders (user_id, guest_email, full_name, address_line, city, delivery_phone, provider, momo_number, notes, latitude, longitude, total_amount, status, momo_transaction_id, payment_status) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (
                            pending_order['user_id'],
                            pending_order['guest_email'],
                            pending_order['full_name'],
                            pending_order['address_line'],
                            pending_order['city'],
                            pending_order['delivery_phone'],
                            pending_order['provider'],
                            pending_order['momo_number'],
                            pending_order['notes'],
                            pending_order['latitude'],
                            pending_order['longitude'],
                            pending_order['total_amount'],
                            'SUCCESSFUL',
                            payment_ref,
                            'paid'
                        )
                    )
                    order_id = cur.lastrowid
                    
                    # Insert order items and deduct stock
                    for item in pending_order['cart_items']:
                        subtotal = item['price'] * item['quantity']
                        # Use actual product_id for database operations
                        product_id_for_db = item.get('product_id', item['id'])
                        variations = item.get('variations', '')
                        product_name_with_variations = item['name']
                        
                        print(f"Saving order item:")
                        print(f"   Product: {product_name_with_variations}")
                        print(f"   Variations RAW: '{variations}'")
                        print(f"   Variations TYPE: {type(variations)}")
                        print(f"   Full item dict: {item}")
                        
                        cur.execute(
                            "INSERT INTO order_items (order_id, product_id, product_name, price, quantity, subtotal, VARIATIONS) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (order_id, product_id_for_db, product_name_with_variations, item['price'], item['quantity'], subtotal, variations)
                        )
                        
                        # DEDUCT STOCK from appropriate level (triggers will cascade)
                        stock_level = deduct_stock_smartly(cur, product_id_for_db, int(item['quantity']), variations)
                        print(f"MTN CHECKOUT: Stock deducted from {stock_level} level for {product_name_with_variations}")
                    
                    # Log payment record
                    try:
                        raw = json.dumps({'verify': payment_status})
                        cur.execute(
                            """
                            INSERT INTO payments (order_id, momo_transaction_id, amount, currency, status, provider, payer_number, raw_response)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                order_id,
                                payment_ref,
                                float(pending_order['total_amount']),
                                pending_order['currency'],
                                'SUCCESSFUL',
                                pending_order['provider'],
                                pending_order['momo_number'],
                                raw
                            )
                        )
                    except Exception as _:
                        pass
                    
                    mysql.connection.commit()
                    
                    # Clear cart and session data
                    session['cart'] = {}
                    session.pop('payment_ref', None)
                    session.pop('pending_order', None)
                    session.pop('provider', None)
                    session.pop('momo_number', None)
                    session.pop('currency', None)
                    session.pop('final_total', None)
                    session.modified = True
                    
                    payment_message = f'Payment successful! Order #{order_id} confirmed.'
                    flash(payment_message, 'success')
                    payment_initiated = True
                except Exception as e:
                    print(f"Error creating order after payment: {e}")
                    mysql.connection.rollback()
                    flash('Payment succeeded but order creation failed. Please contact support.', 'error')
            else:
                flash('Payment succeeded but order data was lost. Please contact support.', 'error')
        elif payment_status.get('status') in ['FAILED', 'REJECTED', 'EXPIRED']:
            # Payment failed - DO NOT create order, just clean up session
            try:
                # Only log the failed payment attempt (no order created)
                raw = json.dumps({'verify': payment_status})
                cur.execute(
                    """
                    INSERT INTO payments (order_id, momo_transaction_id, amount, currency, status, provider, payer_number, raw_response)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        None,  # No order_id since order was not created
                        payment_ref,
                        float(session.get('final_total', 0.0)),
                        session.get('currency', 'RWF'),
                        payment_status['status'],
                        session.get('provider'),
                        session.get('momo_number'),
                        raw
                    )
                )
                mysql.connection.commit()
            except Exception as _:
                pass
            
            # Clean up session but keep cart so user can retry
            session.pop('payment_ref', None)
            session.pop('pending_order', None)
            session.pop('provider', None)
            session.pop('momo_number', None)
            session.pop('currency', None)
            session.pop('final_total', None)
            session.modified = True
            flash(f"Payment {payment_status['status'].lower()}: {payment_status.get('reason', 'Unknown error')}", 'error')
            payment_initiated = False
    if cur:
        cur.close()
    return render_template('checkout.html',
                            categories=categories,
                            cart_items=cart_items,
                            total=total,
                            delivery_fee=delivery_fee,
                            tax_amount=tax_amount,
                            final_total=final_total,
                            payment_initiated=payment_initiated,
                            payment_message=payment_message,
                            payment_ref=payment_ref,
                            user_data=user_data)

"""
Minimal payment endpoint to start fresh
"""

@app.route('/pay/simple', methods=['POST'])
def pay_simple():
    try:
        if not validate_csrf():
            return jsonify({'status': 'error', 'message': 'Invalid session'}), 400

        momo_number = request.form.get('momo_number', '').strip()
        if not momo_number:
            return jsonify({'status': 'error', 'message': 'Mobile money number required'}), 400

        # Calculate total from cart (server truth)
        cur = mysql.connection.cursor()
        cart_items = []
        total = 0.0
        for cart_key, item in session.get('cart', {}).items():
            # Extract actual product_id from cart item (for items with variations)
            actual_product_id = item.get('product_id', cart_key.split('_')[0] if '_' in cart_key else cart_key)
            cur.execute("SELECT id, name, price, stock FROM products WHERE id = %s", (actual_product_id,))
            row = cur.fetchone()
            if row:
                qty = min(item['quantity'], row[3] if len(row) > 3 else item['quantity'])
                if qty > 0:
                    variations_value = item.get('variations', '')
                    print(f"/pay/simple - Building cart_items:")
                    print(f"   Cart Key: {cart_key}")
                    print(f"   Product: {row[1]}")
                    print(f"   Variations: '{variations_value}'")
                    
                    cart_items.append({
                        'id': row[0], 
                        'product_id': actual_product_id,
                        'name': row[1], 
                        'price': float(row[2]), 
                        'quantity': qty,
                        'variations': variations_value
                    })
                    total += float(item['price']) * qty

        if not cart_items or total <= 0:
            cur.close()
            return jsonify({'status': 'error', 'message': 'Your cart is empty'}), 400

        delivery_fee = 1500
        tax_rate = 0.18
        tax_amount = total * tax_rate
        final_total = total + delivery_fee + tax_amount

        # Collect order fields from the form
        full_name = request.form.get('full_name', 'N/A').strip() or 'N/A'
        address_line = request.form.get('address_line', 'N/A').strip() or 'N/A'
        city = request.form.get('city', 'N/A').strip() or 'N/A'
        delivery_phone = request.form.get('delivery_phone', '').strip()
        provider = request.form.get('provider', 'MTN').strip().lower()
        user_momo = request.form.get('momo_number', '').strip()  # preserve what user typed
        notes = request.form.get('notes', '').strip()

        # Sandbox phone handling (map Rwandan local to MTN sandbox MSISDN)
        # Build API MSISDN separately, keep user_momo for DB
        if hasattr(PayClass, 'environment_mode') and getattr(PayClass, 'environment_mode') == 'sandbox':
            raw = user_momo.replace(' ', '').replace('-', '')
            if raw.startswith('07') or raw.startswith('+2507') or raw.startswith('2507'):
                api_momo = '56733123450'
            else:
                api_momo = raw.replace('+', '')
        else:
            api_momo = user_momo.replace('+', '').replace(' ', '')
            if api_momo.startswith('07') or api_momo.startswith('78'):
                api_momo = f"250{api_momo.lstrip('0')}"

        external_id = str(uuid.uuid4())
        PayClass.initialize_api_user()
        currency = 'EUR' if getattr(PayClass, 'environment_mode', 'sandbox') == 'sandbox' else 'RWF'

        # Store order data for later creation
        lat_raw = request.form.get('latitude')
        lng_raw = request.form.get('longitude')
        latitude = float(lat_raw) if lat_raw and lat_raw.strip() != '' else None
        longitude = float(lng_raw) if lng_raw and lng_raw.strip() != '' else None
        
        order_data = {
            'user_id': session.get('user_id'),
            'full_name': full_name,
            'address_line': address_line,
            'city': city,
            'delivery_phone': delivery_phone,
            'provider': provider,
            'momo_number': user_momo,
            'notes': notes,
            'latitude': latitude,
            'longitude': longitude,
            'total_amount': float(total),
            'cart_items': cart_items,
            'currency': currency
        }

        # INITIATE PAYMENT FIRST - DO NOT CREATE ORDER YET
        callPay = PayClass.momopay(
            str(int(final_total)),
            currency,
            external_id,
            api_momo,
            'Payment to eMarket'
        )

        print(f"/pay/simple initiation: amount={final_total}, phone={momo_number}, resp={callPay}")

        if callPay.get('response') in (200, 202):
            # Payment initiated successfully
            verify = PayClass.verifymomo(callPay.get('ref'))
            print(f"/pay/simple verify: {verify}")

            if isinstance(verify, dict) and verify.get('status') == 'SUCCESSFUL':
                # Payment SUCCESSFUL - NOW create the order
                ref = callPay.get('ref')
                try:
                    cur = mysql.connection.cursor()
                    # Create order in database
                    cur.execute(
                        """
                        INSERT INTO orders (user_id, full_name, address_line, city, delivery_phone, provider, momo_number, notes, latitude, longitude, total_amount, status, momo_transaction_id, payment_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (order_data['user_id'], order_data['full_name'], order_data['address_line'], order_data['city'], 
                         order_data['delivery_phone'], order_data['provider'], order_data['momo_number'], order_data['notes'], 
                         order_data['latitude'], order_data['longitude'], order_data['total_amount'], 'paid', ref, 'paid')
                    )
                    order_id = cur.lastrowid
                    
                    # Insert order items and decrement stock
                    for ci in order_data['cart_items']:
                        subtotal = float(ci['price']) * int(ci['quantity'])
                        variations = ci.get('variations', '')
                        product_id_for_db = ci.get('product_id', ci['id'])
                        product_name = ci['name']
                        
                        print(f"/pay/simple - Saving order item:")
                        print(f"   Product: {product_name}")
                        print(f"   Variations: '{variations}'")
                        
                        cur.execute(
                            """
                            INSERT INTO order_items (order_id, product_id, product_name, price, quantity, subtotal, VARIATIONS)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (order_id, product_id_for_db, product_name, float(ci['price']), int(ci['quantity']), subtotal, variations)
                        )
                        
                        # DEDUCT STOCK from appropriate level (triggers will cascade)
                        stock_level = deduct_stock_smartly(cur, product_id_for_db, int(ci['quantity']), variations)
                        print(f"MTN PAYMENT: Stock deducted from {stock_level} level for {product_name}")
                    
                    # Log payment record
                    raw = json.dumps({'init': callPay, 'verify': verify})
                    cur.execute(
                        """
                        INSERT INTO payments (order_id, momo_transaction_id, amount, currency, status, provider, payer_number, raw_response)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (order_id, ref, order_data['total_amount'], order_data['currency'], 'SUCCESSFUL', order_data['provider'], order_data['momo_number'], raw)
                    )
                    payment_id = cur.lastrowid
                    
                    mysql.connection.commit()
                    
                    # Send order confirmation email
                    user_email = None
                    if order_data['user_id']:
                        cur.execute("SELECT email, first_name FROM users WHERE id = %s", (order_data['user_id'],))
                        user_row = cur.fetchone()
                        if user_row:
                            user_email = user_row[0]
                            user_first_name = user_row[1]
                    
                    cur.close()
                    
                    if user_email:
                        items_html = ''.join([f"<li>{ci['name']} x {ci['quantity']} - RWF {ci['price']:,.0f}</li>" for ci in order_data['cart_items']])
                        order_email_html = f"""
                        <html>
                          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                              <h2 style="color: #2e4d2c;">Order Confirmation - Order #{order_id}</h2>
                              <p>Hi {user_first_name},</p>
                              <p>Your payment was successful! Here are your order details:</p>
                              <h3>Order Items:</h3>
                              <ul>{items_html}</ul>
                              <p><strong>Total Amount:</strong> RWF {order_data['total_amount']:,.2f}</p>
                              <p><strong>Delivery Address:</strong> {order_data['address_line']}, {order_data['city']}</p>
                              <p><strong>Delivery Phone:</strong> {order_data['delivery_phone']}</p>
                              <p style="margin-top: 30px; font-size: 0.9em; color: #666;">Thank you for shopping with us!</p>
                              <p style="font-size: 0.9em; color: #666;">- eMarket Team</p>
                            </div>
                          </body>
                        </html>
                        """
                        send_email(user_email, f'Order Confirmation - Order #{order_id}', order_email_html)
                    
                    # Clear cart on success
                    session['cart'] = {}
                    session.modified = True
                    
                    return jsonify({
                        'status': 'successful',
                        'message': 'Order has been sent! Wait for a call from admin.',
                        'details': verify,
                        'order_id': order_id,
                        'payment_id': payment_id
                    }), 200
                except Exception as e:
                    print(f"Error creating order after payment success: {e}")
                    mysql.connection.rollback()
                    return jsonify({
                        'status': 'error',
                        'message': 'Payment succeeded but order creation failed. Contact support.',
                        'details': verify
                    }), 500
                    
            elif isinstance(verify, dict) and verify.get('status') in ('FAILED', 'REJECTED', 'EXPIRED'):
                # Payment FAILED - DO NOT create order
                ref = callPay.get('ref')
                try:
                    cur = mysql.connection.cursor()
                    # Only log the failed payment attempt (no order created)
                    raw = json.dumps({'init': callPay, 'verify': verify})
                    cur.execute(
                        """
                        INSERT INTO payments (order_id, momo_transaction_id, amount, currency, status, provider, payer_number, raw_response)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (None, ref, order_data['total_amount'], order_data['currency'], verify.get('status'), order_data['provider'], order_data['momo_number'], raw)
                    )
                    mysql.connection.commit()
                    cur.close()
                except Exception as e:
                    print(f"Error logging failed payment: {e}")
                    
                return jsonify({
                    'status': 'failed',
                    'message': 'Payment failed. Please try again.',
                    'details': verify
                }), 200
            else:
                # Payment PENDING - store in session, don't create order yet
                ref = callPay.get('ref')
                return jsonify({
                    'status': 'pending',
                    'message': 'Payment initiated. Please approve on your phone.',
                    'ref': ref,
                    'details': verify
                }), 200
        else:
            # Payment initiation FAILED - DO NOT create order
            try:
                ref = callPay.get('ref') or str(uuid.uuid4())
                cur = mysql.connection.cursor()
                # Only log the error (no order created)
                cur.execute(
                    """
                    INSERT INTO payments (order_id, momo_transaction_id, amount, currency, status, provider, payer_number, raw_response)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (None, ref, order_data['total_amount'], order_data['currency'], 'ERROR', order_data['provider'], order_data['momo_number'], json.dumps({'init': callPay}))
                )
                payment_id = cur.lastrowid
                mysql.connection.commit()
                cur.close()
                print(f"/pay/simple logged ERROR payment payment_id={payment_id}")
            except Exception as e:
                print(f"Error logging payment initiation failure: {e}")
                
            return jsonify({
                'status': 'error',
                'message': 'Payment initiation failed. Please try again.',
                'code': callPay.get('response'),
                'error': callPay.get('error')
            }), 400
    except Exception as e:
        print(f"/pay/simple error: {e}")
        print(f"Exception type: {type(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': f'Server error: {str(e)}'}), 500

@app.route('/pay/cod', methods=['POST'])
def pay_cod():
    try:
        if not validate_csrf():
            return jsonify({'status': 'error', 'message': 'Invalid session'}), 400

        # Build cart server-side
        cur = mysql.connection.cursor()
        cart_items = []
        total = 0.0
        for cart_key, item in session.get('cart', {}).items():
            # Extract actual product_id from cart item
            actual_product_id = item.get('product_id', cart_key.split('_')[0] if '_' in cart_key else cart_key)
            cur.execute("SELECT id, name, price, stock, discount FROM products WHERE id = %s", (actual_product_id,))
            row = cur.fetchone()
            if row:
                qty = min(item['quantity'], row[3] if len(row) > 3 else item['quantity'])
                if qty > 0:
                    # Calculate discounted price
                    original_price = float(row[2])
                    discount = float(row[4]) if len(row) > 4 and row[4] else 0
                    discounted_price = original_price * (1 - discount / 100) if discount > 0 else original_price
                    
                    cart_items.append({
                        'id': row[0], 
                        'name': row[1], 
                        'price': discounted_price, 
                        'quantity': qty,
                        'variations': item.get('variations', '')
                    })
                    total += discounted_price * qty

        if not cart_items or total <= 0:
            cur.close()
            return jsonify({'status': 'error', 'message': 'Your cart is empty'}), 400

        delivery_fee = 1500
        tax_rate = 0.18
        tax_amount = total * tax_rate
        final_total = total + delivery_fee + tax_amount

        # Form fields
        full_name = request.form.get('full_name', 'N/A').strip() or 'N/A'
        address_line = request.form.get('address_line', 'N/A').strip() or 'N/A'
        city = request.form.get('city', 'N/A').strip() or 'N/A'
        delivery_phone = request.form.get('delivery_phone', '').strip()
        notes = request.form.get('notes', '').strip()
        lat_raw = request.form.get('latitude')
        lng_raw = request.form.get('longitude')
        latitude = float(lat_raw) if lat_raw and lat_raw.strip() != '' else None
        longitude = float(lng_raw) if lng_raw and lng_raw.strip() != '' else None
        
        print(f"DEBUG: lat_raw = '{lat_raw}', lng_raw = '{lng_raw}'")
        print(f"DEBUG: latitude = {latitude}, longitude = {longitude}")

        # Create order - SIMPLE!
        try:
            print(f"DEBUG: Creating COD order for user_id: {session.get('user_id')}")
            print(f"DEBUG: Order details - name: {full_name}, phone: {delivery_phone}, total: {total}")
            
            # Insert into orders table
            cur.execute(
                """
                INSERT INTO orders (user_id, full_name, address_line, city, delivery_phone, provider, momo_number, notes, latitude, longitude, total_amount, status, momo_transaction_id, payment_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (session.get('user_id'), full_name, address_line, city, delivery_phone, 'NONE', None, notes, latitude, longitude, float(total), 'pending', None, 'pending')
            )
            order_id = cur.lastrowid
            print(f"DEBUG: Order created with ID: {order_id}")
            
            # Insert into order_items table
            for ci in cart_items:
                subtotal = float(ci['price']) * int(ci['quantity'])
                variations = ci.get('variations', '')
                print(f"DEBUG: Adding item - {ci['name']}, qty: {ci['quantity']}, price: {ci['price']}, variations: {variations}")
                cur.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, product_name, price, quantity, subtotal, VARIATIONS)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (order_id, ci['id'], ci['name'], float(ci['price']), int(ci['quantity']), subtotal, variations)
                )
                
                # DEDUCT STOCK from appropriate level (triggers will cascade)
                stock_level = deduct_stock_smartly(cur, ci['id'], int(ci['quantity']), variations)
                print(f"COD ORDER: Stock deducted from {stock_level} level for {ci['name']}")
            
            print("[DEBUG] About to get user email")
            # Get user email BEFORE committing
            user_email = None
            if session.get('user_id'):
                # Get logged-in user's email
                cur.execute("SELECT email FROM users WHERE id = %s", (session.get('user_id'),))
                user_row = cur.fetchone()
                user_email = user_row[0] if user_row else None
            else:
                # Get guest email from form
                user_email = request.form.get('guest_email', '').strip()
            
            mysql.connection.commit()
            cur.close()
            
            # Send order confirmation email (after cursor is closed)
            print(f"[DEBUG] Guest email from form: {user_email}")
            print(f"[DEBUG] Final user_email: {user_email}")
            if user_email:
                print(f"[EMAIL] Sending order confirmation to {user_email}")
                result = send_order_confirmation_email(user_email, order_id, full_name, total, cart_items)
                print(f"[EMAIL] Send result: {result}")
            else:
                print(f"[WARNING] No email address found for order {order_id}")
            print("DEBUG: COD order created successfully!")
        except Exception as e:
            print(f"[ERROR] COD order error: {e}")
            print(f"[ERROR] COD order error type: {type(e)}")
            import traceback
            traceback.print_exc()
            try:
                mysql.connection.rollback()
                cur.close()
            except:
                pass
            return jsonify({'status': 'error', 'message': f'Could not create COD order: {str(e)}'}), 500

        # Clear cart and respond
        print("[DEBUG] Clearing cart and responding with success")
        session['cart'] = {}
        session.modified = True
        return jsonify({'status': 'successful', 'message': 'Order placed successfully! You will pay cash on delivery.', 'order_id': order_id}), 200
    except Exception as e:
        print(f"[ERROR] Outer COD error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': 'Server error creating COD order'}), 500

@app.route('/api/product/<int:product_id>')
def get_product_api(product_id):
    """API endpoint to get product details for modal"""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product_data = cur.fetchone()
        cur.close()
        
        if not product_data:
            return jsonify({'error': 'Product not found'}), 404
        
        # Schema: id, name, price, image, category_id, stock, description (optional)
        product = {
            'id': product_data[0],
            'name': product_data[1],
            'price': float(product_data[2]) if product_data[2] is not None else 0.0,
            'description': product_data[6] if len(product_data) > 6 and product_data[6] is not None else '',
            'image': resolve_image_url(product_data[3]),
            'category_id': product_data[4],
            'stock': product_data[5] if len(product_data) > 5 and product_data[5] is not None else 0,
            'rating': float(product_data[8]) if len(product_data) > 8 and product_data[8] is not None else explicit_rating
        }
        
        # Debug: Print image path
        print(f"API returning image path: {product['image']}")
        
        return jsonify(product)
    except Exception as e:
        print(f"Product API error: {e}")
        return jsonify({'error': 'Error loading product'}), 500

@app.route('/api/search')
def search_products_api():
    """Global product search for navbar typeahead.

    Returns a JSON list of simple product objects (no images) matching
    the query string, limited to 10 results.
    """
    try:
        query = request.args.get('q', '').strip()
        results = []
        if not query:
            print(f"[SEARCH] Empty query")
            return jsonify(results)

        cur = mysql.connection.cursor()
        like = f"%{query}%"
        print(f"[SEARCH] Query: '{query}', LIKE pattern: '{like}'")

        try:
            # Search products by name or description
            print(f"[SEARCH] Attempting query with description column...")
            cur.execute(
                """
                SELECT id, name, price
                FROM products
                WHERE name LIKE %s OR (description IS NOT NULL AND description LIKE %s)
                ORDER BY name ASC
                LIMIT 10
                """,
                (like, like),
            )
            rows = cur.fetchall()
            print(f"[SEARCH] Query with description succeeded, found {len(rows)} rows")
        except Exception as e:
            # Fallback for databases without a description column
            print(f"[SEARCH] Query with description failed: {e}, trying name-only fallback...")
            cur.execute(
                """
                SELECT id, name, price
                FROM products
                WHERE name LIKE %s
                ORDER BY name ASC
                LIMIT 10
                """,
                (like,),
            )
            rows = cur.fetchall()
            print(f"[SEARCH] Fallback query succeeded, found {len(rows)} rows")

        cur.close()

        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "price": float(row[2]) if row[2] is not None else 0.0,
                }
            )

        print(f"[SEARCH] Returning {len(results)} results: {[r['name'] for r in results]}")
        return jsonify(results)
    except Exception as e:
        print(f"[SEARCH] API error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error performing search"}), 500

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """View single product details (full page)"""
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product_data = cur.fetchone()
    # Attempt to also fetch rating explicitly from products.rate (schema has 'rate')
    try:
        cur.execute("SELECT COALESCE(rate, 0) FROM products WHERE id = %s", (product_id,))
        rating_row = cur.fetchone()
        explicit_rating = float(rating_row[0]) if rating_row is not None and rating_row[0] is not None else 0.0
    except Exception:
        explicit_rating = 0.0
    if not product_data:
        flash('Product not found', 'error')
        return redirect('/')
    
    # Schema: id, name, price, image, category_id, stock, description, discount (optional)
    product = {
        'id': product_data[0],
        'name': product_data[1],
        'price': float(product_data[2]) if product_data[2] is not None else 0.0,
        'description': product_data[6] if len(product_data) > 6 and product_data[6] is not None else '',
        'image': resolve_image_url(product_data[3]),
        'category_id': product_data[4],
        'stock': product_data[5] if len(product_data) > 5 and product_data[5] is not None else 0,
        'discount': float(product_data[7] if len(product_data) > 7 and product_data[7] is not None else 0),
        # Use explicit_rating computed above to avoid depending on a specific column index
        'rating': explicit_rating
    }
    
    # Check if in wishlist for current user
    in_wishlist = False
    try:
        uid = session.get('user_id')
        if uid:
            cur.execute("SELECT 1 FROM wishlist WHERE user_id = %s AND product_id = %s LIMIT 1", (uid, product_id))
            in_wishlist = cur.fetchone() is not None
    except Exception:
        in_wishlist = False

    # Load categories for sidebar
    try:
        cur.execute("SELECT id, name FROM categories ORDER BY name")
        categories = [{'id': r[0], 'name': r[1]} for r in cur.fetchall()]
    except Exception:
        categories = []

    # Get random related products from same category
    if product['category_id']:
        cur.execute("SELECT * FROM products WHERE category_id = %s AND id != %s ORDER BY RAND() LIMIT 12",
                    (product['category_id'], product_id))
        related_products = []
        for row in cur.fetchall():
            # Use discount helper function for related products
            product_with_discount = get_product_with_discount(row)
            if product_with_discount:
                related_products.append(product_with_discount)
    else:
        related_products = []
    
    # Fetch variations for this product using standardized helper functions
    image_variations = fetch_image_variations(cur, product_id)
    dropdown_variations = fetch_dropdown_variations(cur, product_id)
    
    # Fetch reviews for this product (latest first)
    try:
        cur.execute("""
            SELECT r.id, r.user_id, u.username, r.rating, r.review, r.replie
            FROM reviews r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.product_id = %s
            ORDER BY r.id DESC
        """, (product_id,))
        rows = cur.fetchall()
        reviews = []
        for row in rows:
            reviews.append({
                'id': row[0],
                'user_id': row[1],
                'username': row[2] or 'User',
                'rating': int(row[3]) if row[3] is not None else None,
                'review': row[4],
                'reply': row[5] if len(row) > 5 and row[5] else None
            })
    except Exception:
        reviews = []

    # Build cart items for sidebar
    cart_items = []
    for cart_key, item in session.get('cart', {}).items():
        # Extract actual product_id from cart item
        actual_product_id = item.get('product_id', cart_key.split('_')[0] if '_' in cart_key else cart_key)
        img_var_id = item.get('img_var_id', '')
        cur.execute("SELECT * FROM products WHERE id = %s", (actual_product_id,))
        product_data = cur.fetchone()
        if product_data:
            product_obj = get_product_with_discount(product_data)
            if product_obj:
                item['quantity'] = min(item['quantity'], product_obj['stock'])
                if item['quantity'] > 0:
                    # Fetch image from database based on variation
                    image_url = product_obj['image']
                    if img_var_id and str(img_var_id).strip():
                        try:
                            cur.execute("SELECT img_url FROM image_variations WHERE id = %s", (img_var_id,))
                            result = cur.fetchone()
                            if result and result[0]:
                                image_url = resolve_image_url(result[0])
                        except Exception:
                            pass
                    
                    cart_items.append({
                        'id': cart_key,  # Use cart_key which includes variations
                        'product_id': actual_product_id,
                        'name': item['name'],
                        'price': item['price'],
                        'image': image_url,
                        'quantity': item['quantity'],
                        'stock': product_obj['stock'],
                        'variations': item.get('variations', ''),
                        'is_new': False
                    })
    
    cur.close()
    
    return render_template('product_details.html', product=product, related_products=related_products, categories=categories, in_wishlist=in_wishlist, reviews=reviews, cart_items=cart_items, dropdown_variations=dropdown_variations, image_variations=image_variations)


# Reviews: create (login required)
@app.route('/reviews/add', methods=['POST'])
@login_required
def add_review():
    try:
        product_id = request.form.get('product_id')
        review_text = (request.form.get('review') or '').strip()
        rating_val = request.form.get('rating')
        try:
            rating = int(rating_val) if rating_val is not None else None
        except Exception:
            rating = None
        if not product_id:
            flash('Product is required', 'error')
            return redirect(url_for('home'))
        if rating is None or rating == 0:
            flash('Please select a rating before submitting', 'error')
            return redirect(url_for('product_detail', product_id=product_id))
        if not review_text:
            flash('Please write a review before submitting', 'error')
            return redirect(url_for('product_detail', product_id=product_id))

        # Basic length guard
        if len(review_text) > 2000:
            review_text = review_text[:2000]

        cur = mysql.connection.cursor()
        # Insert review with rating into reviews table (replie field required by DB schema)
        cur.execute(
            "INSERT INTO reviews (user_id, rating, review, product_id, replie) VALUES (%s, %s, %s, %s, %s)",
            (session['user_id'], rating if rating is not None else 0, review_text, product_id, '')
        )
        
        # Recompute product average rating and update products.rate
        cur.execute("SELECT AVG(rating) FROM reviews WHERE product_id = %s", (product_id,))
        avg_row = cur.fetchone()
        avg_rating = float(avg_row[0]) if avg_row and avg_row[0] is not None else 0.0
        cur.execute("UPDATE products SET rate = %s WHERE id = %s", (round(avg_rating, 1), product_id))
        mysql.connection.commit()
        cur.close()

        flash('Review posted', 'success')
        return redirect(url_for('product_detail', product_id=product_id))
    except Exception as e:
        print(f"Add review error: {e}")
        flash('Error posting review', 'error')
        return redirect(url_for('home'))

# Performance: Add cache headers for static files
@app.after_request
def add_cache_headers(response):
    """Add cache headers to improve performance"""
    # Cache static files for 1 week
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=604800'
    # Don't cache HTML pages (always fresh content)
    elif 'text/html' in response.headers.get('Content-Type', ''):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route('/add-test-discounts')
def add_test_discounts():
    """Add some test discounts to products"""
    try:
        cur = mysql.connection.cursor()
        
        # Add discounts to first few products
        discounts = [
            (1, 25.0),  # 25% discount on product 1
            (2, 15.0),  # 15% discount on product 2
            (3, 30.0),  # 30% discount on product 3
            (4, 10.0),  # 10% discount on product 4
            (5, 20.0),  # 20% discount on product 5
        ]
        
        for product_id, discount in discounts:
            cur.execute("UPDATE products SET discount = %s WHERE id = %s", (discount, product_id))
        
        mysql.connection.commit()
        cur.close()
        
        return "Test discounts added successfully! Go check the home page."
    except Exception as e:
        return f"Error adding discounts: {e}"

@app.route('/clear-cart')
def clear_cart():
    """Clear the cart to test with fresh discount items"""
    session['cart'] = {}
    session.modified = True
    return "Cart cleared! Now add some products with discounts to see the discount system in action."

@app.route('/api/geocode')
def geocode():
    """Server-side geocoding proxy to bypass CORS/CSP issues"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 3:
        return jsonify({'error': 'Query too short', 'results': []}), 400
    
    print(f"[OpenStreetMap SEARCH] Searching for: '{query}'")
    
    try:
        # OpenStreetMap Nominatim API with multiple strategies
        queries_to_try = [
            query,  # Original query
            f"{query}, Rwanda",  # Add country context
            f"{query}, Kigali",  # Try with capital city
        ]
        
        for attempt, search_query in enumerate(queries_to_try, 1):
            osm_url = f"https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&q={requests.utils.quote(search_query)}&limit=15"
            print(f"[OpenStreetMap] Attempt {attempt}/3: Searching '{search_query}'")
            
            headers = {'User-Agent': 'eMarket/1.0 (ecommerce app)'}
            response = requests.get(osm_url, headers=headers, timeout=10)
            
            print(f"[OpenStreetMap] Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OpenStreetMap] Found {len(data)} results")
                if data and len(data) > 0:
                    print(f"[OpenStreetMap] SUCCESS! Returning {min(len(data), 10)} results")
                    return jsonify({'results': data[:10], 'source': 'openstreetmap'})
            else:
                print(f"[OpenStreetMap] HTTP {response.status_code}")
        
        # OpenStreetMap didn't find results, trying alternative OSM data source (Photon)
        print(f"[OpenStreetMap] No results from primary OSM API. Trying Photon (alternative OSM index)...")
        photon_url = f"https://photon.komoot.io/api/?q={requests.utils.quote(query)}&limit=10"
        response = requests.get(photon_url, timeout=10)
        
        print(f"[Photon/OSM] Response status: {response.status_code}")
        
        if response.status_code == 200:
            photon_data = response.json()
            if photon_data and 'features' in photon_data:
                features = photon_data['features']
                print(f"[Photon/OSM] Found {len(features)} results")
                # Transform Photon format to standard format
                results = []
                for feature in features[:10]:
                    props = feature.get('properties', {})
                    coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                    results.append({
                        'lat': coords[1],
                        'lon': coords[0],
                        'display_name': ', '.join(filter(None, [
                            props.get('name'),
                            props.get('street'),
                            props.get('city'),
                            props.get('state'),
                            props.get('country')
                        ]))
                    })
                if results:
                    print(f"[Photon/OSM] SUCCESS! Returning {len(results)} results")
                    return jsonify({'results': results, 'source': 'openstreetmap-photon'})
        
        print(f"[OpenStreetMap SEARCH] No results found for '{query}' in OpenStreetMap database")
        return jsonify({
            'error': f'No results found for "{query}". Try a different spelling or add more context (e.g., street name, neighborhood).',
            'results': [],
            'query': query
        }), 404
        
    except requests.exceptions.Timeout:
        print(f"[OpenStreetMap SEARCH] Timeout for query: '{query}'")
        return jsonify({'error': 'OpenStreetMap search timed out. Please try again.', 'results': []}), 408
    except Exception as e:
        print(f"[OpenStreetMap SEARCH ERROR] {type(e).__name__}: {e}")
        return jsonify({'error': 'OpenStreetMap service error. Please try again.', 'results': []}), 500

@app.route('/debug/test-momo')
def test_momo():
    """Debug route to test MTN MoMo API connectivity"""
    if not PRODUCTION_MODE:  # Only in development
        try:
            # Test token generation
            token_result = PayClass.momotoken()
            token_success = token_result.get('access_token') is not None
            
            # Test basic API connectivity
            url = f"{PayClass.accurl}/collection/v1_0/requesttopay"
            headers = {
                'X-Target-Environment': PayClass.environment_mode,
                'Ocp-Apim-Subscription-Key': PayClass.collections_subkey,
                'Content-Type': 'application/json'
            }
            
            # Just test connectivity without actual payment
            import requests
            response = requests.head(url, headers=headers, timeout=10)
            api_reachable = response.status_code in [200, 400, 401, 405]  # Any response means API is reachable
            
            return jsonify({
                'status': 'MTN MoMo API Test',
                'environment': PayClass.environment_mode,
                'api_url': PayClass.accurl,
                'token_generation': 'SUCCESS' if token_success else 'FAILED',
                'api_reachable': 'YES' if api_reachable else 'NO',
                'api_response_code': response.status_code,
                'credentials_configured': {
                    'collections_subkey': bool(PayClass.collections_subkey),
                    'api_user': bool(PayClass.collections_apiuser),
                    'api_key': bool(PayClass.api_key_collections)
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'MTN MoMo API Test',
                'error': str(e),
                'error_type': type(e).__name__
            })
    else:
        return jsonify({'error': 'Debug route only available in development mode'}), 403

@app.route('/test-payment-setup')
def test_payment_setup():
    """Test payment setup independently"""
    if not PRODUCTION_MODE:  # Only in development
        try:
            print("TESTING: Payment setup diagnostics...")
            
            # Test token generation
            token_result = PayClass.momotoken()
            print(f"Token result: {token_result}")
            
            # Test API user initialization
            PayClass.initialize_api_user()
            
            # Test basic connectivity
            import requests
            test_url = f"{PayClass.accurl}/collection/v1_0/requesttopay"
            headers = {
                'X-Target-Environment': PayClass.environment_mode,
                'Ocp-Apim-Subscription-Key': PayClass.collections_subkey,
                'Content-Type': 'application/json'
            }
            
            try:
                response = requests.head(test_url, headers=headers, timeout=10)
                connectivity_status = f"HTTP {response.status_code}"
                connectivity_ok = response.status_code in [200, 400, 401, 405]
            except requests.exceptions.ConnectionError:
                connectivity_status = "CONNECTION_ERROR"
                connectivity_ok = False
            except requests.exceptions.Timeout:
                connectivity_status = "TIMEOUT"
                connectivity_ok = False
            except Exception as e:
                connectivity_status = f"ERROR: {str(e)}"
                connectivity_ok = False
            
            return jsonify({
                'status': 'Payment Setup Diagnostics',
                'token_obtained': bool(token_result.get('access_token')),
                'api_user': bool(PayClass.collections_apiuser),
                'api_key': bool(PayClass.api_key_collections),
                'environment': PayClass.environment_mode,
                'base_url': PayClass.accurl,
                'connectivity': connectivity_status,
                'connectivity_ok': connectivity_ok,
                'credentials': {
                    'subkey_configured': bool(PayClass.collections_subkey),
                    'api_user_id': PayClass.collections_apiuser[:8] + '...' if PayClass.collections_apiuser else None,
                    'basic_auth_configured': bool(PayClass.basic_authorisation_collections)
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'Payment Setup Diagnostics',
                'error': str(e),
                'error_type': type(e).__name__
            })
    else:
        return jsonify({'error': 'Test route only available in development mode'}), 403

# ============================================
# Email Routes for Admin
# ============================================

@app.route('/api/send-promotional-email', methods=['POST'])
def api_send_promotional_email():
    """API endpoint to send promotional emails to all users"""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if user is admin (you can add admin check here)
    data = request.get_json()
    
    try:
        subject = data.get('subject', 'Special Offer from CiTiPlug')
        promo_title = data.get('promo_title', 'Exclusive Offer')
        promo_description = data.get('promo_description', 'Check out our amazing products!')
        promo_code = data.get('promo_code')
        discount_percent = data.get('discount_percent')
        valid_until = data.get('valid_until')
        
        # Get all user emails
        cur = mysql.connection.cursor()
        cur.execute("SELECT email FROM users WHERE is_active = TRUE")
        users = cur.fetchall()
        cur.close()
        
        recipient_emails = [user[0] for user in users]
        
        if not recipient_emails:
            return jsonify({'error': 'No active users to send emails to'}), 400
        
        # Send promotional email
        success = send_promotional_email(
            recipient_emails,
            subject,
            promo_title,
            promo_description,
            promo_code,
            discount_percent,
            valid_until
        )
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Promotional email sent to {len(recipient_emails)} users',
                'recipients_count': len(recipient_emails)
            }), 200
        else:
            return jsonify({'error': 'Failed to send some emails'}), 500
            
    except Exception as e:
        print(f"[ERROR] Promotional email error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/send-order-status-email', methods=['POST'])
def api_send_order_status_email():
    """API endpoint to send order status update emails"""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    
    try:
        order_id = data.get('order_id')
        status = data.get('status')  # processing, shipped, delivered, cancelled
        tracking_info = data.get('tracking_info')
        
        # Get order and user info
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT o.user_id, u.email, u.first_name, u.last_name 
            FROM orders o 
            JOIN users u ON o.user_id = u.id 
            WHERE o.id = %s
        """, (order_id,))
        result = cur.fetchone()
        cur.close()
        
        if not result:
            return jsonify({'error': 'Order not found'}), 404
        
        user_id, email, first_name, last_name = result
        full_name = f"{first_name} {last_name}"
        
        # Send status email
        success = send_order_status_email(email, full_name, order_id, status, tracking_info)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Order status email sent to {email}'
            }), 200
        else:
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        print(f"[ERROR] Order status email error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/send-order-cancellation-email', methods=['POST'])
def api_send_order_cancellation_email():
    """API endpoint to send order cancellation emails"""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    
    try:
        order_id = data.get('order_id')
        reason = data.get('reason')
        
        # Get order and user info
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT o.user_id, u.email, u.first_name, u.last_name 
            FROM orders o 
            JOIN users u ON o.user_id = u.id 
            WHERE o.id = %s
        """, (order_id,))
        result = cur.fetchone()
        cur.close()
        
        if not result:
            return jsonify({'error': 'Order not found'}), 404
        
        user_id, email, first_name, last_name = result
        full_name = f"{first_name} {last_name}"
        
        # Send cancellation email
        success = send_order_cancellation_email(email, full_name, order_id, reason)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Cancellation email sent to {email}'
            }), 200
        else:
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        print(f"[ERROR] Order cancellation email error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/send-admin-notification', methods=['POST'])
def api_send_admin_notification():
    """API endpoint to send admin notification when order is placed"""
    data = request.get_json()
    
    try:
        admin_email = os.environ.get('ADMIN_EMAIL', 'ndwyfrank5@gmail.com')
        order_id = data.get('order_id')
        customer_name = data.get('customer_name')
        customer_email = data.get('customer_email')
        total_amount = data.get('total_amount')
        items_count = data.get('items_count')
        
        # Send admin notification
        success = send_admin_notification_email(
            admin_email,
            order_id,
            customer_name,
            customer_email,
            total_amount,
            items_count
        )
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Admin notification sent to {admin_email}'
            }), 200
        else:
            return jsonify({'error': 'Failed to send email'}), 500
            
    except Exception as e:
        print(f"[ERROR] Admin notification email error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================
# WhatsApp Routes (Link Generator)
# ============================================

@app.route('/api/whatsapp-link', methods=['POST'])
def api_whatsapp_link():
    """API endpoint to generate WhatsApp link"""
    data = request.get_json()
    
    try:
        phone_number = data.get('phone_number')
        message_text = data.get('message')
        
        if not phone_number or not message_text:
            return jsonify({'error': 'Phone number and message required'}), 400
        
        # Generate link
        whatsapp_link = generate_whatsapp_link(phone_number, message_text)
        
        return jsonify({
            'status': 'success',
            'link': whatsapp_link,
            'message': 'Click the link to send message via WhatsApp'
        }), 200
            
    except Exception as e:
        print(f"[ERROR] WhatsApp link error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/whatsapp-otp-link', methods=['POST'])
def api_whatsapp_otp_link():
    """API endpoint to generate WhatsApp OTP link"""
    data = request.get_json()
    
    try:
        phone_number = data.get('phone_number')
        otp_code = data.get('otp_code')
        
        if not phone_number or not otp_code:
            return jsonify({'error': 'Phone number and OTP required'}), 400
        
        message = f'Your OTP is: {otp_code}\n\nDo not share this code with anyone.'
        whatsapp_link = generate_whatsapp_link(phone_number, message)
        
        return jsonify({
            'status': 'success',
            'link': whatsapp_link,
            'message': 'Click the link to send OTP via WhatsApp'
        }), 200
            
    except Exception as e:
        print(f"[ERROR] WhatsApp OTP link error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/whatsapp-order-link', methods=['POST'])
def api_whatsapp_order_link():
    """API endpoint to generate WhatsApp order notification link"""
    data = request.get_json()
    
    try:
        phone_number = data.get('phone_number')
        order_id = data.get('order_id')
        customer_name = data.get('customer_name')
        total_amount = data.get('total_amount')
        
        if not phone_number or not order_id:
            return jsonify({'error': 'Phone number and order ID required'}), 400
        
        message = f"""Hi {customer_name}! 👋

Your order #{order_id} has been confirmed! 🎉

Total Amount: RWF {total_amount:,.0f}

You'll receive updates about your order soon.

Thank you for shopping with CiTiPlug! 🛍️"""
        
        whatsapp_link = generate_whatsapp_link(phone_number, message)
        
        return jsonify({
            'status': 'success',
            'link': whatsapp_link,
            'message': 'Click the link to send order notification via WhatsApp'
        }), 200
            
    except Exception as e:
        print(f"[ERROR] WhatsApp order link error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)