"""
database.py - نظام إدارة قاعدة البيانات المتكامل للمشروع
يدعم: المنتجات المتقدمة، التوالف، المشتريات، المرتجعات، نظام الجرد، ومتوسط التكلفة المرجح
🔄 [متوافق تماماً] مع جميع واجهات المستخدم المحدثة
✅ [نظام الرسائل النصية] - جميع الدوال تعيد (bool, str) لعرض رسائل مباشرة دون QMessageBox
🔐 [تشفير كلمات المرور] - باستخدام SHA-256 مع Salt
📊 [قوائم الأسعار المتعددة] - دعم تجزئة/جملة/VIP
🎯 [العروض والخصومات] - دعم buy_x_get_y, percent, fixed_amount
📂 [التصنيفات] - إدارة تصنيفات ديناميكية
💰 [المصروفات] - تسجيل وإدارة المصروفات
🕐 [تسجيل الدخول/الخروج] - تتبع أوقات الدخول والخروج
🔑 [الصلاحيات الدقيقة] - نظام صلاحيات متقدم
"""

import sqlite3
import os
import sys
import random
import shutil
import zipfile
import json
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

# ========== إعداد نظام التسجيل (Logging) ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================================
# =========== تحديد مسار قاعدة البيانات =======================
# =============================================================

def get_base_path():
    """
    الحصول على المسار الأساسي للتطبيق
    - عند التشغيل كـ EXE: نستخدم مسار مجلد الـ EXE
    - عند التشغيل كـ Script عادي: نستخدم مسار المجلد الحالي
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db_path():
    """
    تحديد مسار قاعدة البيانات بشكل آمن مع دعم PyInstaller
    """
    base_path = get_base_path()
    db_dir = os.path.join(base_path, 'database')
    db_path = os.path.join(db_dir, 'supermarket.db')
    
    if not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"تم إنشاء مجلد قاعدة البيانات: {db_dir}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء المجلد: {e}")
            fallback_path = os.path.join(os.path.expanduser("~"), "SupermarketDB")
            os.makedirs(fallback_path, exist_ok=True)
            db_path = os.path.join(fallback_path, 'supermarket.db')
            logger.info(f"استخدام مسار بديل: {db_path}")
    
    return db_path


# تعيين المتغيرات العامة
BASE_DIR = get_base_path()
DB_DIR = os.path.join(BASE_DIR, 'database')
DB_PATH = get_db_path()

logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"DB_PATH: {DB_PATH}")
logger.info(f"Frozen mode: {getattr(sys, 'frozen', False)}")


def get_connection():
    """فتح اتصال مع قاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ========== دوال التشفير ==========
def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """
    تشفير كلمة المرور باستخدام SHA-256 مع Salt
    
    @param password: كلمة المرور النصية
    @param salt: الملح (يتم توليده تلقائياً إذا لم يتم توفيره)
    @return: (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    combined = password + salt
    hashed = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    return hashed, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """
    التحقق من كلمة المرور
    
    @param password: كلمة المرور النصية المدخلة
    @param hashed: الهاش المخزن
    @param salt: الملح المخزن
    @return: True إذا كانت مطابقة
    """
    combined = password + salt
    return hashlib.sha256(combined.encode('utf-8')).hexdigest() == hashed


def is_password_hashed(password: str) -> bool:
    """
    التحقق مما إذا كانت كلمة المرور مشفرة (تحتوي على 64 حرف hex)
    """
    return len(password) == 64 and all(c in '0123456789abcdefABCDEF' for c in password)


def migrate_existing_passwords(username: str, password: str) -> Tuple[str, str]:
    """
    ترقية كلمة المرور من نص صريح إلى هاش
    
    @param username: اسم المستخدم
    @param password: كلمة المرور النصية
    @return: (hashed_password, salt)
    """
    hashed, salt = hash_password(password)
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET password = ?, salt = ? WHERE username = ?",
            (hashed, salt, username)
        )
        conn.commit()
        return hashed, salt
    finally:
        conn.close()


# =============================================================
# ==================== دوال إعدادات المظهر ====================
# =============================================================

def get_theme_settings() -> Tuple[Dict[str, str], bool, str]:
    """
    جلب إعدادات المظهر من ملف settings.json
    @return: (dict, bool, str) - (الإعدادات, نجاح العملية, رسالة)
    """
    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                theme = {
                    'primary_color': settings.get('theme_primary_color', '#38bdf8'),
                    'font_size': settings.get('theme_font_size', 'medium')
                }
                return theme, True, "تم تحميل إعدادات المظهر"
        else:
            # إعدادات افتراضية
            return {'primary_color': '#38bdf8', 'font_size': 'medium'}, True, "استخدام الإعدادات الافتراضية"
    except Exception as e:
        logger.error(f"خطأ في تحميل إعدادات المظهر: {e}")
        return {'primary_color': '#38bdf8', 'font_size': 'medium'}, False, str(e)


def save_theme_settings(primary_color: str, font_size: str) -> Tuple[bool, str]:
    """
    حفظ إعدادات المظهر في ملف settings.json
    @param primary_color: اللون الأساسي (hex)
    @param font_size: حجم الخط (small, medium, large)
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        settings = {}
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
        
        settings['theme_primary_color'] = primary_color
        settings['theme_font_size'] = font_size
        
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        return True, "تم حفظ إعدادات المظهر بنجاح"
    except Exception as e:
        logger.error(f"خطأ في حفظ إعدادات المظهر: {e}")
        return False, str(e)


# ========== دوال إعدادات النظام (العملة، المتجر) ==========
def get_system_settings() -> Dict[str, Any]:
    """
    جلب إعدادات النظام من ملف settings.json
    @return: قاموس الإعدادات
    """
    try:
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"خطأ في تحميل إعدادات النظام: {e}")
        return {}


def save_system_settings(settings: Dict[str, Any]) -> Tuple[bool, str]:
    """
    حفظ إعدادات النظام في ملف settings.json
    @param settings: قاموس الإعدادات
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        existing = {}
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                existing = json.load(f)
        
        existing.update(settings)
        
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        
        return True, "تم حفظ إعدادات النظام بنجاح"
    except Exception as e:
        logger.error(f"خطأ في حفظ إعدادات النظام: {e}")
        return False, str(e)


# =============================================================
# ==================== تهيئة الجداول =========================
# =============================================================

def initialize_database():
    """
    إنشاء جميع الجداول المطلوبة في قاعدة البيانات
    مع دعم جميع الحقول المتقدمة للمشروع
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # ========== جدول المنتجات المتقدم ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            barcode         TEXT    UNIQUE,
            purchase_price  REAL    DEFAULT 0,
            sell_price      REAL    DEFAULT 0,
            price_wholesale REAL    DEFAULT 0,
            stock           REAL    DEFAULT 0,
            actual_stock    REAL    DEFAULT 0,
            alert_limit     INTEGER DEFAULT 5,
            reorder_level   INTEGER DEFAULT 10,
            weight_unit     TEXT    DEFAULT 'قطعة',
            unit            TEXT    DEFAULT 'قطعة',
            sub_unit_qty    INTEGER DEFAULT 1,
            category        TEXT    DEFAULT 'عام',
            has_expiry      INTEGER DEFAULT 0,
            expiry_date     TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ========== جدول التصنيفات (جديد) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ========== جدول المبيعات ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount    REAL    DEFAULT 0,
            discount        REAL    DEFAULT 0,
            paid_amount     REAL    DEFAULT 0,
            cash_paid       REAL    DEFAULT 0,
            visa_paid       REAL    DEFAULT 0,
            status          TEXT    DEFAULT 'مكتمل',
            payment_method  TEXT    DEFAULT 'نقدي',
            return_status   INTEGER DEFAULT 0,
            sale_type       TEXT    DEFAULT 'نقدي',
            sale_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cashier_name    TEXT    DEFAULT 'Admin',
            customer_name   TEXT    DEFAULT ''
        )
    ''')
    
    # ========== جدول عناصر المبيعات ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id        INTEGER,
            product_id     INTEGER,
            quantity       REAL,
            price_at_sale  REAL,
            FOREIGN KEY(sale_id)    REFERENCES sales(id)    ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    # ========== جدول المستخدمين (مع أعمدة جديدة) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            salt        TEXT,
            role        TEXT DEFAULT 'مندوب مبيعات',
            last_login  TIMESTAMP,
            last_logout TIMESTAMP
        )
    ''')
    
    # ========== جدول العملاء ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            phone           TEXT,
            total_debt      REAL DEFAULT 0,
            paid_amount     REAL DEFAULT 0,
            loyalty_points  INTEGER DEFAULT 0,
            last_transaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ========== جدول الموردين ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            contact_person  TEXT,
            phone           TEXT,
            total_balance   REAL DEFAULT 0,
            paid_amount     REAL DEFAULT 0,
            next_payment_date TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ========== جدول الديون ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS debts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name    TEXT NOT NULL,
            customer_phone   TEXT,
            amount           REAL NOT NULL,
            paid_amount      REAL DEFAULT 0,
            remaining_amount REAL NOT NULL,
            debt_date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date         TIMESTAMP,
            status           TEXT DEFAULT 'مستحق',
            notes            TEXT,
            sale_id          INTEGER,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE SET NULL
        )
    ''')
    
    # ========== جدول دفعات الديون ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS debt_payments (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_id        INTEGER,
            payment_amount REAL,
            payment_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT DEFAULT 'نقدي',
            notes          TEXT,
            FOREIGN KEY(debt_id) REFERENCES debts(id) ON DELETE CASCADE
        )
    ''')
    
    # ========== جدول المنتجات التالفة ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS damaged_products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id    INTEGER,
            product_name  TEXT NOT NULL,
            quantity      REAL NOT NULL,
            quantity_unit TEXT DEFAULT 'قطعة',
            damage_reason TEXT,
            loss_amount   REAL,
            damage_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status        TEXT DEFAULT 'قيد المراجعة',
            reported_by   TEXT,
            notes         TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    # ========== جدول تحويلات المخزون ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_transfers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            transfer_number TEXT UNIQUE NOT NULL,
            product_id      INTEGER,
            product_name    TEXT NOT NULL,
            quantity        REAL NOT NULL,
            from_warehouse  TEXT NOT NULL,
            to_warehouse    TEXT NOT NULL,
            transfer_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transfer_reason TEXT,
            status          TEXT DEFAULT 'مكتمل',
            transferred_by  TEXT,
            notes           TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    ''')
    
    # ========== جدول مرتجعات المبيعات ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_returns (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id            INTEGER,
            return_number      TEXT UNIQUE NOT NULL,
            return_date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_return_amount REAL NOT NULL,
            return_reason      TEXT,
            status             TEXT DEFAULT 'مكتمل',
            processed_by       TEXT,
            notes              TEXT,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE
        )
    ''')
    
    # ========== جدول عناصر مرتجعات المبيعات ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_return_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            return_id    INTEGER,
            product_id   INTEGER,
            quantity     REAL,
            return_price REAL,
            FOREIGN KEY(return_id)  REFERENCES sales_returns(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    # ========== جدول مرتجعات المشتريات ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_returns (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            return_number       TEXT UNIQUE NOT NULL,
            supplier_name       TEXT NOT NULL,
            return_date         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_return_amount REAL NOT NULL,
            return_reason       TEXT,
            status              TEXT DEFAULT 'مكتمل',
            processed_by        TEXT,
            notes               TEXT
        )
    ''')
    
    # ========== جدول عناصر مرتجعات المشتريات ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_return_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            return_id    INTEGER,
            product_id   INTEGER,
            product_name TEXT NOT NULL,
            quantity     REAL,
            return_price REAL,
            FOREIGN KEY(return_id)  REFERENCES purchase_returns(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    ''')
    
    # ========== جدول فواتير المشتريات ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_invoices (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number      TEXT UNIQUE NOT NULL,
            supplier_name       TEXT NOT NULL,
            invoice_date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount        REAL NOT NULL,
            tax_amount          REAL DEFAULT 0,
            net_amount          REAL NOT NULL,
            payment_method      TEXT DEFAULT 'كاش',
            status              TEXT DEFAULT 'مكتمل',
            processed_by        TEXT,
            notes               TEXT
        )
    ''')
    
    # ========== جدول عناصر فواتير المشتريات ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_invoice_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id   INTEGER,
            product_id   INTEGER,
            product_name TEXT NOT NULL,
            quantity     REAL,
            purchase_price REAL,
            total_price  REAL,
            FOREIGN KEY(invoice_id)  REFERENCES purchase_invoices(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id)  REFERENCES products(id) ON DELETE SET NULL
        )
    ''')
    
    # ========== جدول سجل حركة المنتج (Stock Card) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_movements (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   INTEGER,
            date_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            movement_type TEXT NOT NULL,
            in_qty       REAL DEFAULT 0,
            out_qty      REAL DEFAULT 0,
            balance      REAL NOT NULL,
            user_name    TEXT,
            reference_id INTEGER,
            notes        TEXT,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    # ========== جدول سجل النشاط (Activity Log) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            username    TEXT,
            action      TEXT,
            details     TEXT
        )
    ''')
    
    # ========== جدول سجل التدقيق (Audit Log) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            username    TEXT,
            action      TEXT NOT NULL,
            details     TEXT,
            timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address  TEXT,
            user_agent  TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # ========== جدول المصروفات (جديد) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_type  TEXT NOT NULL,
            amount        REAL NOT NULL,
            description   TEXT,
            expense_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_by       TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ========== جدول العروض والخصومات (جديد) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promotions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            promo_type     TEXT NOT NULL CHECK (promo_type IN ('buy_x_get_y', 'percent', 'fixed_amount')),
            product_id     INTEGER,
            category       TEXT,
            buy_qty        INTEGER DEFAULT 0,
            get_qty        INTEGER DEFAULT 0,
            discount_value REAL DEFAULT 0,
            is_active      INTEGER DEFAULT 1,
            start_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date       TIMESTAMP,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    # ========== جدول قوائم الأسعار (محدث مع is_default) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_lists (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT UNIQUE NOT NULL,
            is_default  INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ========== جدول أسعار المنتجات حسب القائمة (جديد) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_prices (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id     INTEGER NOT NULL,
            price_list_id  INTEGER NOT NULL,
            price          REAL NOT NULL,
            updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY(price_list_id) REFERENCES price_lists(id) ON DELETE CASCADE,
            UNIQUE(product_id, price_list_id)
        )
    ''')
    
    # ========== جدول الصلاحيات الدقيقة (جديد) ==========
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            role        TEXT NOT NULL,
            action_key  TEXT NOT NULL,
            allowed     INTEGER DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(role, action_key)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # ترقية الجداول القديمة
    upgrade_tables()
    
    # إنشاء قيم افتراضية للصلاحيات
    seed_default_permissions()
    
    # إضافة تصنيفات افتراضية
    seed_default_categories()
    
    # إضافة قوائم أسعار افتراضية
    seed_default_price_lists()
    
    logger.info("تم تهيئة قاعدة البيانات بنجاح")


def seed_default_price_lists():
    """إضافة قوائم أسعار افتراضية"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # التحقق من وجود قوائم أسعار
        cursor.execute("SELECT COUNT(*) FROM price_lists")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # إضافة قائمة التجزئة كافتراضية
            cursor.execute(
                "INSERT INTO price_lists (name, is_default) VALUES (?, ?)",
                ("التجزئة", 1)
            )
            
            # إضافة قوائم أخرى
            cursor.execute(
                "INSERT INTO price_lists (name, is_default) VALUES (?, ?)",
                ("الجملة", 0)
            )
            cursor.execute(
                "INSERT INTO price_lists (name, is_default) VALUES (?, ?)",
                ("VIP", 0)
            )
            
            conn.commit()
            logger.info("تم إضافة قوائم الأسعار الافتراضية")
    except Exception as e:
        logger.error(f"خطأ في seed_default_price_lists: {e}")
    finally:
        conn.close()


def upgrade_tables():
    """ترقية الجداول لإضافة الأعمدة الجديدة إذا لم تكن موجودة"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # ===== ترقية جدول price_lists لإضافة is_default =====
        cursor.execute("PRAGMA table_info(price_lists)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_default' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE price_lists ADD COLUMN is_default INTEGER DEFAULT 0")
                logger.info("تم إضافة عمود is_default إلى جدول price_lists")
            except Exception as e:
                logger.error(f"خطأ في إضافة is_default: {e}")
        
        # ===== ترقية جدول المستخدمين =====
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        user_new_columns = {
            'salt': 'TEXT',
            'last_login': 'TIMESTAMP',
            'last_logout': 'TIMESTAMP'
        }
        
        for col_name, col_type in user_new_columns.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    logger.info(f"تم إضافة عمود {col_name} إلى جدول users")
                except Exception as e:
                    logger.error(f"خطأ في إضافة عمود {col_name}: {e}")
        
        # ===== قائمة columns للمنتجات =====
        cursor.execute("PRAGMA table_info(products)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        new_columns = {
            'actual_stock': 'REAL DEFAULT 0',
            'reorder_level': 'INTEGER DEFAULT 10',
            'has_expiry': 'INTEGER DEFAULT 0',
            'expiry_date': 'TEXT',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'unit': 'TEXT DEFAULT "قطعة"',
            'price_wholesale': 'REAL DEFAULT 0.0'
        }
        
        for col_name, col_type in new_columns.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
                    logger.info(f"تم إضافة عمود {col_name} إلى جدول products")
                except Exception as e:
                    logger.error(f"خطأ في إضافة عمود {col_name}: {e}")
        
        # ===== ترقية جدول المبيعات =====
        cursor.execute("PRAGMA table_info(sales)")
        sales_columns = [col[1] for col in cursor.fetchall()]
        
        sales_new_columns = {
            'cash_paid': 'REAL DEFAULT 0',
            'visa_paid': 'REAL DEFAULT 0',
            'cashier_name': "TEXT DEFAULT 'Admin'",
            'customer_name': "TEXT DEFAULT ''"
        }
        
        for col_name, col_type in sales_new_columns.items():
            if col_name not in sales_columns:
                try:
                    cursor.execute(f"ALTER TABLE sales ADD COLUMN {col_name} {col_type}")
                    logger.info(f"تم إضافة عمود {col_name} إلى جدول sales")
                except Exception as e:
                    logger.error(f"خطأ في إضافة عمود {col_name}: {e}")
        
        # ===== ترقية جدول العملاء =====
        cursor.execute("PRAGMA table_info(customers)")
        customers_columns = [col[1] for col in cursor.fetchall()]
        
        if 'loyalty_points' not in customers_columns:
            try:
                cursor.execute("ALTER TABLE customers ADD COLUMN loyalty_points INTEGER DEFAULT 0")
                logger.info("تم إضافة عمود loyalty_points إلى جدول customers")
            except Exception as e:
                logger.error(f"خطأ في إضافة loyalty_points: {e}")
        
        # ===== ترقية جدول الديون =====
        cursor.execute("PRAGMA table_info(debts)")
        debt_columns = [col[1] for col in cursor.fetchall()]
        
        if 'remaining_amount' not in debt_columns:
            try:
                cursor.execute("ALTER TABLE debts ADD COLUMN remaining_amount REAL DEFAULT 0")
                cursor.execute("UPDATE debts SET remaining_amount = amount - paid_amount")
                logger.info("تم إضافة عمود remaining_amount إلى جدول debts")
            except Exception as e:
                logger.error(f"خطأ في إضافة remaining_amount: {e}")
        
        conn.commit()
        logger.info("تم ترقية الجداول بنجاح")
    except Exception as e:
        logger.error(f"خطأ في ترقية الجداول: {e}")
    finally:
        conn.close()


def seed_default_permissions():
    """إضافة قيم افتراضية للصلاحيات"""
    conn = get_connection()
    cursor = conn.cursor()
    
    default_permissions = [
        ('مدير', 'delete_sale_item', 1),
        ('مدير', 'edit_price', 1),
        ('مدير', 'view_reports', 1),
        ('مدير', 'apply_discount', 1),
        ('مدير', 'delete_product', 1),
        ('مدير', 'add_product', 1),
        ('مدير', 'edit_product', 1),
        ('مدير', 'view_products', 1),
        ('مدير', 'manage_users', 1),
        ('مدير', 'manage_suppliers', 1),
        ('مدير', 'manage_customers', 1),
        ('مدير', 'view_financial', 1),
        ('مدير', 'export_data', 1),
        ('مدير', 'manage_settings', 1),
        ('مدير', 'manage_promotions', 1),
        ('مدير', 'manage_price_lists', 1),
        ('مدير', 'manage_categories', 1),
        
        ('محاسب', 'view_reports', 1),
        ('محاسب', 'view_financial', 1),
        ('محاسب', 'export_data', 1),
        ('محاسب', 'apply_discount', 1),
        ('محاسب', 'view_products', 1),
        ('محاسب', 'edit_price', 0),
        ('محاسب', 'delete_product', 0),
        ('محاسب', 'manage_users', 0),
        
        ('كاشير', 'view_products', 1),
        ('كاشير', 'apply_discount', 0),
        ('كاشير', 'edit_price', 0),
        ('كاشير', 'delete_product', 0),
        ('كاشير', 'view_reports', 0),
        ('كاشير', 'manage_users', 0),
        ('كاشير', 'manage_suppliers', 0),
        ('كاشير', 'manage_customers', 0),
    ]
    
    try:
        for role, action_key, allowed in default_permissions:
            cursor.execute('''
                INSERT OR IGNORE INTO permissions (role, action_key, allowed)
                VALUES (?, ?, ?)
            ''', (role, action_key, allowed))
        conn.commit()
        logger.info("تم إضافة الصلاحيات الافتراضية")
    except Exception as e:
        logger.error(f"خطأ في seed_default_permissions: {e}")
    finally:
        conn.close()


def seed_default_categories():
    """إضافة تصنيفات افتراضية"""
    default_categories = ['عام', 'أغذية', 'منظفات', 'مشروبات', 'مجمدات', 'خضروات', 'فواكه', 'لحوم']
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        for cat in default_categories:
            cursor.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (cat,))
        conn.commit()
        logger.info("تم إضافة التصنيفات الافتراضية")
    except Exception as e:
        logger.error(f"خطأ في seed_default_categories: {e}")
    finally:
        conn.close()


# =============================================================
# ==================== دوال سجل التدقيق (Audit Log) ===========
# =============================================================

def create_audit_log_table():
    """
    إنشاء جدول سجل التدقيق إذا لم يكن موجوداً
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                username    TEXT,
                action      TEXT NOT NULL,
                details     TEXT,
                timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address  TEXT,
                user_agent  TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')
        conn.commit()
        logger.info("تم إنشاء جدول audit_logs")
        return True
    except Exception as e:
        logger.error(f"خطأ في إنشاء audit_logs: {e}")
        return False
    finally:
        conn.close()


def log_activity(user_id: int, action: str, details: str = "",
                 username: str = "", ip_address: str = "",
                 user_agent: str = "") -> bool:
    """
    تسجيل نشاط المستخدم في جدول سجل التدقيق (Audit Log)
    
    @param user_id: معرف المستخدم (يمكن أن يكون None للمستخدمين غير المسجلين)
    @param action: الإجراء المطلوب تسجيله
    @param details: تفاصيل إضافية عن الإجراء
    @param username: اسم المستخدم (اختياري)
    @param ip_address: عنوان IP للمستخدم (اختياري)
    @param user_agent: معلومات المتصفح/الجهاز (اختياري)
    @return: bool - نجاح العملية
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if username == "" and user_id is not None:
            try:
                cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    username = row[0]
            except Exception:
                pass
        
        cursor.execute('''
            INSERT INTO audit_logs (user_id, username, action, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, action, details, ip_address, user_agent))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"خطأ في log_activity: {e}")
        return False


def get_audit_logs(limit: int = 200, user_id: int = None,
                   action: str = None, start_date: str = None,
                   end_date: str = None) -> List[Dict[str, Any]]:
    """
    جلب سجل التدقيق مع إمكانية التصفية
    
    @param limit: عدد السجلات المطلوبة
    @param user_id: تصفية حسب معرف المستخدم (اختياري)
    @param action: تصفية حسب الإجراء (اختياري)
    @param start_date: تصفية من تاريخ (اختياري)
    @param end_date: تصفية إلى تاريخ (اختياري)
    @return: قائمة من القواميس
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if action:
            query += " AND action = ?"
            params.append(action)
        
        if start_date:
            query += " AND date(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date(timestamp) <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_audit_logs: {e}")
        return []


def clear_audit_logs(days_to_keep: int = 30) -> Tuple[bool, str]:
    """
    حذف سجلات التدقيق الأقدم من عدد الأيام المحدد
    
    @param days_to_keep: عدد الأيام المطلوب الاحتفاظ بالسجلات فيها
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM audit_logs 
            WHERE timestamp < datetime('now', ?)
        ''', (f'-{days_to_keep} days',))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return True, f"تم حذف {deleted_count} سجل قديم من سجل التدقيق"
    except Exception as e:
        logger.error(f"خطأ في clear_audit_logs: {e}")
        return False, f"خطأ في تنظيف سجل التدقيق: {str(e)}"


# =============================================================
# ==================== دوال النسخ الاحتياطي ===================
# =============================================================

def backup_database(destination_path: str) -> Tuple[bool, str]:
    """
    إنشاء نسخة احتياطية مضغوطة (ZIP) من قاعدة البيانات
    
    @param destination_path: المسار الكامل لملف ZIP الناتج
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        dest_dir = os.path.dirname(destination_path)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        if not os.path.exists(DB_PATH):
            return False, f"ملف قاعدة البيانات غير موجود: {DB_PATH}"
        
        with zipfile.ZipFile(destination_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(DB_PATH, os.path.basename(DB_PATH))
            
            settings_path = os.path.join(BASE_DIR, 'settings.json')
            if os.path.exists(settings_path):
                zipf.write(settings_path, 'settings.json')
            
            invoices_dir = os.path.join(BASE_DIR, 'invoices')
            if os.path.exists(invoices_dir) and os.path.isdir(invoices_dir):
                for root, dirs, files in os.walk(invoices_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('invoices', file)
                        zipf.write(file_path, arcname)
        
        zip_size = os.path.getsize(destination_path)
        logger.info(f"تم إنشاء النسخة الاحتياطية: {destination_path} ({zip_size/1024:.2f} KB)")
        
        return True, f"تم إنشاء النسخة الاحتياطية بنجاح في {destination_path}"
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
        return False, f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}"


def restore_database(zip_path: str) -> Tuple[bool, str]:
    """
    استعادة قاعدة البيانات من ملف ZIP احتياطي
    
    @param zip_path: المسار الكامل لملف ZIP الاحتياطي
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    temp_dir = os.path.join(BASE_DIR, 'temp_restore')
    try:
        if not os.path.exists(zip_path):
            return False, f"ملف ZIP غير موجود: {zip_path}"
        
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        db_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.db'):
                    db_files.append(os.path.join(root, file))
        
        if not db_files:
            shutil.rmtree(temp_dir)
            return False, "لم يتم العثور على ملف قاعدة بيانات في النسخة الاحتياطية"
        
        temp_db_path = db_files[0]
        
        if os.path.exists(DB_PATH):
            backup_name = f"supermarket_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = os.path.join(os.path.dirname(DB_PATH), backup_name)
            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"تم عمل نسخة احتياطية للقاعدة الحالية: {backup_path}")
        
        shutil.copy2(temp_db_path, DB_PATH)
        shutil.rmtree(temp_dir)
        
        logger.info(f"تم استعادة قاعدة البيانات من: {zip_path}")
        
        return True, f"تم استعادة قاعدة البيانات بنجاح من {os.path.basename(zip_path)}"
        
    except Exception as e:
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass
        logger.error(f"خطأ في استعادة قاعدة البيانات: {e}")
        return False, f"خطأ في استعادة قاعدة البيانات: {str(e)}"


def list_backups(backup_dir: str = None) -> List[Dict[str, Any]]:
    """
    عرض قائمة بالنسخ الاحتياطية المتاحة
    
    @param backup_dir: مجلد النسخ الاحتياطية (اختياري)
    @return: قائمة من القواميس تحتوي على معلومات النسخ الاحتياطية
    """
    if backup_dir is None:
        backup_dir = os.path.join(BASE_DIR, 'backups')
    
    backups = []
    
    if not os.path.exists(backup_dir):
        return backups
    
    try:
        for file in os.listdir(backup_dir):
            if file.endswith('.zip'):
                file_path = os.path.join(backup_dir, file)
                stat = os.stat(file_path)
                backups.append({
                    'filename': file,
                    'path': file_path,
                    'size': stat.st_size,
                    'size_mb': stat.st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        backups.sort(key=lambda x: x['modified'], reverse=True)
        return backups
    except Exception as e:
        logger.error(f"خطأ في list_backups: {e}")
        return []


# =============================================================
# ==================== دوال المستخدمين ========================
# =============================================================

def initialize_system():
    """تهيئة النظام - إنشاء الجداول فقط"""
    initialize_database()
    create_audit_log_table()


def is_users_table_empty() -> bool:
    """التحقق مما إذا كان جدول المستخدمين فارغاً"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) as count FROM users")
        row = cursor.fetchone()
        count = row[0] if row else 0
        return count == 0
    except Exception as e:
        logger.error(f"خطأ في التحقق من جدول المستخدمين: {e}")
        return True
    finally:
        conn.close()


def register_admin(username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """إنشاء حساب مدير جديد مع تشفير كلمة المرور"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        hashed, salt = hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (username, password, salt, role)
            VALUES (?, ?, ?, ?)
        ''', (username.strip(), hashed, salt, 'مدير'))
        conn.commit()
        
        cursor.execute("SELECT id, username, role FROM users WHERE username = ?", (username.strip(),))
        user = cursor.fetchone()
        
        user_dict = {'id': user[0], 'username': user[1], 'role': user[2]} if user else None
        
        log_activity(user_dict['id'] if user_dict else None, 'تسجيل مدير جديد',
                    f'تم إنشاء حساب مدير جديد: {username}', username)
        
        return True, "تم إنشاء حساب المدير بنجاح", user_dict
    except sqlite3.IntegrityError:
        return False, "اسم المستخدم موجود بالفعل! يرجى اختيار اسم آخر.", None
    except Exception as e:
        logger.error(f"خطأ في register_admin: {e}")
        return False, str(e), None
    finally:
        conn.close()


def login_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    التحقق من بيانات المستخدم باستخدام التشفير وإرجاع بياناته
    مع دعم ترقية كلمات المرور القديمة (نص صريح)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, username, password, salt, role FROM users WHERE username=?", (username.strip(),))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            log_activity(None, 'محاولة دخول فاشلة', f'محاولة دخول فاشلة للمستخدم: {username}', username)
            return None
        
        user_id, db_username, db_password, salt, role = user
        
        # التحقق مما إذا كانت كلمة المرور مخزنة كنص صريح (غير مشفرة)
        if not is_password_hashed(db_password):
            # ترقية كلمة المرور إلى هاش
            hashed, new_salt = hash_password(password)
            cursor.execute(
                "UPDATE users SET password = ?, salt = ? WHERE id = ?",
                (hashed, new_salt, user_id)
            )
            conn.commit()
            
            # التحقق من صحة كلمة المرور بعد الترقية
            if verify_password(password, hashed, new_salt):
                # تحديث last_login
                cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                
                user_dict = {'id': user_id, 'username': db_username, 'role': role, 'password_upgraded': True}
                log_activity(user_id, 'تسجيل دخول (ترقية كلمة مرور)', 
                           f'تم ترقية كلمة المرور وتحديثها إلى هاش للمستخدم: {username}', username)
                return user_dict
            else:
                conn.close()
                log_activity(user_id, 'محاولة دخول فاشلة', f'كلمة مرور غير صحيحة للمستخدم: {username}', username)
                return None
        
        # كلمة المرور مشفرة - تحقق منها
        if verify_password(password, db_password, salt):
            cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            
            user_dict = {'id': user_id, 'username': db_username, 'role': role, 'password_upgraded': False}
            log_activity(user_id, 'تسجيل دخول', f'تسجيل دخول ناجح: {username}', username)
            return user_dict
        
        conn.close()
        log_activity(user_id, 'محاولة دخول فاشلة', f'كلمة مرور غير صحيحة للمستخدم: {username}', username)
        return None
        
    except Exception as e:
        logger.error(f"خطأ في login_user: {e}")
        return None


def record_logout(username: str) -> bool:
    """
    تسجيل وقت الخروج للمستخدم
    
    @param username: اسم المستخدم
    @return: bool - نجاح العملية
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE users SET last_logout = CURRENT_TIMESTAMP WHERE username = ?", (username.strip(),))
        conn.commit()
        conn.close()
        
        log_activity(None, 'تسجيل خروج', f'تسجيل خروج للمستخدم: {username}', username)
        return True
    except Exception as e:
        logger.error(f"خطأ في record_logout: {e}")
        return False


def change_password(username: str, old_password: str, new_password: str) -> Tuple[bool, str, bool]:
    """
    تغيير كلمة المرور مع دعم التشفير
    
    @return: (bool, str, bool) - (نجاح العملية, رسالة, تم_ترقية_الهاش)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, password, salt FROM users WHERE username = ?", (username.strip(),))
        user = cursor.fetchone()
        
        if not user:
            return False, "اسم المستخدم غير موجود", False
        
        user_id, db_password, salt = user
        
        # التحقق من كلمة المرور الحالية
        if is_password_hashed(db_password):
            if not verify_password(old_password, db_password, salt):
                return False, "كلمة المرور الحالية غير صحيحة", False
        else:
            # كلمة المرور مخزنة كنص صريح
            if old_password != db_password:
                return False, "كلمة المرور الحالية غير صحيحة", False
        
        # تشفير كلمة المرور الجديدة
        hashed, new_salt = hash_password(new_password)
        cursor.execute("UPDATE users SET password = ?, salt = ? WHERE id = ?", (hashed, new_salt, user_id))
        conn.commit()
        
        was_upgraded = not is_password_hashed(db_password)
        
        log_activity(user_id, 'تغيير كلمة المرور', f'تم تغيير كلمة المرور للمستخدم: {username}', username)
        
        return True, "تم تغيير كلمة المرور بنجاح", was_upgraded
    except Exception as e:
        logger.error(f"خطأ في change_password: {e}")
        return False, str(e), False
    finally:
        if conn:
            conn.close()


def get_all_users() -> List[Dict[str, Any]]:
    """جلب جميع المستخدمين"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, username, role, last_login, last_logout FROM users ORDER BY id")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_all_users: {e}")
        return []
    finally:
        conn.close()


def add_user(username: str, password: str, role: str) -> Tuple[bool, str]:
    """إضافة مستخدم جديد مع تشفير كلمة المرور"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hashed, salt = hash_password(password)
        
        cursor.execute("INSERT INTO users (username, password, salt, role) VALUES (?, ?, ?, ?)",
                       (username.strip(), hashed, salt, role))
        conn.commit()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", (username.strip(),))
        row = cursor.fetchone()
        if row:
            log_activity(row[0], 'إضافة مستخدم', f'تم إضافة مستخدم جديد: {username} (دور: {role})', username)
        
        return True, "تم إضافة المستخدم بنجاح"
    except sqlite3.IntegrityError:
        return False, "اسم المستخدم موجود بالفعل!"
    except Exception as e:
        logger.error(f"خطأ في add_user: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def delete_user(user_id: int) -> Tuple[bool, str]:
    """حذف مستخدم"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        username = user[0] if user else f"ID:{user_id}"
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()[0]
        
        if count <= 1:
            return False, "لا يمكن حذف المستخدم الوحيد المتبقي في النظام"
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        
        log_activity(None, 'حذف مستخدم', f'تم حذف المستخدم: {username}', 'System')
        
        return True, "تم حذف المستخدم بنجاح"
    except Exception as e:
        logger.error(f"خطأ في delete_user: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


# =============================================================
# ==================== دوال الصلاحيات الدقيقة =================
# =============================================================

def check_permission(role: str, action_key: str) -> bool:
    """
    التحقق من صلاحية مستخدم لعملية معينة
    
    @param role: دور المستخدم
    @param action_key: مفتاح العملية
    @return: bool - True إذا كان مسموحاً، False إذا غير مسموح
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT allowed FROM permissions WHERE role = ? AND action_key = ?",
            (role, action_key)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return bool(row[0])
        
        # إذا لم يوجد سجل، نرجع True افتراضياً (عدم منع المستخدم)
        return True
    except Exception as e:
        logger.error(f"خطأ في check_permission: {e}")
        return True  # افتراضي True في حالة الخطأ


def set_permission(role: str, action_key: str, allowed: bool) -> Tuple[bool, str]:
    """
    تعيين صلاحية لدور معين
    
    @param role: دور المستخدم
    @param action_key: مفتاح العملية
    @param allowed: مسموح أم لا
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO permissions (role, action_key, allowed)
            VALUES (?, ?, ?)
        ''', (role, action_key, 1 if allowed else 0))
        
        conn.commit()
        conn.close()
        
        return True, f"تم تعيين صلاحية {action_key} لدور {role} إلى {allowed}"
    except Exception as e:
        logger.error(f"خطأ في set_permission: {e}")
        return False, str(e)


def get_role_permissions(role: str) -> List[Dict[str, Any]]:
    """
    جلب جميع صلاحيات دور معين
    
    @param role: دور المستخدم
    @return: قائمة من القواميس
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT action_key, allowed FROM permissions WHERE role = ?",
            (role,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [{'action_key': row[0], 'allowed': bool(row[1])} for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_role_permissions: {e}")
        return []


# =============================================================
# ==================== دوال التصنيفات =========================
# =============================================================

def add_category(name: str) -> Tuple[bool, str]:
    """
    إضافة تصنيف جديد
    
    @param name: اسم التصنيف
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name.strip(),))
        conn.commit()
        conn.close()
        
        return True, f"تم إضافة التصنيف {name} بنجاح"
    except sqlite3.IntegrityError:
        return False, f"التصنيف {name} موجود بالفعل"
    except Exception as e:
        logger.error(f"خطأ في add_category: {e}")
        return False, str(e)


def get_all_categories() -> List[Dict[str, Any]]:
    """
    جلب جميع التصنيفات
    
    @return: قائمة من القواميس
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, created_at FROM categories ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_all_categories: {e}")
        return []


def update_category(category_id: int, new_name: str) -> Tuple[bool, str]:
    """
    تحديث اسم تصنيف
    
    @param category_id: معرف التصنيف
    @param new_name: الاسم الجديد
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # التحقق من وجود التصنيف
        cursor.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
        if not cursor.fetchone():
            conn.close()
            return False, "التصنيف غير موجود"
        
        cursor.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name.strip(), category_id))
        conn.commit()
        conn.close()
        
        return True, f"تم تحديث التصنيف إلى {new_name} بنجاح"
    except sqlite3.IntegrityError:
        return False, f"التصنيف {new_name} موجود بالفعل"
    except Exception as e:
        logger.error(f"خطأ في update_category: {e}")
        return False, str(e)


def delete_category(category_id: int) -> Tuple[bool, str]:
    """
    حذف تصنيف مع التحقق من عدم وجود منتجات مرتبطة به
    
    @param category_id: معرف التصنيف
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # التحقق من وجود التصنيف
        cursor.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
        cat = cursor.fetchone()
        if not cat:
            conn.close()
            return False, "التصنيف غير موجود"
        
        cat_name = cat[0]
        
        # التحقق من وجود منتجات مرتبطة بهذا التصنيف
        cursor.execute("SELECT COUNT(*) FROM products WHERE category = ?", (cat_name,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return False, f"لا يمكن حذف التصنيف {cat_name} لأنه مرتبط بـ {count} منتج(منتجات)"
        
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        conn.close()
        
        return True, f"تم حذف التصنيف {cat_name} بنجاح"
    except Exception as e:
        logger.error(f"خطأ في delete_category: {e}")
        return False, str(e)


# =============================================================
# ==================== دوال المصروفات =========================
# =============================================================

def add_expense(expense_type: str, amount: float, description: str = "",
                expense_date: str = None, paid_by: str = "Admin") -> Tuple[bool, str]:
    """
    إضافة مصروف جديد
    
    @param expense_type: نوع المصروف
    @param amount: المبلغ
    @param description: وصف المصروف
    @param expense_date: تاريخ المصروف (اختياري)
    @param paid_by: من قام بالدفع
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if expense_date is None:
            expense_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO expenses (expense_type, amount, description, expense_date, paid_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (expense_type.strip(), float(amount), description.strip(), expense_date, paid_by))
        
        conn.commit()
        conn.close()
        
        return True, f"تم إضافة المصروف {expense_type} بقيمة {amount:.2f} ج.م بنجاح"
    except Exception as e:
        logger.error(f"خطأ في add_expense: {e}")
        return False, str(e)


def get_expenses(date_from: str = None, date_to: str = None) -> List[Dict[str, Any]]:
    """
    جلب المصروفات مع إمكانية التصفية بالتاريخ
    
    @param date_from: تاريخ البداية (اختياري)
    @param date_to: تاريخ النهاية (اختياري)
    @return: قائمة من القواميس
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM expenses WHERE 1=1"
        params = []
        
        if date_from:
            query += " AND date(expense_date) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND date(expense_date) <= ?"
            params.append(date_to)
        
        query += " ORDER BY expense_date DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_expenses: {e}")
        return []


def delete_expense(expense_id: int) -> Tuple[bool, str]:
    """
    حذف مصروف
    
    @param expense_id: معرف المصروف
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,))
        if not cursor.fetchone():
            conn.close()
            return False, "المصروف غير موجود"
        
        cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        conn.close()
        
        return True, "تم حذف المصروف بنجاح"
    except Exception as e:
        logger.error(f"خطأ في delete_expense: {e}")
        return False, str(e)


def get_expenses_summary(date_from: str = None, date_to: str = None) -> Dict[str, Any]:
    """
    الحصول على ملخص المصروفات (الإجمالي مقسم حسب النوع)
    
    @param date_from: تاريخ البداية (اختياري)
    @param date_to: تاريخ النهاية (اختياري)
    @return: قاموس يحتوي على الإجمالي الكلي وتفاصيل حسب النوع
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT expense_type, SUM(amount) as total FROM expenses WHERE 1=1"
        params = []
        
        if date_from:
            query += " AND date(expense_date) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND date(expense_date) <= ?"
            params.append(date_to)
        
        query += " GROUP BY expense_type"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # الإجمالي الكلي
        total_query = "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE 1=1"
        total_params = []
        if date_from:
            total_query += " AND date(expense_date) >= ?"
            total_params.append(date_from)
        if date_to:
            total_query += " AND date(expense_date) <= ?"
            total_params.append(date_to)
        
        cursor.execute(total_query, total_params)
        total = cursor.fetchone()[0] or 0
        
        # أكبر بند
        cursor.execute(query + " ORDER BY total DESC LIMIT 1", params)
        largest = cursor.fetchone()
        
        conn.close()
        
        return {
            'total': float(total),
            'by_type': [dict(row) for row in rows],
            'count': len(rows),
            'largest_item': largest[0] if largest else 'لا يوجد',
            'largest_amount': float(largest[1]) if largest else 0
        }
    except Exception as e:
        logger.error(f"خطأ في get_expenses_summary: {e}")
        return {'total': 0, 'by_type': [], 'count': 0, 'largest_item': 'لا يوجد', 'largest_amount': 0}


# =============================================================
# ==================== دوال قوائم الأسعار (محدثة) =============
# =============================================================

def add_price_list(name: str, is_default: bool = False) -> Tuple[bool, str]:
    """
    إضافة قائمة أسعار جديدة
    
    @param name: اسم قائمة الأسعار
    @param is_default: جعلها القائمة الافتراضية
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # إذا كانت هذه القائمة هي الافتراضية، نلغي الافتراضية عن القوائم الأخرى
        if is_default:
            cursor.execute("UPDATE price_lists SET is_default = 0")
        
        cursor.execute(
            "INSERT INTO price_lists (name, is_default) VALUES (?, ?)",
            (name.strip(), 1 if is_default else 0)
        )
        
        conn.commit()
        conn.close()
        
        return True, f"تم إضافة قائمة الأسعار {name} بنجاح"
    except sqlite3.IntegrityError:
        return False, f"قائمة الأسعار {name} موجودة بالفعل"
    except Exception as e:
        logger.error(f"خطأ في add_price_list: {e}")
        return False, str(e)


def get_price_lists() -> List[Dict[str, Any]]:
    """
    جلب جميع قوائم الأسعار مع معلومات is_default
    
    @return: قائمة من القواميس
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, is_default, created_at FROM price_lists ORDER BY is_default DESC, name")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_price_lists: {e}")
        return []


def get_default_price_list() -> Optional[Dict[str, Any]]:
    """
    الحصول على قائمة الأسعار الافتراضية
    
    @return: قاموس القائمة الافتراضية أو None
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, name, is_default, created_at FROM price_lists WHERE is_default = 1 LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"خطأ في get_default_price_list: {e}")
        return None


def set_default_price_list(price_list_id: int) -> Tuple[bool, str]:
    """
    تعيين قائمة أسعار كافتراضية
    
    @param price_list_id: معرف قائمة الأسعار
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # التحقق من وجود القائمة
        cursor.execute("SELECT id FROM price_lists WHERE id = ?", (price_list_id,))
        if not cursor.fetchone():
            conn.close()
            return False, "قائمة الأسعار غير موجودة"
        
        # إلغاء التحديد الافتراضي عن جميع القوائم
        cursor.execute("UPDATE price_lists SET is_default = 0")
        
        # تعيين القائمة المحددة كافتراضية
        cursor.execute("UPDATE price_lists SET is_default = 1 WHERE id = ?", (price_list_id,))
        
        conn.commit()
        conn.close()
        
        return True, "تم تعيين قائمة الأسعار كافتراضية بنجاح"
    except Exception as e:
        logger.error(f"خطأ في set_default_price_list: {e}")
        return False, str(e)


def delete_price_list(price_list_id: int) -> Tuple[bool, str]:
    """
    حذف قائمة أسعار مع حذف جميع الأسعار المرتبطة بها
    
    @param price_list_id: معرف قائمة الأسعار
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # التحقق من عدم كونها القائمة الافتراضية
        cursor.execute("SELECT is_default FROM price_lists WHERE id = ?", (price_list_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "قائمة الأسعار غير موجودة"
        
        if row[0] == 1:
            conn.close()
            return False, "لا يمكن حذف قائمة الأسعار الافتراضية"
        
        # التحقق من عدم وجود منتجات مرتبطة
        cursor.execute("SELECT COUNT(*) FROM product_prices WHERE price_list_id = ?", (price_list_id,))
        count = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM price_lists WHERE id = ?", (price_list_id,))
        # سيتم حذف الأسعار المرتبطة تلقائياً بسبب CASCADE
        
        conn.commit()
        conn.close()
        
        return True, f"تم حذف قائمة الأسعار و {count} سعر مرتبط بها بنجاح"
    except Exception as e:
        logger.error(f"خطأ في delete_price_list: {e}")
        return False, str(e)


def set_product_price(product_id: int, price_list_id: int, price: float) -> Tuple[bool, str]:
    """
    تعيين سعر منتج في قائمة أسعار معينة
    
    @param product_id: معرف المنتج
    @param price_list_id: معرف قائمة الأسعار
    @param price: السعر
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO product_prices (product_id, price_list_id, price, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (product_id, price_list_id, float(price)))
        
        conn.commit()
        conn.close()
        
        return True, f"تم تعيين السعر بنجاح"
    except Exception as e:
        logger.error(f"خطأ في set_product_price: {e}")
        return False, str(e)


def get_product_price(product_id: int, price_list_id: int) -> Optional[float]:
    """
    الحصول على سعر منتج في قائمة أسعار معينة
    
    @param product_id: معرف المنتج
    @param price_list_id: معرف قائمة الأسعار
    @return: السعر أو None إذا لم يوجد
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT price FROM product_prices WHERE product_id = ? AND price_list_id = ?",
            (product_id, price_list_id)
        )
        row = cursor.fetchone()
        conn.close()
        
        return float(row[0]) if row else None
    except Exception as e:
        logger.error(f"خطأ في get_product_price: {e}")
        return None


def get_product_prices(product_id: int) -> Dict[int, float]:
    """
    الحصول على جميع أسعار منتج في جميع قوائم الأسعار
    
    @param product_id: معرف المنتج
    @return: قاموس {price_list_id: price}
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT price_list_id, price FROM product_prices WHERE product_id = ?",
            (product_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return {row[0]: float(row[1]) for row in rows}
    except Exception as e:
        logger.error(f"خطأ في get_product_prices: {e}")
        return {}


def get_product_price_for_list(product_id: int, price_list_id: int) -> Optional[float]:
    """
    الحصول على سعر منتج في قائمة أسعار معينة (نسخة متوافقة مع POS)
    
    @param product_id: معرف المنتج
    @param price_list_id: معرف قائمة الأسعار
    @return: السعر أو None
    """
    return get_product_price(product_id, price_list_id)


def get_price_lists_with_default() -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """
    جلب قوائم الأسعار مع تحديد معرف القائمة الافتراضية
    
    @return: (قائمة القواميس, معرف القائمة الافتراضية)
    """
    price_lists = get_price_lists()
    default_id = None
    
    for pl in price_lists:
        if pl.get('is_default', 0) == 1:
            default_id = pl['id']
            break
    
    return price_lists, default_id


# =============================================================
# ==================== دوال العروض والخصومات =================
# =============================================================

def add_promotion(name: str, promo_type: str, product_id: int = None,
                  category: str = None, buy_qty: int = 0, get_qty: int = 0,
                  discount_value: float = 0, is_active: bool = True,
                  start_date: str = None, end_date: str = None) -> Tuple[bool, str]:
    """
    إضافة عرض أو خصم جديد
    
    @param name: اسم العرض
    @param promo_type: نوع العرض (buy_x_get_y, percent, fixed_amount)
    @param product_id: معرف المنتج (اختياري)
    @param category: التصنيف (اختياري)
    @param buy_qty: الكمية المشتراة (لـ buy_x_get_y)
    @param get_qty: الكمية المجانية (لـ buy_x_get_y)
    @param discount_value: قيمة الخصم (لـ percent و fixed_amount)
    @param is_active: نشط أم لا
    @param start_date: تاريخ البدء
    @param end_date: تاريخ الانتهاء
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if start_date is None:
            start_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO promotions (
                name, promo_type, product_id, category, buy_qty, get_qty,
                discount_value, is_active, start_date, end_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name.strip(),
            promo_type,
            product_id,
            category,
            buy_qty,
            get_qty,
            float(discount_value),
            1 if is_active else 0,
            start_date,
            end_date
        ))
        
        conn.commit()
        conn.close()
        
        return True, f"تم إضافة العرض {name} بنجاح"
    except Exception as e:
        logger.error(f"خطأ في add_promotion: {e}")
        return False, str(e)


def get_active_promotions() -> List[Dict[str, Any]]:
    """
    جلب العروض النشطة حالياً
    
    @return: قائمة من القواميس
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM promotions
            WHERE is_active = 1
            AND (end_date IS NULL OR datetime(end_date) >= datetime('now'))
            AND (start_date IS NULL OR datetime(start_date) <= datetime('now'))
            ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_active_promotions: {e}")
        return []


def get_all_promotions() -> List[Dict[str, Any]]:
    """
    جلب جميع العروض
    
    @return: قائمة من القواميس
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM promotions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_all_promotions: {e}")
        return []


def update_promotion(promotion_id: int, **kwargs) -> Tuple[bool, str]:
    """
    تحديث عرض موجود
    
    @param promotion_id: معرف العرض
    @param kwargs: الحقول المراد تحديثها
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        allowed_fields = {
            'name': 'name',
            'promo_type': 'promo_type',
            'product_id': 'product_id',
            'category': 'category',
            'buy_qty': 'buy_qty',
            'get_qty': 'get_qty',
            'discount_value': 'discount_value',
            'is_active': 'is_active',
            'start_date': 'start_date',
            'end_date': 'end_date'
        }
        
        fields = []
        values = []
        
        for key, db_field in allowed_fields.items():
            if key in kwargs:
                fields.append(f"{db_field} = ?")
                values.append(kwargs[key])
        
        if not fields:
            conn.close()
            return True, "لا توجد تغييرات"
        
        values.append(promotion_id)
        query = f"UPDATE promotions SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        
        conn.commit()
        conn.close()
        
        return True, "تم تحديث العرض بنجاح"
    except Exception as e:
        logger.error(f"خطأ في update_promotion: {e}")
        return False, str(e)


def delete_promotion(promotion_id: int) -> Tuple[bool, str]:
    """
    حذف عرض
    
    @param promotion_id: معرف العرض
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM promotions WHERE id = ?", (promotion_id,))
        if not cursor.fetchone():
            conn.close()
            return False, "العرض غير موجود"
        
        cursor.execute("DELETE FROM promotions WHERE id = ?", (promotion_id,))
        conn.commit()
        conn.close()
        
        return True, "تم حذف العرض بنجاح"
    except Exception as e:
        logger.error(f"خطأ في delete_promotion: {e}")
        return False, str(e)


def get_product_promotions(product_id: int) -> Optional[Dict[str, Any]]:
    """
    جلب العرض المرتبط بمنتج معين (إذا كان نشطاً)
    
    @param product_id: معرف المنتج
    @return: قاموس العرض أو None
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM promotions
            WHERE product_id = ?
            AND is_active = 1
            AND (end_date IS NULL OR datetime(end_date) >= datetime('now'))
            AND (start_date IS NULL OR datetime(start_date) <= datetime('now'))
            ORDER BY created_at DESC
            LIMIT 1
        ''', (product_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"خطأ في get_product_promotions: {e}")
        return None


def get_applicable_promotion(product_id: int, category: str, quantity: float) -> Optional[Dict[str, Any]]:
    """
    التحقق من وجود عرض ساري على منتج أو تصنيف معين
    
    @param product_id: معرف المنتج
    @param category: تصنيف المنتج
    @param quantity: الكمية المشتراة
    @return: تفاصيل العرض أو None إذا لم يوجد عرض ساري
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # البحث عن عرض خاص بالمنتج أولاً
        cursor.execute('''
            SELECT * FROM promotions
            WHERE product_id = ?
            AND is_active = 1
            AND (end_date IS NULL OR datetime(end_date) >= datetime('now'))
            AND (start_date IS NULL OR datetime(start_date) <= datetime('now'))
            ORDER BY created_at DESC
            LIMIT 1
        ''', (product_id,))
        row = cursor.fetchone()
        
        # إذا لم يوجد عرض للمنتج، نبحث عن عرض للتصنيف
        if not row and category:
            cursor.execute('''
                SELECT * FROM promotions
                WHERE category = ?
                AND product_id IS NULL
                AND is_active = 1
                AND (end_date IS NULL OR datetime(end_date) >= datetime('now'))
                AND (start_date IS NULL OR datetime(start_date) <= datetime('now'))
                ORDER BY created_at DESC
                LIMIT 1
            ''', (category,))
            row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        promo = dict(row)
        
        # التحقق من شرط الكمية لـ buy_x_get_y
        if promo['promo_type'] == 'buy_x_get_y':
            if quantity < promo.get('buy_qty', 1):
                return None
        
        return promo
    except Exception as e:
        logger.error(f"خطأ في get_applicable_promotion: {e}")
        return None


# =============================================================
# ==================== دوال المنتجات ==========================
# =============================================================

def add_product(name: str, barcode: str = None, purchase_price: float = 0,
                sell_price: float = 0, stock: float = 0, category: str = "عام",
                alert_limit: int = 5, weight_unit: str = "قطعة",
                sub_unit_qty: int = 1, reorder_level: int = 10,
                has_expiry: bool = False, expiry_date: str = None,
                price_wholesale: float = 0, unit: str = "قطعة") -> Tuple[bool, str]:
    """
    إضافة منتج جديد مع دعم جميع الحقول المتقدمة
    
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        safe_stock = float(stock) if stock else 0.0
        safe_purchase = float(purchase_price) if purchase_price else 0.0
        safe_sell = float(sell_price) if sell_price else 0.0
        safe_wholesale = float(price_wholesale) if price_wholesale else 0.0
        safe_alert = int(alert_limit) if alert_limit else 5
        safe_reorder = int(reorder_level) if reorder_level else 10
        safe_sub_unit = int(sub_unit_qty) if sub_unit_qty else 1
        safe_weight_unit = weight_unit if weight_unit else 'قطعة'
        safe_unit = unit if unit else 'قطعة'
        safe_has_expiry = 1 if has_expiry else 0
        
        if not barcode or barcode.strip() == '':
            barcode = str(random.randint(1000000000000, 9999999999999))
        
        # التأكد من وجود التصنيف في جدول categories
        try:
            cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
        except Exception:
            pass
        
        cursor.execute('''
            INSERT INTO products (
                name, barcode, purchase_price, sell_price, price_wholesale,
                stock, actual_stock, category, alert_limit, reorder_level,
                weight_unit, unit, sub_unit_qty, has_expiry, expiry_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name.strip(),
            barcode.strip(),
            safe_purchase,
            safe_sell,
            safe_wholesale,
            safe_stock,
            safe_stock,
            category,
            safe_alert,
            safe_reorder,
            safe_weight_unit,
            safe_unit,
            safe_sub_unit,
            safe_has_expiry,
            expiry_date
        ))
        
        product_id = cursor.lastrowid
        
        if safe_stock > 0:
            cursor.execute('''
                INSERT INTO stock_movements (product_id, movement_type, in_qty, out_qty, balance, user_name, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (product_id, 'شراء', safe_stock, 0, safe_stock, 'Admin', 'إضافة منتج جديد'))
        
        conn.commit()
        return True, "تمت إضافة المنتج بنجاح"
        
    except sqlite3.IntegrityError:
        return False, "هذا الباركود مسجل مسبقاً"
    except Exception as e:
        logger.error(f"خطأ في add_product: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_all_products() -> List[Dict[str, Any]]:
    """جلب جميع المنتجات مرتبة أبجدياً - إرجاع قائمة من القواميس"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, name, barcode, purchase_price, sell_price, price_wholesale,
                   stock, actual_stock, category, alert_limit, reorder_level,
                   weight_unit, unit, sub_unit_qty, has_expiry, expiry_date
            FROM products
            ORDER BY name
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_all_products: {e}")
        return []
    finally:
        conn.close()


def get_product(product_id: int) -> Optional[Dict[str, Any]]:
    """جلب منتج واحد بالـ ID - إرجاع قاموس"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, name, barcode, purchase_price, sell_price, price_wholesale,
                   stock, actual_stock, category, alert_limit, reorder_level,
                   weight_unit, unit, sub_unit_qty, has_expiry, expiry_date
            FROM products WHERE id = ?
        ''', (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"خطأ في get_product: {e}")
        return None
    finally:
        conn.close()


def get_product_by_barcode(barcode: str) -> Optional[Dict[str, Any]]:
    """جلب منتج بالباركود - إرجاع قاموس"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, name, barcode, purchase_price, sell_price, price_wholesale,
                   stock, actual_stock, category, alert_limit, reorder_level,
                   weight_unit, unit, sub_unit_qty, has_expiry, expiry_date
            FROM products WHERE barcode = ?
        ''', (barcode,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"خطأ في get_product_by_barcode: {e}")
        return None
    finally:
        conn.close()


def update_product(product_id: int, **kwargs) -> bool:
    """
    تحديث بيانات منتج موجود مع دعم جميع الحقول
    
    @param product_id: معرف المنتج
    @param kwargs: الحقول المراد تحديثها
    @return: bool - نجاح العملية
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        old_product = get_product(product_id)
        old_stock = old_product['stock'] if old_product else 0
        old_category = old_product['category'] if old_product else 'عام'
        
        fields = []
        values = []
        
        allowed_fields = {
            'name': 'name',
            'barcode': 'barcode',
            'purchase_price': 'purchase_price',
            'sell_price': 'sell_price',
            'price_wholesale': 'price_wholesale',
            'stock': 'stock',
            'category': 'category',
            'alert_limit': 'alert_limit',
            'reorder_level': 'reorder_level',
            'weight_unit': 'weight_unit',
            'unit': 'unit',
            'sub_unit_qty': 'sub_unit_qty',
            'has_expiry': 'has_expiry',
            'expiry_date': 'expiry_date',
            'actual_stock': 'actual_stock'
        }
        
        for key, db_field in allowed_fields.items():
            if key in kwargs:
                fields.append(f"{db_field} = ?")
                values.append(kwargs[key])
        
        if not fields:
            return True
        
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(product_id)
        
        query = f"UPDATE products SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        
        new_category = kwargs.get('category', old_category)
        if new_category != old_category:
            try:
                cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (new_category,))
            except Exception:
                pass
        
        new_stock = kwargs.get('stock', old_stock)
        if new_stock != old_stock:
            diff = float(new_stock) - float(old_stock)
            if diff > 0:
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, movement_type, in_qty, out_qty, balance, user_name, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (product_id, 'تعديل مخزون', diff, 0, new_stock, 'Admin', 'تحديث الكمية'))
            else:
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, movement_type, in_qty, out_qty, balance, user_name, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (product_id, 'تعديل مخزون', 0, abs(diff), new_stock, 'Admin', 'تحديث الكمية'))
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"خطأ في update_product: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def delete_product(product_id: int) -> bool:
    """
    حذف منتج بالـ ID
    
    @return: bool - نجاح العملية
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        if not cursor.fetchone():
            return False
        
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"خطأ في delete_product: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def search_products(search_text: str) -> List[Dict[str, Any]]:
    """البحث عن منتجات بالاسم أو الباركود - إرجاع قائمة من القواميس"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, name, barcode, purchase_price, sell_price, price_wholesale,
                   stock, actual_stock, category, alert_limit, reorder_level,
                   weight_unit, unit, sub_unit_qty, has_expiry, expiry_date
            FROM products
            WHERE name LIKE ? OR barcode = ?
            ORDER BY name
        ''', (f'%{search_text}%', search_text))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في search_products: {e}")
        return []
    finally:
        conn.close()


def get_low_stock_products(threshold: int = None) -> List[Dict[str, Any]]:
    """جلب المنتجات التي وصلت لحد التنبيه أو حد الطلب الأدنى"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if threshold is not None:
            cursor.execute('''
                SELECT id, name, stock, alert_limit, reorder_level, weight_unit, unit, sub_unit_qty
                FROM products 
                WHERE stock <= ?
                ORDER BY stock ASC
            ''', (threshold,))
        else:
            cursor.execute('''
                SELECT id, name, stock, alert_limit, reorder_level, weight_unit, unit, sub_unit_qty
                FROM products 
                WHERE stock <= alert_limit OR stock <= reorder_level
                ORDER BY stock ASC
            ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_low_stock_products: {e}")
        return []
    finally:
        conn.close()


def get_all_low_stock_products() -> List[Dict[str, Any]]:
    """جلب جميع المنتجات التي وصلت لحد التنبيه - إرجاع قائمة من القواميس"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, name, stock, alert_limit, reorder_level, weight_unit, unit, sub_unit_qty
            FROM products 
            WHERE stock <= alert_limit
            ORDER BY stock ASC
        ''')
        rows = cursor.fetchall()
        alerts = []
        for row in rows:
            alerts.append({
                'id': row[0],
                'name': row[1],
                'stock': float(row[2]),
                'alert_limit': row[3],
                'reorder_level': row[4],
                'unit': row[6] if row[6] else 'قطعة',
                'weight_unit': row[5] if row[5] else 'قطعة',
                'sub_unit_qty': row[7] if len(row) > 7 and row[7] else 1
            })
        return alerts
    except Exception as e:
        logger.error(f"خطأ في get_all_low_stock_products: {e}")
        return []
    finally:
        conn.close()


def calculate_display_quantity(stock: float, sub_unit_qty: int,
                               weight_unit: str) -> Tuple[int, int]:
    """
    حساب وعرض الكمية ككراتين وقطع
    
    @param stock: إجمالي الكمية
    @param sub_unit_qty: عدد القطع في الكرتونة
    @param weight_unit: وحدة القياس
    @return: (كراتين, قطع فردية)
    """
    try:
        if weight_unit != "قطعة" or int(sub_unit_qty) <= 1:
            return 0, int(stock)
        
        sub_qty = int(sub_unit_qty)
        if sub_qty <= 0:
            sub_qty = 1
        
        cartons = int(stock) // sub_qty
        remaining_pieces = int(stock) % sub_qty
        return cartons, remaining_pieces
    except Exception:
        return 0, int(stock)


# =============================================================
# ==================== دوال العملاء ونقاط الولاء =============
# =============================================================

def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:
    """البحث عن عميل بالاسم"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM customers WHERE name = ?
        ''', (name.strip(),))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"خطأ في get_customer_by_name: {e}")
        return None


def add_loyalty_points(customer_name: str, points: int) -> Tuple[bool, str]:
    """
    إضافة نقاط ولاء لعميل
    
    @param customer_name: اسم العميل
    @param points: عدد النقاط المراد إضافتها
    @return: (bool, str)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE customers 
            SET loyalty_points = loyalty_points + ?
            WHERE name = ?
        ''', (points, customer_name.strip()))
        
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO customers (name, loyalty_points, total_debt, paid_amount)
                VALUES (?, ?, ?, ?)
            ''', (customer_name.strip(), points, 0, 0))
        
        conn.commit()
        conn.close()
        return True, f"تم إضافة {points} نقطة ولاء للعميل {customer_name}"
    except Exception as e:
        logger.error(f"خطأ في add_loyalty_points: {e}")
        return False, str(e)


def update_customer_transaction(customer_name: str, sale_amount: float) -> Tuple[bool, str]:
    """
    تحديث بيانات العميل بعد عملية شراء
    
    @param customer_name: اسم العميل
    @param sale_amount: قيمة الفاتورة
    @return: (bool, str)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        loyalty_points = int(sale_amount // 10)
        
        cursor.execute('''
            UPDATE customers 
            SET loyalty_points = loyalty_points + ?,
                last_transaction = CURRENT_TIMESTAMP
            WHERE name = ?
        ''', (loyalty_points, customer_name.strip()))
        
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO customers (name, loyalty_points, last_transaction)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (customer_name.strip(), loyalty_points))
        
        conn.commit()
        conn.close()
        return True, f"تم تحديث بيانات العميل وإضافة {loyalty_points} نقطة ولاء"
    except Exception as e:
        logger.error(f"خطأ في update_customer_transaction: {e}")
        return False, str(e)


# =============================================================
# ==================== دوال المشتريات =========================
# =============================================================

def add_purchase(supplier: str, invoice_number: str, payment_method: str,
                 items: List[Dict], subtotal: float, tax: float,
                 net_total: float) -> Tuple[bool, str]:
    """
    إضافة فاتورة شراء جديدة مع حساب متوسط التكلفة المرجح
    
    @param items: قائمة من (product_id, product_name, qty, price)
    @return: (bool, message)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        
        cursor.execute('''
            INSERT INTO purchase_invoices (
                invoice_number, supplier_name, total_amount, tax_amount,
                net_amount, payment_method, processed_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (invoice_number, supplier, subtotal, tax, net_total, payment_method, 'Admin'))
        
        invoice_id = cursor.lastrowid
        
        for item in items:
            product_id = item.get('product_id')
            product_name = item.get('product_name', '')
            qty = float(item.get('qty', 0))
            price = float(item.get('price', 0))
            total_price = qty * price
            
            cursor.execute('''
                INSERT INTO purchase_invoice_items (
                    invoice_id, product_id, product_name, quantity,
                    purchase_price, total_price
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (invoice_id, product_id, product_name, qty, price, total_price))
            
            if product_id:
                update_weighted_average_cost(product_id, qty, price)
                
                product = get_product(product_id)
                current_stock = product['stock'] if product else 0
                cursor.execute('''
                    INSERT INTO stock_movements (
                        product_id, movement_type, in_qty, out_qty, balance, user_name, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (product_id, 'شراء', qty, 0, current_stock, 'Admin',
                      f'فاتورة شراء {invoice_number}'))
        
        conn.commit()
        return True, f"تم حفظ فاتورة الشراء بنجاح رقم {invoice_number}"
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في add_purchase: {e}")
        return False, f"خطأ في حفظ فاتورة الشراء: {str(e)}"
    finally:
        if conn:
            conn.close()


def update_weighted_average_cost(product_id: int, new_qty: float, new_price: float) -> None:
    """
    تحديث سعر الشراء باستخدام معادلة متوسط التكلفة المرجح
    
    New Purchase Price = (Old Stock × Old Price + New Qty × New Price) / (Old Stock + New Qty)
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT stock, purchase_price FROM products WHERE id = ?
        ''', (product_id,))
        row = cursor.fetchone()
        
        if row:
            old_stock = float(row[0])
            old_price = float(row[1])
            
            total_quantity = old_stock + new_qty
            if total_quantity > 0:
                total_cost = (old_stock * old_price) + (new_qty * new_price)
                new_avg_price = total_cost / total_quantity
                
                cursor.execute('''
                    UPDATE products
                    SET purchase_price = ?, stock = stock + ?, actual_stock = actual_stock + ?
                    WHERE id = ?
                ''', (new_avg_price, new_qty, new_qty, product_id))
                conn.commit()
    except Exception as e:
        logger.error(f"خطأ في update_weighted_average_cost: {e}")
    finally:
        conn.close()


def get_purchase_invoices() -> List[Dict[str, Any]]:
    """جلب جميع فواتير المشتريات"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM purchase_invoices
            ORDER BY invoice_date DESC
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_purchase_invoices: {e}")
        return []
    finally:
        conn.close()


def get_purchase_invoice_items(invoice_id: int) -> List[Dict[str, Any]]:
    """جلب عناصر فاتورة شراء"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT * FROM purchase_invoice_items
            WHERE invoice_id = ?
        ''', (invoice_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_purchase_invoice_items: {e}")
        return []
    finally:
        conn.close()


# =============================================================
# ==================== دوال مرتجعات المشتريات =================
# =============================================================

def add_purchase_return(supplier_name: str, product_id: int,
                        product_name: str, quantity: float,
                        return_price: float, reason: str = "",
                        notes: str = "") -> Tuple[bool, str]:
    """
    إضافة مرتجع مشتريات مع خصم الكمية من المخزون
    
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        
        total_return = quantity * return_price
        return_number = f"PR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        cursor.execute('''
            INSERT INTO purchase_returns
                (return_number, supplier_name, total_return_amount, return_reason, processed_by, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (return_number, supplier_name, total_return, reason, 'Admin', notes))
        
        return_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO purchase_return_items (return_id, product_id, product_name, quantity, return_price)
            VALUES (?, ?, ?, ?, ?)
        ''', (return_id, product_id, product_name, quantity, return_price))
        
        if product_id:
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
            
            product = get_product(product_id)
            current_stock = product['stock'] if product else 0
            cursor.execute('''
                INSERT INTO stock_movements (
                    product_id, movement_type, in_qty, out_qty, balance, user_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (product_id, 'مرتجع مشتريات', 0, quantity, current_stock, 'Admin',
                  f'مرتجع مشتريات {return_number}'))
        
        conn.commit()
        return True, f"تم تسجيل مرتجع المشتريات بنجاح، رقم العملية: {return_number}"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في add_purchase_return: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_all_purchase_returns() -> List[Dict[str, Any]]:
    """جلب جميع مرتجعات المشتريات"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM purchase_returns ORDER BY return_date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_all_purchase_returns: {e}")
        return []
    finally:
        conn.close()


def delete_purchase_return(return_id: int) -> Tuple[bool, str]:
    """
    حذف مرتجع مشتريات مع إعادة الكميات للمخزون
    
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        
        cursor.execute('SELECT product_id, quantity FROM purchase_return_items WHERE return_id = ?', (return_id,))
        items = cursor.fetchall()
        
        if not items:
            conn.rollback()
            return False, "مرتجع المشتريات غير موجود"
        
        for item in items:
            if item[0]:
                cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?',
                               (float(item[1]), item[0]))
        
        cursor.execute('DELETE FROM purchase_return_items WHERE return_id = ?', (return_id,))
        cursor.execute('DELETE FROM purchase_returns WHERE id = ?', (return_id,))
        conn.commit()
        return True, f"تم حذف مرتجع المشتريات رقم {return_id} بنجاح"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في delete_purchase_return: {e}")
        return False, f"خطأ في حذف مرتجع المشتريات: {str(e)}"
    finally:
        if conn:
            conn.close()


# =============================================================
# ==================== دوال التوالف ===========================
# =============================================================

def add_damaged(product_id: int, product_name: str, quantity: float,
                damage_reason: str, loss_amount: float,
                notes: str = "") -> Tuple[bool, str]:
    """
    إضافة منتج تالف مع خصم الكمية من المخزون وحساب تكلفة الخسارة
    
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        
        quantity_val = float(quantity)
        loss_val = float(loss_amount)
        
        cursor.execute('''
            INSERT INTO damaged_products
                (product_id, product_name, quantity, quantity_unit, damage_reason,
                 loss_amount, reported_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product_id, product_name, quantity_val, 'قطعة',
              damage_reason, loss_val, 'Admin', notes))
        
        if product_id:
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity_val, product_id))
            
            product = get_product(product_id)
            current_stock = product['stock'] if product else 0
            cursor.execute('''
                INSERT INTO stock_movements (
                    product_id, movement_type, in_qty, out_qty, balance, user_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (product_id, 'تالف', 0, quantity_val, current_stock, 'Admin',
                  f'تلف المنتج - السبب: {damage_reason}'))
        
        conn.commit()
        return True, f"تم تسجيل المنتج التالف وخصمه من المخزون، قيمة الخسارة: {loss_val:.2f} ج.م"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في add_damaged: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_all_damaged() -> List[Dict[str, Any]]:
    """جلب جميع المنتجات التالفة"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT dp.*, p.name as current_product_name
            FROM damaged_products dp
            LEFT JOIN products p ON dp.product_id = p.id
            ORDER BY dp.damage_date DESC
        ''')
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_all_damaged: {e}")
        return []
    finally:
        conn.close()


def delete_damaged(damaged_id: int) -> Tuple[bool, str]:
    """
    حذف سجل منتج تالف
    
    @return: (bool, str) - (نجاح العملية, رسالة)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM damaged_products WHERE id = ?", (damaged_id,))
        if not cursor.fetchone():
            return False, "السجل غير موجود"
        
        cursor.execute("DELETE FROM damaged_products WHERE id = ?", (damaged_id,))
        conn.commit()
        return True, "تم حذف السجل بنجاح"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في delete_damaged: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def clear_all_damaged() -> Tuple[bool, str]:
    """حذف جميع سجلات التوالف"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM damaged_products")
        conn.commit()
        return True, "تم حذف جميع سجلات التوالف"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في clear_all_damaged: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_total_loss_from_damaged() -> float:
    """إجمالي الخسائر من المنتجات التالفة"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(loss_amount), 0) FROM damaged_products")
        total_loss = cursor.fetchone()[0]
        conn.close()
        return float(total_loss) if total_loss else 0
    except Exception as e:
        logger.error(f"خطأ في get_total_loss_from_damaged: {e}")
        return 0


# =============================================================
# ==================== دوال المبيعات ==========================
# =============================================================

def make_sale(items_list: List[Tuple], total_amount: float,
              discount: float = 0, payment_method: str = 'نقدي',
              customer_name: str = None, cash_paid: float = 0.0,
              visa_paid: float = 0.0) -> Tuple[bool, Any, List]:
    """
    تسجيل عملية بيع جديدة مع دعم البيع الآجل وتقسيم الدفع
    
    @param items_list: قائمة من (product_id, quantity, price_at_sale)
    @param total_amount: إجمالي الفاتورة بعد الخصم
    @param discount: قيمة الخصم الكلي
    @param payment_method: طريقة الدفع (نقدي / آجل)
    @param customer_name: اسم العميل (للبيع الآجل أو تتبع العملاء)
    @param cash_paid: المبلغ المدفوع كاش (لتقسيم الدفع)
    @param visa_paid: المبلغ المدفوع فيزا (لتقسيم الدفع)
    @return: (bool, sale_id_or_error, low_stock_alerts)
    """
    conn = None
    low_stock_alerts = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
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
            INSERT INTO sales (
                total_amount, discount, paid_amount, cash_paid, visa_paid,
                status, payment_method, return_status, sale_type, cashier_name,
                customer_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            float(total_amount),
            float(discount),
            paid_amount,
            float(cash_paid),
            float(visa_paid),
            status,
            payment_method,
            0,
            sale_type,
            'Admin',
            customer_name if customer_name else ''
        ))
        
        sale_id = cursor.lastrowid
        
        for product_id, quantity, price in items_list:
            qty = float(quantity)
            pr = float(price)
            
            cursor.execute('''
                INSERT INTO sale_items (sale_id, product_id, quantity, price_at_sale)
                VALUES (?, ?, ?, ?)
            ''', (sale_id, int(product_id), qty, pr))
            
            cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (qty, int(product_id)))
            
            product = get_product(int(product_id))
            current_stock = product['stock'] if product else 0
            cursor.execute('''
                INSERT INTO stock_movements (
                    product_id, movement_type, in_qty, out_qty, balance, user_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (int(product_id), 'بيع', 0, qty, current_stock, 'Admin',
                  f'فاتورة مبيعات رقم {sale_id}'))
            
            cursor.execute('''
                SELECT id, name, stock, alert_limit, reorder_level, weight_unit, unit, sub_unit_qty
                FROM products 
                WHERE id = ? AND stock <= alert_limit
            ''', (int(product_id),))
            low_stock_row = cursor.fetchone()
            
            if low_stock_row:
                low_stock_alerts.append({
                    'id': low_stock_row[0],
                    'name': low_stock_row[1],
                    'stock': float(low_stock_row[2]),
                    'alert_limit': low_stock_row[3],
                    'reorder_level': low_stock_row[4],
                    'unit': low_stock_row[6] if low_stock_row[6] else 'قطعة',
                    'weight_unit': low_stock_row[5] if low_stock_row[5] else 'قطعة',
                    'sub_unit_qty': low_stock_row[7] if len(low_stock_row) > 7 and low_stock_row[7] else 1
                })
        
        if payment_method == 'آجل' and customer_name:
            if not customer_name.strip():
                raise ValueError("اسم العميل مطلوب للبيع الآجل")
            
            cursor.execute('''
                INSERT INTO debts
                    (customer_name, amount, paid_amount, remaining_amount, sale_id, status, debt_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?)
            ''', (
                customer_name.strip(),
                float(total_amount),
                0.0,
                float(total_amount),
                sale_id,
                'مستحق',
                f'فاتورة آجلة رقم {sale_id} للعميل {customer_name}'
            ))
        
        if customer_name and customer_name.strip():
            loyalty_points = int(float(total_amount) // 10)
            if loyalty_points > 0:
                cursor.execute('''
                    UPDATE customers 
                    SET loyalty_points = loyalty_points + ?,
                        last_transaction = CURRENT_TIMESTAMP
                    WHERE name = ?
                ''', (loyalty_points, customer_name.strip()))
                
                if cursor.rowcount == 0:
                    cursor.execute('''
                        INSERT INTO customers (name, loyalty_points, total_debt, paid_amount, last_transaction)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (customer_name.strip(), loyalty_points, 0, 0))
        
        conn.commit()
        
        unique_alerts = []
        seen_names = set()
        for alert in low_stock_alerts:
            if alert['name'] not in seen_names:
                seen_names.add(alert['name'])
                unique_alerts.append(alert)
        
        return True, sale_id, unique_alerts
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في make_sale: {e}")
        return False, str(e), []
    finally:
        if conn:
            conn.close()


def get_all_sales() -> List[Dict[str, Any]]:
    """جلب جميع المبيعات"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT s.*,
                   strftime('%Y-%m-%d %H:%M:%S', s.sale_date) as sale_date,
                   d.customer_name as debt_customer,
                   d.remaining_amount
            FROM sales s
            LEFT JOIN debts d ON s.id = d.sale_id
            ORDER BY s.id DESC
        ''')
        rows = cursor.fetchall()
        result = []
        for row in rows:
            sale = dict(row)
            if not sale.get('customer_name') and sale.get('debt_customer'):
                sale['customer_name'] = sale['debt_customer']
            result.append(sale)
        return result
    except Exception as e:
        logger.error(f"خطأ في get_all_sales: {e}")
        return []
    finally:
        conn.close()


def get_sale_by_id(sale_id: int) -> Optional[Dict[str, Any]]:
    """جلب بيانات فاتورة مبيعات مع تفاصيلها"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, 
                   d.customer_name as debt_customer,
                   d.remaining_amount,
                   strftime('%Y-%m-%d %H:%M:%S', s.sale_date) as sale_date
            FROM sales s
            LEFT JOIN debts d ON s.id = d.sale_id
            WHERE s.id = ?
        ''', (sale_id,))
        
        sale = cursor.fetchone()
        if not sale:
            conn.close()
            return None
        
        sale_dict = dict(sale)
        
        if not sale_dict.get('customer_name') and sale_dict.get('debt_customer'):
            sale_dict['customer_name'] = sale_dict['debt_customer']
        
        cursor.execute('''
            SELECT si.product_id, p.name, si.quantity, si.price_at_sale
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.sale_id = ?
        ''', (sale_id,))
        
        items = cursor.fetchall()
        sale_dict['items'] = []
        for item in items:
            sale_dict['items'].append({
                'product_id': item[0],
                'name': item[1],
                'quantity': float(item[2]),
                'price_at_sale': float(item[3]),
                'price': float(item[3])
            })
        
        conn.close()
        return sale_dict
        
    except Exception as e:
        logger.error(f"خطأ في get_sale_by_id: {e}")
        return None


def get_sale_items(sale_id: int) -> List[Dict[str, Any]]:
    """جلب أصناف فاتورة معينة"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT si.*, p.name as product_name
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.sale_id = ?
        ''', (sale_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_sale_items: {e}")
        return []
    finally:
        conn.close()


def get_cash_sales() -> List[Dict[str, Any]]:
    """جلب المبيعات النقدية فقط"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT s.*,
                   d.customer_name as debt_customer,
                   strftime('%Y-%m-%d %H:%M:%S', s.sale_date) as sale_date
            FROM sales s
            LEFT JOIN debts d ON s.id = d.sale_id
            WHERE s.payment_method = 'نقدي'
            ORDER BY s.id DESC
        ''')
        rows = cursor.fetchall()
        result = []
        for row in rows:
            sale = dict(row)
            if not sale.get('customer_name') and sale.get('debt_customer'):
                sale['customer_name'] = sale['debt_customer']
            result.append(sale)
        return result
    except Exception as e:
        logger.error(f"خطأ في get_cash_sales: {e}")
        return []
    finally:
        conn.close()


def get_deferred_sales() -> List[Dict[str, Any]]:
    """جلب المبيعات الآجلة فقط"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT s.*,
                   d.customer_name as debt_customer,
                   d.remaining_amount,
                   d.status as debt_status,
                   strftime('%Y-%m-%d %H:%M:%S', s.sale_date) as sale_date
            FROM sales s
            JOIN debts d ON s.id = d.sale_id
            WHERE s.payment_method = 'آجل'
            ORDER BY s.id DESC
        ''')
        rows = cursor.fetchall()
        result = []
        for row in rows:
            sale = dict(row)
            if not sale.get('customer_name') and sale.get('debt_customer'):
                sale['customer_name'] = sale['debt_customer']
            result.append(sale)
        return result
    except Exception as e:
        logger.error(f"خطأ في get_deferred_sales: {e}")
        return []
    finally:
        conn.close()


def get_returned_sales() -> List[Dict[str, Any]]:
    """جلب فواتير المبيعات التي تحتوي على مرتجعات"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT 
                s.id,
                s.total_amount,
                s.discount,
                s.paid_amount,
                s.status,
                s.payment_method,
                s.return_status,
                s.sale_type,
                strftime('%Y-%m-%d %H:%M:%S', s.sale_date) as sale_date,
                s.customer_name,
                d.customer_name as debt_customer,
                sr.return_number,
                sr.total_return_amount,
                sr.return_reason,
                sr.return_date
            FROM sales s
            INNER JOIN sales_returns sr ON s.id = sr.sale_id
            LEFT JOIN debts d ON s.id = d.sale_id
            ORDER BY sr.return_date DESC
        ''')
        rows = cursor.fetchall()
        result = []
        for row in rows:
            sale = dict(row)
            if not sale.get('customer_name') and sale.get('debt_customer'):
                sale['customer_name'] = sale['debt_customer']
            result.append(sale)
        return result
    except Exception as e:
        logger.error(f"خطأ في get_returned_sales: {e}")
        return []
    finally:
        conn.close()


def get_sale_details(sale_id: int) -> List[Dict[str, Any]]:
    """جلب تفاصيل المنتجات داخل فاتورة مبيعات"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                si.id,
                si.sale_id,
                si.product_id,
                p.name as name,
                si.quantity,
                si.price_at_sale,
                (si.quantity * si.price_at_sale) as total_price
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.sale_id = ?
        ''', (sale_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_sale_details: {e}")
        return []
    finally:
        conn.close()


def delete_sale(sale_id: int) -> Tuple[bool, str]:
    """حذف فاتورة مع جميع بياناتها المرتبطة"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        
        cursor.execute('SELECT product_id, quantity FROM sale_items WHERE sale_id = ?', (sale_id,))
        current_items = cursor.fetchall()
        
        if not current_items:
            conn.rollback()
            return False, "الفاتورة غير موجودة"
        
        cursor.execute('SELECT sale_type FROM sales WHERE id = ?', (sale_id,))
        sale_data = cursor.fetchone()
        sale_type = sale_data[0] if sale_data else 'نقدي'
        
        if sale_type != 'مرتجع':
            for product_id, remaining_qty in current_items:
                if remaining_qty and float(remaining_qty) > 0:
                    cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?',
                                   (float(remaining_qty), product_id))
        
        cursor.execute('DELETE FROM sales_return_items WHERE return_id IN (SELECT id FROM sales_returns WHERE sale_id = ?)', (sale_id,))
        cursor.execute('DELETE FROM sales_returns WHERE sale_id = ?', (sale_id,))
        cursor.execute('DELETE FROM sale_items WHERE sale_id = ?', (sale_id,))
        cursor.execute('DELETE FROM debt_payments WHERE debt_id IN (SELECT id FROM debts WHERE sale_id = ?)', (sale_id,))
        cursor.execute('DELETE FROM debts WHERE sale_id = ?', (sale_id,))
        cursor.execute('DELETE FROM sales WHERE id = ?', (sale_id,))
        
        conn.commit()
        return True, f"تم حذف الفاتورة رقم {sale_id} بنجاح"
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في delete_sale: {e}")
        return False, f"خطأ في حذف الفاتورة: {str(e)}"
    finally:
        if conn:
            conn.close()


# =============================================================
# ==================== دوال مرتجعات المبيعات =================
# =============================================================

def process_sales_return(sale_id: int, items: List[Tuple],
                         reason: str = "", processed_by: str = "Admin") -> Tuple[bool, str]:
    """
    معالجة مرتجع مبيعات - كلي أو جزئي
    
    @param sale_id: رقم الفاتورة الأصلية
    @param items: قائمة من (product_id, quantity, return_price)
    @param reason: سبب المرتجع
    @param processed_by: من قام بالمعالجة
    @return: (bool, message)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        
        return_number = f"SR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        total_return = sum(qty * price for _, qty, price in items)
        
        cursor.execute('''
            INSERT INTO sales_returns
                (sale_id, return_number, total_return_amount, return_reason, processed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (sale_id, return_number, total_return, reason, processed_by))
        
        return_id = cursor.lastrowid
        
        for product_id, quantity, return_price in items:
            qty = float(quantity)
            price = float(return_price)
            
            cursor.execute('''
                INSERT INTO sales_return_items (return_id, product_id, quantity, return_price)
                VALUES (?, ?, ?, ?)
            ''', (return_id, product_id, qty, price))
            
            cursor.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (qty, product_id))
            
            product = get_product(product_id)
            current_stock = product['stock'] if product else 0
            cursor.execute('''
                INSERT INTO stock_movements (
                    product_id, movement_type, in_qty, out_qty, balance, user_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (product_id, 'مرتجع مبيعات', qty, 0, current_stock, processed_by,
                  f'مرتجع مبيعات {return_number}'))
        
        cursor.execute('''
            UPDATE sales SET return_status = 1, sale_type = 'مرتجع'
            WHERE id = ?
        ''', (sale_id,))
        
        cursor.execute('''
            SELECT SUM(quantity) FROM sale_items WHERE sale_id = ?
        ''', (sale_id,))
        total_sold = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT SUM(quantity) FROM sales_return_items WHERE return_id = ?
        ''', (return_id,))
        total_returned = cursor.fetchone()[0] or 0
        
        if total_returned >= total_sold:
            cursor.execute('''
                UPDATE sales SET return_status = 2, sale_type = 'مرتجع كلي'
                WHERE id = ?
            ''', (sale_id,))
        
        conn.commit()
        return True, f"تم تنفيذ مرتجع المبيعات بنجاح، رقم العملية: {return_number}"
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في process_sales_return: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


# =============================================================
# ==================== دوال الديون والعملاء ===================
# =============================================================

def get_all_customers() -> List[Dict[str, Any]]:
    """جلب جميع العملاء مع ديونهم"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                c.*,
                COALESCE((SELECT SUM(remaining_amount) FROM debts WHERE customer_name = c.name AND status != 'مدفوع'), 0) as remaining,
                (SELECT COUNT(*) FROM debts WHERE customer_name = c.name AND status != 'مدفوع') as active_debts
            FROM customers c
            ORDER BY c.name
        ''')
        rows = cursor.fetchall()
        result = []
        for row in rows:
            customer = dict(row)
            if 'remaining' not in customer:
                customer['remaining'] = 0
            if 'active_debts' not in customer:
                customer['active_debts'] = 0
            result.append(customer)
        return result
    except Exception as e:
        logger.error(f"خطأ في get_all_customers: {e}")
        return []
    finally:
        conn.close()


def add_customer(name: str, phone: str = "", debt: float = 0) -> Tuple[bool, str]:
    """إضافة عميل جديد"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO customers (name, phone, total_debt)
            VALUES (?, ?, ?)
        ''', (name, phone, debt))
        conn.commit()
        return True, f"تم إضافة العميل {name} بنجاح"
    except Exception as e:
        logger.error(f"خطأ في add_customer: {e}")
        return False, str(e)
    finally:
        conn.close()


def add_customer_debt(customer_id: int, amount: float) -> Tuple[bool, str]:
    """تسجيل دين جديد على عميل موجود"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name, phone FROM customers WHERE id = ?", (customer_id,))
        customer = cursor.fetchone()
        if not customer:
            return False, "العميل غير موجود"

        cursor.execute('''
            INSERT INTO debts (customer_name, customer_phone, amount, paid_amount, remaining_amount, status, notes)
            VALUES (?, ?, ?, 0, ?, 'مستحق', ?)
        ''', (
            customer['name'],
            customer['phone'],
            amount,
            amount,
            f'دين مضاف يدويًا للعميل ID: {customer_id}'
        ))

        conn.commit()
        return True, f"تم تسجيل دين بقيمة {amount:.2f} ج.م"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في add_customer_debt: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def delete_customer(customer_id: int) -> Tuple[bool, str]:
    """حذف عميل"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        return True, "تم حذف العميل بنجاح"
    except Exception as e:
        logger.error(f"خطأ في delete_customer: {e}")
        return False, str(e)
    finally:
        conn.close()


def add_customer_payment(customer_id: int, amount: float) -> Tuple[bool, str]:
    """تسجيل دفعة من عميل"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        
        cursor.execute('''
            UPDATE customers 
            SET total_debt = total_debt - ?, paid_amount = paid_amount + ?
            WHERE id = ?
        ''', (amount, amount, customer_id))
        
        cursor.execute("SELECT name FROM customers WHERE id = ?", (customer_id,))
        customer = cursor.fetchone()
        if customer:
            cursor.execute('''
                INSERT INTO debts (customer_name, amount, paid_amount, remaining_amount, status, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (customer[0], amount, amount, 0, 'مدفوع', f'دفعة من عميل ID: {customer_id}'))
        
        conn.commit()
        return True, f"تم تسجيل دفعة بقيمة {amount:.2f} ج.م"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في add_customer_payment: {e}")
        return False, str(e)
    finally:
        conn.close()


def get_all_suppliers() -> List[Dict[str, Any]]:
    """جلب جميع الموردين"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM suppliers
            ORDER BY name
        ''')
        rows = cursor.fetchall()
        suppliers = []
        for row in rows:
            sup = dict(row)
            sup['remaining'] = sup.get('total_balance', 0) - sup.get('paid_amount', 0)
            suppliers.append(sup)
        return suppliers
    except Exception as e:
        logger.error(f"خطأ في get_all_suppliers: {e}")
        return []
    finally:
        conn.close()


def add_supplier(name: str, contact: str = "", phone: str = "", balance: float = 0) -> Tuple[bool, str]:
    """إضافة مورد جديد"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO suppliers (name, contact_person, phone, total_balance)
            VALUES (?, ?, ?, ?)
        ''', (name, contact, phone, balance))
        conn.commit()
        return True, f"تم إضافة المورد {name} بنجاح"
    except Exception as e:
        logger.error(f"خطأ في add_supplier: {e}")
        return False, str(e)
    finally:
        conn.close()

def delete_supplier(supplier_id: int) -> Tuple[bool, str]:
    """حذف مورد"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
        conn.commit()
        return True, "تم حذف المورد بنجاح"
    except Exception as e:
        logger.error(f"خطأ في delete_supplier: {e}")
        return False, str(e)
    finally:
        conn.close()


def update_supplier_payment_date(supplier_id: int, date: str, amount: float) -> Tuple[bool, str]:
    """تحديث موعد سداد مورد مع تسجيل دفعة"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        
        cursor.execute('''
            UPDATE suppliers 
            SET next_payment_date = ?, paid_amount = paid_amount + ?
            WHERE id = ?
        ''', (date, amount, supplier_id))
        
        conn.commit()
        return True, f"تم تحديث موعد السداد إلى {date} بقيمة {amount:.2f} ج.م"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في update_supplier_payment_date: {e}")
        return False, str(e)
    finally:
        conn.close()


def add_supplier_balance(supplier_id: int, amount: float) -> Tuple[bool, str]:
    """تسجيل مديونية جديدة لمورد مع تحديث الرصيد"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')

        cursor.execute("SELECT id, total_balance FROM suppliers WHERE id = ?", (supplier_id,))
        row = cursor.fetchone()
        if not row:
            return False, "المورد غير موجود"

        current_balance = float(row[1]) if row[1] else 0.0
        new_balance = current_balance + float(amount)

        cursor.execute("UPDATE suppliers SET total_balance = ? WHERE id = ?", (new_balance, supplier_id))
        conn.commit()
        return True, f"تم تسجيل مديونية بقيمة {amount:.2f} ج.م (الرصيد الجديد: {new_balance:.2f} ج.م)"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في add_supplier_balance: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_all_debts() -> List[Dict[str, Any]]:
    """جلب جميع الديون"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
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
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_all_debts: {e}")
        return []
    finally:
        conn.close()


def add_debt_payment(debt_id: int, payment_amount: float,
                     payment_method: str = "نقدي", notes: str = "") -> Tuple[bool, str]:
    """تسجيل دفعة على دين"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        
        payment_val = float(payment_amount)
        
        if payment_val <= 0:
            return False, "يجب أن يكون مبلغ الدفعة أكبر من صفر"
        
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
            UPDATE debts SET status = 'مدفوع'
            WHERE id = ? AND remaining_amount <= 0
        ''', (debt_id,))
        
        conn.commit()
        return True, "تم تسجيل الدفعة بنجاح"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في add_debt_payment: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


# =============================================================
# ==================== دوال التحويلات ==========================
# =============================================================

def add_transfer(product_id: int, product_name: str, quantity: float,
                 from_warehouse: str, to_warehouse: str,
                 reason: str = "", notes: str = "") -> Tuple[bool, str]:
    """إضافة عملية تحويل مخزني"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        quantity_val = float(quantity)
        transfer_number = f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        cursor.execute('BEGIN TRANSACTION')
        cursor.execute('''
            INSERT INTO stock_transfers
                (transfer_number, product_id, product_name, quantity,
                 from_warehouse, to_warehouse, transfer_reason, transferred_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transfer_number, product_id, product_name, quantity_val,
              from_warehouse, to_warehouse, reason, 'Admin', notes))
        
        product = get_product(product_id)
        current_stock = product['stock'] if product else 0
        cursor.execute('''
            INSERT INTO stock_movements (
                product_id, movement_type, in_qty, out_qty, balance, user_name, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (product_id, 'تحويل', 0, quantity_val, current_stock, 'Admin',
              f'تحويل من {from_warehouse} إلى {to_warehouse}'))
        
        conn.commit()
        return True, f"تم تسجيل التحويل المخزني بنجاح، رقم العملية: {transfer_number}"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في add_transfer: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_all_transfers() -> List[Dict[str, Any]]:
    """جلب جميع تحويلات المخزون"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM stock_transfers ORDER BY transfer_date DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_all_transfers: {e}")
        return []
    finally:
        conn.close()


def delete_transfer(transfer_id: int) -> Tuple[bool, str]:
    """حذف عملية نقل مخزني"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM stock_transfers WHERE id = ?", (transfer_id,))
        if not cursor.fetchone():
            return False, "عملية النقل غير موجودة"
        
        cursor.execute("DELETE FROM stock_transfers WHERE id = ?", (transfer_id,))
        conn.commit()
        return True, f"تم حذف عملية النقل رقم {transfer_id} بنجاح"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في delete_transfer: {e}")
        return False, f"خطأ في حذف عملية النقل: {str(e)}"
    finally:
        if conn:
            conn.close()


def clear_all_transfers() -> Tuple[bool, str]:
    """حذف جميع عمليات النقل"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stock_transfers")
        conn.commit()
        return True, "تم حذف جميع عمليات النقل"
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"خطأ في clear_all_transfers: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


# =============================================================
# ==================== دوال سجل الحركة (Stock Card) ===========
# =============================================================

def get_stock_movements(product_id: int = None,
                        start_date: str = None,
                        end_date: str = None) -> List[Dict[str, Any]]:
    """
    جلب سجل حركة المنتج مع إمكانية التصفية
    
    @param product_id: معرف المنتج (اختياري)
    @param start_date: تاريخ البداية (اختياري)
    @param end_date: تاريخ النهاية (اختياري)
    @return: قائمة من القواميس
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = '''
            SELECT sm.*, p.name as product_name
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.id
            WHERE 1=1
        '''
        params = []
        
        if product_id:
            query += " AND sm.product_id = ?"
            params.append(product_id)
        
        if start_date:
            query += " AND date(sm.date_time) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date(sm.date_time) <= ?"
            params.append(end_date)
        
        query += " ORDER BY sm.date_time DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_stock_movements: {e}")
        return []
    finally:
        conn.close()


# =============================================================
# ==================== دوال سجل النشاط ========================
# =============================================================

def log_user_activity(username: str, action: str, details: str = "") -> bool:
    """تسجيل نشاط في سجل الأنشطة (متوافق مع الواجهات القديمة)"""
    return log_activity(None, action, details, username)


def get_activity_log(limit: int = 100) -> List[Dict[str, Any]]:
    """جلب سجل الأنشطة"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM activity_log
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"خطأ في get_activity_log: {e}")
        return []


def clear_activity_log() -> bool:
    """مسح سجل الأنشطة"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM activity_log")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"خطأ في clear_activity_log: {e}")
        return False


# =============================================================
# ==================== دوال الإحصائيات ========================
# =============================================================

def get_dashboard_stats() -> Dict[str, Any]:
    """
    إحصائيات لوحة التحكم الرئيسية - بيانات حقيقية من قاعدة البيانات
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) 
            FROM sales 
            WHERE date(sale_date) = date('now') 
            AND sale_type != 'مرتجع'
        """)
        daily_total = float(cursor.fetchone()[0] or 0)
        
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) 
            FROM sales 
            WHERE date(sale_date) = date('now') 
            AND payment_method = 'نقدي' 
            AND sale_type != 'مرتجع'
        """)
        daily_cash = float(cursor.fetchone()[0] or 0)
        
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) 
            FROM sales 
            WHERE date(sale_date) = date('now') 
            AND payment_method = 'آجل' 
            AND sale_type != 'مرتجع'
        """)
        daily_deferred = float(cursor.fetchone()[0] or 0)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM sales 
            WHERE date(sale_date) = date('now')
        """)
        daily_invoices = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COALESCE(SUM(remaining_amount), 0) FROM debts WHERE status != 'مدفوع'")
        total_debts = float(cursor.fetchone()[0] or 0)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM products 
            WHERE stock <= alert_limit
        """)
        low_stock_count = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT id, name, stock, alert_limit, unit
            FROM products 
            WHERE stock <= alert_limit
            ORDER BY stock ASC
            LIMIT 10
        """)
        low_stock_items = []
        for row in cursor.fetchall():
            low_stock_items.append({
                'id': row[0],
                'name': row[1],
                'stock': float(row[2]),
                'alert_limit': row[3],
                'unit': row[4] if row[4] else 'قطعة'
            })
        
        conn.close()
        
        return {
            'daily_total': daily_total,
            'daily_cash': daily_cash,
            'daily_deferred': daily_deferred,
            'daily_invoices': daily_invoices,
            'total_debts': total_debts,
            'low_stock_count': low_stock_count,
            'low_stock_items': low_stock_items
        }
    except Exception as e:
        logger.error(f"خطأ في get_dashboard_stats: {e}")
        return {
            'daily_total': 0,
            'daily_cash': 0,
            'daily_deferred': 0,
            'daily_invoices': 0,
            'total_debts': 0,
            'low_stock_count': 0,
            'low_stock_items': []
        }


def get_today_cash_sales() -> float:
    """إجمالي المبيعات النقدية اليوم"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(total_amount), 0) FROM sales WHERE date(sale_date) = date('now') AND payment_method='نقدي' AND sale_type != 'مرتجع'"
        )
        total = cursor.fetchone()[0]
        conn.close()
        return float(total) if total else 0
    except Exception as e:
        logger.error(f"خطأ في get_today_cash_sales: {e}")
        return 0


def get_today_deferred_sales() -> float:
    """إجمالي المبيعات الآجلة اليوم"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(total_amount), 0) FROM sales WHERE date(sale_date) = date('now') AND payment_method='آجل' AND sale_type != 'مرتجع'"
        )
        total = cursor.fetchone()[0]
        conn.close()
        return float(total) if total else 0
    except Exception as e:
        logger.error(f"خطأ في get_today_deferred_sales: {e}")
        return 0


def get_total_outstanding_debts() -> float:
    """إجمالي الديون المستحقة"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(remaining_amount), 0) FROM debts WHERE status != 'مدفوع'")
        total_debts = cursor.fetchone()[0]
        conn.close()
        return float(total_debts) if total_debts else 0
    except Exception as e:
        logger.error(f"خطأ في get_total_outstanding_debts: {e}")
        return 0


def get_customer_loyalty_points(customer_name: str) -> int:
    """الحصول على نقاط الولاء لعميل"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT loyalty_points FROM customers WHERE name = ?", (customer_name.strip(),))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception as e:
        logger.error(f"خطأ في get_customer_loyalty_points: {e}")
        return 0


# =============================================================
# ==================== تهيئة تلقائية ==========================
# =============================================================

# تهيئة قاعدة البيانات عند استيراد الملف
initialize_system()

logger.info("تم تهيئة قاعدة البيانات بنجاح")