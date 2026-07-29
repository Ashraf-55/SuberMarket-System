# ================= sales_history_ui.py - سجل المبيعات المتطور (نسخة مع إصلاح النص العربي النهائي) =================
"""
شاشة سجل المبيعات والبحث المتقدم
تدعم التصفية حسب الفترة الزمنية، الكاشير، العميل
مع إمكانية طباعة الفواتير وتصدير PDF مع دعم اللغة العربية
📌 تعمل فقط مع قاعدة البيانات الفعلية - لا توجد بيانات افتراضية
"""

import os
import logging
import subprocess
import time
import traceback
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel, 
                             QLineEdit, QFrame, QDialog, QTextEdit, QScrollArea,
                             QComboBox, QSizePolicy, QDateEdit, QGroupBox,
                             QCheckBox, QApplication, QFileDialog)
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer, QDate, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm, letter, A4
from reportlab.lib.units import mm as mm_unit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

from back.database import (get_all_sales, get_cash_sales, get_deferred_sales, 
                           get_returned_sales, get_sale_details, delete_sale,
                           get_sale_by_id, log_user_activity, get_connection)

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== استيراد مكتبات العربية ==========
ARABIC_SUPPORT = False
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    pass

ARABIC_FONT_AVAILABLE = False
try:
    # محاولة العثور على خط عربي في مسارات متعددة
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/arialuni.ttf",
        "C:/Windows/Fonts/Simplified_Arabic.ttf",
        "C:/Windows/Fonts/Arabic Typesetting.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Helvetica.ttf",
        "/System/Library/Fonts/Arial.ttf"
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
                ARABIC_FONT_AVAILABLE = True
                logger.info(f"تم تحميل الخط العربي من: {font_path}")
                break
            except Exception as e:
                logger.warning(f"فشل تحميل الخط من {font_path}: {e}")
                continue
    
    # إذا لم يتم العثور على خط عربي، حاول استخدام الخط الافتراضي مع دعم يونيكود
    if not ARABIC_FONT_AVAILABLE:
        try:
            # محاولة استخدام خط مدمج مع دعم يونيكود
            from reportlab.pdfbase import pdfmetrics
            from reportlab.lib.fonts import addMapping
            # استخدام Helvetica مع دعم يونيكود
            ARABIC_FONT_AVAILABLE = True
            logger.warning("لم يتم العثور على خط عربي، سيتم استخدام الخط الافتراضي")
        except:
            pass
            
except Exception as e:
    logger.error(f"خطأ في تحميل الخط العربي: {e}")

# ========== حل مشكلة reportlab md5 ==========
try:
    import hashlib
    from reportlab.pdfbase import pdfdoc
    try:
        pdfdoc.md5 = lambda usedforsecurity=False: hashlib.md5()
    except Exception as e:
        logger.error(f"تعذر تصحيح دالة md5 المستخدمة في reportlab: {e}")
except Exception as e:
    logger.error(f"تعذر استيراد أو تصحيح وحدة md5 الخاصة بـ reportlab: {e}")

# ========== الألوان الثابتة ==========
COLORS = {
    'bg_dark': '#F3F7F7',
    'bg_sidebar': '#FFFFFF',
    'bg_card': '#FFFFFF',
    'text': '#1e293b',
    'text_muted': '#64748b',
    'accent': '#0284c7',
    'accent_hover': '#0369a1',
    'success': '#16a34a',
    'success_hover': '#15803d',
    'danger': '#dc2626',
    'danger_hover': '#b91c1c',
    'warning': '#d97706',
    'warning_hover': '#b45309',
    'info': '#0284c7',
    'info_hover': '#0369a1',
    'border': '#cbd5e1',
    'deferred_color': '#d97706',
    'cash_color': '#16a34a',
    'return_color': '#9333ea',
    'loyalty_color': '#db2777',
    'purple': '#7c3aed'
}


# ========== رسالة Toast موحدة ==========
class ToastMessage(QLabel):
    def __init__(self, parent, message, duration=2500):
        # لون موحد للجميع
        toast_color = COLORS['bg_card']
        border_color = COLORS['accent']
        
        super().__init__(message, parent)
        self.duration = duration
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {toast_color};
                color: {COLORS['text']};
                border-radius: 12px;
                padding: 14px 24px;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid {border_color};
            }}
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumHeight(50)
        self.setMaximumWidth(420)
        
        # حساب الموقع بناءً على حجم الشاشة
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setFixedWidth(min(350, screen_geometry.width() - 40))
        
        x = (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.height() - 120
        self.move(x, y)
        self.raise_()
        self.show()
        
        QTimer.singleShot(duration, self.fade_out)
    
    def fade_out(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(400)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()


# ========== دوال معالجة النصوص العربية المحسنة ==========
def reshape_arabic_text(text):
    """إعادة تشكيل النص العربي للعرض الصحيح"""
    if not text:
        return ""
    text = str(text)
    if not ARABIC_SUPPORT:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except Exception as e:
        logger.warning(f"خطأ في reshape_arabic_text: {e}")
        return text


def get_arabic_font():
    """الحصول على اسم الخط العربي المناسب"""
    if ARABIC_FONT_AVAILABLE:
        return 'ArabicFont'
    return 'Helvetica'


def get_absolute_path(filename):
    """إنشاء المسار المطلق للملف مع إنشاء المجلدات إذا لزم الأمر"""
    abs_path = os.path.abspath(filename)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    return abs_path


# ========== نافذة عرض التفاصيل (معدلة لعرض كمية المرتجع) ==========
class SaleDetailsDialog(QDialog):
    def __init__(self, sale_id, details, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📄 تفاصيل الفاتورة رقم {sale_id}")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.4)
        height = int(screen_geometry.height() * 0.5)
        self.setMinimumSize(int(screen_geometry.width() * 0.35), int(screen_geometry.height() * 0.4))
        self.resize(max(500, width), max(450, height))
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
            }}
            QTextEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                padding: 15px;
                font-size: 13px;
                font-family: 'Segoe UI', 'Arial', monospace;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel(f"📋 تفاصيل الفاتورة #{sale_id}")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # ====== تعديل الريسبونسيف: تغليف محتوى التفاصيل بـ ScrollArea ======
        text_scroll = QScrollArea()
        text_scroll.setWidgetResizable(True)
        text_scroll.setStyleSheet("border: none; background-color: transparent;")
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        
        # الحصول على معلومات المرتجع من قاعدة البيانات
        return_info = self.get_return_info(sale_id)
        formatted_text = self.format_details_text(sale_id, details, return_info)
        self.details_text.setPlainText(formatted_text)
        
        text_scroll.setWidget(self.details_text)
        layout.addWidget(text_scroll)
        
        close_btn = QPushButton("إغلاق")
        close_btn.setMinimumHeight(40)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_hover']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def get_return_info(self, sale_id):
        """الحصول على معلومات المرتجع للفاتورة"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # الحصول على جميع مرتجعات هذه الفاتورة
            cursor.execute('''
                SELECT 
                    sr.id,
                    sr.sale_id,
                    sr.product_id,
                    p.name as product_name,
                    sr.quantity,
                    sr.return_price,
                    sr.total_amount,
                    sr.return_date,
                    sr.reason,
                    sr.status
                FROM sales_returns sr
                JOIN products p ON sr.product_id = p.id
                WHERE sr.sale_id = ?
                AND sr.status = 'completed'
            ''', (sale_id,))
            
            returns = cursor.fetchall()
            conn.close()
            return returns
        except Exception as e:
            logger.error(f"خطأ في get_return_info: {e}")
            return []
    
    def format_details_text(self, sale_id, details, return_info):
        """تنسيق نص التفاصيل مع عرض معلومات المرتجع"""
        text = ""
        text += "═" * 55 + "\n"
        text += f"  فاتورة رقم: {sale_id}\n"
        text += "═" * 55 + "\n\n"
        text += "المنتجات:\n"
        text += "─" * 55 + "\n"
        
        # جمع كميات المرتجع لكل منتج
        return_quantities = {}
        if return_info:
            for ret in return_info:
                product_id = ret[2]  # product_id
                qty = ret[4]  # quantity
                return_quantities[product_id] = return_quantities.get(product_id, 0) + qty
        
        # عرض المنتجات مع كميات البيع والمرتجع
        for idx, d in enumerate(details, 1):
            if isinstance(d, dict):
                product_id = d.get('product_id')
                product_name = d.get('name', '')
                quantity = d.get('quantity', 0)
                price = d.get('price_at_sale', 0)
            else:
                product_id = d[0] if len(d) > 0 else None
                product_name = d[1] if len(d) > 1 else ""
                quantity = d[2] if len(d) > 2 else 0
                price = d[3] if len(d) > 3 else 0
            
            item_total = quantity * price
            text += f"{idx}. {product_name}\n"
            text += f"   الكمية المباعة: {quantity}\n"
            
            # عرض كمية المرتجع إذا وجدت
            returned_qty = return_quantities.get(product_id, 0)
            if returned_qty > 0:
                text += f"   ⚠️ الكمية المرتجعة: {returned_qty}\n"
                remaining = quantity - returned_qty
                text += f"   ✅ المتبقي بعد المرتجع: {remaining}\n"
            
            text += f"   السعر: {price:,.2f} ج.م\n"
            text += f"   الإجمالي: {item_total:,.2f} ج.م\n"
            text += "─" * 55 + "\n"
        
        if details:
            first_item = details[0]
            if isinstance(first_item, dict):
                total_amount = float(first_item.get('total_amount', 0))
                discount = float(first_item.get('discount', 0))
                sale_type = first_item.get('sale_type', 'نقدي')
                loyalty_points = first_item.get('loyalty_points', 0)
            else:
                total_amount = float(first_item[4]) if len(first_item) > 4 and first_item[4] else 0
                discount = float(first_item[5]) if len(first_item) > 5 and first_item[5] else 0
                sale_type = first_item[7] if len(first_item) > 7 else 'نقدي'
                loyalty_points = first_item[8] if len(first_item) > 8 else 0
            
            subtotal = 0
            for d in details:
                if isinstance(d, dict):
                    subtotal += d.get('quantity', 0) * d.get('price_at_sale', 0)
                else:
                    subtotal += d[2] * d[3] if len(d) > 3 else 0
            
            text += "\n" + "═" * 55 + "\n"
            text += f"المجموع الفرعي: {subtotal:,.2f} ج.م\n"
            if discount > 0:
                text += f"الخصم: {discount:,.2f} ج.م\n"
            text += f"الإجمالي النهائي: {total_amount:,.2f} ج.م\n"
            text += f"نوع الفاتورة: {sale_type}\n"
            if loyalty_points != 0:
                text += f"نقاط الولاء: {loyalty_points:+d}\n"
            
            # عرض ملخص المرتجعات
            if return_info:
                total_return_amount = sum(r[6] for r in return_info)  # total_amount
                text += "\n" + "─" * 55 + "\n"
                text += f"🔄 ملخص المرتجعات:\n"
                text += f"   عدد المرتجعات: {len(return_info)}\n"
                text += f"   إجمالي المبلغ المسترد: {total_return_amount:,.2f} ج.م\n"
            
            text += "═" * 55 + "\n"
        return text


# ========== نافذة سجل الفواتير (معدلة) ==========
class SalesHistoryWindow(QWidget):
    sale_deleted = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.all_sales = []
        self.displayed_sales = []
        self.current_filter = 'all'
        self.init_ui()
        self.load_sales_from_db()

    def show_toast(self, message, duration=2500):
        ToastMessage(self, message, duration)
    
    def show_success_toast(self, message):
        self.show_toast(message)
    
    def show_warning_toast(self, message):
        self.show_toast(message)
    
    def show_info_toast(self, message):
        self.show_toast(message)
    
    def show_danger_toast(self, message):
        self.show_toast(message)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                padding: 12px;
                margin: 15px 15px 0 15px;
            }}
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(10)
        
        title_row = QHBoxLayout()
        title = QLabel("📜 سجل الفواتير السابقة")
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['accent']};")
        title_row.addWidget(title)
        title_row.addStretch()
        
        self.btn_export_report = QPushButton("📊 تصدير تقرير PDF")
        self.btn_export_report.setMinimumHeight(38)
        self.btn_export_report.setMinimumWidth(160)
        self.btn_export_report.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['purple']};
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_hover']};
            }}
        """)
        self.btn_export_report.clicked.connect(self.export_full_report_pdf)
        title_row.addWidget(self.btn_export_report)
        
        header_layout.addLayout(title_row)
        
        filter_row1 = QHBoxLayout()
        filter_row1.setSpacing(12)
        
        filter_row1.addWidget(QLabel("📅 من:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 30px;
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        filter_row1.addWidget(self.start_date)
        
        filter_row1.addWidget(QLabel("إلى:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 30px;
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        filter_row1.addWidget(self.end_date)
        
        self.btn_search = QPushButton("🔍 بحث وتحديث")
        self.btn_search.setMinimumHeight(32)
        self.btn_search.setMinimumWidth(130)
        self.btn_search.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        self.btn_search.clicked.connect(self.load_sales_from_db)
        filter_row1.addWidget(self.btn_search)
        
        filter_row1.addStretch()
        header_layout.addLayout(filter_row1)
        
        filter_row2 = QHBoxLayout()
        filter_row2.setSpacing(12)
        
        filter_row2.addWidget(QLabel("👤 الكاشير:"))
        self.cashier_filter = QComboBox()
        self.cashier_filter.addItem("الكل")
        self.cashier_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 5px 10px;
                min-height: 30px;
                min-width: 120px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['accent']};
            }}
        """)
        filter_row2.addWidget(self.cashier_filter)
        
        filter_row2.addWidget(QLabel("👥 العميل:"))
        self.customer_filter = QComboBox()
        self.customer_filter.addItem("الكل")
        self.customer_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 5px 10px;
                min-height: 30px;
                min-width: 120px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['accent']};
            }}
        """)
        filter_row2.addWidget(self.customer_filter)
        
        filter_row2.addStretch()
        header_layout.addLayout(filter_row2)
        
        filter_row3 = QHBoxLayout()
        filter_row3.setSpacing(8)
        
        filter_label = QLabel("نوع الفاتورة:")
        filter_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold; font-size: 12px;")
        filter_row3.addWidget(filter_label)
        
        self.btn_all = QPushButton("📋 الكل")
        self.btn_all.setMinimumWidth(75)
        self.btn_all.setMinimumHeight(32)
        self.btn_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: {COLORS['info_hover']}; }}
        """)
        self.btn_all.clicked.connect(lambda: self.set_filter('all'))
        filter_row3.addWidget(self.btn_all)
        
        self.btn_cash = QPushButton("💰 نقدي")
        self.btn_cash.setMinimumWidth(75)
        self.btn_cash.setMinimumHeight(32)
        self.btn_cash.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['cash_color']};
                color: white;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: #16a34a; }}
        """)
        self.btn_cash.clicked.connect(lambda: self.set_filter('cash'))
        filter_row3.addWidget(self.btn_cash)
        
        self.btn_deferred = QPushButton("📋 آجل")
        self.btn_deferred.setMinimumWidth(75)
        self.btn_deferred.setMinimumHeight(32)
        self.btn_deferred.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['deferred_color']};
                color: white;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: #d97706; }}
        """)
        self.btn_deferred.clicked.connect(lambda: self.set_filter('deferred'))
        filter_row3.addWidget(self.btn_deferred)
        
        self.btn_returned = QPushButton("🔄 مرتجع")
        self.btn_returned.setMinimumWidth(75)
        self.btn_returned.setMinimumHeight(32)
        self.btn_returned.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['return_color']};
                color: white;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: #9333ea; }}
        """)
        self.btn_returned.clicked.connect(lambda: self.set_filter('returned'))
        filter_row3.addWidget(self.btn_returned)
        
        filter_row3.addStretch()
        
        search_label = QLabel("🔍 بحث:")
        search_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold; font-size: 12px;")
        filter_row3.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("رقم الفاتورة، العميل، الكاشير...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setMinimumHeight(35)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.search_input.textChanged.connect(self.apply_filters)
        filter_row3.addWidget(self.search_input)
        
        header_layout.addLayout(filter_row3)
        layout.addWidget(header_frame)

        # ===== جدول مع دعم Scroll =====
        table_container = QScrollArea()
        table_container.setWidgetResizable(True)
        table_container.setStyleSheet("border: none; background-color: transparent;")
        
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "رقم الفاتورة", "الإجمالي", "الخصم", "التاريخ", 
            "الكاشير", "العميل", "نقاط الولاء", "الإجراءات", ""
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 260)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        self.table.setColumnWidth(8, 75)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(55)
        
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                font-size: 12px;
                gridline-color: {COLORS['border']};
            }}
            QTableWidget::item {{
                padding: 10px 6px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(56, 189, 248, 0.2);
            }}
            QHeaderView::section {{
                background-color: #0f172a;
                color: white;
                padding: 10px 6px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }}
            QTableCornerButton::section {{
                background-color: #0f172a;
                border: none;
            }}
        """)
        
        table_container.setWidget(self.table)
        layout.addWidget(table_container)
        self.clear_table()

    def clear_table(self):
        self.table.setRowCount(0)
        self.displayed_sales = []

    def load_sales_from_db(self):
        try:
            if self.current_filter == 'all':
                self.all_sales = get_all_sales()
            elif self.current_filter == 'cash':
                self.all_sales = get_cash_sales()
            elif self.current_filter == 'deferred':
                self.all_sales = get_deferred_sales()
            elif self.current_filter == 'returned':
                self.all_sales = get_returned_sales()
            else:
                self.all_sales = get_all_sales()
            
            self.update_filter_lists()
            self.apply_filters()
            
            if len(self.displayed_sales) == 0:
                self.show_warning_toast("🔍 لا توجد فواتير في هذه الفترة")
            else:
                self.show_success_toast(f"✅ تم العثور على {len(self.displayed_sales)} فاتورة")
        except Exception as e:
            logger.error(f"خطأ في load_sales_from_db: {e}")
            self.show_warning_toast(f"❌ خطأ في تحميل الفواتير: {str(e)}")

    def update_filter_lists(self):
        cashiers = set()
        customers = set()
        
        for sale in self.all_sales:
            if isinstance(sale, dict):
                cashier = sale.get('cashier_name', '')
                customer = sale.get('customer_name', '')
                if cashier:
                    cashiers.add(cashier)
                if customer:
                    customers.add(customer)
        
        self.cashier_filter.blockSignals(True)
        self.cashier_filter.clear()
        self.cashier_filter.addItem("الكل")
        for c in sorted(cashiers):
            self.cashier_filter.addItem(c)
        self.cashier_filter.blockSignals(False)
        
        self.customer_filter.blockSignals(True)
        self.customer_filter.clear()
        self.customer_filter.addItem("الكل")
        for c in sorted(customers):
            self.customer_filter.addItem(c)
        self.customer_filter.blockSignals(False)

    def format_datetime(self, date_value):
        if not date_value:
            return "غير محدد"
        try:
            if isinstance(date_value, datetime):
                return date_value.strftime("%d-%m-%Y %I:%M %p")
            if isinstance(date_value, str):
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d"]:
                    try:
                        dt = datetime.strptime(date_value, fmt)
                        return dt.strftime("%d-%m-%Y %I:%M %p")
                    except (ValueError, TypeError):
                        continue
                return date_value
            return str(date_value)
        except Exception as e:
            logger.error(f"خطأ في format_datetime: {e}")
            return str(date_value)

    def create_centered_item(self, text, alignment=Qt.AlignCenter):
        item = QTableWidgetItem(text)
        item.setTextAlignment(alignment | Qt.AlignVCenter)
        return item

    def set_filter(self, filter_type):
        self.current_filter = filter_type
        self.update_button_styles(filter_type)
        self.load_sales_from_db()

    def update_button_styles(self, active):
        reset_style = """
            QPushButton {
                background-color: %s;
                color: white;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: %s; }
        """
        self.btn_all.setStyleSheet(reset_style % (COLORS['info'], COLORS['info_hover']))
        self.btn_cash.setStyleSheet(reset_style % (COLORS['cash_color'], '#16a34a'))
        self.btn_deferred.setStyleSheet(reset_style % (COLORS['deferred_color'], '#d97706'))
        self.btn_returned.setStyleSheet(reset_style % (COLORS['return_color'], '#9333ea'))
        
        active_style = "border: 2px solid %s;"
        if active == 'all':
            self.btn_all.setStyleSheet(self.btn_all.styleSheet() + active_style % COLORS['accent'])
        elif active == 'cash':
            self.btn_cash.setStyleSheet(self.btn_cash.styleSheet() + active_style % COLORS['accent'])
        elif active == 'deferred':
            self.btn_deferred.setStyleSheet(self.btn_deferred.styleSheet() + active_style % COLORS['accent'])
        elif active == 'returned':
            self.btn_returned.setStyleSheet(self.btn_returned.styleSheet() + active_style % COLORS['accent'])

    def apply_filters(self):
        try:
            search_text = self.search_input.text().strip().lower()
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()
            cashier_filter = self.cashier_filter.currentText()
            customer_filter = self.customer_filter.currentText()
            
            filtered_sales = []
            
            for sale in self.all_sales:
                if not isinstance(sale, dict):
                    continue
                
                sale_type = sale.get('sale_type', 'نقدي')
                sale_date = sale.get('sale_date')
                cashier_name = sale.get('cashier_name', '')
                customer_name = sale.get('customer_name', '')
                sale_id = sale.get('id', '')
                
                if self.current_filter == 'cash' and sale_type != 'نقدي':
                    continue
                if self.current_filter == 'deferred' and sale_type != 'آجل':
                    continue
                if self.current_filter == 'returned' and sale_type not in ['مرتجع', 'مرتجع كلي']:
                    continue
                
                if isinstance(sale_date, datetime):
                    sale_date = sale_date.date()
                if isinstance(sale_date, str):
                    try:
                        sale_date = datetime.strptime(sale_date[:10], "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        sale_date = None
                
                if sale_date:
                    if sale_date < start_date or sale_date > end_date:
                        continue
                
                if cashier_filter != "الكل" and cashier_name != cashier_filter:
                    continue
                
                if customer_filter != "الكل" and customer_name != customer_filter:
                    continue
                
                if search_text:
                    search_match = (
                        search_text in str(sale_id) or
                        search_text in str(customer_name).lower() or
                        search_text in str(cashier_name).lower()
                    )
                    if not search_match:
                        continue
                
                filtered_sales.append(sale)
            
            self.displayed_sales = filtered_sales
            self.display_sales(filtered_sales)
            
        except Exception as e:
            logger.error(f"خطأ في apply_filters: {e}")
            self.show_warning_toast(f"❌ خطأ في تطبيق الفلاتر: {str(e)}")

    def display_sales(self, sales_list):
        self.table.setRowCount(0)
        
        if not sales_list:
            return
        
        for sale in sales_list:
            if not isinstance(sale, dict):
                continue
                
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            sale_id = sale.get('id')
            total_val = float(sale.get('total_amount', 0))
            discount_val = float(sale.get('discount', 0))
            sale_date = sale.get('sale_date')
            payment_method = sale.get('payment_method', 'نقدي')
            sale_type = sale.get('sale_type', 'نقدي')
            customer_name = sale.get('customer_name', '')
            cashier_name = sale.get('cashier_name', '')
            loyalty_points = sale.get('loyalty_points', 0)
            
            is_returned = (sale_type in ['مرتجع', 'مرتجع كلي'])
            
            id_item = self.create_centered_item(str(sale_id))
            if is_returned:
                id_item.setForeground(QColor(COLORS['return_color']))
            self.table.setItem(row, 0, id_item)
            
            total_item = QTableWidgetItem(f"{total_val:,.2f} ج.م")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            total_item.setForeground(QColor(COLORS['success']))
            total_item.setFont(QFont("Segoe UI", 11, QFont.Bold))
            if is_returned:
                total_item.setForeground(QColor(COLORS['return_color']))
            self.table.setItem(row, 1, total_item)
            
            discount_item = QTableWidgetItem(f"{discount_val:,.2f} ج.م")
            discount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if discount_val > 0:
                discount_item.setForeground(QColor(COLORS['warning']))
            self.table.setItem(row, 2, discount_item)
            
            formatted_date = self.format_datetime(sale_date)
            date_item = self.create_centered_item(formatted_date)
            self.table.setItem(row, 3, date_item)
            
            cashier_item = self.create_centered_item(cashier_name)
            self.table.setItem(row, 4, cashier_item)
            
            customer_item = self.create_centered_item(customer_name)
            if payment_method == 'آجل':
                customer_item.setForeground(QColor(COLORS['deferred_color']))
                customer_item.setToolTip(f"فاتورة آجلة - العميل: {customer_name}")
            self.table.setItem(row, 5, customer_item)
            
            loyalty_item = self.create_centered_item(f"{loyalty_points:+d}" if loyalty_points != 0 else "0")
            if loyalty_points > 0:
                loyalty_item.setForeground(QColor(COLORS['loyalty_color']))
                loyalty_item.setToolTip(f"{loyalty_points} نقطة ولاء مستحقة")
            elif loyalty_points < 0:
                loyalty_item.setForeground(QColor(COLORS['danger']))
                loyalty_item.setToolTip(f"{abs(loyalty_points)} نقطة ولاء مستهلكة")
            self.table.setItem(row, 6, loyalty_item)
            
            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            layout_btns = QHBoxLayout(container)
            layout_btns.setAlignment(Qt.AlignCenter)
            layout_btns.setSpacing(4)
            layout_btns.setContentsMargins(2, 4, 2, 4)
            
            btn_print = QPushButton("🖨️")
            btn_print.setFixedSize(30, 28)
            btn_print.setCursor(Qt.PointingHandCursor)
            btn_print.setToolTip("طباعة الفاتورة")
            btn_print.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['success']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
            """)
            btn_print.clicked.connect(lambda ch, sid=sale_id: self.reprint_invoice(sid))
            
            btn_details = QPushButton("📋")
            btn_details.setFixedSize(30, 28)
            btn_details.setCursor(Qt.PointingHandCursor)
            btn_details.setToolTip("عرض التفاصيل")
            btn_details.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['info']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {COLORS['info_hover']}; }}
            """)
            btn_details.clicked.connect(lambda ch, sid=sale_id: self.show_details(sid))
            
            btn_pdf = QPushButton("📄")
            btn_pdf.setFixedSize(30, 28)
            btn_pdf.setCursor(Qt.PointingHandCursor)
            btn_pdf.setToolTip("تصدير PDF")
            btn_pdf.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {COLORS['warning_hover']}; }}
            """)
            btn_pdf.clicked.connect(lambda ch, sid=sale_id: self.export_pdf(sid))
            
            layout_btns.addWidget(btn_print)
            layout_btns.addWidget(btn_details)
            layout_btns.addWidget(btn_pdf)
            
            self.table.setCellWidget(row, 7, container)
            
            btn_delete = QPushButton("🗑️")
            btn_delete.setFixedSize(32, 28)
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.setToolTip("حذف الفاتورة")
            btn_delete.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['danger']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {COLORS['danger_hover']}; }}
            """)
            btn_delete.clicked.connect(lambda ch, sid=sale_id: self.delete_sale(sid))
            self.table.setCellWidget(row, 8, btn_delete)

    def delete_sale(self, sale_id):
        try:
            success, msg = delete_sale(sale_id)
            if success:
                log_user_activity('Admin', 'حذف فاتورة', f'تم حذف الفاتورة رقم {sale_id}')
                self.show_success_toast(f"✅ {msg}")
                self.load_sales_from_db()
            else:
                self.show_warning_toast(f"❌ {msg}")
        except Exception as e:
            logger.error(f"خطأ في delete_sale: {e}")
            self.show_warning_toast(f"❌ خطأ في حذف الفاتورة: {str(e)}")

    def get_sale_by_id(self, sale_id):
        for sale in self.all_sales:
            if sale.get('id') == sale_id:
                return sale
        return None

    def show_details(self, sale_id):
        try:
            details = get_sale_details(sale_id)
            if not details:
                self.show_warning_toast("لا توجد تفاصيل لهذه الفاتورة")
                return
            dialog = SaleDetailsDialog(sale_id, details, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"خطأ في show_details: {e}")
            self.show_warning_toast(f"خطأ في عرض التفاصيل: {str(e)}")

    def reprint_invoice(self, sale_id):
        try:
            logger.info(f"بدء طباعة الفاتورة رقم {sale_id}")
            
            details = get_sale_details(sale_id)
            
            if not details:
                logger.error("لا توجد تفاصيل للفاتورة")
                self.show_warning_toast("لا توجد تفاصيل لهذه الفاتورة")
                return
            
            logger.info(f"تم العثور على {len(details)} منتج في الفاتورة")
            
            items = []
            total_amount = 0
            discount = 0
            sale_type = "نقدي"
            customer_name = ""
            cashier_name = ""
            
            for d in details:
                if isinstance(d, dict):
                    product_name = d.get('name', '')
                    quantity = d.get('quantity', 0)
                    price_at_sale = d.get('price_at_sale', 0)
                    total_amount = float(d.get('total_amount', 0))
                    discount = float(d.get('discount', 0))
                    sale_type = d.get('sale_type', 'نقدي')
                    customer_name = d.get('customer_name', '')
                    cashier_name = d.get('cashier_name', '')
                else:
                    product_name = d[1] if len(d) > 1 else ""
                    quantity = d[2] if len(d) > 2 else 0
                    price_at_sale = d[3] if len(d) > 3 else 0
                    total_amount = float(d[4]) if len(d) > 4 and d[4] else 0
                    discount = float(d[5]) if len(d) > 5 and d[5] else 0
                    sale_type = d[7] if len(d) > 7 else 'نقدي'
                    customer_name = d[6] if len(d) > 6 else ''
                    cashier_name = d[8] if len(d) > 8 else ''
                
                items.append((product_name, quantity, price_at_sale))
            
            if not items:
                logger.error("لا توجد منتجات في الفاتورة")
                self.show_warning_toast("لا توجد منتجات في هذه الفاتورة")
                return
            
            subtotal = sum(q * p for _, q, p in items)
            
            timestamp = int(time.time())
            filename = f"invoices/invoice_{sale_id}_{timestamp}.pdf"
            
            abs_filename = self.generate_professional_invoice(
                filename, sale_id, items, total_amount, discount, subtotal, 
                sale_type, customer_name, cashier_name
            )
            
            logger.info(f"تم توليد PDF بنجاح: {abs_filename}")
            
            try:
                if os.name == 'nt':
                    os.startfile(abs_filename)
                else:
                    subprocess.run(['xdg-open', abs_filename], check=False)
                self.show_success_toast(f"✅ تمت طباعة الفاتورة رقم {sale_id}")
                logger.info(f"تم فتح الملف: {abs_filename}")
            except Exception as e:
                logger.error(f"تعذر فتح الملف تلقائياً: {e}")
                self.show_info_toast(f"تم حفظ الفاتورة في: {abs_filename}")
            
        except Exception as e:
            logger.error(f"خطأ في reprint_invoice: {e}")
            error_msg = str(e)
            if "PermissionError" in error_msg or "usedforsecurity" in error_msg:
                self.show_warning_toast("⚠️ تعذر إنشاء PDF بسبب تعارض في الملفات. الرجاء إغلاق الملف المفتوح والمحاولة مرة أخرى")
            else:
                self.show_warning_toast(f"⚠️ خطأ في طباعة الفاتورة: {error_msg[:100]}")

    def export_pdf(self, sale_id):
        try:
            logger.info(f"بدء تصدير الفاتورة رقم {sale_id}")
            
            details = get_sale_details(sale_id)
            
            if not details:
                logger.error("لا توجد تفاصيل للفاتورة")
                self.show_warning_toast("لا توجد تفاصيل لهذه الفاتورة")
                return
            
            logger.info(f"تم العثور على {len(details)} منتج في الفاتورة")
            
            items = []
            total_amount = 0
            discount = 0
            sale_type = "نقدي"
            customer_name = ""
            cashier_name = ""
            
            for d in details:
                if isinstance(d, dict):
                    product_name = d.get('name', '')
                    quantity = d.get('quantity', 0)
                    price_at_sale = d.get('price_at_sale', 0)
                    total_amount = float(d.get('total_amount', 0))
                    discount = float(d.get('discount', 0))
                    sale_type = d.get('sale_type', 'نقدي')
                    customer_name = d.get('customer_name', '')
                    cashier_name = d.get('cashier_name', '')
                else:
                    product_name = d[1] if len(d) > 1 else ""
                    quantity = d[2] if len(d) > 2 else 0
                    price_at_sale = d[3] if len(d) > 3 else 0
                    total_amount = float(d[4]) if len(d) > 4 and d[4] else 0
                    discount = float(d[5]) if len(d) > 5 and d[5] else 0
                    sale_type = d[7] if len(d) > 7 else 'نقدي'
                    customer_name = d[6] if len(d) > 6 else ''
                    cashier_name = d[8] if len(d) > 8 else ''
                
                items.append((product_name, quantity, price_at_sale))
            
            if not items:
                logger.error("لا توجد منتجات في الفاتورة")
                self.show_warning_toast("لا توجد منتجات في هذه الفاتورة")
                return
            
            subtotal = sum(q * p for _, q, p in items)
            
            timestamp = int(time.time())
            filename = f"exports/invoice_{sale_id}_{timestamp}.pdf"
            
            abs_filename = self.generate_professional_invoice(
                filename, sale_id, items, total_amount, discount, subtotal, 
                sale_type, customer_name, cashier_name
            )
            
            logger.info(f"تم تصدير PDF بنجاح: {abs_filename}")
            self.show_success_toast(f"✅ تم تصدير الفاتورة إلى PDF")
            
            try:
                if os.name == 'nt':
                    os.startfile(abs_filename)
                else:
                    subprocess.run(['xdg-open', abs_filename], check=False)
            except Exception as e:
                logger.error(f"تعذر فتح الملف تلقائياً: {e}")
                self.show_info_toast(f"تم حفظ الفاتورة في: {abs_filename}")
                
        except Exception as e:
            logger.error(f"خطأ في export_pdf: {e}")
            error_msg = str(e)
            if "PermissionError" in error_msg or "usedforsecurity" in error_msg:
                self.show_warning_toast("⚠️ تعذر إنشاء PDF بسبب تعارض في الملفات. الرجاء إغلاق الملف المفتوح والمحاولة مرة أخرى")
            else:
                self.show_warning_toast(f"⚠️ خطأ في تصدير الفاتورة: {error_msg[:100]}")

    def generate_professional_invoice(self, filename, sale_id, items, total, discount, subtotal, 
                                      sale_type="نقدي", customer_name="", cashier_name=""):
        """توليد فاتورة PDF مع دعم كامل للغة العربية - نسخة محسنة"""
        try:
            if not items:
                raise Exception("لا توجد منتجات في الفاتورة للطباعة")
            
            abs_filename = get_absolute_path(filename)
            
            LINE_HEIGHT = 7 * mm
            TOP_MARGIN = 15 * mm
            BOTTOM_MARGIN = 15 * mm
            LEFT_MARGIN = 5 * mm
            RIGHT_MARGIN = 5 * mm
            PAGE_WIDTH = 80 * mm
            
            page_height = (len(items) * 8 * mm) + (130 * mm)
            page_height = max(180 * mm, page_height)
            
            c = canvas.Canvas(abs_filename, pagesize=(PAGE_WIDTH, page_height))
            
            # محاولة استخدام الخط العربي
            font_name = get_arabic_font()
            try:
                c.setFont(font_name, 11)
            except Exception as e:
                logger.warning(f"تعذر استخدام الخط {font_name}: {e}")
                c.setFont('Helvetica', 11)
                font_name = 'Helvetica'
            
            def draw_arabic_text(x, y, text, font_size=10, bold=False):
                if not text:
                    return
                try:
                    # استخدام الخط مع دعم العربية
                    if font_name == 'ArabicFont':
                        c.setFont(font_name, font_size)
                    elif bold and font_name == 'Helvetica':
                        c.setFont('Helvetica-Bold', font_size)
                    else:
                        c.setFont(font_name, font_size)
                except Exception as e:
                    logger.warning(f"تعذر ضبط الخط في draw_arabic_text: {e}")
                    c.setFont('Helvetica', font_size)
                
                # معالجة النص العربي
                processed_text = reshape_arabic_text(text)
                c.drawString(x, y, processed_text)
            
            def draw_arabic_centered(x, y, text, font_size=11, bold=False):
                if not text:
                    return
                try:
                    if font_name == 'ArabicFont':
                        c.setFont(font_name, font_size)
                    elif bold and font_name == 'Helvetica':
                        c.setFont('Helvetica-Bold', font_size)
                    else:
                        c.setFont(font_name, font_size)
                except Exception as e:
                    logger.warning(f"تعذر ضبط الخط في draw_arabic_centered: {e}")
                    c.setFont('Helvetica', font_size)
                
                processed_text = reshape_arabic_text(text)
                try:
                    text_width = c.stringWidth(processed_text, font_name if font_name else 'Helvetica', font_size)
                except Exception:
                    text_width = c.stringWidth(processed_text, 'Helvetica', font_size)
                c.drawString(x - (text_width / 2), y, processed_text)
            
            def draw_right_aligned_arabic(x, y, text, font_size=10, bold=False):
                if not text:
                    return
                try:
                    if font_name == 'ArabicFont':
                        c.setFont(font_name, font_size)
                    elif bold and font_name == 'Helvetica':
                        c.setFont('Helvetica-Bold', font_size)
                    else:
                        c.setFont(font_name, font_size)
                except Exception as e:
                    logger.warning(f"تعذر ضبط الخط في draw_right_aligned_arabic: {e}")
                    c.setFont('Helvetica', font_size)
                
                processed_text = reshape_arabic_text(text)
                try:
                    text_width = c.stringWidth(processed_text, font_name if font_name else 'Helvetica', font_size)
                except Exception:
                    text_width = c.stringWidth(processed_text, 'Helvetica', font_size)
                c.drawString(x - text_width, y, processed_text)
            
            y = page_height - TOP_MARGIN
            
            # رأس الفاتورة
            draw_arabic_centered(PAGE_WIDTH / 2, y, "سوبر ماركت", font_size=18, bold=True)
            y -= LINE_HEIGHT
            
            draw_arabic_centered(PAGE_WIDTH / 2, y, "فاتورة بيع", font_size=12)
            y -= LINE_HEIGHT * 1.2
            
            c.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
            y -= LINE_HEIGHT
            
            # معلومات الفاتورة
            invoice_label = reshape_arabic_text("رقم الفاتورة:")
            draw_right_aligned_arabic(PAGE_WIDTH - RIGHT_MARGIN - 5 * mm, y, f"{invoice_label} {sale_id}", font_size=11)
            y -= LINE_HEIGHT * 0.8
            
            current_date = datetime.now().strftime('%Y-%m-%d %I:%M %p')
            date_label = reshape_arabic_text("التاريخ:")
            draw_right_aligned_arabic(PAGE_WIDTH - RIGHT_MARGIN - 5 * mm, y, f"{date_label} {current_date}", font_size=11)
            y -= LINE_HEIGHT * 0.8
            
            if customer_name:
                customer_label = reshape_arabic_text("العميل:")
                draw_right_aligned_arabic(PAGE_WIDTH - RIGHT_MARGIN - 5 * mm, y, f"{customer_label} {customer_name}", font_size=11)
                y -= LINE_HEIGHT * 0.8
            
            if cashier_name:
                cashier_label = reshape_arabic_text("الكاشير:")
                draw_right_aligned_arabic(PAGE_WIDTH - RIGHT_MARGIN - 5 * mm, y, f"{cashier_label} {cashier_name}", font_size=11)
                y -= LINE_HEIGHT * 0.8
            
            # نوع الفاتورة
            if sale_type == 'مرتجع':
                type_display = "مرتجع"
                c.setFillColorRGB(0.65, 0.33, 0.10)
            elif sale_type == 'آجل':
                type_display = "آجل"
                c.setFillColorRGB(0.83, 0.33, 0)
            else:
                type_display = "نقدي"
                c.setFillColorRGB(0.15, 0.68, 0.38)
            
            type_label = reshape_arabic_text("نوع الفاتورة:")
            draw_right_aligned_arabic(PAGE_WIDTH - RIGHT_MARGIN - 5 * mm, y, f"{type_label} {reshape_arabic_text(type_display)}", font_size=11)
            c.setFillColorRGB(0, 0, 0)
            y -= LINE_HEIGHT
            
            c.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
            y -= LINE_HEIGHT * 0.8
            
            # رأس الجدول
            col_product_x = LEFT_MARGIN + 2 * mm
            col_qty_x = PAGE_WIDTH - 30 * mm
            col_price_x = PAGE_WIDTH - 50 * mm
            col_total_x = PAGE_WIDTH - 17 * mm
            
            draw_right_aligned_arabic(col_product_x, y, "المنتج", font_size=10, bold=True)
            draw_right_aligned_arabic(col_qty_x, y, "الكمية", font_size=10, bold=True)
            draw_right_aligned_arabic(col_price_x, y, "السعر", font_size=10, bold=True)
            draw_right_aligned_arabic(col_total_x, y, "الإجمالي", font_size=10, bold=True)
            y -= LINE_HEIGHT * 0.6
            
            c.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
            y -= LINE_HEIGHT * 0.5
            
            # عرض المنتجات
            for product_name, quantity, price in items:
                if y < 50 * mm:
                    c.showPage()
                    y = page_height - TOP_MARGIN
                    try:
                        c.setFont(font_name, 10)
                    except Exception:
                        c.setFont('Helvetica', 10)
                    
                    draw_right_aligned_arabic(col_product_x, y, "المنتج", font_size=10, bold=True)
                    draw_right_aligned_arabic(col_qty_x, y, "الكمية", font_size=10, bold=True)
                    draw_right_aligned_arabic(col_price_x, y, "السعر", font_size=10, bold=True)
                    draw_right_aligned_arabic(col_total_x, y, "الإجمالي", font_size=10, bold=True)
                    y -= LINE_HEIGHT * 0.6
                    c.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
                    y -= LINE_HEIGHT * 0.5
                
                item_total = quantity * price
                
                product_name_processed = reshape_arabic_text(str(product_name))
                draw_right_aligned_arabic(col_product_x, y, product_name_processed, font_size=10)
                
                qty_display = str(int(quantity) if quantity == int(quantity) else f"{quantity:.2f}")
                c.drawString(col_qty_x, y, qty_display)
                c.drawString(col_price_x, y, f"{price:,.2f}")
                c.drawString(col_total_x, y, f"{item_total:,.2f}")
                
                y -= LINE_HEIGHT
            
            y -= LINE_HEIGHT * 0.3
            c.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
            y -= LINE_HEIGHT * 0.8
            
            # الإجماليات
            subtotal_label = reshape_arabic_text("المجموع الفرعي:")
            draw_right_aligned_arabic(PAGE_WIDTH - RIGHT_MARGIN - 5 * mm, y, f"{subtotal_label} {subtotal:,.2f} ج.م", font_size=11)
            y -= LINE_HEIGHT * 0.8
            
            if discount > 0:
                discount_label = reshape_arabic_text("الخصم:")
                draw_right_aligned_arabic(PAGE_WIDTH - RIGHT_MARGIN - 5 * mm, y, f"{discount_label} {discount:,.2f} ج.م", font_size=11)
                y -= LINE_HEIGHT * 0.8
            
            c.line(LEFT_MARGIN, y, PAGE_WIDTH - RIGHT_MARGIN, y)
            y -= LINE_HEIGHT * 0.8
            
            total_label = reshape_arabic_text("الإجمالي النهائي:")
            draw_right_aligned_arabic(PAGE_WIDTH - RIGHT_MARGIN - 5 * mm, y, f"{total_label} {total:,.2f} ج.م", font_size=13, bold=True)
            y -= LINE_HEIGHT * 1.5
            
            # تذييل
            draw_arabic_centered(PAGE_WIDTH / 2, y, "شكراً لتسوقكم معنا", font_size=10)
            
            c.save()
            
            return abs_filename
            
        except Exception as e:
            logger.error(f"خطأ في generate_professional_invoice: {e}")
            raise Exception(f"خطأ في إنشاء PDF: {str(e)}")

    def export_full_report_pdf(self):
        try:
            if not self.displayed_sales:
                self.show_warning_toast("لا توجد فواتير للتصدير")
                return
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "حفظ تقرير المبيعات", 
                f"تقرير_المبيعات_{datetime.now().strftime('%Y%m%d')}.pdf",
                "PDF Files (*.pdf)"
            )
            
            if not filename:
                return
            
            abs_filename = self.generate_full_report_pdf(filename)
            self.show_success_toast(f"✅ تم تصدير التقرير بنجاح: {os.path.basename(abs_filename)}")
            
            try:
                if os.name == 'nt':
                    os.startfile(abs_filename)
                else:
                    subprocess.run(['xdg-open', abs_filename], check=False)
            except Exception as e:
                logger.error(f"تعذر فتح ملف التقرير تلقائياً: {e}")
                self.show_info_toast(f"تم حفظ التقرير في: {abs_filename}")
                
        except Exception as e:
            logger.error(f"خطأ في export_full_report_pdf: {e}")
            self.show_warning_toast(f"❌ خطأ في تصدير التقرير: {str(e)}")

    def generate_full_report_pdf(self, filename):
        try:
            abs_filename = get_absolute_path(filename)
            
            c = canvas.Canvas(abs_filename, pagesize=A4)
            page_width, page_height = A4
            margin = 20 * mm
            
            font_name = get_arabic_font()
            try:
                c.setFont(font_name, 10)
            except Exception:
                c.setFont('Helvetica', 10)
                font_name = 'Helvetica'
            
            def draw_arabic_text(x, y, text, size=10, bold=False):
                if not text:
                    return
                try:
                    if font_name == 'ArabicFont':
                        c.setFont(font_name, size)
                    elif bold and font_name == 'Helvetica':
                        c.setFont('Helvetica-Bold', size)
                    else:
                        c.setFont(font_name, size)
                except Exception:
                    c.setFont('Helvetica', size)
                
                processed_text = reshape_arabic_text(text)
                c.drawString(x, y, processed_text)
            
            def draw_arabic_centered(x, y, text, size=10, bold=False):
                if not text:
                    return
                try:
                    if font_name == 'ArabicFont':
                        c.setFont(font_name, size)
                    elif bold and font_name == 'Helvetica':
                        c.setFont('Helvetica-Bold', size)
                    else:
                        c.setFont(font_name, size)
                except Exception:
                    c.setFont('Helvetica', size)
                
                processed_text = reshape_arabic_text(text)
                try:
                    text_width = c.stringWidth(processed_text, font_name if font_name else 'Helvetica', size)
                except Exception:
                    text_width = c.stringWidth(processed_text, 'Helvetica', size)
                c.drawString(x - (text_width / 2), y, processed_text)
            
            y = page_height - margin
            
            draw_arabic_centered(page_width/2, y, "تقرير المبيعات", size=22, bold=True)
            y -= 12 * mm
            
            from_label = reshape_arabic_text("الفترة من")
            to_label = reshape_arabic_text("إلى")
            draw_arabic_centered(page_width/2, y, f"{from_label} {self.start_date.date().toString('yyyy-MM-dd')} {to_label} {self.end_date.date().toString('yyyy-MM-dd')}", size=12)
            y -= 8 * mm
            
            report_label = reshape_arabic_text("تاريخ التقرير:")
            draw_arabic_centered(page_width/2, y, f"{report_label} {datetime.now().strftime('%Y-%m-%d %I:%M %p')}", size=10)
            y -= 14 * mm
            
            total_sales = len(self.displayed_sales)
            total_amount = sum(float(s.get('total_amount', 0)) for s in self.displayed_sales)
            total_discount = sum(float(s.get('discount', 0)) for s in self.displayed_sales)
            avg_invoice = (total_amount/total_sales) if total_sales > 0 else 0
            
            c.setFillColorRGB(0.15, 0.68, 0.38)
            
            sales_count_label = reshape_arabic_text("📊 إجمالي عدد الفواتير:")
            draw_arabic_text(margin, y, f"{sales_count_label} {total_sales}", size=12, bold=True)
            y -= 6 * mm
            
            total_amount_label = reshape_arabic_text("💰 إجمالي المبيعات:")
            draw_arabic_text(margin, y, f"{total_amount_label} {total_amount:,.2f} ج.م", size=12, bold=True)
            y -= 6 * mm
            
            discount_total_label = reshape_arabic_text("🏷️ إجمالي الخصومات:")
            draw_arabic_text(margin, y, f"{discount_total_label} {total_discount:,.2f} ج.م", size=12, bold=True)
            y -= 6 * mm
            
            avg_label = reshape_arabic_text("📈 متوسط قيمة الفاتورة:")
            draw_arabic_text(margin, y, f"{avg_label} {avg_invoice:,.2f} ج.م", size=12, bold=True)
            c.setFillColorRGB(0, 0, 0)
            y -= 14 * mm
            
            # رأس الجدول
            col_id_x = margin
            col_date_x = margin + 35 * mm
            col_customer_x = margin + 75 * mm
            col_cashier_x = margin + 120 * mm
            col_total_x = page_width - margin - 15 * mm
            
            c.setFillColorRGB(0.2, 0.2, 0.3)
            c.rect(margin - 2, y + 2, page_width - 2*margin, 7 * mm, fill=1)
            c.setFillColorRGB(1, 1, 1)
            
            draw_arabic_text(col_id_x, y, "رقم الفاتورة", size=9, bold=True)
            draw_arabic_text(col_date_x, y, "التاريخ", size=9, bold=True)
            draw_arabic_text(col_customer_x, y, "العميل", size=9, bold=True)
            draw_arabic_text(col_cashier_x, y, "الكاشير", size=9, bold=True)
            draw_arabic_centered(col_total_x + 15 * mm, y, "الإجمالي", size=9, bold=True)
            
            c.setFillColorRGB(0, 0, 0)
            y -= 8 * mm
            c.line(margin, y, page_width - margin, y)
            y -= 4 * mm
            
            # عرض الفواتير
            for sale in self.displayed_sales:
                if y < 30 * mm:
                    c.showPage()
                    y = page_height - margin
                    c.setFont(font_name, 10)
                    
                    c.setFillColorRGB(0.2, 0.2, 0.3)
                    c.rect(margin - 2, y + 2, page_width - 2*margin, 7 * mm, fill=1)
                    c.setFillColorRGB(1, 1, 1)
                    
                    draw_arabic_text(col_id_x, y, "رقم الفاتورة", size=9, bold=True)
                    draw_arabic_text(col_date_x, y, "التاريخ", size=9, bold=True)
                    draw_arabic_text(col_customer_x, y, "العميل", size=9, bold=True)
                    draw_arabic_text(col_cashier_x, y, "الكاشير", size=9, bold=True)
                    draw_arabic_centered(col_total_x + 15 * mm, y, "الإجمالي", size=9, bold=True)
                    
                    c.setFillColorRGB(0, 0, 0)
                    y -= 8 * mm
                    c.line(margin, y, page_width - margin, y)
                    y -= 4 * mm
                
                sale_id = sale.get('id', '')
                sale_date = self.format_datetime(sale.get('sale_date', ''))
                customer_name = sale.get('customer_name', '')
                cashier_name = sale.get('cashier_name', '')
                total = float(sale.get('total_amount', 0))
                
                draw_arabic_text(col_id_x, y, str(sale_id), size=9)
                draw_arabic_text(col_date_x, y, sale_date[:16], size=8)
                draw_arabic_text(col_customer_x, y, customer_name[:20] if customer_name else "-", size=9)
                draw_arabic_text(col_cashier_x, y, cashier_name[:15] if cashier_name else "-", size=9)
                
                total_text = f"{total:,.2f} ج.م"
                draw_arabic_centered(col_total_x + 15 * mm, y, total_text, size=9)
                
                y -= 5 * mm
            
            y -= 5 * mm
            c.line(margin, y, page_width - margin, y)
            y -= 10 * mm
            
            c.setFillColorRGB(0.4, 0.4, 0.4)
            footer_text = "تم إنشاء هذا التقرير بواسطة نظام الماركت الذكي"
            draw_arabic_centered(page_width/2, y, footer_text, size=9)
            
            c.save()
            
            return abs_filename
            
        except Exception as e:
            logger.error(f"خطأ في generate_full_report_pdf: {e}")
            raise Exception(f"خطأ في إنشاء التقرير: {str(e)}")


if __name__ == "__main__":
    app = QApplication([])
    window = SalesHistoryWindow()
    window.showMaximized()
    app.exec_()