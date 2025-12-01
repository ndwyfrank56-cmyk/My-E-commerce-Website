# Railway MySQL Database Setup - Complete Package

## 🚀 Quick Start

**Recommended Method: MySQL Workbench**

1. Open MySQL Workbench
2. Create new connection with details below
3. Open `init_railway_db_complete.sql`
4. Click Execute
5. Done! ✓

**Connection Details:**
```
Host:     nozomi.proxy.rlwy.net
Port:     26283
User:     root
Password: sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu
Database: railway
```

---

## 📁 Files Included

### Setup Guides
| File | Purpose |
|------|---------|
| **SETUP_SUMMARY.txt** | 📋 Complete overview & quick reference |
| **MYSQL_WORKBENCH_GUIDE.md** | 📖 Detailed step-by-step guide for MySQL Workbench |
| **WORKBENCH_CHECKLIST.txt** | ✅ Interactive checklist to follow |
| **QUICK_RAILWAY_SETUP.txt** | ⚡ Quick reference card |
| **RAILWAY_SETUP_GUIDE.md** | 📚 Comprehensive guide with all 4 methods |

### SQL Files
| File | Purpose |
|------|---------|
| **init_railway_db_complete.sql** | 🎯 Complete schema (16 tables) - USE THIS |
| **init_railway_db.sql** | Basic schema (8 tables) - Backup option |

### Python Setup Script
| File | Purpose |
|------|---------|
| **setup_railway_db.py** | 🐍 Automated setup script (alternative to MySQL Workbench) |

### Documentation
| File | Purpose |
|------|---------|
| **DATABASE_SCHEMA.md** | 📊 Complete schema documentation |
| **README_SETUP.md** | 📖 This file |

---

## 🎯 Choose Your Setup Method

### Method 1: MySQL Workbench (Recommended) ⭐
**Best for:** Visual users who prefer GUI

**Time:** ~5 minutes

**Steps:**
1. Open MySQL Workbench
2. Click + to create connection
3. Enter connection details
4. Test Connection
5. Open `init_railway_db_complete.sql`
6. Click Execute
7. Verify tables created

**Guides:**
- `MYSQL_WORKBENCH_GUIDE.md` - Detailed steps
- `WORKBENCH_CHECKLIST.txt` - Step-by-step checklist

---

### Method 2: Python Script
**Best for:** Automated setup

**Time:** ~2 minutes

**Steps:**
```bash
python setup_railway_db.py
```

**Guides:**
- `RAILWAY_SETUP_GUIDE.md` - Method 2 section

---

### Method 3: Command Line
**Best for:** Terminal users

**Time:** ~3 minutes

**Steps:**
```bash
mysql -h nozomi.proxy.rlwy.net -u root -p --port 26283 railway
source init_railway_db_complete.sql
```

**Guides:**
- `RAILWAY_SETUP_GUIDE.md` - Method 3 section

---

### Method 4: Railway Web Console
**Best for:** No local tools needed

**Time:** ~5 minutes

**Steps:**
1. Go to railway.app
2. Navigate to MySQL service
3. Click Data → Connect
4. Paste SQL script
5. Execute

**Guides:**
- `RAILWAY_SETUP_GUIDE.md` - Method 4 section

---

## 📊 Database Schema

### 16 Tables Created

**Core Tables (10):**
- `users` - User accounts & authentication
- `categories` - Product categories
- `products` - Product listings
- `image_variations` - Product colors/styles
- `dropdown_variation` - Product sizes/attributes
- `orders` - Customer orders
- `order_items` - Items in orders
- `payments` - Payment transactions
- `wishlist` - User wishlists
- `password_resets` - Password reset tokens

**Supporting Tables (6):**
- `banners` - Promotional banners
- `low_stock_alerts` - Inventory alerts
- `reviews` - Product reviews
- `workers` - Staff information
- `worker_login` - Staff credentials
- `worker_page_permissions` - Staff access control

**Full Documentation:** See `DATABASE_SCHEMA.md`

---

## 🔧 Stock Management

The database includes automatic stock cascading:

```
dropdown_variation (e.g., size 40)
         ↓ (auto-cascade)
image_variations (e.g., brown color)
         ↓ (auto-cascade)
products (overall stock)
```

When an order is placed:
1. Stock deducted from `dropdown_variation`
2. Automatically cascades to `image_variations`
3. Automatically cascades to `products`

---

## ✅ Verification

After setup, verify all tables were created:

**In MySQL Workbench:**
1. Right-click "Tables" → Refresh
2. Expand "Tables" folder
3. Should see all 16 tables

**Via Command Line:**
```sql
SHOW TABLES;
```

**Expected Output:**
```
banners
categories
dropdown_variation
image_variations
low_stock_alerts
order_items
orders
password_resets
payments
products
reviews
users
wishlist
worker_login
worker_page_permissions
workers
```

---

## 🚨 Troubleshooting

### Connection Failed
- Check hostname: `nozomi.proxy.rlwy.net`
- Check port: `26283`
- Check username: `root`
- Check password: `sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu`
- Ensure no extra spaces

**See:** `MYSQL_WORKBENCH_GUIDE.md` - Troubleshooting section

### Authentication Failed
- Double-check password (case-sensitive)
- Use "Store in Vault" in MySQL Workbench
- Copy password directly from this file

### Tables Not Showing
- Right-click "Tables" → Refresh
- Close and reopen connection
- Check Output panel for errors

### Script Execution Error
- Check Output panel for specific error
- Ensure using `init_railway_db_complete.sql`
- Safe to run multiple times (uses IF NOT EXISTS)

---

## 📝 Next Steps

After successful setup:

1. ✅ Create database tables (this package)
2. Update `.env` file:
   ```env
   MYSQL_HOST=nozomi.proxy.rlwy.net
   MYSQL_PORT=26283
   MYSQL_USER=root
   MYSQL_PASSWORD=sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu
   MYSQL_DB=railway
   ```
3. Test Flask connection
4. Deploy to Railway
5. Monitor database

---

## 📚 Documentation Files

### For Quick Reference
- `SETUP_SUMMARY.txt` - Overview & quick reference
- `QUICK_RAILWAY_SETUP.txt` - Quick reference card

### For Detailed Setup
- `MYSQL_WORKBENCH_GUIDE.md` - Step-by-step with screenshots
- `WORKBENCH_CHECKLIST.txt` - Interactive checklist
- `RAILWAY_SETUP_GUIDE.md` - All 4 methods

### For Understanding Schema
- `DATABASE_SCHEMA.md` - Complete documentation

---

## 🎓 Learning Resources

- **Railway Support:** https://railway.app/support
- **MySQL Documentation:** https://dev.mysql.com/doc/
- **MySQL Workbench:** https://dev.mysql.com/doc/workbench/en/

---

## ✨ Features

✓ Product variations (colors/styles with sizes)
✓ Automatic stock cascading
✓ MoMo & COD payment support
✓ Location tracking for orders
✓ Staff management & permissions
✓ Low stock alerts
✓ Product reviews & ratings
✓ Wishlist functionality
✓ OAuth support (Google login)
✓ Account security (failed login tracking)

---

## 💡 Tips

- **Safe to re-run:** All scripts use `CREATE TABLE IF NOT EXISTS`
- **Bookmark connection:** Save Railway connection in MySQL Workbench for future use
- **Quick execute:** Use `Ctrl+Shift+Enter` in MySQL Workbench
- **View structure:** Right-click table → "Inspect Table" to see columns

---

**Ready to set up? Start with `MYSQL_WORKBENCH_GUIDE.md` or `WORKBENCH_CHECKLIST.txt`!**
