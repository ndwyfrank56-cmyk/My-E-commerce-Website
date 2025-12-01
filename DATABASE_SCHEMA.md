# Complete Database Schema

## Overview
Your e-commerce application uses 16 tables organized into core and supporting modules.

## Core Tables (Essential for Operations)

### 1. **users**
- User accounts and authentication
- OAuth support (Google login)
- Account locking after failed login attempts
- Discount tracking

**Key Columns:**
- `id` - Primary key
- `username`, `email` - Unique identifiers
- `password_hash` - Bcrypt hashed password
- `first_name`, `last_name`, `phone`, `city`, `address` - User info
- `oauth_provider`, `oauth_id` - For Google login
- `failed_login_attempts`, `locked_until` - Security
- `discounts` - User discount percentage

---

### 2. **categories**
- Product categories (clothes, shoes, perfumes, jewelry, belts, watches)

**Key Columns:**
- `id` - Primary key
- `name` - Category name

---

### 3. **products**
- Product listings with pricing and inventory
- Supports product variations (colors, styles, sizes)

**Key Columns:**
- `id` - Primary key
- `name`, `price`, `image` - Basic product info
- `category_id` - Foreign key to categories
- `stock` - Current stock (auto-calculated from variations)
- `description`, `discount` - Product details
- `rate`, `cost_of_goods` - Analytics
- `has_variations` - Flag for products with variations

---

### 4. **image_variations**
- Product color/style variations (e.g., "brown", "military blue")
- Each variation has its own image and stock

**Key Columns:**
- `id` - Primary key
- `prod_id` - Foreign key to products
- `type` - ENUM('color', 'style')
- `name` - Variation name (e.g., "brown")
- `stock` - Stock for this variation
- `img_url` - Image URL for this variation

**Stock Hierarchy:**
- Image variation stock = sum of all dropdown variations linked to it
- Product stock = sum of all image variations

---

### 5. **dropdown_variation**
- Product attributes like sizes (40, 41, 42, etc.)
- Linked to image variations for granular stock control

**Key Columns:**
- `id` - Primary key
- `prod_id` - Foreign key to products
- `attr_name` - Attribute name (e.g., "size")
- `attr_value` - Attribute value (e.g., "40")
- `stock` - Stock for this specific combination
- `img_var_id` - Foreign key to image_variations

**Example:**
```
Product: Jordan 4 Brown
├── Image Variation: brown (style)
│   ├── Dropdown: size 40 (stock: 10)
│   ├── Dropdown: size 41 (stock: 21)
│   └── Dropdown: size 42 (stock: 10)
├── Image Variation: military blue (style)
│   ├── Dropdown: size 40 (stock: 5)
│   └── Dropdown: size 41 (stock: 21)
```

---

### 6. **orders**
- Customer orders with delivery information
- Supports MoMo and COD payment methods
- Location tracking (latitude/longitude)

**Key Columns:**
- `id` - Primary key
- `user_id` - Foreign key to users (NULL for guest orders)
- `guest_email` - Email for guest checkouts
- `full_name`, `address_line`, `city`, `delivery_phone` - Delivery info
- `provider` - Payment provider (mtn, COD, NONE)
- `momo_number` - MoMo phone number
- `latitude`, `longitude` - Delivery location
- `total_amount` - Order total
- `status` - Order status (pending, paid, cancelled)
- `momo_transaction_id` - MoMo transaction reference
- `delivered` - Delivery status (YES/NO)
- `payment_status` - Payment status (pending, paid, cancelled)

---

### 7. **order_items**
- Individual items in each order
- Stores product variations at time of purchase

**Key Columns:**
- `id` - Primary key
- `order_id` - Foreign key to orders
- `product_id` - Foreign key to products
- `product_name`, `price`, `quantity`, `subtotal` - Item details
- `VARIATIONS` - Variation string (e.g., "style:brown, size:40")

---

### 8. **payments**
- Payment transaction logs
- MoMo transaction tracking

**Key Columns:**
- `id` - Primary key
- `order_id` - Foreign key to orders
- `momo_transaction_id` - MoMo transaction ID
- `amount`, `currency` - Payment amount
- `status` - Payment status (SUCCESSFUL, FAILED, PENDING)
- `provider` - Payment provider (mtn)
- `payer_number` - Payer phone number
- `raw_response` - Full API response (JSON)

---

### 9. **wishlist**
- User wishlist items

**Key Columns:**
- `id` - Primary key
- `user_id` - Foreign key to users
- `product_id` - Foreign key to products
- `added_at` - Timestamp

---

### 10. **password_resets**
- Password reset tokens and expiration

**Key Columns:**
- `id` - Primary key
- `user_id` - Foreign key to users
- `email` - User email
- `reset_code` - Unique reset token
- `used` - Whether token was used
- `expires_at` - Token expiration time

---

## Supporting Tables

### 11. **banners**
- Homepage banners/promotional images

**Key Columns:**
- `baner_id` - Primary key
- `baner_name` - Banner name
- `banner_image` - Image URL

---

### 12. **low_stock_alerts**
- Automatic alerts for low stock products/variations

**Key Columns:**
- `id` - Primary key
- `product_id` - Foreign key to products
- `variation_type` - Type (dropdown, image, product)
- `variation_id` - ID of the variation
- `variation_name` - Name of variation
- `current_stock` - Current stock level
- `threshold` - Alert threshold (default: 5)
- `resolved` - Whether alert is resolved

---

### 13. **reviews**
- Product reviews and ratings

**Key Columns:**
- `id` - Primary key
- `user_id` - Foreign key to users
- `product_id` - Foreign key to products
- `rating` - Rating (1-5)
- `review` - Review text
- `replie` - Admin reply

---

### 14. **workers**
- Staff/employee information

**Key Columns:**
- `worker_id` - Primary key
- `name`, `phone`, `email` - Contact info
- `salary` - Salary amount
- `profession` - Job title
- `deptName` - Department name

---

### 15. **worker_login**
- Staff login credentials

**Key Columns:**
- `login_id` - Primary key
- `worker_id` - Foreign key to workers
- `username` - Login username
- `password` - Hashed password

---

### 16. **worker_page_permissions**
- Staff access control

**Key Columns:**
- `id` - Primary key
- `worker_id` - Foreign key to workers
- `pages` - Page name (dashboard, orders, products, reviews, customers, workers, reports)

---

## Stock Deduction Logic

When an order is placed:

1. **If product has dropdown variations:**
   - Deduct from `dropdown_variation.stock`
   - Trigger cascades: dropdown → image_variation → product

2. **Else if product has image variations:**
   - Deduct from `image_variation.stock`
   - Trigger cascades: image_variation → product

3. **Else:**
   - Deduct from `products.stock` directly

---

## Database Triggers

The database includes automatic triggers for:

- **Stock cascading:** Automatically update parent stock levels
- **Stock validation:** Prevent negative stock
- **Low stock alerts:** Trigger alerts when stock ≤ 5
- **Variation linking:** Ensure dropdowns are linked to image variations

---

## Relationships

```
users
├── orders (1:N)
│   ├── order_items (1:N)
│   └── payments (1:N)
├── wishlist (1:N)
├── reviews (1:N)
└── password_resets (1:N)

categories
└── products (1:N)

products
├── image_variations (1:N)
│   └── dropdown_variation (1:N)
├── order_items (1:N)
├── reviews (1:N)
├── wishlist (1:N)
└── low_stock_alerts (1:N)

workers
├── worker_login (1:1)
└── worker_page_permissions (1:N)
```

---

## Indexes for Performance

- `users`: email, username
- `products`: category_id
- `image_variations`: prod_id
- `dropdown_variation`: prod_id, img_var_id
- `orders`: user_id, status, created_at, momo_transaction_id
- `order_items`: order_id
- `payments`: order_id, momo_transaction_id
- `wishlist`: user_id
- `low_stock_alerts`: product_id, resolved
- `reviews`: user_id, product_id
- `worker_login`: worker_id
- `worker_page_permissions`: worker_id

---

## Setup Instructions

Run the setup script:
```bash
python setup_railway_db.py
```

Or manually execute:
```bash
mysql -h nozomi.proxy.rlwy.net -u root -p --port 26283 railway < init_railway_db_complete.sql
```
