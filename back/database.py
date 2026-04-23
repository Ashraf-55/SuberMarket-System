import sqlite3
import os
from datetime import datetime

# 1. تحديد المسارات والتهيئة التلقائية
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')
DB_PATH = os.path.join(DB_DIR, 'supermarket.db')

def get_connection():
    """فتح اتصال مع قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def upgrade_sales_table():
    """ترقية جدول sales لإضافة الأعمدة المطلوبة للبيع الآجل"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(sales)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'paid_amount' not in columns:
            cursor.execute("ALTER TABLE sales ADD COLUMN paid_amount REAL DEFAULT 0")
        
        if 'status' not in columns:
            cursor.execute("ALTER TABLE sales ADD COLUMN status TEXT DEFAULT 'مكتمل'")
        
        if 'payment_method' not in columns:
            cursor.execute("ALTER TABLE sales ADD COLUMN payment_method TEXT DEFAULT 'نقدي'")
        
        # إضافة عمود return_status إذا لم يكن موجوداً
        # 0 = لم يتم, 1 = مرتجع جزئي, 2 = مرتجع كلي
        if 'return_status' not in columns:
            cursor.execute("ALTER TABLE sales ADD COLUMN return_status INTEGER DEFAULT 0")
        
        # إضافة عمود sale_type (نوع الفاتورة)
        if 'sale_type' not in columns:
            cursor.execute("ALTER TABLE sales ADD COLUMN sale_type TEXT DEFAULT 'نقدي'")
        
        conn.commit()
    except Exception as e:
        print(f"خطأ في ترقية الجدول: {e}")
    finally:
        conn.close()

def initialize_system():
    """إنشاء الفولدر والجداول لو مش موجودة"""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            barcode TEXT UNIQUE NOT NULL,
            purchase_price REAL DEFAULT 0,
            sell_price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            category TEXT DEFAULT 'عام'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            paid_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'مكتمل',
            payment_method TEXT DEFAULT 'نقدي',
            return_status INTEGER DEFAULT 0,
            sale_type TEXT DEFAULT 'نقدي',
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price_at_sale REAL,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'cashier'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            amount REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            remaining_amount REAL NOT NULL,
            debt_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date TIMESTAMP,
            status TEXT DEFAULT 'مستحق',
            notes TEXT,
            sale_id INTEGER,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE SET NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_id INTEGER,
            payment_amount REAL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT DEFAULT 'نقدي',
            notes TEXT,
            FOREIGN KEY(debt_id) REFERENCES debts(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS damaged_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            quantity_unit TEXT DEFAULT 'قطعة',
            damage_reason TEXT,
            loss_amount REAL,
            damage_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'قيد المراجعة',
            reported_by TEXT,
            notes TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transfer_number TEXT UNIQUE NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            from_warehouse TEXT NOT NULL,
            to_warehouse TEXT NOT NULL,
            transfer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transfer_reason TEXT,
            status TEXT DEFAULT 'مكتمل',
            transferred_by TEXT,
            notes TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            return_number TEXT UNIQUE NOT NULL,
            return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_return_amount REAL NOT NULL,
            return_reason TEXT,
            status TEXT DEFAULT 'مكتمل',
            processed_by TEXT,
            notes TEXT,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_return_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            return_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            return_price REAL,
            FOREIGN KEY(return_id) REFERENCES sales_returns(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            return_number TEXT UNIQUE NOT NULL,
            supplier_name TEXT NOT NULL,
            return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_return_amount REAL NOT NULL,
            return_reason TEXT,
            status TEXT DEFAULT 'مكتمل',
            processed_by TEXT,
            notes TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_return_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            return_id INTEGER,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER,
            return_price REAL,
            FOREIGN KEY(return_id) REFERENCES purchase_returns(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')

    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                      ('admin', 'admin123', 'admin'))
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                      ('cashier', 'cashier123', 'cashier'))

    conn.commit()
    conn.close()
    
    upgrade_sales_table()

def add_product(name, barcode, purchase, sell, stock, category="عام"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, barcode, purchase_price, sell_price, stock, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, barcode, float(purchase), float(sell), int(stock), category))
        conn.commit()
        conn.close()
        return True, "تمت الإضافة"
    except sqlite3.IntegrityError:
        return False, "الباركود ده موجود قبل كدة!"
    except Exception as e:
        return False, str(e)

def get_all_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product

def update_product(p_id, name, barcode, purchase, sell, stock, category):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products 
            SET name=?, barcode=?, purchase_price=?, sell_price=?, stock=?, category=?
            WHERE id=?
        ''', (name, barcode, float(purchase), float(sell), int(stock), category, p_id))
        conn.commit()
        conn.close()
        return True, "تم التعديل بنجاح"
    except Exception as e:
        return False, str(e)

def delete_product(product_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        if not cursor.fetchone():
            return False, "المنتج غير موجود"
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        return True, "تم حذف المنتج بنجاح"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def get_product_by_barcode(barcode):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE barcode = ?", (barcode,))
    product = cursor.fetchone()
    conn.close()
    return product

def search_products(text):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM products WHERE name LIKE ? OR barcode = ?"
    cursor.execute(query, (f'%{text}%', text))
    results = cursor.fetchall()
    conn.close()
    return results

def login_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

def make_sale(items_list, total_amount, discount=0, payment_method='نقدي', customer_name=None):
    """تسجيل عملية بيع جديدة مع دعم البيع النقدي والآجل"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        if payment_method == 'آجل':
            paid_amount = 0.0
            status = 'آجل'
            sale_type = 'آجل'
        else:
            paid_amount = float(total_amount)
            status = 'مكتمل'
            sale_type = 'نقدي'
        
        cursor.execute('''
            INSERT INTO sales (total_amount, discount, paid_amount, status, payment_method, return_status, sale_type) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (float(total_amount), float(discount), paid_amount, status, payment_method, 0, sale_type))
        
        sale_id = cursor.lastrowid
        
        for p_id, qty, price in items_list:
            cursor.execute('''
                INSERT INTO sale_items (sale_id, product_id, quantity, price_at_sale) 
                VALUES (?, ?, ?, ?)
            ''', (sale_id, int(p_id), int(qty), float(price)))
            cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (int(qty), int(p_id)))
        
        if payment_method == 'آجل' and customer_name:
            if not customer_name or not customer_name.strip():
                raise ValueError("اسم العميل مطلوب للبيع الآجل")
            
            remaining_amount = float(total_amount)
            
            cursor.execute('''
                INSERT INTO debts (
                    customer_name, amount, paid_amount, remaining_amount, 
                    sale_id, status, debt_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?)
            ''', (
                customer_name.strip(), float(total_amount), 0.0, remaining_amount,
                sale_id, 'مستحق', f'فاتورة آجلة رقم {sale_id}'
            ))
        
        conn.commit()
        return True, sale_id
        
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def get_today_cash_sales():
    """إجمالي المبيعات النقدية اليوم فقط"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total_amount) FROM sales WHERE date(sale_date) = date('now') AND payment_method='نقدي'")
    total = cursor.fetchone()[0]
    conn.close()
    return float(total) if total else 0

def get_today_deferred_sales():
    """إجمالي المبيعات الآجلة اليوم (اللي لسه متحصلش)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total_amount) FROM sales WHERE date(sale_date) = date('now') AND payment_method='آجل'")
    total = cursor.fetchone()[0]
    conn.close()
    return float(total) if total else 0

def get_all_sales():
    """جلب جميع المبيعات مع طريقة الدفع وحالة المرتجع"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.total_amount, s.discount, s.paid_amount, s.status, s.payment_method, s.return_status, s.sale_type,
               strftime('%Y-%m-%d %H:%M:%S', s.sale_date) as sale_date,
               d.customer_name
        FROM sales s
        LEFT JOIN debts d ON s.id = d.sale_id
        ORDER BY s.id DESC
    ''')
    sales = cursor.fetchall()
    conn.close()
    return sales

def get_cash_sales():
    """جلب المبيعات النقدية فقط"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.total_amount, s.discount, s.paid_amount, s.status, s.payment_method, s.return_status, s.sale_type,
               strftime('%Y-%m-%d %H:%M:%S', s.sale_date) as sale_date
        FROM sales s
        WHERE s.payment_method = 'نقدي'
        ORDER BY s.id DESC
    ''')
    sales = cursor.fetchall()
    conn.close()
    return sales

def get_deferred_sales():
    """جلب المبيعات الآجلة فقط مع اسم العميل"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.total_amount, s.discount, s.paid_amount, s.status, s.payment_method, s.return_status, s.sale_type,
               strftime('%Y-%m-%d %H:%M:%S', s.sale_date) as sale_date,
               d.customer_name, d.remaining_amount, d.status as debt_status
        FROM sales s
        JOIN debts d ON s.id = d.sale_id
        WHERE s.payment_method = 'آجل'
        ORDER BY s.id DESC
    ''')
    sales = cursor.fetchall()
    conn.close()
    return sales

def get_returned_sales():
    """جلب الفواتير التي تم إرجاعها (للعرض في سجل الفواتير)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.id, s.total_amount, s.discount, s.paid_amount, s.status, s.payment_method, s.return_status, s.sale_type,
               strftime('%Y-%m-%d %H:%M:%S', s.sale_date) as sale_date,
               d.customer_name
        FROM sales s
        LEFT JOIN debts d ON s.id = d.sale_id
        WHERE s.sale_type = 'مرتجع'
        ORDER BY s.id DESC
    ''')
    sales = cursor.fetchall()
    conn.close()
    return sales

def get_sale_details(sale_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT si.product_id, p.name, si.quantity, si.price_at_sale, 
               s.total_amount, s.discount, s.return_status, s.sale_type
        FROM sale_items si
        JOIN products p ON si.product_id = p.id
        JOIN sales s ON si.sale_id = s.id
        WHERE si.sale_id = ?
    ''', (sale_id,))
    details = cursor.fetchall()
    conn.close()
    
    converted_details = []
    for d in details:
        product_name = str(d[1])
        remaining_quantity = int(d[2]) if d[2] else 0
        price_at_sale = float(d[3]) if d[3] else 0
        total_amount = float(d[4]) if d[4] else 0
        discount = float(d[5]) if d[5] else 0
        return_status = int(d[6]) if d[6] else 0
        sale_type = str(d[7]) if len(d) > 7 else ''
        
        converted_details.append((sale_id, product_name, remaining_quantity, price_at_sale, total_amount, discount, return_status, sale_type))
    
    return converted_details

def delete_sale(sale_id):
    """
    حذف فاتورة مع جميع بياناتها المرتبطة (بما في ذلك المرتجعات)
    
    Args:
        sale_id (int): رقم الفاتورة المراد حذفها
    
    Returns:
        tuple: (success, message)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        # 1. جلب عناصر الفاتورة لمعرفة المنتجات والكميات
        cursor.execute('SELECT product_id, quantity FROM sale_items WHERE sale_id = ?', (sale_id,))
        current_items = cursor.fetchall()
        
        if not current_items:
            conn.rollback()
            conn.close()
            return (False, "الفاتورة غير موجودة")
        
        # 2. معرفة نوع الفاتورة (مرتجع أم لا)
        cursor.execute('SELECT sale_type FROM sales WHERE id = ?', (sale_id,))
        sale_data = cursor.fetchone()
        sale_type = sale_data['sale_type'] if sale_data else 'نقدي'
        
        # 3. إذا كانت الفاتورة مرتجع، لا نعيد الكميات للمخزن (لأنها مضافة بالفعل عند المرتجع)
        if sale_type != 'مرتجع':
            for product_id, remaining_qty in current_items:
                if remaining_qty > 0:
                    cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (remaining_qty, product_id))
        
        # 4. حذف عناصر المرتجعات المرتبطة بهذه الفاتورة (بما فيها عناصر المرتجع)
        cursor.execute('''
            DELETE FROM sales_return_items 
            WHERE return_id IN (SELECT id FROM sales_returns WHERE sale_id = ?)
        ''', (sale_id,))
        
        # 5. حذف سجلات المرتجعات
        cursor.execute('DELETE FROM sales_returns WHERE sale_id = ?', (sale_id,))
        
        # 6. حذف عناصر الفاتورة
        cursor.execute('DELETE FROM sale_items WHERE sale_id = ?', (sale_id,))
        
        # 7. حذف الديون المرتبطة بالفاتورة (إذا وجدت)
        cursor.execute('DELETE FROM debt_payments WHERE debt_id IN (SELECT id FROM debts WHERE sale_id = ?)', (sale_id,))
        cursor.execute('DELETE FROM debts WHERE sale_id = ?', (sale_id,))
        
        # 8. حذف الفاتورة نفسها
        cursor.execute('DELETE FROM sales WHERE id = ?', (sale_id,))
        
        conn.commit()
        conn.close()
        return (True, f"تم حذف الفاتورة رقم {sale_id} بنجاح")
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return (False, f"خطأ في حذف الفاتورة: {str(e)}")

def process_sales_return(sale_id, return_items_list, return_reason="", processed_by=""):
    """
    معالجة مرتجع مبيعات وتحديث المخزون وحالة الفاتورة
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        # 1. جلب بيانات الفاتورة
        cursor.execute('SELECT total_amount, return_status, payment_method, sale_type FROM sales WHERE id = ?', (sale_id,))
        sale_data = cursor.fetchone()
        if not sale_data:
            conn.rollback()
            return False, f"الفاتورة رقم {sale_id} غير موجودة"
        
        current_total = sale_data['total_amount']
        current_return_status = sale_data['return_status'] if sale_data['return_status'] else 0
        
        # التحقق إذا كان المرتجع قد تم مسبقاً
        if current_return_status == 2:
            conn.rollback()
            return False, "هذه الفاتورة تم إرجاعها بالكامل مسبقاً"
        
        # 2. جلب بيانات عناصر الفاتورة الحالية
        cursor.execute('SELECT id, product_id, quantity, price_at_sale FROM sale_items WHERE sale_id = ?', (sale_id,))
        sale_items_data = cursor.fetchall()
        
        if not sale_items_data:
            conn.rollback()
            return False, "لا توجد منتجات في هذه الفاتورة"
        
        # تخزين البيانات في قاموس
        current_items_dict = {}
        for item in sale_items_data:
            current_items_dict[item['product_id']] = {
                'sale_item_id': item['id'],
                'quantity': item['quantity'],
                'price': item['price_at_sale']
            }
        
        # 3. معالجة العناصر المرتجعة
        processed_returns = []
        total_return_amount = 0.0
        
        for item in return_items_list:
            if isinstance(item, (tuple, list)):
                product_id = int(item[0])
                return_qty = int(float(item[1]))
                return_price = float(item[2]) if len(item) > 2 else 0
            elif isinstance(item, dict):
                product_id = int(item['product_id'])
                return_qty = int(float(item['quantity']))
                return_price = float(item.get('price', 0))
            else:
                continue
            
            if product_id not in current_items_dict:
                conn.rollback()
                return False, f"المنتج {product_id} غير موجود في الفاتورة"
            
            current_qty = current_items_dict[product_id]['quantity']
            current_price = current_items_dict[product_id]['price']
            
            if return_price == 0:
                return_price = current_price
            
            if return_qty > current_qty:
                conn.rollback()
                return False, f"لا يمكن إرجاع {return_qty} من المنتج، الكمية المتبقية: {current_qty}"
            
            if return_qty <= 0:
                conn.rollback()
                return False, f"الكمية المرتجعة يجب أن تكون أكبر من صفر"
            
            processed_returns.append({
                'product_id': product_id,
                'sale_item_id': current_items_dict[product_id]['sale_item_id'],
                'current_qty': current_qty,
                'return_qty': return_qty,
                'return_price': return_price,
                'new_qty': current_qty - return_qty
            })
            
            total_return_amount += return_qty * return_price
        
        if not processed_returns:
            conn.rollback()
            return False, "لا توجد منتجات صالحة للمرتجع"
        
        # 4. إدراج سجل المرتجع
        return_number = f"RET-{sale_id}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        cursor.execute('''
            INSERT INTO sales_returns (sale_id, return_number, total_return_amount, return_reason, processed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (sale_id, return_number, total_return_amount, return_reason, processed_by))
        return_id = cursor.lastrowid
        
        # 5. تحديث الكميات في sale_items
        for ret in processed_returns:
            cursor.execute('UPDATE sale_items SET quantity = ? WHERE id = ?', (ret['new_qty'], ret['sale_item_id']))
        
        # 6. حساب المبلغ الجديد للفاتورة
        new_total = current_total - total_return_amount
        if new_total < 0:
            new_total = 0
        
        cursor.execute('UPDATE sales SET total_amount = ? WHERE id = ?', (new_total, sale_id))
        
        # 7. إدراج عناصر المرتجع وإرجاع الكميات للمخزن
        for ret in processed_returns:
            cursor.execute('''
                INSERT INTO sales_return_items (return_id, product_id, quantity, return_price)
                VALUES (?, ?, ?, ?)
            ''', (return_id, ret['product_id'], ret['return_qty'], ret['return_price']))
            cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (ret['return_qty'], ret['product_id']))
        
        # 8. تحديث حالة المرتجع في جدول sales
        cursor.execute('SELECT SUM(quantity) as total_remaining FROM sale_items WHERE sale_id = ?', (sale_id,))
        total_remaining = cursor.fetchone()['total_remaining'] or 0
        
        # تحديد حالة المرتجع الجديدة
        if total_remaining == 0:
            new_return_status = 2  # مرتجع كلي
            status_message = "مرتجع كلي"
            # تغيير sale_type إلى 'مرتجع'
            cursor.execute('UPDATE sales SET sale_type = ? WHERE id = ?', ('مرتجع', sale_id))
        else:
            new_return_status = 1  # مرتجع جزئي
            status_message = "مرتجع جزئي"
        
        cursor.execute('UPDATE sales SET return_status = ? WHERE id = ?', (new_return_status, sale_id))
        
        conn.commit()
        return True, f"تم معالجة المرتجع بنجاح ({status_message})، رقم العملية: {return_number}"
        
    except Exception as e:
        conn.rollback()
        return False, f"خطأ في معالجة المرتجع: {str(e)}"
    finally:
        conn.close()

def get_sales_returns():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sr.*, s.total_amount as original_sale_amount, s.return_status, s.sale_type
        FROM sales_returns sr
        LEFT JOIN sales s ON sr.sale_id = s.id
        ORDER BY sr.return_date DESC
    ''')
    returns = cursor.fetchall()
    conn.close()
    return returns

def add_debt(customer_name, amount, due_date=None, sale_id=None, customer_phone="", notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        amount_val = float(amount)
        cursor.execute('''
            INSERT INTO debts (customer_name, customer_phone, amount, paid_amount, remaining_amount, due_date, sale_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_name, customer_phone, amount_val, 0.0, amount_val, due_date, sale_id, notes))
        conn.commit()
        debt_id = cursor.lastrowid
        conn.close()
        return True, debt_id
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def add_debt_payment(debt_id, payment_amount, payment_method="نقدي", notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        payment_val = float(payment_amount)
        cursor.execute('BEGIN TRANSACTION')
        cursor.execute('''
            INSERT INTO debt_payments (debt_id, payment_amount, payment_method, notes)
            VALUES (?, ?, ?, ?)
        ''', (debt_id, payment_val, payment_method, notes))
        cursor.execute('''
            UPDATE debts 
            SET paid_amount = paid_amount + ?,
                remaining_amount = remaining_amount - ?
            WHERE id = ?
        ''', (payment_val, payment_val, debt_id))
        cursor.execute('''
            UPDATE debts 
            SET status = 'مدفوع'
            WHERE id = ? AND remaining_amount <= 0
        ''', (debt_id,))
        conn.commit()
        conn.close()
        return True, "تم تسجيل الدفعة بنجاح"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def get_all_debts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM debts 
        ORDER BY 
            CASE status 
                WHEN 'متأخر' THEN 1 
                WHEN 'مستحق' THEN 2 
                ELSE 3 
            END,
            debt_date DESC
    ''')
    debts = cursor.fetchall()
    conn.close()
    return debts

def delete_debt(debt_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
        conn.commit()
        conn.close()
        return True, "تم حذف الدين بنجاح"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def add_damaged_product(product_id, product_name, quantity, damage_reason, loss_amount, reported_by="", notes="", quantity_unit="قطعة"):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        quantity_val = int(quantity)
        loss_val = float(loss_amount)
        cursor.execute('BEGIN TRANSACTION')
        cursor.execute('''
            INSERT INTO damaged_products (product_id, product_name, quantity, quantity_unit, damage_reason, loss_amount, reported_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product_id, product_name, quantity_val, quantity_unit, damage_reason, loss_val, reported_by, notes))
        if product_id:
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity_val, product_id))
        conn.commit()
        conn.close()
        return True, "تم تسجيل المنتج التالف وخصمه من المخزون"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def get_damaged_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT dp.*, p.name as current_product_name
        FROM damaged_products dp
        LEFT JOIN products p ON dp.product_id = p.id
        ORDER BY dp.damage_date DESC
    ''')
    damaged = cursor.fetchall()
    conn.close()
    return damaged

def delete_damaged_entry(damaged_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM damaged_products WHERE id = ?", (damaged_id,))
        if not cursor.fetchone():
            conn.close()
            return (False, "السجل غير موجود")
        
        cursor.execute("DELETE FROM damaged_products WHERE id = ?", (damaged_id,))
        conn.commit()
        conn.close()
        return (True, "تم حذف السجل بنجاح")
    except Exception as e:
        conn.rollback()
        conn.close()
        return (False, str(e))

def add_stock_transfer(product_id, product_name, quantity, from_warehouse, to_warehouse, transfer_reason="", transferred_by="", notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        quantity_val = int(quantity)
        transfer_number = f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute('BEGIN TRANSACTION')
        cursor.execute('''
            INSERT INTO stock_transfers (transfer_number, product_id, product_name, quantity, 
                                        from_warehouse, to_warehouse, transfer_reason, transferred_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transfer_number, product_id, product_name, quantity_val, 
              from_warehouse, to_warehouse, transfer_reason, transferred_by, notes))
        conn.commit()
        conn.close()
        return True, f"تم تسجيل تحويل المخزني بنجاح، رقم العملية: {transfer_number}"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def get_stock_transfers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM stock_transfers 
        ORDER BY transfer_date DESC
    ''')
    transfers = cursor.fetchall()
    conn.close()
    return transfers

def add_purchase_return(supplier_name, return_items_list, return_reason="", processed_by="", notes=""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        items_converted = []
        total_return = 0
        for item in return_items_list:
            product_id = int(item[0]) if item[0] else None
            product_name = str(item[1])
            quantity = int(float(item[2]))
            return_price = float(item[3])
            items_converted.append((product_id, product_name, quantity, return_price))
            total_return += quantity * return_price
        
        return_number = f"PR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute('BEGIN TRANSACTION')
        cursor.execute('''
            INSERT INTO purchase_returns (return_number, supplier_name, total_return_amount, return_reason, processed_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (return_number, supplier_name, float(total_return), return_reason, processed_by, notes))
        return_id = cursor.lastrowid
        for product_id, product_name, quantity, return_price in items_converted:
            cursor.execute('''
                INSERT INTO purchase_return_items (return_id, product_id, product_name, quantity, return_price)
                VALUES (?, ?, ?, ?, ?)
            ''', (return_id, product_id, product_name, quantity, return_price))
            if product_id:
                cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        conn.commit()
        conn.close()
        return True, f"تم تسجيل مرتجع المشتريات بنجاح، رقم العملية: {return_number}"
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e)

def get_purchase_returns():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM purchase_returns 
        ORDER BY return_date DESC
    ''')
    returns = cursor.fetchall()
    conn.close()
    return returns

def get_total_loss_from_damaged():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(loss_amount) FROM damaged_products")
    total_loss = cursor.fetchone()[0]
    conn.close()
    return float(total_loss) if total_loss else 0

def get_total_outstanding_debts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(remaining_amount) FROM debts WHERE status != 'مدفوع'")
    total_debts = cursor.fetchone()[0]
    conn.close()
    return float(total_debts) if total_debts else 0

def get_total_sales_returns_amount():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(total_return_amount) FROM sales_returns")
    total_returns = cursor.fetchone()[0]
    conn.close()
    return float(total_returns) if total_returns else 0


# ================= دوال تنظيف النظام وتصفير البيانات =================

def clear_all_returns():
    """حذف جميع سجلات المرتجعات وإعادة تعيين حالة الفواتير"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        details = {
            'sales_returns_deleted': 0,
            'sales_return_items_deleted': 0,
            'purchase_returns_deleted': 0,
            'purchase_return_items_deleted': 0,
            'sales_reset': 0
        }
        
        # حذف عناصر مرتجعات المبيعات
        cursor.execute('DELETE FROM sales_return_items')
        details['sales_return_items_deleted'] = cursor.rowcount
        
        # حذف سجلات مرتجعات المبيعات
        cursor.execute('DELETE FROM sales_returns')
        details['sales_returns_deleted'] = cursor.rowcount
        
        # حذف عناصر مرتجعات المشتريات
        cursor.execute('DELETE FROM purchase_return_items')
        details['purchase_return_items_deleted'] = cursor.rowcount
        
        # حذف سجلات مرتجعات المشتريات
        cursor.execute('DELETE FROM purchase_returns')
        details['purchase_returns_deleted'] = cursor.rowcount
        
        # إعادة تعيين حالة الفواتير المرتجعة
        cursor.execute('''
            UPDATE sales 
            SET sale_type = CASE 
                WHEN payment_method = 'نقدي' THEN 'نقدي'
                WHEN payment_method = 'آجل' THEN 'آجل'
                ELSE 'نقدي'
            END,
            return_status = 0
            WHERE sale_type = 'مرتجع' OR return_status > 0
        ''')
        details['sales_reset'] = cursor.rowcount
        
        conn.commit()
        
        message = f"""
✅ تم تنظيف النظام بنجاح:

📦 مرتجعات المبيعات:
   - حذف {details['sales_returns_deleted']} سجل مرتجع مبيعات
   - حذف {details['sales_return_items_deleted']} عنصر مرتجع

📦 مرتجعات المشتريات:
   - حذف {details['purchase_returns_deleted']} سجل مرتجع مشتريات
   - حذف {details['purchase_return_items_deleted']} عنصر مرتجع

🔄 إعادة تعيين:
   - تم تصفير {details['sales_reset']} فاتورة كانت مرتجعة
"""
        
        return True, message, details
        
    except Exception as e:
        conn.rollback()
        return False, f"خطأ في تنظيف النظام: {str(e)}", {}
    finally:
        conn.close()

def reset_system_full():
    """إعادة تعيين كامل للنظام (حذف كل شيء ما عدا المستخدمين)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        tables_to_clear = [
            'debt_payments',
            'debts',
            'sales_return_items',
            'sales_returns',
            'purchase_return_items',
            'purchase_returns',
            'sale_items',
            'sales',
            'stock_transfers',
            'damaged_products',
            'products'
        ]
        
        stats = {}
        
        for table in tables_to_clear:
            cursor.execute(f'DELETE FROM {table}')
            stats[table] = cursor.rowcount
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
        
        conn.commit()
        
        message = f"""
✅ تم إعادة تعيين النظام بالكامل:

📊 إحصائيات التنظيف:
   - المنتجات: {stats.get('products', 0)}
   - فواتير المبيعات: {stats.get('sales', 0)}
   - عناصر الفواتير: {stats.get('sale_items', 0)}
   - مرتجعات المبيعات: {stats.get('sales_returns', 0)}
   - مرتجعات المشتريات: {stats.get('purchase_returns', 0)}
   - الديون: {stats.get('debts', 0)}
   - مدفوعات الديون: {stats.get('debt_payments', 0)}
   - تحويلات المخزون: {stats.get('stock_transfers', 0)}
   - المنتجات التالفة: {stats.get('damaged_products', 0)}

👤 تم الاحتفاظ بحسابات المستخدمين.
"""
        
        return True, message
        
    except Exception as e:
        conn.rollback()
        return False, f"خطأ في إعادة تعيين النظام: {str(e)}"
    finally:
        conn.close()

def get_system_stats():
    """الحصول على إحصائيات النظام"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    try:
        cursor.execute('SELECT COUNT(*) FROM products')
        stats['products_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM sales')
        stats['sales_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sales WHERE sale_type = 'مرتجع'")
        stats['returned_sales_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM sales_returns')
        stats['sales_returns_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM purchase_returns')
        stats['purchase_returns_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM debts')
        stats['debts_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(total_amount) FROM sales WHERE sale_type != "مرتجع"')
        stats['total_sales'] = float(cursor.fetchone()[0] or 0)
        
        cursor.execute('SELECT SUM(total_return_amount) FROM sales_returns')
        stats['total_returns'] = float(cursor.fetchone()[0] or 0)
        
        return stats
        
    except Exception as e:
        print(f"خطأ في جلب الإحصائيات: {e}")
        return {}
    finally:
        conn.close()


# ================= دوال حذف مرتجعات المشتريات والنقل المخزني =================

def delete_purchase_return(return_id):
    """
    حذف مرتجع مشتريات مع جميع عناصره المرتبطة وإعادة الكميات إلى المخزون
    
    Args:
        return_id (int): رقم مرتجع المشتريات المراد حذفه
    
    Returns:
        tuple: (success, message)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        # 1. جلب عناصر المرتجع لمعرفة المنتجات والكميات المرتجعة
        cursor.execute('SELECT product_id, quantity FROM purchase_return_items WHERE return_id = ?', (return_id,))
        items = cursor.fetchall()
        
        if not items:
            conn.rollback()
            conn.close()
            return (False, "مرتجع المشتريات غير موجود")
        
        # 2. إعادة الكميات إلى المخزون (عكس عملية المرتجع)
        for item in items:
            product_id = item['product_id']
            quantity = item['quantity']
            if product_id:
                cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (quantity, product_id))
        
        # 3. حذف عناصر المرتجع
        cursor.execute('DELETE FROM purchase_return_items WHERE return_id = ?', (return_id,))
        
        # 4. حذف سجل المرتجع
        cursor.execute('DELETE FROM purchase_returns WHERE id = ?', (return_id,))
        
        conn.commit()
        conn.close()
        return (True, f"تم حذف مرتجع المشتريات رقم {return_id} بنجاح")
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return (False, f"خطأ في حذف مرتجع المشتريات: {str(e)}")


def delete_stock_transfer(transfer_id):
    """
    حذف عملية نقل مخزني مع إعادة الكميات إلى المخزن المصدر
    
    Args:
        transfer_id (int): رقم عملية النقل المراد حذفها
    
    Returns:
        tuple: (success, message)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        # 1. جلب بيانات عملية النقل
        cursor.execute('SELECT product_id, quantity, from_warehouse, to_warehouse FROM stock_transfers WHERE id = ?', (transfer_id,))
        transfer = cursor.fetchone()
        
        if not transfer:
            conn.rollback()
            conn.close()
            return (False, "عملية النقل غير موجودة")
        
        product_id = transfer['product_id']
        quantity = transfer['quantity']
        from_warehouse = transfer['from_warehouse']
        
        # 2. إعادة الكمية إلى المخزن المصدر (لأن النقل كان قد خصم من المخزن المصدر)
        if product_id:
            cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (quantity, product_id))
        
        # 3. حذف سجل النقل
        cursor.execute('DELETE FROM stock_transfers WHERE id = ?', (transfer_id,))
        
        conn.commit()
        conn.close()
        return (True, f"تم حذف عملية النقل رقم {transfer_id} بنجاح")
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return (False, f"خطأ في حذف عملية النقل: {str(e)}")


def delete_stock_transfer_simple(transfer_id):
    """
    حذف عملية نقل مخزني فقط (دون إعادة الكميات إلى المخزن)
    يستخدم هذا إذا كنت لا تريد إعادة الكميات
    
    Args:
        transfer_id (int): رقم عملية النقل المراد حذفها
    
    Returns:
        tuple: (success, message)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        # التحقق من وجود عملية النقل
        cursor.execute('SELECT id FROM stock_transfers WHERE id = ?', (transfer_id,))
        if not cursor.fetchone():
            conn.rollback()
            conn.close()
            return (False, "عملية النقل غير موجودة")
        
        # حذف سجل النقل
        cursor.execute('DELETE FROM stock_transfers WHERE id = ?', (transfer_id,))
        
        conn.commit()
        conn.close()
        return (True, f"تم حذف عملية النقل رقم {transfer_id} بنجاح")
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return (False, f"خطأ في حذف عملية النقل: {str(e)}")


def delete_purchase_return_simple(return_id):
    """
    حذف مرتجع مشتريات فقط (دون إعادة الكميات إلى المخزون)
    
    Args:
        return_id (int): رقم مرتجع المشتريات المراد حذفه
    
    Returns:
        tuple: (success, message)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('BEGIN TRANSACTION')
        
        # التحقق من وجود المرتجع
        cursor.execute('SELECT id FROM purchase_returns WHERE id = ?', (return_id,))
        if not cursor.fetchone():
            conn.rollback()
            conn.close()
            return (False, "مرتجع المشتريات غير موجود")
        
        # حذف عناصر المرتجع أولاً (بسبب الـ Foreign Key)
        cursor.execute('DELETE FROM purchase_return_items WHERE return_id = ?', (return_id,))
        
        # حذف سجل المرتجع
        cursor.execute('DELETE FROM purchase_returns WHERE id = ?', (return_id,))
        
        conn.commit()
        conn.close()
        return (True, f"تم حذف مرتجع المشتريات رقم {return_id} بنجاح")
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return (False, f"خطأ في حذف مرتجع المشتريات: {str(e)}")


initialize_system()