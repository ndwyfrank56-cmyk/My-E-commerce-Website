# Railway MySQL Database Setup Guide

## Overview
This guide walks you through setting up your e-commerce database on Railway MySQL.

## Your Connection Details
From the Railway dashboard, you have:
- **Host:** `nozomi.proxy.rlwy.net`
- **Port:** `26283`
- **User:** `root`
- **Password:** `sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu`
- **Database:** `railway`

## Method 1: Using MySQL Workbench (Recommended - GUI)

### Prerequisites
- MySQL Workbench installed on your computer

### Quick Steps
1. **Open MySQL Workbench**
2. **Click +** next to "MySQL Connections"
3. **Fill in connection details:**
   - Connection Name: `Railway Production`
   - Hostname: `nozomi.proxy.rlwy.net`
   - Port: `26283`
   - Username: `root`
   - Password: Click "Store in Vault" → `sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu`
   - Default Schema: `railway`
4. **Click "Test Connection"** → OK → OK
5. **Double-click "Railway Production"** to connect
6. **File → Open SQL Script** → Select `init_railway_db_complete.sql`
7. **Click Execute** (⚡ lightning bolt) or **Ctrl+Shift+Enter**
8. **Wait for completion** - watch the Output panel
9. **Right-click Tables → Refresh** to verify all 16 tables created
10. **Done! ✓**

### Detailed Guide
For step-by-step screenshots and troubleshooting, see: **MYSQL_WORKBENCH_GUIDE.md**

### Checklist
For a complete checklist, see: **WORKBENCH_CHECKLIST.txt**

---

## Method 2: Using Python Script

### Prerequisites
```bash
pip install mysql-connector-python
```

### Steps
1. Open PowerShell in your project directory
2. Run the setup script:
```bash
python setup_railway_db.py
```

3. When prompted, enter your Railway credentials:
   - Host: `nozomi.proxy.rlwy.net`
   - Port: `26283`
   - User: `root`
   - Password: `sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu`
   - Database: `railway`

4. The script will create all necessary tables and verify the setup

### Or use environment variables:
```bash
$env:MYSQL_HOST="nozomi.proxy.rlwy.net"
$env:MYSQL_PORT="26283"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu"
$env:MYSQL_DB="railway"
python setup_railway_db.py
```

---

## Method 3: Using MySQL Command Line

### Step 1: Connect via Command Line
```bash
mysql -h nozomi.proxy.rlwy.net -u root -p --port 26283 railway
```

When prompted for password, enter: `sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu`

### Step 2: Execute SQL Script
```sql
source init_railway_db.sql
```

Or copy-paste the entire content of `init_railway_db.sql` into the MySQL prompt.

### Step 3: Verify Tables
```sql
SHOW TABLES;
```

You should see:
```
+-------------------+
| Tables_in_railway |
+-------------------+
| categories        |
| order_items       |
| orders            |
| password_resets   |
| payments          |
| products          |
| users             |
| wishlist          |
+-------------------+
```

---

## Method 4: Using Railway Web Console

### Step 1: Access Railway Dashboard
1. Go to [railway.app](https://railway.app)
2. Log in to your account
3. Navigate to your project
4. Click on the **MySQL** service

### Step 2: Access Database Console
1. Click on the **Data** tab
2. Click **Connect** button
3. This opens a web-based SQL editor

### Step 3: Run SQL Script
1. Copy the entire content of `init_railway_db.sql`
2. Paste it into the Railway SQL editor
3. Click **Execute** or **Run**
4. All tables will be created

---

## Update Your .env File

After successful setup, update your `.env` file:

```env
MYSQL_HOST=nozomi.proxy.rlwy.net
MYSQL_PORT=26283
MYSQL_USER=root
MYSQL_PASSWORD=sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu
MYSQL_DB=railway
```

---

## Verify Connection in Flask

Your Flask app will automatically create tables on startup via the `ensure_db_initialized()` function. However, it's better to pre-create them using this guide.

To test the connection:
```python
from flask_mysqldb import MySQL
import os

app.config['MYSQL_HOST'] = 'nozomi.proxy.rlwy.net'
app.config['MYSQL_PORT'] = 26283
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu'
app.config['MYSQL_DB'] = 'railway'

mysql = MySQL(app)

try:
    cur = mysql.connection.cursor()
    cur.execute("SHOW TABLES")
    tables = cur.fetchall()
    print(f"Connected! Found {len(tables)} tables")
    cur.close()
except Exception as e:
    print(f"Connection failed: {e}")
```

---

## Tables Created

### 1. **users**
- User accounts with authentication
- OAuth support (Google login)
- Account locking after failed attempts

### 2. **categories**
- Product categories

### 3. **products**
- Product listings with pricing, stock, and discounts

### 4. **orders**
- Customer orders with delivery information
- Support for MoMo and COD payment methods

### 5. **order_items**
- Individual items in each order

### 6. **payments**
- Payment transaction logs
- MoMo transaction tracking

### 7. **wishlist**
- User wishlist items

### 8. **password_resets**
- Password reset tokens and expiration

---

## Troubleshooting

### Connection Refused
- Check that Railway MySQL service is running
- Verify host and port are correct
- Ensure your IP is whitelisted (Railway usually allows all by default)

### Authentication Failed
- Double-check username and password
- Ensure no extra spaces in credentials
- Try copying directly from Railway dashboard

### Tables Already Exist
- The SQL script uses `CREATE TABLE IF NOT EXISTS`
- Existing tables won't be overwritten
- Safe to run multiple times

### Permission Denied
- Ensure the user has CREATE TABLE permissions
- The `root` user should have full permissions

---

## Next Steps

1. ✅ Create database tables (this guide)
2. Update `.env` with Railway credentials
3. Test Flask connection
4. Deploy your application to Railway
5. Monitor database in Railway dashboard

---

## Support

For Railway support: https://railway.app/support
For MySQL documentation: https://dev.mysql.com/doc/
