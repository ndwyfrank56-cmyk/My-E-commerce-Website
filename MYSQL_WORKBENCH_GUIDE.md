# MySQL Workbench Setup Guide - Railway

## Step-by-Step Instructions

### Step 1: Open MySQL Workbench
1. Launch MySQL Workbench on your computer
2. You should see the home screen with "MySQL Connections" section

### Step 2: Create New Connection
1. Look for the **+** button next to "MySQL Connections"
2. Click it to open "Setup New Connection" dialog

### Step 3: Fill Connection Details

In the "Setup New Connection" dialog, fill in:

| Field | Value |
|-------|-------|
| **Connection Name** | Railway Production |
| **Connection Method** | Standard (TCP/IP) |
| **Hostname** | nozomi.proxy.rlwy.net |
| **Port** | 26283 |
| **Username** | root |
| **Password** | sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu |
| **Default Schema** | railway |

### Step 4: Store Password Securely
1. Click the **"Store in Vault..."** button next to Password field
2. Enter password: `sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu`
3. Click OK

### Step 5: Test Connection
1. Click **"Test Connection"** button
2. Wait for confirmation message
3. If successful, you'll see: "Successfully made the MySQL connection"
4. Click **OK** to close the dialog
5. Click **OK** again to save the connection

### Step 6: Connect to Railway
1. In the MySQL Connections section, you should now see "Railway Production"
2. **Double-click** on "Railway Production" to open the connection
3. Wait for it to connect (you'll see the connection open in a new tab)

### Step 7: Open SQL Script
1. Go to **File** menu → **Open SQL Script**
2. Navigate to your project folder: `c:\Users\Public\Ecommerce website\`
3. Select **`init_railway_db_complete.sql`** (this has all 16 tables)
4. Click **Open**

### Step 8: Execute SQL Script
1. The SQL script will open in a new tab
2. You should see all the CREATE TABLE statements
3. Click the **Execute** button (lightning bolt icon ⚡) in the toolbar
4. Or press **Ctrl + Shift + Enter**

### Step 9: Monitor Execution
1. Watch the "Output" panel at the bottom
2. You should see messages like:
   ```
   [OK] users table created
   [OK] categories table created
   [OK] products table created
   ...
   ```
3. Wait until all statements complete

### Step 10: Verify Tables Created
1. In the left panel, expand your connection
2. Right-click on **"Tables"** and select **"Refresh"**
3. You should see all 16 tables:
   - banners
   - categories
   - dropdown_variation
   - image_variations
   - low_stock_alerts
   - order_items
   - orders
   - password_resets
   - payments
   - products
   - reviews
   - users
   - wishlist
   - worker_login
   - worker_page_permissions
   - workers

### Step 11: Done! ✓
Your Railway MySQL database is now fully set up with all tables!

---

## Troubleshooting

### Connection Failed
**Error:** "Could not connect to the target MySQL Server"

**Solutions:**
1. Verify hostname: `nozomi.proxy.rlwy.net`
2. Verify port: `26283`
3. Check username: `root`
4. Check password: `sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu`
5. Ensure no extra spaces in credentials
6. Check your internet connection

### Authentication Failed
**Error:** "Access denied for user 'root'@..."

**Solutions:**
1. Double-check the password (case-sensitive)
2. Click "Clear" and re-enter password
3. Use "Store in Vault" to save password securely

### Tables Not Showing
**Error:** Tables don't appear after execution

**Solutions:**
1. Right-click "Tables" → "Refresh"
2. Close and reopen the connection
3. Check the Output panel for errors
4. Look for red error messages in output

### Script Execution Error
**Error:** "Error executing SQL statement"

**Solutions:**
1. Check the Output panel for specific error
2. Ensure you selected `init_railway_db_complete.sql` (not the basic version)
3. Try executing line by line instead of all at once
4. Check if tables already exist (safe to run multiple times)

---

## What Gets Created

### Core Tables (10)
- **users** - User accounts with authentication
- **categories** - Product categories
- **products** - Product listings
- **image_variations** - Product colors/styles
- **dropdown_variation** - Product sizes/attributes
- **orders** - Customer orders
- **order_items** - Items in orders
- **payments** - Payment transactions
- **wishlist** - User wishlists
- **password_resets** - Password reset tokens

### Supporting Tables (6)
- **banners** - Promotional banners
- **low_stock_alerts** - Inventory alerts
- **reviews** - Product reviews
- **workers** - Staff information
- **worker_login** - Staff credentials
- **worker_page_permissions** - Staff access control

---

## Next Steps

1. ✅ Create database tables (completed)
2. Update `.env` file with Railway credentials:
   ```
   MYSQL_HOST=nozomi.proxy.rlwy.net
   MYSQL_PORT=26283
   MYSQL_USER=root
   MYSQL_PASSWORD=sbYYCDjoHzrDkxPIfmGIpHewbbkQTALu
   MYSQL_DB=railway
   ```
3. Test Flask connection to Railway
4. Deploy your application

---

## Tips

- **Bookmark the connection:** Right-click "Railway Production" → "Edit Connection" to modify later
- **Quick execute:** Use `Ctrl + Shift + Enter` to execute SQL
- **View table structure:** Right-click table → "Inspect Table" to see columns
- **Safe to re-run:** The script uses `CREATE TABLE IF NOT EXISTS`, so it's safe to run multiple times

---

## Support

- Railway Support: https://railway.app/support
- MySQL Workbench Docs: https://dev.mysql.com/doc/workbench/en/
