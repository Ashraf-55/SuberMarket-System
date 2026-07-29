import sys, os, json, time, subprocess, logging, webbrowser, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, QLabel, 
                             QHeaderView, QListWidget, QFrame, QDoubleSpinBox, 
                             QDialog, QShortcut, QScrollArea, QTabWidget, 
                             QComboBox, QGroupBox, QGridLayout, QCheckBox, 
                             QSplitter, QApplication, QInputDialog, QSizePolicy,
                             QListWidgetItem, QMessageBox)
from PyQt5.QtCore import Qt, QPropertyAnimation, QPoint, QTimer, QEvent, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence, QKeyEvent, QColor, QPalette
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm, letter
from reportlab.lib.units import mm as mm_unit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from datetime import datetime
from back.database import (search_products, make_sale, get_all_low_stock_products,
                           get_product_by_barcode, add_loyalty_points, 
                           update_customer_transaction, get_customer_by_name,
                           get_sale_by_id, log_user_activity,
                           get_applicable_promotion, get_price_lists,
                           get_product_price, get_default_price_list,
                           get_price_lists_with_default, set_product_price)

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== محاولة استيراد مكتبات العربية ==========
ARABIC_SUPPORT = False
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    pass

ARABIC_FONT_AVAILABLE = False
try:
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "C:/Windows/Fonts/arialuni.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Helvetica.ttf"
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
            ARABIC_FONT_AVAILABLE = True
            break
except Exception as e:
    logger.error(f"خطأ في تحميل الخط العربي: {e}")

# ========== حل مشكلة reportlab md5 ==========
try:
    import hashlib
    from reportlab.pdfbase import pdfdoc
    try:
        pdfdoc.md5 = lambda usedforsecurity=False: hashlib.md5()
    except Exception:
        pass
except Exception:
    pass

# ========== الألوان ==========
COLORS = {
    'bg_dark': '#F3F7F7',            # خلفية الشاشة الأساسية (فاتحة)
    'bg_sidebar': '#FFFFFF',         # خلفية القائمة الجانبية (بيضاء نقية)
    'bg_card': '#FFFFFF',            # خلفية الكروت والكتل (بيضاء)
    'bg_input': '#FFFFFF',           # خلفية حقول الإدخال
    'text': '#1e293b',               # لون النصوص الرئيسية (غامق وواضح)
    'text_muted': '#64748b',         # لون النصوص الفرعية أو التوضيحية
    'accent': '#0284c7',             # اللون الأساسي (أزرق متناسق مع الفاتح)
    'accent_hover': '#0369a1',
    'success': '#16a34a',            # أخضر للحفظ والنجاح
    'success_hover': '#15803d',
    'danger': '#dc2626',             # أحمر للحذف والتنبيهات
    'danger_hover': '#b91c1c',
    'warning': '#d97706',            # برتقالي للتحذيرات
    'warning_hover': '#b45309',
    'info': '#0284c7',
    'info_hover': '#0369a1',
    'border': '#cbd5e1',             # لون الحدود (رمادي فاتح وواضح بدل الغامق)
    'border_light': '#e2e8f0',
    'promotion': '#9333ea'
}


# ========== رسالة Toast موحدة ==========
class ToastMessage(QLabel):
    def __init__(self, parent, message, duration=2500):
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


# ========== نافذة عرض العميل (Customer Display) ==========
class CustomerDisplayWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_pos = parent
        self.setWindowTitle("شاشة عرض العميل")
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
            }}
        """)
        
        # محاولة جعلها Full Screen على الشاشة الثانية
        screens = QApplication.screens()
        if len(screens) > 1:
            screen_geometry = screens[1].geometry()
            self.setGeometry(screen_geometry)
        else:
            # إذا كانت شاشة واحدة، تجعلها Full Screen على نفس الشاشة
            screen = QApplication.primaryScreen()
            self.setGeometry(screen.availableGeometry())
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        # عنوان المتجر
        self.store_name_label = QLabel("سوبر ماركت")
        self.store_name_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #38bdf8;")
        self.store_name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.store_name_label)
        
        layout.addStretch()
        
        # عرض الأصناف
        self.items_label = QLabel("مرحباً بكم")
        self.items_label.setStyleSheet("font-size: 28px; color: #f8fafc;")
        self.items_label.setAlignment(Qt.AlignCenter)
        self.items_label.setWordWrap(True)
        layout.addWidget(self.items_label)
        
        layout.addStretch()
        
        # السعر الإجمالي
        self.total_label = QLabel("الإجمالي: 0.00 ج.م")
        self.total_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #22c55e;")
        self.total_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.total_label)
        
        # زر إغلاق
        close_btn = QPushButton("✕ إغلاق")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 30px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        close_btn.clicked.connect(self.close)
        close_btn.setFixedWidth(150)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.showFullScreen()
        self.setFocusPolicy(Qt.StrongFocus)
        self.activateWindow()
        self.setFocus()
    
    def keyPressEvent(self, event):
        """يسمح بإغلاق شاشة العميل بمفتاح Escape، بغض النظر عن مشاكل استقبال كليك الماوس"""
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """يضمن أن أي طريقة لإغلاق النافذة (زر داخلي، Alt+F4، إلخ) تُزامن الحالة مع الواجهة الرئيسية"""
        try:
            if self.parent_pos is not None:
                if getattr(self.parent_pos, 'customer_display', None) is self:
                    self.parent_pos.customer_display = None
                if hasattr(self.parent_pos, 'tab_widget'):
                    for i in range(self.parent_pos.tab_widget.count()):
                        tab = self.parent_pos.tab_widget.widget(i)
                        if hasattr(tab, 'customer_display_btn'):
                            tab.customer_display_btn.setText("🖥️ عرض العميل")
        except Exception as e:
            logger.error(f"خطأ في closeEvent الخاص بشاشة عرض العميل: {e}")
        event.accept()
    
    def update_display(self, items, total):
        """تحديث شاشة العرض بالأصناف والإجمالي"""
        try:
            if not items:
                self.items_label.setText("مرحباً بكم\n\nلا توجد منتجات")
                self.total_label.setText("الإجمالي: 0.00 ج.م")
                return
            
            # عرض آخر 5 أصناف فقط
            display_items = items[-5:] if len(items) > 5 else items
            text = ""
            for item in display_items:
                name = item.get('name', '')
                qty = item.get('qty', 0)
                price = item.get('price', 0)
                qty_display = str(int(qty)) if qty % 1 < 0.001 else f"{qty:.3f}".rstrip('0').rstrip('.')
                text += f"{name} × {qty_display} = {qty * price:.2f} ج.م\n"
            
            if len(items) > 5:
                text += f"\n... و {len(items) - 5} منتجات أخرى"
            
            self.items_label.setText(text)
            self.total_label.setText(f"الإجمالي: {total:.2f} ج.م")
        except Exception as e:
            logger.error(f"خطأ في update_display: {e}")


# ========== دوال معالجة النصوص العربية للـ PDF ==========
def reshape_arabic_text(text):
    if not text:
        return ""
    if not ARABIC_SUPPORT:
        return str(text)
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        bidi_text = get_display(reshaped)
        return bidi_text
    except Exception:
        return str(text)


def get_arabic_font():
    if ARABIC_FONT_AVAILABLE:
        return 'ArabicFont'
    return 'Helvetica'


# ========== نافذة استدعاء الفواتير المعلقة ==========
class RecallInvoicesDialog(QDialog):
    def __init__(self, held_invoices, parent=None):
        super().__init__(parent)
        self.held_invoices = held_invoices
        self.selected_hold_id = None
        self.setWindowTitle("📋 استدعاء فاتورة معلقة")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.4)
        height = int(screen_geometry.height() * 0.4)
        self.setMinimumSize(int(screen_geometry.width() * 0.3), int(screen_geometry.height() * 0.3))
        self.resize(max(500, width), max(350, height))
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border: 2px solid {COLORS['accent']};
                border-radius: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        title_label = QLabel("📋 استدعاء فاتورة معلقة")
        title_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {COLORS['accent']};
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        if not held_invoices:
            empty_label = QLabel("📭 لا توجد فواتير معلقة")
            empty_label.setStyleSheet(f"""
                font-size: 16px;
                color: {COLORS['text_muted']};
                padding: 30px;
            """)
            empty_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty_label)
            
            close_btn = QPushButton("✓ حسناً")
            close_btn.setMinimumHeight(40)
            close_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: white;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_hover']};
                }}
            """)
            close_btn.clicked.connect(self.accept)
            layout.addWidget(close_btn)
            return
        
        # ====== تعديل الريسبونسيف: تغليف قائمة الفواتير بـ ScrollArea ======
        list_scroll = QScrollArea()
        list_scroll.setWidgetResizable(True)
        list_scroll.setStyleSheet("border: none; background-color: transparent;")
        
        self.invoice_list = QListWidget()
        self.invoice_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                padding: 4px;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 12px 16px;
                border-bottom: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['bg_sidebar']};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['accent']};
                color: white;
            }}
        """)
        
        for hold_id, data in held_invoices.items():
            time_str = data.get('time', 'غير معروف')
            total = data.get('total', 0)
            count = len(data.get('items', []))
            tab_name = data.get('tab_name', f'فاتورة {hold_id}')
            item_text = f"📌 #{hold_id} | {tab_name} | {time_str} | {total:.2f} ج.م ({count} أصناف)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, hold_id)
            self.invoice_list.addItem(item)
        
        list_scroll.setWidget(self.invoice_list)
        layout.addWidget(list_scroll)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        recall_btn = QPushButton("🔄 استعادة الفاتورة")
        recall_btn.setMinimumHeight(44)
        recall_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        recall_btn.clicked.connect(self.confirm_recall)
        btn_layout.addWidget(recall_btn)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setMinimumHeight(44)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.invoice_list.setFocus()
        self.invoice_list.itemDoubleClicked.connect(self.on_item_double_clicked)
    
    def on_item_double_clicked(self, item):
        try:
            hold_id = item.data(Qt.UserRole)
            self.selected_hold_id = hold_id
            self.accept()
        except Exception as e:
            logger.error(f"خطأ في on_item_double_clicked: {e}")
            self.show_toast("❌ حدث خطأ في اختيار الفاتورة")
    
    def confirm_recall(self):
        try:
            current_item = self.invoice_list.currentItem()
            if current_item:
                self.selected_hold_id = current_item.data(Qt.UserRole)
                self.accept()
            else:
                self.show_toast("⚠️ الرجاء اختيار فاتورة أولاً")
        except Exception as e:
            logger.error(f"خطأ في confirm_recall: {e}")
            self.show_toast("❌ حدث خطأ في استدعاء الفاتورة")
    
    def show_toast(self, message):
        ToastMessage(self, message)


# ========== نافذة تأكيد الفاتورة مع خيارات الإرسال ==========
class InvoiceConfirmationDialog(QDialog):
    def __init__(self, sale_id, items, total, subtotal, discount, 
                 sale_type, customer_name=None, payment_data=None, parent=None):
        super().__init__(parent)
        self.sale_id = sale_id
        self.items = items
        self.total = total
        self.subtotal = subtotal
        self.discount = discount
        self.sale_type = sale_type
        self.customer_name = customer_name
        self.payment_data = payment_data
        self.parent_pos = parent
        self.setWindowTitle("✅ تأكيد الفاتورة")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.35)
        height = int(screen_geometry.height() * 0.45)
        self.setMinimumSize(int(screen_geometry.width() * 0.3), int(screen_geometry.height() * 0.35))
        self.resize(max(450, width), max(400, height))
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border: 2px solid {COLORS['success']};
                border-radius: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # العنوان
        title_label = QLabel("✅ تمت عملية البيع بنجاح")
        title_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {COLORS['success']};
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # معلومات الفاتورة
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        info_layout = QVBoxLayout(info_frame)
        
        info_text = f"""
            📋 رقم الفاتورة: {sale_id}
            💰 الإجمالي: {total:.2f} ج.م
            📌 نوع الدفع: {sale_type}
        """
        if customer_name:
            info_text += f"\n👤 العميل: {customer_name}"
        if payment_data:
            if payment_data.get('cash', 0) > 0:
                info_text += f"\n💵 كاش: {payment_data['cash']:.2f} ج.م"
            if payment_data.get('visa', 0) > 0:
                info_text += f"\n💳 فيزا: {payment_data['visa']:.2f} ج.م"
            if payment_data.get('wallet', 0) > 0:
                info_text += f"\n📱 محفظة: {payment_data['wallet']:.2f} ج.م"
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px;")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        layout.addWidget(info_frame)
        
        # أزرار الإرسال
        send_layout = QHBoxLayout()
        send_layout.setSpacing(12)
        
        self.whatsapp_btn = QPushButton("📱 إرسال واتساب")
        self.whatsapp_btn.setMinimumHeight(42)
        self.whatsapp_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #25D366;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: #128C7E;
            }}
        """)
        self.whatsapp_btn.clicked.connect(self.send_whatsapp)
        send_layout.addWidget(self.whatsapp_btn)
        
        self.email_btn = QPushButton("📧 إرسال إيميل")
        self.email_btn.setMinimumHeight(42)
        self.email_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #EA4335;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: #C62828;
            }}
        """)
        self.email_btn.clicked.connect(self.send_email)
        send_layout.addWidget(self.email_btn)
        
        layout.addLayout(send_layout)
        
        # زر الإغلاق
        close_btn = QPushButton("✓ حسناً")
        close_btn.setMinimumHeight(44)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def get_invoice_text(self):
        """توليد نص الفاتورة للإرسال"""
        text = "🛒 *فاتورة شراء*\n"
        text += "=" * 30 + "\n"
        text += f"رقم الفاتورة: {self.sale_id}\n"
        text += f"التاريخ: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
        if self.customer_name:
            text += f"العميل: {self.customer_name}\n"
        text += "=" * 30 + "\n"
        
        for name, qty, price in self.items:
            qty_display = str(int(qty)) if qty % 1 < 0.001 else f"{qty:.3f}".rstrip('0').rstrip('.')
            text += f"{name} × {qty_display} = {qty * price:.2f} ج.م\n"
        
        text += "=" * 30 + "\n"
        text += f"المجموع الفرعي: {self.subtotal:.2f} ج.م\n"
        if self.discount > 0:
            text += f"الخصم: {self.discount:.2f} ج.م\n"
        text += f"*الإجمالي: {self.total:.2f} ج.م*\n"
        text += "=" * 30 + "\n"
        text += "شكراً لتسوقكم معنا 🙏"
        return text
    
    def send_whatsapp(self):
        """إرسال الفاتورة عبر واتساب"""
        try:
            # محاولة قراءة رقم الهاتف من الإعدادات
            phone = ""
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    phone = settings.get("store_phone", "").strip()
            
            if not phone:
                # طلب رقم الهاتف من المستخدم
                phone, ok = QInputDialog.getText(
                    self, "رقم الهاتف", 
                    "📱 الرجاء إدخال رقم الهاتف (مع مفتاح الدولة):\nمثال: 201234567890",
                    QLineEdit.Normal, ""
                )
                if not ok or not phone.strip():
                    self.show_toast("❌ تم إلغاء إرسال واتساب")
                    return
                phone = phone.strip()
            
            # تنظيف رقم الهاتف
            phone = ''.join(filter(str.isdigit, phone))
            if not phone:
                self.show_toast("❌ رقم الهاتف غير صالح")
                return
            
            invoice_text = self.get_invoice_text()
            # ترميز النص للـ URL
            import urllib.parse
            encoded_text = urllib.parse.quote(invoice_text)
            
            url = f"https://wa.me/{phone}?text={encoded_text}"
            webbrowser.open(url)
            self.show_toast("✅ تم فتح واتساب لإرسال الفاتورة")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال واتساب: {e}")
            self.show_toast(f"❌ خطأ في إرسال واتساب: {str(e)}")
    
    def send_email(self):
        """إرسال الفاتورة عبر الإيميل"""
        try:
            # قراءة إعدادات SMTP
            smtp_settings = {}
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    smtp_settings = {
                        'host': settings.get('smtp_host', ''),
                        'port': settings.get('smtp_port', 587),
                        'username': settings.get('smtp_username', ''),
                        'password': settings.get('smtp_password', ''),
                        'from_email': settings.get('smtp_from_email', ''),
                        'to_email': settings.get('smtp_to_email', '')
                    }
            
            # التحقق من الإعدادات
            if not smtp_settings['host'] or not smtp_settings['username']:
                self.show_toast("⚠️ الإعدادات غير مكتملة. الرجاء ضبط SMTP في شاشة الإعدادات")
                return
            
            if not smtp_settings['to_email']:
                # طلب البريد الإلكتروني للمستلم
                to_email, ok = QInputDialog.getText(
                    self, "البريد الإلكتروني", 
                    "📧 الرجاء إدخال البريد الإلكتروني للمستلم:",
                    QLineEdit.Normal, ""
                )
                if not ok or not to_email.strip():
                    self.show_toast("❌ تم إلغاء إرسال الإيميل")
                    return
                smtp_settings['to_email'] = to_email.strip()
            
            # إنشاء الرسالة
            msg = MIMEMultipart()
            msg['From'] = smtp_settings['from_email'] or smtp_settings['username']
            msg['To'] = smtp_settings['to_email']
            msg['Subject'] = f"فاتورة #{self.sale_id} - {datetime.now().strftime('%Y-%m-%d')}"
            
            body = self.get_invoice_text()
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # إرسال الإيميل
            try:
                server = smtplib.SMTP(smtp_settings['host'], int(smtp_settings['port']))
                server.starttls()
                server.login(smtp_settings['username'], smtp_settings['password'])
                server.send_message(msg)
                server.quit()
                self.show_toast(f"✅ تم إرسال الإيميل إلى {smtp_settings['to_email']}")
            except smtplib.SMTPAuthenticationError:
                self.show_toast("❌ فشل المصادقة. تحقق من اسم المستخدم وكلمة المرور")
            except smtplib.SMTPException as e:
                self.show_toast(f"❌ خطأ في SMTP: {str(e)}")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال الإيميل: {e}")
            self.show_toast(f"❌ خطأ في إرسال الإيميل: {str(e)}")
    
    def show_toast(self, message):
        ToastMessage(self, message)


# ========== نافذة تنبيه المخزون ==========
class LowStockAlertDialog(QDialog):
    def __init__(self, alerts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠️ تنبيه المخزون المنخفض")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.35)
        height = int(screen_geometry.height() * 0.35)
        self.setMinimumSize(int(screen_geometry.width() * 0.3), int(screen_geometry.height() * 0.25))
        self.resize(max(420, width), max(280, height))
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border: 2px solid {COLORS['warning']};
                border-radius: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        title_label = QLabel("⚠️ تنبيه: المنتجات التالية بحاجة للطلب")
        title_label.setStyleSheet(f"""
            font-size: 17px;
            font-weight: bold;
            color: {COLORS['warning']};
        """)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # ====== تعديل الريسبونسيف: تغليف التنبيهات بـ ScrollArea ======
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        alerts_widget = QWidget()
        alerts_layout = QVBoxLayout(alerts_widget)
        alerts_layout.setSpacing(8)
        
        for alert in alerts:
            try:
                if isinstance(alert, dict):
                    name = alert.get('name', 'غير معروف')
                    stock = alert.get('stock', 0)
                    alert_limit = alert.get('alert_limit', 0)
                    unit = alert.get('unit', 'قطعة')
                else:
                    name = alert[1] if len(alert) > 1 else 'غير معروف'
                    stock = alert[2] if len(alert) > 2 else 0
                    alert_limit = alert[3] if len(alert) > 3 else 0
                    unit = alert[4] if len(alert) > 4 else 'قطعة'
                
                stock_display = f"{stock:.3f}".rstrip('0').rstrip('.') if stock % 1 != 0 else str(int(stock))
                alert_label = QLabel(f"📦 {name}: {stock_display} {unit} متبقي (الحد الأدنى: {alert_limit})")
                alert_label.setStyleSheet(f"""
                    font-size: 13px;
                    color: {COLORS['text']};
                    padding: 10px 14px;
                    background-color: {COLORS['bg_card']};
                    border-radius: 8px;
                    border-left: 4px solid {COLORS['warning']};
                """)
                alert_label.setWordWrap(True)
                alerts_layout.addWidget(alert_label)
            except Exception as e:
                logger.error(f"خطأ في عرض تنبيه المخزون: {e}")
        
        alerts_layout.addStretch()
        scroll.setWidget(alerts_widget)
        layout.addWidget(scroll)
        
        close_btn = QPushButton("✓ حسناً")
        close_btn.setMinimumHeight(44)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['warning']};
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['warning_hover']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# ========== نافذة تقسيم الدفع (النسخة النهائية الفائقة الأناقة) ==========
class SplitPaymentDialog(QDialog):
    payment_confirmed = pyqtSignal(dict)
    
    def __init__(self, total_amount, parent=None):
        super().__init__(parent)
        self.total_amount = total_amount
        self.payment_data = None
        self.setWindowTitle("💰 تقسيم عملية الدفع")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.3), int(screen_geometry.height() * 0.4))
        self.resize(int(screen_geometry.width() * 0.35), int(screen_geometry.height() * 0.45))
        
        # تفعيل اتجاه الكتابة من اليمين إلى اليسار ليتناسب مع واجهة البرنامج العربية
        self.setLayoutDirection(Qt.RightToLeft)
        
        # ستايل النافذة العام مع حواف دائرية أنيقة تتناسب مع برنامجك
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border: 2px solid {COLORS['accent']};
                border-radius: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(18)
        
        # 1. عنوان النافذة
        title_label = QLabel("💰 تقسيم الدفع")
        title_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {COLORS['accent']};
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 2. بطاقة إجمالي الفاتورة
        total_frame = QFrame()
        total_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        total_layout = QHBoxLayout(total_frame)
        total_layout.setContentsMargins(20, 12, 20, 12)
        
        total_title = QLabel("💵 إجمالي الفاتورة:")
        total_title.setStyleSheet(f"font-size: 15px; color: {COLORS['text_muted']}; font-weight: bold;")
        
        total_val = QLabel(f"{total_amount:.2f} ج.م")
        total_val.setStyleSheet(f"font-size: 22px; font-weight: 900; color: {COLORS['text']};")
        
        total_layout.addWidget(total_title)
        total_layout.addStretch()
        total_layout.addWidget(total_val)
        layout.addWidget(total_frame)
        
        # 3. صندوق طرق الدفع
        payment_group = QGroupBox("طرق الدفع المتاحة")
        payment_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top right; /* لتبدو بشكل صحيح في الـ RTL */
                margin-right: 15px;
                padding: 0 10px;
                background-color: {COLORS['bg_dark']};
            }}
        """)
        
        payment_layout = QGridLayout(payment_group)
        payment_layout.setSpacing(15)
        payment_layout.setContentsMargins(20, 15, 20, 15)
        
        payment_fields = [
            ("💵 كاش (نقدي):", 'cash_input'),
            ("💳 فيزا (شبكة):", 'visa_input'),
            ("📱 محفظة إلكترونية:", 'wallet_input')
        ]
        
        for row, (label_text, attr_name) in enumerate(payment_fields):
            label = QLabel(label_text)
            label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: bold;")
            payment_layout.addWidget(label, row, 0)
            
            spinbox = QDoubleSpinBox()
            spinbox.setRange(0, total_amount)
            spinbox.setSingleStep(5)
            spinbox.setDecimals(2)
            spinbox.setSuffix(" ج.م")
            spinbox.setAlignment(Qt.AlignCenter)
            spinbox.setMinimumWidth(180)
            spinbox.setMinimumHeight(42)
            
            # ستايل محسن ومتباعد للـ SpinBox يمنع تداخل النصوص مع الأزرار الجانبية
            spinbox.setStyleSheet(f"""
                QDoubleSpinBox {{
                    background-color: {COLORS['bg_input']};
                    color: #ffffff;
                    border: 2px solid {COLORS['border']};
                    border-radius: 8px;
                    padding-left: 5px;
                    padding-right: 5px;
                    font-size: 16px;
                    font-weight: bold;
                }}
                QDoubleSpinBox:focus {{
                    border: 2px solid {COLORS['accent']};
                    background-color: {COLORS['bg_dark']};
                }}
                QDoubleSpinBox::up-button {{
                    width: 25px;
                    background-color: {COLORS['bg_sidebar']};
                    border-left: 1px solid {COLORS['border']};
                    border-top-left-radius: 6px;
                }}
                QDoubleSpinBox::down-button {{
                    width: 25px;
                    background-color: {COLORS['bg_sidebar']};
                    border-left: 1px solid {COLORS['border']};
                    border-bottom-left-radius: 6px;
                }}
            """)
            spinbox.valueChanged.connect(self.update_remaining)
            setattr(self, attr_name, spinbox)
            payment_layout.addWidget(spinbox, row, 1)
        
        layout.addWidget(payment_group)
        
        # 4. شريط المتبقي الديناميكي
        self.remaining_frame = QFrame()
        self.remaining_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(245, 158, 11, 0.1);
                border: 1px solid {COLORS['warning']};
                border-radius: 10px;
            }}
        """)
        remaining_layout = QHBoxLayout(self.remaining_frame)
        remaining_layout.setContentsMargins(15, 10, 15, 10)
        
        self.remaining_title = QLabel("⚖️ المتبقي غير المدفوع:")
        self.remaining_title.setStyleSheet(f"font-size: 14px; color: {COLORS['text']}; font-weight: bold;")
        
        self.remaining_label = QLabel(f"{total_amount:.2f} ج.م")
        self.remaining_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 900;
            color: {COLORS['warning']};
        """)
        
        remaining_layout.addWidget(self.remaining_title)
        remaining_layout.addStretch()
        remaining_layout.addWidget(self.remaining_label)
        layout.addWidget(self.remaining_frame)
        
        # 5. أزرار التحكم السفلية
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.confirm_btn = QPushButton("✓ تأكيد العملية")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                border: none;
                min-height: 45px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
        """)
        self.confirm_btn.clicked.connect(self.confirm_payment)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                border: none;
                min-height: 45px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_btn, stretch=2)
        button_layout.addWidget(cancel_btn, stretch=1)
        
        layout.addLayout(button_layout)
        self.cash_input.setFocus()
    
    def update_remaining(self):
        try:
            total_paid = self.cash_input.value() + self.visa_input.value() + self.wallet_input.value()
            remaining = self.total_amount - total_paid
            
            if abs(remaining) < 0.01:
                self.remaining_label.setText("تم استيفاء المبلغ بالكامل! 🎉")
                self.remaining_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {COLORS['success']};")
                self.remaining_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: rgba(34, 197, 94, 0.1);
                        border: 1px solid {COLORS['success']};
                        border-radius: 10px;
                    }}
                """)
                self.confirm_btn.setEnabled(True)
            elif remaining < 0:
                self.remaining_label.setText(f"زيادة في المدفوع: {abs(remaining):.2f} ج.م ⚠️")
                self.remaining_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {COLORS['danger']};")
                self.remaining_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: rgba(239, 68, 110, 0.1);
                        border: 1px solid {COLORS['danger']};
                        border-radius: 10px;
                    }}
                """)
                self.confirm_btn.setEnabled(False)
            else:
                self.remaining_label.setText(f"{remaining:.2f} ج.م")
                self.remaining_label.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {COLORS['warning']};")
                self.remaining_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: rgba(245, 158, 11, 0.1);
                        border: 1px solid {COLORS['warning']};
                        border-radius: 10px;
                    }}
                """)
                self.confirm_btn.setEnabled(False)
        except Exception as e:
            logger.error(f"خطأ في update_remaining: {e}")
    
    def confirm_payment(self):
        try:
            self.payment_data = {
                'cash': self.cash_input.value(),
                'visa': self.visa_input.value(),
                'wallet': self.wallet_input.value()
            }
            self.accept()
        except Exception as e:
            logger.error(f"خطأ في confirm_payment: {e}")
    
    def get_payment_data(self):
        return self.payment_data


# ========== تبويب الفاتورة ==========
class InvoiceTab(QWidget):
    def __init__(self, tab_id, parent=None):
        super().__init__(parent)
        self.tab_id = tab_id
        self.parent_window = parent
        self.cart_items = {}
        self.discount_percent = 0
        self.discount_amount = 0
        self.wholesale_mode = False
        self.current_price_list_id = None
        self._updating_spin = False
        self._updating_table = False
        self._updating_discount = False
        self._is_clearing = False
        self._updating_prices = False  # منع التكرار عند تحديث الأسعار
        self.init_ui()
        self.load_price_lists()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # ===== شريط قائمة السعر =====
        price_list_frame = QFrame()
        price_list_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 8px;
                padding: 5px 10px;
            }}
        """)
        price_list_layout = QHBoxLayout(price_list_frame)
        price_list_layout.setSpacing(10)
        
        price_list_label = QLabel("📊 قائمة السعر:")
        price_list_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: bold;")
        price_list_layout.addWidget(price_list_label)
        
        self.price_list_combo = QComboBox()
        self.price_list_combo.setMinimumWidth(180)
        self.price_list_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                min-height: 30px;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
            }}
        """)
        self.price_list_combo.currentIndexChanged.connect(self.on_price_list_changed)
        price_list_layout.addWidget(self.price_list_combo)
        
        price_list_layout.addStretch()
        
        # زر تفعيل شاشة العرض للعميل
        self.customer_display_btn = QPushButton("🖥️ عرض العميل")
        self.customer_display_btn.setMinimumHeight(32)
        self.customer_display_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: none;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_hover']};
            }}
        """)
        self.customer_display_btn.clicked.connect(self.toggle_customer_display)
        price_list_layout.addWidget(self.customer_display_btn)
        
        layout.addWidget(price_list_frame)
        
        # ===== جدول المنتجات =====
        self.table = QTableWidget(0, 6)  # زيادة عمود للعروض
        self.table.setHorizontalHeaderLabels(["المنتج", "السعر", "الكمية", "الإجمالي", "العرض", "حذف"])
        self.table.setStyleSheet(f"""
            QTableWidget {{
                border-radius: 10px;
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: 1px solid {COLORS['border']};
                alternate-background-color: {COLORS['bg_sidebar']};
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(56, 189, 248, 0.15);
            }}
            QTableWidget::item:alternate {{
                background-color: {COLORS['bg_sidebar']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 10px 8px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 55)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        
        # ===== شريط التحكم السفلي =====
        control_frame = QFrame()
        control_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setSpacing(15)
        
        discount_p_layout = QHBoxLayout()
        discount_p_layout.setSpacing(5)
        discount_p_label = QLabel("خصم %:")
        discount_p_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        self.discount_percent_spin = QDoubleSpinBox()
        self.discount_percent_spin.setRange(0, 100)
        self.discount_percent_spin.setSingleStep(1)
        self.discount_percent_spin.setDecimals(1)
        self.discount_percent_spin.setSuffix(" %")
        self.discount_percent_spin.setFixedWidth(90)
        self.discount_percent_spin.setStyleSheet(self._get_spinbox_style())
        self.discount_percent_spin.valueChanged.connect(self._on_discount_changed)
        discount_p_layout.addWidget(discount_p_label)
        discount_p_layout.addWidget(self.discount_percent_spin)
        control_layout.addLayout(discount_p_layout)
        
        discount_a_layout = QHBoxLayout()
        discount_a_layout.setSpacing(5)
        discount_a_label = QLabel("خصم مبلغ:")
        discount_a_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        self.discount_amount_spin = QDoubleSpinBox()
        self.discount_amount_spin.setRange(0, 10000)
        self.discount_amount_spin.setSingleStep(1)
        self.discount_amount_spin.setDecimals(2)
        self.discount_amount_spin.setPrefix("ج.م ")
        self.discount_amount_spin.setFixedWidth(110)
        self.discount_amount_spin.setStyleSheet(self._get_spinbox_style())
        self.discount_amount_spin.valueChanged.connect(self._on_discount_changed)
        discount_a_layout.addWidget(discount_a_label)
        discount_a_layout.addWidget(self.discount_amount_spin)
        control_layout.addLayout(discount_a_layout)
        
        control_layout.addStretch()
        
        self.wholesale_toggle = QCheckBox(" جملة (10%)")
        self.wholesale_toggle.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text']};
                font-size: 12px;
                font-weight: bold;
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 5px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent']};
                border: 2px solid {COLORS['accent']};
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {COLORS['accent_hover']};
            }}
        """)
        self.wholesale_toggle.toggled.connect(self._on_wholesale_toggled)
        control_layout.addWidget(self.wholesale_toggle)
        
        self.btn_clear_invoice = QPushButton("🗑️ إلغاء الفاتورة")
        self.btn_clear_invoice.setMinimumHeight(38)
        self.btn_clear_invoice.setMinimumWidth(130)
        self.btn_clear_invoice.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        self.btn_clear_invoice.clicked.connect(self.clear_cart_with_confirmation)
        control_layout.addWidget(self.btn_clear_invoice)
        
        self.tab_total_label = QLabel("الإجمالي: 0.00 ج.م")
        self.tab_total_label.setStyleSheet(f"""
            font-size: 20px;
            color: {COLORS['success']};
            font-weight: 900;
            min-width: 180px;
            padding: 0 10px;
        """)
        control_layout.addWidget(self.tab_total_label)
        
        layout.addWidget(control_frame)
        self.table.setFocus()
    
    def _get_spinbox_style(self):
        return f"""
            QDoubleSpinBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
            }}
            QDoubleSpinBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 16px;
            }}
        """
    
    def _safe_show_toast(self, message, duration=2500):
        try:
            ToastMessage(self, message, duration)
        except Exception as e:
            logger.error(f"خطأ في عرض Toast: {e}")
    
    def load_price_lists(self):
        """تحميل قوائم الأسعار في الـ ComboBox مع تعيين القائمة الافتراضية"""
        try:
            self.price_list_combo.blockSignals(True)  # منع التفعيل أثناء التحميل
            
            # الحصول على قوائم الأسعار مع معرف القائمة الافتراضية
            price_lists, default_id = get_price_lists_with_default()
    
            self.price_list_combo.clear()
            # إضافة قوائم الأسعار من قاعدة البيانات
            for pl in price_lists:
                pl_id = pl.get('id')
                name = pl.get('name', '')
                is_default = pl.get('is_default', 0)
                
                if pl_id is not None:
                    combo_index = self.price_list_combo.count()
                    # إضافة أيقونة مختلفة للقائمة الافتراضية
                    if is_default == 1:
                        self.price_list_combo.addItem(f"⭐ {name} (افتراضي)", pl_id)
                    else:
                        self.price_list_combo.addItem(f"📋 {name}", pl_id)
                    
                    if is_default == 1:
                        default_index = combo_index
            
            # تعيين القيمة الافتراضية (إما القائمة المحددة من قاعدة البيانات أو التجزئة)
            if default_id is not None:
                # البحث عن الفهرس المقابل للقائمة الافتراضية
                for i in range(self.price_list_combo.count()):
                    if self.price_list_combo.itemData(i) == default_id:
                        default_index = i
                        break
            
            self.price_list_combo.setCurrentIndex(default_index)
            self.current_price_list_id = self.price_list_combo.currentData()
            
            self.price_list_combo.blockSignals(False)
            
        except Exception as e:
            logger.error(f"خطأ في load_price_lists: {e}")
            self.price_list_combo.blockSignals(False)
            try:
                self._safe_show_toast(f"⚠️ خطأ في تحميل قوائم الأسعار: {str(e)}")
            except:
                pass
    
    def on_price_list_changed(self, index):
        """
        تغيير قائمة السعر - تحديث أسعار الأصناف المضافة تلقائياً
        """
        if self._updating_prices:
            return
        
        self._updating_prices = True
        try:
            # الحصول على معرف قائمة الأسعار الجديدة
            new_price_list_id = self.price_list_combo.currentData()
            
            # تحديث المتغير الحالي
            self.current_price_list_id = new_price_list_id
            
            # إذا كانت السلة فارغة، نقوم فقط بتحديث العرض
            if not self.cart_items:
                self.update_total()
                self._updating_prices = False
                return
            
            # تحديث أسعار جميع المنتجات في السلة
            updated_count = 0
            for p_id, info in self.cart_items.items():
                # الحصول على السعر الجديد من قائمة الأسعار المحددة
                new_price = None
                if new_price_list_id is not None:
                    new_price = get_product_price(p_id, new_price_list_id)
                
                # إذا لم يتم العثور على سعر، نستخدم السعر الأصلي (سعر التجزئة)
                if new_price is None:
                    new_price = info.get('original_price', info.get('price', 0))
                
                # تحديث السعر إذا تغير
                old_price = info.get('price', 0)
                if abs(new_price - old_price) > 0.001:
                    info['price'] = new_price
                    # إعادة تطبيق العروض
                    self.apply_promotion_to_product(p_id, info)
                    updated_count += 1
            
            # إعادة بناء الجدول وعرض الرسالة المناسبة
            if updated_count > 0:
                self._rebuild_table_from_cart()
                self.update_total()
                
                # عرض اسم القائمة المختارة في رسالة التأكيد
                list_name = self.price_list_combo.currentText()
                if list_name:
                    self._safe_show_toast(f"✅ تم تحديث {updated_count} منتج(منتجات) حسب قائمة {list_name}")
                else:
                    self._safe_show_toast(f"✅ تم تحديث {updated_count} منتج(منتجات) حسب قائمة السعر المحددة")
            else:
                # لا توجد تغييرات في الأسعار
                list_name = self.price_list_combo.currentText()
                if list_name:
                    self._safe_show_toast(f"ℹ️ الأسعار متطابقة مع قائمة {list_name}")
                else:
                    self._safe_show_toast("ℹ️ لا توجد تغييرات في الأسعار")
            
        except Exception as e:
            logger.error(f"خطأ في on_price_list_changed: {e}")
            self._safe_show_toast(f"❌ خطأ في تحديث الأسعار: {str(e)}")
        finally:
            self._updating_prices = False
    
    def get_price_for_product(self, product_id):
        """
        الحصول على سعر المنتج حسب قائمة السعر المحددة
        @param product_id: معرف المنتج
        @return: السعر المناسب
        """
        try:
            # إذا كانت هناك قائمة أسعار محددة
            if self.current_price_list_id is not None:
                price = get_product_price(product_id, self.current_price_list_id)
                if price is not None:
                    return price
            
            # إذا لم يوجد سعر في القائمة، نبحث عن السعر الافتراضي من معلومات المنتج
            if product_id in self.cart_items:
                original_price = self.cart_items[product_id].get('original_price', 0)
                if original_price > 0:
                    return original_price
            
            # محاولة جلب المنتج من قاعدة البيانات
            product = get_product(product_id)
            if product:
                return float(product.get('sell_price', 0))
            
            return None
        except Exception as e:
            logger.error(f"خطأ في get_price_for_product: {e}")
            return None
    
    def toggle_customer_display(self):
        """تفعيل/تعطيل شاشة عرض العميل"""
        try:
            if self.parent_window and hasattr(self.parent_window, 'customer_display'):
                if self.parent_window.customer_display and self.parent_window.customer_display.isVisible():
                    display_window = self.parent_window.customer_display
                    display_window.close()
                    self._safe_show_toast("🔄 تم إغلاق شاشة عرض العميل")
                else:
                    old_display = self.parent_window.customer_display
                    if old_display is not None:
                        try:
                            old_display.deleteLater()
                        except Exception:
                            pass
                    self.parent_window.customer_display = CustomerDisplayWindow(self.parent_window)
                    self.parent_window.customer_display.show()
                    self.customer_display_btn.setText("🖥️ إخفاء العرض")
                    self._safe_show_toast("✅ تم فتح شاشة عرض العميل")
                    self.update_customer_display()
        except Exception as e:
            logger.error(f"خطأ في toggle_customer_display: {e}")
    
    def _get_price(self, info):
        # الاحتفاظ بوضع الجملة
        if self.wholesale_mode:
            return info['price'] * 0.9
        return info['price']
    
    def _calculate_item_total(self, info):
        try:
            qty = info['qty']
            price = self._get_price(info)
            total = qty * price
            
            # تطبيق الخصم التلقائي من العروض (إن وجد)
            if info.get('promotion_discount', 0) > 0:
                total -= info['promotion_discount']
            
            return max(0, total)
        except Exception as e:
            logger.error(f"خطأ في _calculate_item_total: {e}")
            return 0.0
    
    def get_subtotal(self):
        try:
            if not self.cart_items:
                return 0.0
            subtotal = 0.0
            for p_id, info in self.cart_items.items():
                subtotal += self._calculate_item_total(info)
            return subtotal
        except Exception as e:
            logger.error(f"خطأ في get_subtotal: {e}")
            return 0.0
    
    def calculate_total(self):
        try:
            if not self.cart_items:
                return 0.0
            subtotal = self.get_subtotal()
            discount_percent = self.discount_percent_spin.value()
            discount_amount = self.discount_amount_spin.value()
            discount_from_percent = (subtotal * discount_percent) / 100
            total_discount = discount_from_percent + discount_amount
            return max(0, subtotal - total_discount)
        except Exception as e:
            logger.error(f"خطأ في calculate_total: {e}")
            return 0.0
    
    def update_total(self):
        try:
            # تحديث شاشة عرض العميل
            self.update_customer_display()
            
            if not self.cart_items:
                self.tab_total_label.setText("الإجمالي: 0.00 ج.م")
                try:
                    if self.parent_window and hasattr(self.parent_window, 'update_main_total'):
                        self.parent_window.update_main_total()
                except Exception as e:
                    logger.error(f"خطأ في تحديث main_total: {e}")
                return
            total = self.calculate_total()
            self.tab_total_label.setText(f"الإجمالي: {total:.2f} ج.م")
            try:
                if self.parent_window and hasattr(self.parent_window, 'update_main_total'):
                    self.parent_window.update_main_total()
            except Exception as e:
                logger.error(f"خطأ في تحديث main_total: {e}")
        except Exception as e:
            logger.error(f"خطأ في update_total: {e}")
            self.tab_total_label.setText("الإجمالي: 0.00 ج.م")
    
    def update_customer_display(self):
        """تحديث شاشة عرض العميل بالبيانات الحالية"""
        try:
            if self.parent_window and hasattr(self.parent_window, 'customer_display'):
                if self.parent_window.customer_display and self.parent_window.customer_display.isVisible():
                    items = self.get_cart_items()
                    total = self.calculate_total()
                    self.parent_window.customer_display.update_display(items, total)
        except Exception as e:
            logger.error(f"خطأ في update_customer_display: {e}")
    
    def _on_discount_changed(self):
        if self._updating_discount:
            return
        self._updating_discount = True
        try:
            if self.cart_items:
                self.update_total()
            else:
                self.tab_total_label.setText("الإجمالي: 0.00 ج.م")
                try:
                    if self.parent_window and hasattr(self.parent_window, 'update_main_total'):
                        self.parent_window.update_main_total()
                except Exception as e:
                    logger.error(f"خطأ في تحديث main_total في _on_discount_changed: {e}")
        except Exception as e:
            logger.error(f"خطأ في _on_discount_changed: {e}")
        finally:
            self._updating_discount = False
    
    def apply_promotion_to_product(self, p_id, info):
        """تطبيق العروض التلقائية على المنتج"""
        try:
            # الحصول على العرض المناسب
            promotion = get_applicable_promotion(p_id, info.get('category', ''), info['qty'])
            
            if promotion:
                promo_type = promotion.get('promo_type', '')
                promo_value = promotion.get('discount_value', 0)
                promo_desc = promotion.get('name', '')
                
                # حساب الخصم التلقائي
                item_price = self._get_price(info)
                item_total = info['qty'] * item_price
                
                if promo_type == 'percent':
                    # خصم نسبة مئوية
                    discount_amount = item_total * (promo_value / 100)
                    info['promotion_discount'] = discount_amount
                    info['promotion_desc'] = f"خصم {promo_value}%"
                    return True
                elif promo_type == 'fixed_amount':
                    # خصم مبلغ ثابت
                    discount_amount = min(promo_value, item_total)
                    info['promotion_discount'] = discount_amount
                    info['promotion_desc'] = f"خصم {promo_value} ج.م"
                    return True
                elif promo_type == 'buy_x_get_y':
                    # اشتري X واحصل على Y مجاناً
                    buy_qty = promotion.get('buy_qty', 1)
                    free_qty = promotion.get('get_qty', 0)
                    if info['qty'] >= buy_qty:
                        free_items = (info['qty'] // buy_qty) * free_qty
                        discount_amount = free_items * item_price
                        info['promotion_discount'] = min(discount_amount, item_total)
                        info['promotion_desc'] = f"اشتري {buy_qty} احصل على {free_qty} مجاناً"
                        return True
                
                # إذا لم يتم تطبيق أي عرض
                info['promotion_discount'] = 0
                info['promotion_desc'] = ''
                return False
            else:
                # لا يوجد عرض
                info['promotion_discount'] = 0
                info['promotion_desc'] = ''
                return False
        except Exception as e:
            logger.error(f"خطأ في apply_promotion_to_product: {e}")
            info['promotion_discount'] = 0
            info['promotion_desc'] = ''
            return False
    
    def add_product(self, product, qty=None):
        try:
            if isinstance(product, dict):
                p_id = product.get('id')
                name = product.get('name', '')
                price = float(product.get('sell_price', 0))
                stock = float(product.get('stock', 0))
                unit = product.get('weight_unit', product.get('unit', 'قطعة'))
                category = product.get('category', '')
            else:
                p_id = product[0] if len(product) > 0 else None
                name = product[1] if len(product) > 1 else ''
                price = float(product[4]) if len(product) > 4 else 0
                stock = float(product[5]) if len(product) > 5 else 0
                unit = product[8] if len(product) > 8 else 'قطعة'
                category = product[7] if len(product) > 7 else ''
            
            is_weighable = unit in ['كيلو', 'جرام', 'لتر', 'ملليلتر']
            
            if p_id is None:
                self._safe_show_toast("❌ بيانات المنتج غير صالحة")
                return False
            
            if stock <= 0.001:
                self._safe_show_toast(f"⚠️ المنتج {name} غير متوفر")
                return False
            
            # الحصول على السعر حسب قائمة السعر المحددة
            if self.current_price_list_id is not None:
                list_price = get_product_price(p_id, self.current_price_list_id)
                if list_price is not None:
                    price = list_price
            
            if p_id in self.cart_items:
                info = self.cart_items[p_id]
                current_qty = info['qty']
                step = 0.5 if is_weighable else 1.0
                new_qty = current_qty + step
                
                if new_qty <= stock + 0.001:
                    info['qty'] = new_qty
                    info['stock'] = stock
                    # تطبيق العروض التلقائية
                    self.apply_promotion_to_product(p_id, info)
                    self._update_table_from_cart()
                    self.update_total()
                    self._safe_show_toast(f"✅ تم إضافة {step} {unit} إلى {name}")
                    return True
                else:
                    self._safe_show_toast(f"⚠️ الكمية المطلوبة أكبر من المتاحة ({stock:.3f} {unit})")
                    return False
            else:
                initial_qty = qty if qty is not None else (0.5 if is_weighable else 1.0)
                if initial_qty > stock:
                    initial_qty = stock
                    if initial_qty <= 0:
                        self._safe_show_toast(f"⚠️ المنتج {name} غير متوفر")
                        return False
                
                self.cart_items[p_id] = {
                    'row': len(self.cart_items),
                    'price': price,
                    'original_price': price,
                    'name': name,
                    'stock': stock,
                    'unit': unit,
                    'category': category,
                    'is_weighable': is_weighable,
                    'qty': initial_qty,
                    'promotion_discount': 0,
                    'promotion_desc': ''
                }
                # تطبيق العروض التلقائية
                self.apply_promotion_to_product(p_id, self.cart_items[p_id])
                self._update_table_from_cart()
                self.update_total()
                self._safe_show_toast(f"✅ تم إضافة {name} إلى السلة")
                return True
            
        except Exception as e:
            logger.error(f"خطأ في add_product: {e}")
            self._safe_show_toast(f"❌ خطأ: {str(e)}")
            return False
    
    def update_qty_from_spin(self, p_id, new_qty):
        if self._updating_spin:
            return
        if p_id not in self.cart_items:
            return
        self._updating_spin = True
        try:
            info = self.cart_items[p_id]
            if new_qty > info['stock'] + 0.001:
                self._safe_show_toast(
                    f"⚠️ الكمية المطلوبة أكبر من المتاحة ({info['stock']:.3f} {info['unit']})"
                )
                spin_widget = self.table.cellWidget(info['row'], 2)
                if spin_widget and isinstance(spin_widget, QDoubleSpinBox):
                    spin_widget.setValue(info['qty'])
                return
            info['qty'] = new_qty
            # تطبيق العروض التلقائية عند تغيير الكمية
            self.apply_promotion_to_product(p_id, info)
            self._update_table_row(p_id)
            self.update_total()
        except Exception as e:
            logger.error(f"خطأ في update_qty_from_spin: {e}")
            self._safe_show_toast(f"❌ خطأ في تحديث الكمية: {str(e)}")
        finally:
            self._updating_spin = False
    
    def _update_table_row(self, p_id):
        try:
            if p_id not in self.cart_items:
                return
            info = self.cart_items[p_id]
            row = info['row']
            if row >= self.table.rowCount():
                return
            display_price = self._get_price(info)
            item_total = self._calculate_item_total(info)
            self.table.setItem(row, 1, QTableWidgetItem(f"{display_price:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{item_total:.2f}"))
            
            # عرض معلومات العرض
            if info.get('promotion_desc', ''):
                promo_item = QTableWidgetItem(info['promotion_desc'])
                promo_item.setForeground(QColor(COLORS['promotion']))
                self.table.setItem(row, 4, promo_item)
            else:
                self.table.setItem(row, 4, QTableWidgetItem(""))
            
            spin_widget = self.table.cellWidget(row, 2)
            if spin_widget and isinstance(spin_widget, QDoubleSpinBox):
                spin_widget.blockSignals(True)
                spin_widget.setValue(info['qty'])
                spin_widget.blockSignals(False)
        except Exception as e:
            logger.error(f"خطأ في _update_table_row: {e}")
    
    def _on_wholesale_toggled(self, checked):
        try:
            self.wholesale_mode = checked
            # إعادة تطبيق العروض مع وضع الجملة
            for p_id, info in self.cart_items.items():
                self.apply_promotion_to_product(p_id, info)
            self._rebuild_table_from_cart()
            self.update_total()
            status = "جملة (خصم 10%)" if checked else "تجزئة"
            self._safe_show_toast(f"🔀 تم التبديل إلى وضع {status}")
        except Exception as e:
            logger.error(f"خطأ في _on_wholesale_toggled: {e}")
            self._safe_show_toast(f"❌ خطأ في التبديل: {str(e)}")
    
    def remove_single_item(self, p_id):
        try:
            if p_id in self.cart_items:
                name = self.cart_items[p_id]['name']
                del self.cart_items[p_id]
                for idx, (pid, info) in enumerate(self.cart_items.items()):
                    info['row'] = idx
                self._rebuild_table_from_cart()
                self.update_total()
                self._safe_show_toast(f"🗑️ تم حذف {name} من السلة")
        except Exception as e:
            logger.error(f"خطأ في remove_single_item: {e}")
            self._safe_show_toast(f"❌ خطأ في حذف المنتج: {str(e)}")
    
    def clear_cart_with_confirmation(self):
        if self._is_clearing:
            return
        if len(self.cart_items) == 0:
            self._safe_show_toast("⚠️ السلة فارغة بالفعل")
            return
        self._safe_show_toast("🗑️ جاري إلغاء الفاتورة...")
        QTimer.singleShot(300, self.clear_cart)
    
    def clear_cart(self):
        if self._is_clearing:
            return
        self._is_clearing = True
        try:
            self.cart_items.clear()
            self.table.setRowCount(0)
            self.discount_percent_spin.blockSignals(True)
            self.discount_amount_spin.blockSignals(True)
            self.wholesale_toggle.blockSignals(True)
            try:
                self.discount_percent_spin.setValue(0)
                self.discount_amount_spin.setValue(0)
                self.wholesale_toggle.setChecked(False)
            except Exception as e:
                logger.error(f"خطأ في إعادة تعيين الخصومات: {e}")
            finally:
                self.discount_percent_spin.blockSignals(False)
                self.discount_amount_spin.blockSignals(False)
                self.wholesale_toggle.blockSignals(False)
            self.tab_total_label.setText("الإجمالي: 0.00 ج.م")
            try:
                if self.parent_window and hasattr(self.parent_window, 'update_main_total'):
                    self.parent_window.update_main_total()
                # تحديث شاشة العرض
                self.update_customer_display()
            except Exception as e:
                logger.error(f"خطأ في تحديث main_total في clear_cart: {e}")
            self._safe_show_toast("✅ تم إلغاء الفاتورة بالكامل")
        except Exception as e:
            logger.error(f"خطأ في clear_cart: {e}")
            self.cart_items.clear()
            self.table.setRowCount(0)
            self.tab_total_label.setText("الإجمالي: 0.00 ج.م")
        finally:
            self._is_clearing = False
    
    def _rebuild_table_from_cart(self):
        if self._updating_table:
            return
        self._updating_table = True
        try:
            self.table.setRowCount(0)
            sorted_items = sorted(self.cart_items.items(), key=lambda x: x[1].get('row', 0))
            for idx, (p_id, info) in enumerate(sorted_items):
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setRowHeight(row, 42)
                info['row'] = row
                display_price = self._get_price(info)
                item_total = self._calculate_item_total(info)
                self.table.setItem(row, 0, QTableWidgetItem(info['name']))
                self.table.setItem(row, 1, QTableWidgetItem(f"{display_price:.2f}"))
                
                spin_qty = QDoubleSpinBox()
                spin_qty.setRange(0.001, info['stock'])
                spin_qty.setValue(info['qty'])
                spin_qty.setSingleStep(0.125 if info['is_weighable'] else 1.0)
                spin_qty.setDecimals(3)
                spin_qty.setSuffix(f" {info['unit']}")
                spin_qty.setMinimumWidth(110)
                spin_qty.setStyleSheet(self._get_spinbox_style())
                spin_qty.valueChanged.connect(lambda val, pid=p_id: self.update_qty_from_spin(pid, val))
                self.table.setCellWidget(row, 2, spin_qty)
                self.table.setItem(row, 3, QTableWidgetItem(f"{item_total:.2f}"))
                
                # عرض معلومات العرض
                if info.get('promotion_desc', ''):
                    promo_item = QTableWidgetItem(info['promotion_desc'])
                    promo_item.setForeground(QColor(COLORS['promotion']))
                    self.table.setItem(row, 4, promo_item)
                else:
                    self.table.setItem(row, 4, QTableWidgetItem(""))
                
                btn_del = QPushButton("✕")
                btn_del.setFixedSize(32, 28)
                btn_del.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['danger']};
                        color: white;
                        border-radius: 6px;
                        font-size: 14px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['danger_hover']};
                    }}
                """)
                btn_del.clicked.connect(lambda ch, pid=p_id: self.remove_single_item(pid))
                self.table.setCellWidget(row, 5, btn_del)
        except Exception as e:
            logger.error(f"خطأ في _rebuild_table_from_cart: {e}")
            self._safe_show_toast(f"❌ خطأ في تحديث الجدول: {str(e)}")
        finally:
            self._updating_table = False
    
    def _update_table_from_cart(self):
        self._rebuild_table_from_cart()
    
    def _format_qty(self, qty):
        try:
            if qty % 1 < 0.001:
                return str(int(qty))
            return f"{qty:.3f}".rstrip('0').rstrip('.')
        except Exception as e:
            logger.error(f"خطأ في _format_qty: {e}")
            return str(qty)
    
    def get_cart_items(self):
        try:
            items = []
            for p_id, info in self.cart_items.items():
                if info.get('qty', 0) > 0:
                    items.append({
                        'id': p_id,
                        'name': info['name'],
                        'price': info['price'],
                        'qty': info.get('qty', 0),
                        'unit': info['unit'],
                        'is_weighable': info['is_weighable'],
                        'stock': info['stock'],
                        'promotion_discount': info.get('promotion_discount', 0),
                        'promotion_desc': info.get('promotion_desc', '')
                    })
            return items
        except Exception as e:
            logger.error(f"خطأ في get_cart_items: {e}")
            return []
    
    def load_cart_items(self, items):
        try:
            self.clear_cart()
            for item in items:
                product = {
                    'id': item['id'],
                    'name': item['name'],
                    'sell_price': item['price'],
                    'stock': item['stock'],
                    'unit': item['unit'],
                    'weight_unit': item['unit'] if item['is_weighable'] else ''
                }
                self.add_product(product, item['qty'])
        except Exception as e:
            logger.error(f"خطأ في load_cart_items: {e}")
            self._safe_show_toast(f"❌ خطأ في تحميل عناصر السلة: {str(e)}")


# ========== نافذة POS الرئيسية ==========
class POSWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.held_invoices = {}
        self.hold_counter = 1
        self._processing_barcode = False
        self._last_search_text = ""
        self._last_add_time = 0
        self.main_total_label = None
        self.customer_display = None
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        
        self.init_ui()
        self.setup_shortcuts()
        self.setup_keyboard_navigation()
        self.check_low_stock_on_startup()
    
    def check_low_stock_on_startup(self):
        try:
            low_stock_products = get_all_low_stock_products()
            if low_stock_products:
                LowStockAlertDialog(low_stock_products, self).exec()
        except Exception as e:
            logger.error(f"خطأ في فحص المخزون المنخفض: {e}")
            self.show_toast(f"⚠️ خطأ في فحص المخزون: {str(e)}")

    def init_ui(self):
        self.setWindowTitle("نظام نقطة البيع - SMART POS")
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.85)
        height = int(screen_geometry.height() * 0.85)
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        self.resize(max(1024, width), max(700, height))
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }}
        """)
        
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setHandleWidth(4)
        main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS['border']};
                border-radius: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS['accent']};
            }}
        """)
        
        # ===== المنطقة العلوية: البحث =====
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)
        
        search_container = QFrame()
        search_container.setMinimumHeight(60)
        search_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(15, 8, 15, 8)
        search_layout.setSpacing(12)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 ابحث عن منتج بالاسم أو الباركود... (مسح تلقائي)")
        self.search_input.setMinimumHeight(42)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                font-size: 14px;
                padding: 0 18px;
                border-radius: 10px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.search_input.returnPressed.connect(self.barcode_scanned)
        self.search_input.textChanged.connect(self.live_search)
        self.search_input.installEventFilter(self)
        search_layout.addWidget(self.search_input, stretch=1)
        
        self.btn_hold = QPushButton("📌 تعليق")
        self.btn_hold.setMinimumHeight(42)
        self.btn_hold.setMinimumWidth(100)
        self.btn_hold.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['warning']};
                color: white;
                border-radius: 10px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['warning_hover']};
            }}
        """)
        self.btn_hold.clicked.connect(self.hold_current_invoice)
        search_layout.addWidget(self.btn_hold)
        
        self.btn_restore = QPushButton("🔄 استدعاء")
        self.btn_restore.setMinimumHeight(42)
        self.btn_restore.setMinimumWidth(100)
        self.btn_restore.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border-radius: 10px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_hover']};
            }}
        """)
        self.btn_restore.clicked.connect(self.restore_invoice)
        search_layout.addWidget(self.btn_restore)
        
        self.held_count_label = QLabel("📋 0")
        self.held_count_label.setStyleSheet(f"""
            color: {COLORS['warning']};
            font-size: 14px;
            font-weight: bold;
            padding: 0 10px;
        """)
        search_layout.addWidget(self.held_count_label)
        
        top_layout.addWidget(search_container)
        
        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(130)
        self.results_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 10px 14px;
                border-bottom: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['bg_sidebar']};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['accent']};
                color: white;
            }}
        """)
        self.results_list.hide()
        self.results_list.itemClicked.connect(self.add_from_list)
        self.results_list.installEventFilter(self)
        top_layout.addWidget(self.results_list)
        
        top_widget.setMinimumHeight(100)
        top_widget.setMaximumHeight(240)
        main_splitter.addWidget(top_widget)
        
        # ===== المنطقة الوسطى: التبويبات =====
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                padding: 6px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['text_muted']};
                border-radius: 8px 8px 0 0;
                padding: 10px 20px;
                margin-right: 4px;
                font-weight: bold;
                font-size: 13px;
                min-width: 80px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['accent']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLORS['border']};
                color: {COLORS['text']};
            }}
            QTabBar::close-button {{
                image: none;
                background-color: {COLORS['danger']};
                border-radius: 10px;
                padding: 2px 8px;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }}
            QTabBar::close-button:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        
        self.add_new_tab("فاتورة 1")
        self.tab_widget.setCornerWidget(self._create_add_tab_button(), Qt.TopRightCorner)
        main_splitter.addWidget(self.tab_widget)
        
        # ===== المنطقة السفلية: أزرار الدفع =====
        bottom_widget = QWidget()
        bottom_widget.setMinimumHeight(80)
        bottom_widget.setMaximumHeight(120)
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(10, 8, 10, 8)
        bottom_layout.setSpacing(15)
        
        self.main_total_label = QLabel("الإجمالي: 0.00 ج.م")
        self.main_total_label.setStyleSheet(f"""
            font-size: 24px;
            color: {COLORS['success']};
            font-weight: 900;
            padding: 0 10px;
            min-width: 200px;
        """)
        bottom_layout.addWidget(self.main_total_label)
        bottom_layout.addStretch()
        
        self.btn_cash = QPushButton("💰 كاش (F5)")
        self.btn_cash.setMinimumWidth(150)
        self.btn_cash.setMinimumHeight(52)
        self.btn_cash.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
            QPushButton:pressed {{
                background-color: #15803d;
            }}
        """)
        self.btn_cash.clicked.connect(self.process_cash_sale)
        bottom_layout.addWidget(self.btn_cash)
        
        self.btn_credit = QPushButton("📋 آجل (F2)")
        self.btn_credit.setMinimumWidth(150)
        self.btn_credit.setMinimumHeight(52)
        self.btn_credit.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_hover']};
            }}
            QPushButton:pressed {{
                background-color: #0284c7;
            }}
        """)
        self.btn_credit.clicked.connect(self.process_deferred_sale)
        bottom_layout.addWidget(self.btn_credit)
        
        self.btn_reprint = QPushButton("🖨️ طباعة (F6)")
        self.btn_reprint.setMinimumWidth(150)
        self.btn_reprint.setMinimumHeight(52)
        self.btn_reprint.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['warning']};
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['warning_hover']};
            }}
        """)
        self.btn_reprint.clicked.connect(self.reprint_last_invoice)
        bottom_layout.addWidget(self.btn_reprint)
        
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([140, 400, 100])
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)
        main_layout.addWidget(main_splitter)
    
    def _create_add_tab_button(self):
        btn = QPushButton("+")
        btn.setFixedSize(32, 32)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 16px;
                font-size: 18px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        btn.clicked.connect(self.add_new_tab)
        return btn
    
    def add_new_tab(self, title=None):
        try:
            tab_count = self.tab_widget.count() + 1
            tab_title = title or f"فاتورة {tab_count}"
            if title and self.find_tab_by_title(title) is not None:
                tab_title = f"{title} ({tab_count})"
            new_tab = InvoiceTab(tab_count, self)
            self.tab_widget.addTab(new_tab, tab_title)
            self.tab_widget.setCurrentWidget(new_tab)
            self.update_main_total()
            self.search_input.setFocus()
            return new_tab
        except Exception as e:
            logger.error(f"خطأ في add_new_tab: {e}")
            self.show_toast(f"❌ خطأ في إنشاء تبويب جديد: {str(e)}")
            return None
    
    def find_tab_by_title(self, title):
        try:
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == title:
                    return self.tab_widget.widget(i)
            return None
        except Exception as e:
            logger.error(f"خطأ في find_tab_by_title: {e}")
            return None
    
    def close_tab(self, index):
        try:
            if self.tab_widget.count() <= 1:
                self.show_toast("⚠️ لا يمكن إغلاق التبويب الأخير")
                return
            tab = self.tab_widget.widget(index)
            if tab and len(tab.cart_items) > 0:
                self.show_toast("🗑️ جاري إغلاق التبويب...")
                QTimer.singleShot(300, lambda: self._force_close_tab(index))
            else:
                self._force_close_tab(index)
        except Exception as e:
            logger.error(f"خطأ في close_tab: {e}")
            self.show_toast(f"❌ خطأ في إغلاق التبويب: {str(e)}")
    
    def _force_close_tab(self, index):
        try:
            self.tab_widget.removeTab(index)
            self.update_main_total()
            self.show_toast("✅ تم إغلاق التبويب")
        except Exception as e:
            logger.error(f"خطأ في _force_close_tab: {e}")
            self.show_toast(f"❌ خطأ في إغلاق التبويب: {str(e)}")
    
    def get_current_tab(self):
        try:
            return self.tab_widget.currentWidget()
        except Exception as e:
            logger.error(f"خطأ في get_current_tab: {e}")
            return None
    
    def update_main_total(self):
        try:
            current_tab = self.get_current_tab()
            if current_tab and hasattr(current_tab, 'tab_total_label'):
                total_text = current_tab.tab_total_label.text()
                if self.main_total_label:
                    self.main_total_label.setText(total_text)
            else:
                if self.main_total_label:
                    self.main_total_label.setText("الإجمالي: 0.00 ج.م")
        except Exception as e:
            logger.error(f"خطأ في update_main_total: {e}")
    
    def setup_shortcuts(self):
        try:
            self.shortcut_f5 = QShortcut(QKeySequence("F5"), self)
            self.shortcut_f5.activated.connect(self.process_cash_sale)
            self.shortcut_f2 = QShortcut(QKeySequence("F2"), self)
            self.shortcut_f2.activated.connect(self.process_deferred_sale)
            self.shortcut_f6 = QShortcut(QKeySequence("F6"), self)
            self.shortcut_f6.activated.connect(self.reprint_last_invoice)
            self.shortcut_enter = QShortcut(QKeySequence("Return"), self)
            self.shortcut_enter.activated.connect(self.barcode_scanned)
            self.shortcut_enter2 = QShortcut(QKeySequence("Enter"), self)
            self.shortcut_enter2.activated.connect(self.barcode_scanned)
        except Exception as e:
            logger.error(f"خطأ في setup_shortcuts: {e}")
    
    def setup_keyboard_navigation(self):
        try:
            self.search_input.setFocus()
        except Exception as e:
            logger.error(f"خطأ في setup_keyboard_navigation: {e}")
    
    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.KeyPress:
                key_event = event
                if obj == self.search_input:
                    if key_event.key() == Qt.Key_Down:
                        if self.results_list.isVisible() and self.results_list.count() > 0:
                            self.results_list.setFocus()
                            self.results_list.setCurrentRow(0)
                            return True
                        elif self.get_current_tab() and self.get_current_tab().table.rowCount() > 0:
                            self.get_current_tab().table.setFocus()
                            self.get_current_tab().table.selectRow(0)
                            return True
                elif obj == self.results_list:
                    if key_event.key() in (Qt.Key_Return, Qt.Key_Enter):
                        current_item = self.results_list.currentItem()
                        if current_item:
                            self.add_from_list(current_item)
                            self.search_input.setFocus()
                            return True
                    elif key_event.key() == Qt.Key_Up and self.results_list.currentRow() == 0:
                        self.search_input.setFocus()
                        return True
                elif obj == self.get_current_tab() and hasattr(obj, 'table'):
                    if obj.table == obj:
                        if key_event.key() in (Qt.Key_Return, Qt.Key_Enter):
                            current_row = obj.table.currentRow()
                            if current_row >= 0:
                                for p_id, info in obj.cart_items.items():
                                    if info['row'] == current_row:
                                        current_qty = info['qty']
                                        step = 0.5 if info.get('is_weighable', False) else 1.0
                                        new_qty = current_qty + step
                                        if new_qty <= info['stock'] + 0.001:
                                            info['qty'] = new_qty
                                            # إعادة تطبيق العروض
                                            obj.apply_promotion_to_product(p_id, info)
                                            obj._update_table_row(p_id)
                                            obj.update_total()
                                            self.show_toast(f"✅ تم زيادة كمية {info['name']}")
                                        else:
                                            self.show_toast(f"⚠️ الكمية المطلوبة أكبر من المتاحة ({info['stock']:.3f})")
                                        break
                                return True
                        elif key_event.key() == Qt.Key_Up and obj.table.currentRow() == 0:
                            self.search_input.setFocus()
                            return True
        except Exception as e:
            logger.error(f"خطأ في eventFilter: {e}")
        return super().eventFilter(obj, event)
    
    def show_toast(self, message, duration=2500):
        try:
            ToastMessage(self, message, duration)
        except Exception as e:
            logger.error(f"خطأ في show_toast: {e}")
    
    def live_search(self):
        try:
            text = self.search_input.text()
            if len(text) < 2:
                self.results_list.hide()
                return
            results = search_products(text)
            self.results_list.clear()
            for p in results:
                if isinstance(p, dict):
                    name = p.get('name', '')
                    sell_price = p.get('sell_price', 0)
                    stock = float(p.get('stock', 0))
                    unit = p.get('weight_unit', p.get('unit', 'قطعة'))
                else:
                    name = p[1] if len(p) > 1 else ''
                    sell_price = p[4] if len(p) > 4 else 0
                    stock = p[5] if len(p) > 5 else 0
                    unit = p[8] if len(p) > 8 else 'قطعة'
                stock_display = f"{stock:.3f}".rstrip('0').rstrip('.') if stock % 1 != 0 else str(int(stock))
                item_text = f"📦 {name} | سعر: {sell_price:.2f} ج.م | المخزن: {stock_display} {unit}"
                self.results_list.addItem(item_text)
                self.results_list.item(self.results_list.count()-1).setData(Qt.UserRole, p)
            self.results_list.show() if results else self.results_list.hide()
        except Exception as e:
            logger.error(f"خطأ في البحث: {e}")
            self.show_toast(f"⚠️ خطأ في البحث: {str(e)}")
    
    def barcode_scanned(self):
        if self._processing_barcode:
            return
        current_time = time.time()
        if current_time - self._last_add_time < 0.2:
            return
        text = self.search_input.text().strip()
        if not text:
            return
        self._processing_barcode = True
        self._last_add_time = current_time
        try:
            if text.startswith("22") and len(text) == 13:
                try:
                    product_code = text[2:7]
                    weight_str = text[7:12]
                    weight = float(weight_str) / 1000
                    results = search_products(product_code)
                    if results:
                        product = results[0]
                        if isinstance(product, dict):
                            unit = product.get('weight_unit', product.get('unit', 'قطعة'))
                        else:
                            unit = product[8] if len(product) > 8 else 'قطعة'
                        if unit in ['كيلو', 'جرام', 'لتر', 'ملليلتر']:
                            self.add_product_to_current_tab(product, weight)
                        else:
                            self.add_product_to_current_tab(product)
                        self.search_input.clear()
                        self.search_input.setFocus()
                        self.results_list.hide()
                        return
                    else:
                        self.show_toast(f"⚠️ لم يتم العثور على منتج بالكود: {product_code}")
                        self.search_input.clear()
                        self.search_input.setFocus()
                        return
                except Exception as e:
                    logger.error(f"خطأ في قراءة باركود الميزان: {e}")
                    self.show_toast(f"⚠️ خطأ في قراءة الباركود: {str(e)}")
                    self.search_input.clear()
                    self.search_input.setFocus()
                    return
            results = search_products(text)
            if results:
                self.add_product_to_current_tab(results[0])
                self.search_input.clear()
                self.search_input.setFocus()
                self.results_list.hide()
            else:
                self.show_toast(f"⚠️ لم يتم العثور على منتج: {text}")
                self.search_input.clear()
                self.search_input.setFocus()
        except Exception as e:
            logger.error(f"خطأ في barcode_scanned: {e}")
            self.show_toast(f"❌ خطأ في القراءة: {str(e)}")
            self.search_input.clear()
            self.search_input.setFocus()
        finally:
            self._processing_barcode = False
    
    def add_product_to_current_tab(self, product, qty=None):
        try:
            current_tab = self.get_current_tab()
            if current_tab:
                if current_tab.add_product(product, qty):
                    self.update_main_total()
            else:
                self.show_toast("❌ لا يوجد تبويب نشط")
        except Exception as e:
            logger.error(f"خطأ في add_product_to_current_tab: {e}")
            self.show_toast(f"❌ خطأ في إضافة المنتج: {str(e)}")
    
    def add_from_list(self, item):
        try:
            product = item.data(Qt.UserRole)
            self.add_product_to_current_tab(product)
            self.results_list.hide()
        except Exception as e:
            logger.error(f"خطأ في add_from_list: {e}")
            self.show_toast(f"❌ خطأ في إضافة المنتج: {str(e)}")
    
    def hold_current_invoice(self):
        try:
            current_tab = self.get_current_tab()
            if not current_tab:
                self.show_toast("❌ لا يوجد فاتورة نشطة")
                return
            if len(current_tab.cart_items) == 0:
                self.show_toast("⚠️ السلة فارغة، لا يمكن تعليق فاتورة فارغة")
                return
            hold_id = self.hold_counter
            self.hold_counter += 1
            items_data = current_tab.get_cart_items()
            total = current_tab.calculate_total()
            self.held_invoices[hold_id] = {
                'items': items_data,
                'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total': total,
                'tab_name': self.tab_widget.tabText(self.tab_widget.currentIndex()),
                'discount_percent': current_tab.discount_percent_spin.value(),
                'discount_amount': current_tab.discount_amount_spin.value(),
                'wholesale_mode': current_tab.wholesale_mode,
                'price_list_id': current_tab.current_price_list_id
            }
            self.update_held_count()
            current_tab.clear_cart()
            self.update_main_total()
            self.show_toast(f"📌 تم تعليق الفاتورة رقم {hold_id} - يمكنك استدعاؤها لاحقاً")
        except Exception as e:
            logger.error(f"خطأ في hold_current_invoice: {e}")
            self.show_toast(f"❌ خطأ في تعليق الفاتورة: {str(e)}")
    
    def restore_invoice(self):
        try:
            if not self.held_invoices:
                self.show_toast("📭 لا توجد فواتير معلقة")
                return
            dialog = RecallInvoicesDialog(self.held_invoices, self)
            if dialog.exec() == QDialog.Accepted:
                hold_id = dialog.selected_hold_id
                if hold_id is not None and hold_id in self.held_invoices:
                    data = self.held_invoices[hold_id]
                    current_tab = self.get_current_tab()
                    if not current_tab:
                        current_tab = self.add_new_tab()
                    if len(current_tab.cart_items) > 0:
                        self.show_toast("⚠️ التبويب الحالي يحتوي على منتجات، سيتم تفريغه")
                        current_tab.clear_cart()
                    
                    # استعادة قائمة السعر
                    if data.get('price_list_id') is not None:
                        for i in range(current_tab.price_list_combo.count()):
                            if current_tab.price_list_combo.itemData(i) == data['price_list_id']:
                                current_tab.price_list_combo.setCurrentIndex(i)
                                break
                    
                    current_tab.load_cart_items(data['items'])
                    current_tab.discount_percent_spin.setValue(data.get('discount_percent', 0))
                    current_tab.discount_amount_spin.setValue(data.get('discount_amount', 0))
                    current_tab.wholesale_toggle.setChecked(data.get('wholesale_mode', False))
                    current_tab.update_total()
                    del self.held_invoices[hold_id]
                    self.update_held_count()
                    self.update_main_total()
                    self.show_toast(f"🔄 تم استعادة الفاتورة رقم {hold_id} بنجاح")
                else:
                    self.show_toast("⚠️ الفاتورة المحددة غير موجودة")
        except Exception as e:
            logger.error(f"خطأ في restore_invoice: {e}")
            self.show_toast(f"❌ خطأ في استدعاء الفاتورة: {str(e)}")
    
    def update_held_count(self):
        try:
            count = len(self.held_invoices)
            if hasattr(self, 'held_count_label'):
                self.held_count_label.setText(f"📋 {count}")
        except Exception as e:
            logger.error(f"خطأ في update_held_count: {e}")
    
    def get_sale_data_from_tab(self, tab):
        try:
            if not tab:
                return None, None, None, None, "لا يوجد تبويب نشط"
            if len(tab.cart_items) == 0:
                return None, None, None, None, "لا توجد منتجات في السلة"
            items_for_db = []
            items_for_pdf = []
            for p_id, info in tab.cart_items.items():
                qty = info.get('qty', 0)
                if qty > 0:
                    effective_price = info['price']
                    if tab.wholesale_mode:
                        effective_price = info['price'] * 0.9
                    items_for_db.append((p_id, qty, effective_price))
                    items_for_pdf.append((info['name'], qty, effective_price))
            total = tab.calculate_total()
            subtotal = tab.get_subtotal()
            discount = subtotal - total
            return items_for_db, items_for_pdf, total, discount, None
        except Exception as e:
            logger.error(f"خطأ في get_sale_data_from_tab: {e}")
            return None, None, None, None, f"خطأ: {str(e)}"
    
    def process_cash_sale(self):
        try:
            current_tab = self.get_current_tab()
            if not current_tab:
                self.show_toast("❌ لا يوجد فاتورة نشطة")
                return
            items_for_db, items_for_pdf, total, discount, error = self.get_sale_data_from_tab(current_tab)
            if error:
                self.show_toast(f"⚠️ {error}")
                return
            if not items_for_db:
                self.show_toast("⚠️ لا توجد منتجات في السلة")
                return
            payment_dialog = SplitPaymentDialog(total, self)
            if payment_dialog.exec() == QDialog.Accepted:
                payment_data = payment_dialog.get_payment_data()
                if payment_data:
                    self.open_cash_drawer()
                    try:
                        result = make_sale(items_for_db, total, discount, 
                                          payment_method='نقدي', 
                                          customer_name=None,
                                          cash_paid=payment_data.get('cash', 0),
                                          visa_paid=payment_data.get('visa', 0))
                        if isinstance(result, tuple) and len(result) >= 2:
                            success = result[0]
                            sale_id = result[1] if len(result) > 1 else None
                            low_stock_alerts = result[2] if len(result) > 2 else []
                        else:
                            success = False
                            sale_id = None
                            low_stock_alerts = []
                    except Exception as e:
                        logger.error(f"خطأ في make_sale: {e}")
                        self.show_toast(f"❌ خطأ في حفظ البيع: {str(e)}")
                        return
                    
                    if success:
                        log_user_activity('Admin', 'بيع نقدي', f'فاتورة #{sale_id} بقيمة {total:.2f} ج.م')
                        if low_stock_alerts and len(low_stock_alerts) > 0:
                            try:
                                LowStockAlertDialog(low_stock_alerts, self).exec()
                            except Exception as e:
                                logger.error(f"خطأ في عرض تنبيه المخزون: {e}")
                        self.generate_invoice_pdf(sale_id, items_for_pdf, total, discount, 
                                                  current_tab.get_subtotal(),
                                                  payment_data, sale_type='نقدي')
                        
                        # عرض نافذة التأكيد مع خيارات الإرسال
                        try:
                            confirm_dialog = InvoiceConfirmationDialog(
                                sale_id, items_for_pdf, total, 
                                current_tab.get_subtotal(), discount,
                                'نقدي', None, payment_data, self
                            )
                            confirm_dialog.exec()
                        except Exception as e:
                            logger.error(f"خطأ في عرض نافذة التأكيد: {e}")
                        
                        try:
                            current_tab.clear_cart()
                        except Exception as e:
                            logger.error(f"خطأ في clear_cart بعد البيع: {e}")
                        self.update_main_total()
                        self.show_toast(f"✅ تمت عملية البيع النقدي بنجاح - فاتورة #{sale_id}")
                        self.search_input.setFocus()
                    else:
                        self.show_toast(f"❌ فشل حفظ البيع: {sale_id if sale_id else 'خطأ غير معروف'}")
            else:
                self.show_toast("❌ تم إلغاء عملية الدفع")
        except Exception as e:
            logger.error(f"خطأ في process_cash_sale: {e}")
            try:
                self.show_toast(f"❌ خطأ: {str(e)}")
            except Exception:
                pass
    
    def process_deferred_sale(self):
        try:
            current_tab = self.get_current_tab()
            if not current_tab:
                self.show_toast("❌ لا يوجد فاتورة نشطة")
                return
            items_for_db, items_for_pdf, total, discount, error = self.get_sale_data_from_tab(current_tab)
            if error:
                self.show_toast(f"⚠️ {error}")
                return
            if not items_for_db:
                self.show_toast("⚠️ لا توجد منتجات في السلة")
                return
            customer_name, ok = QInputDialog.getText(
                self, "💰 بيع آجل", 
                "📋 الرجاء إدخال اسم العميل:",
                QLineEdit.Normal, ""
            )
            if ok and customer_name.strip():
                customer_name = customer_name.strip()
                try:
                    customer = get_customer_by_name(customer_name)
                    if not customer:
                        from back.database import add_customer
                        add_customer(customer_name, "", 0)
                        self.show_toast(f"👤 تم إنشاء عميل جديد: {customer_name}")
                    
                    result = make_sale(items_for_db, total, discount, 
                                      payment_method='آجل', 
                                      customer_name=customer_name,
                                      cash_paid=0,
                                      visa_paid=0)
                    if isinstance(result, tuple) and len(result) >= 2:
                        success = result[0]
                        sale_id = result[1] if len(result) > 1 else None
                        low_stock_alerts = result[2] if len(result) > 2 else []
                    else:
                        success = False
                        sale_id = None
                        low_stock_alerts = []
                except Exception as e:
                    logger.error(f"خطأ في make_sale آجل: {e}")
                    self.show_toast(f"❌ خطأ في حفظ البيع: {str(e)}")
                    return
                
                if success:
                    log_user_activity('Admin', 'بيع آجل', f'فاتورة #{sale_id} للعميل {customer_name} بقيمة {total:.2f} ج.م')
                    try:
                        update_customer_transaction(customer_name, total)
                    except Exception as e:
                        logger.error(f"خطأ في تحديث نقاط الولاء: {e}")
                    if low_stock_alerts and len(low_stock_alerts) > 0:
                        try:
                            LowStockAlertDialog(low_stock_alerts, self).exec()
                        except Exception as e:
                            logger.error(f"خطأ في عرض تنبيه المخزون: {e}")
                    self.generate_invoice_pdf(sale_id, items_for_pdf, total, discount,
                                              current_tab.get_subtotal(),
                                              sale_type='آجل', customer_name=customer_name)
                    
                    # عرض نافذة التأكيد مع خيارات الإرسال
                    try:
                        confirm_dialog = InvoiceConfirmationDialog(
                            sale_id, items_for_pdf, total,
                            current_tab.get_subtotal(), discount,
                            'آجل', customer_name, None, self
                        )
                        confirm_dialog.exec()
                    except Exception as e:
                        logger.error(f"خطأ في عرض نافذة التأكيد: {e}")
                    
                    try:
                        current_tab.clear_cart()
                    except Exception as e:
                        logger.error(f"خطأ في clear_cart بعد البيع الآجل: {e}")
                    self.update_main_total()
                    self.show_toast(f"✅ تم خصم البضاعة وتسجيل دَين للعميل {customer_name} - فاتورة #{sale_id}")
                    self.search_input.setFocus()
                else:
                    self.show_toast(f"❌ فشل حفظ البيع: {sale_id if sale_id else 'خطأ غير معروف'}")
            else:
                if not ok:
                    self.show_toast("❌ تم إلغاء عملية البيع الآجل")
                else:
                    self.show_toast("❌ اسم العميل مطلوب")
        except Exception as e:
            logger.error(f"خطأ في process_deferred_sale: {e}")
            try:
                self.show_toast(f"❌ خطأ في البيع الآجل: {str(e)}")
            except Exception:
                pass
    
    def open_cash_drawer(self):
        try:
            drawer_command = b'\x1b\x70\x00\x19\x96'
            if os.name == 'nt':
                try:
                    import win32print
                    printer_name = win32print.GetDefaultPrinter()
                    if printer_name:
                        hprinter = win32print.OpenPrinter(printer_name)
                        try:
                            win32print.StartDocPrinter(hprinter, 1, ("Cash Drawer", None, "RAW"))
                            win32print.StartPagePrinter(hprinter)
                            win32print.WritePrinter(hprinter, drawer_command)
                            win32print.EndPagePrinter(hprinter)
                            win32print.EndDocPrinter(hprinter)
                        finally:
                            win32print.ClosePrinter(hprinter)
                except Exception as e:
                    logger.error(f"خطأ في فتح الدرج النقدي: {e}")
                    self._send_drawer_command_alternative(drawer_command)
            else:
                self._send_drawer_command_alternative(drawer_command)
        except Exception as e:
            logger.error(f"تعذر فتح الدرج النقدي: {e}")
    
    def _send_drawer_command_alternative(self, command):
        try:
            printer_files = ['/dev/usb/lp0', '/dev/lp0', '/dev/usb/lp1']
            for printer_file in printer_files:
                if os.path.exists(printer_file):
                    with open(printer_file, 'wb') as f:
                        f.write(command)
                    return
            if os.name != 'nt':
                try:
                    subprocess.run(['lp', '-d', 'raw', '-o', 'raw'], input=command, check=False)
                except Exception as e:
                    logger.error(f"فشل فتح الدرج النقدي عبر lp: {e}")
        except Exception as e:
            logger.error(f"فشل فتح الدرج النقدي: {e}")
    
    def generate_invoice_pdf(self, sale_id, items, total, discount, subtotal, 
                             payment_data=None, sale_type='نقدي', customer_name=''):
        """توليد فاتورة PDF مع دعم كامل للغة العربية"""
        try:
            try:
                import hashlib
                from reportlab.pdfbase import pdfdoc
                try:
                    pdfdoc.md5 = lambda usedforsecurity=False: hashlib.md5()
                except Exception:
                    pass
            except Exception:
                pass
            
            if not os.path.exists('invoices'):
                try:
                    os.makedirs('invoices')
                except Exception as e:
                    logger.error(f"خطأ في إنشاء مجلد invoices: {e}")
                    self.show_toast("⚠️ تعذر إنشاء مجلد الفواتير")
                    return
            
            filename = f"invoices/invoice_{sale_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            try:
                c = canvas.Canvas(filename, pagesize=(80*mm, 250*mm))
            except Exception as e:
                logger.error(f"خطأ في إنشاء canvas: {e}")
                self.show_toast("⚠️ تعذر إنشاء PDF")
                return
            
            font_name = get_arabic_font()
            try:
                if font_name == 'ArabicFont':
                    try:
                        c.setFont(font_name, 10)
                    except Exception:
                        c.setFont('Helvetica', 10)
                        font_name = 'Helvetica'
                else:
                    c.setFont('Helvetica', 10)
                    font_name = 'Helvetica'
            except Exception:
                c.setFont('Helvetica', 10)
                font_name = 'Helvetica'
            
            y = 235 * mm
            x_center = 40 * mm
            x_left = 5 * mm
            x_right = 75 * mm
            line_height = 5 * mm
            
            def draw_arabic_text(x, y, text, size=10, bold=False):
                if not text:
                    return
                try:
                    if bold and font_name == 'Helvetica':
                        c.setFont('Helvetica-Bold', size)
                    else:
                        c.setFont(font_name, size)
                except Exception:
                    c.setFont('Helvetica', size)
                
                if ARABIC_SUPPORT:
                    try:
                        processed = reshape_arabic_text(text)
                        c.drawString(x, y, processed)
                        return
                    except Exception:
                        pass
                c.drawString(x, y, text)
            
            def draw_arabic_centered(x, y, text, size=10, bold=False):
                if not text:
                    return
                try:
                    if bold and font_name == 'Helvetica':
                        c.setFont('Helvetica-Bold', size)
                    else:
                        c.setFont(font_name, size)
                except Exception:
                    c.setFont('Helvetica', size)
                
                if ARABIC_SUPPORT:
                    try:
                        processed = reshape_arabic_text(text)
                        text_width = c.stringWidth(processed, font_name if font_name else 'Helvetica', size)
                        c.drawString(x - (text_width / 2), y, processed)
                        return
                    except Exception:
                        pass
                text_width = c.stringWidth(text, font_name if font_name else 'Helvetica', size)
                c.drawString(x - (text_width / 2), y, text)
            
            def draw_right_aligned_arabic(x, y, text, size=10, bold=False):
                if not text:
                    return
                try:
                    if bold and font_name == 'Helvetica':
                        c.setFont('Helvetica-Bold', size)
                    else:
                        c.setFont(font_name, size)
                except Exception:
                    c.setFont('Helvetica', size)
                
                if ARABIC_SUPPORT:
                    try:
                        processed = reshape_arabic_text(text)
                        text_width = c.stringWidth(processed, font_name if font_name else 'Helvetica', size)
                        c.drawString(x - text_width, y, processed)
                        return
                    except Exception:
                        pass
                text_width = c.stringWidth(text, font_name if font_name else 'Helvetica', size)
                c.drawString(x - text_width, y, text)
            
            try:
                draw_arabic_centered(x_center, y, "سوبر ماركت", size=18, bold=True)
                y -= 7 * mm
                
                draw_arabic_centered(x_center, y, "فاتورة بيع", size=12)
                y -= 7 * mm
                
                c.line(x_left, y, x_right, y)
                y -= line_height
                
                draw_arabic_text(x_left, y, f"رقم الفاتورة: {sale_id}", size=10)
                y -= line_height
                
                current_date = datetime.now().strftime('%Y-%m-%d %I:%M %p')
                draw_arabic_text(x_left, y, f"التاريخ: {current_date}", size=10)
                y -= line_height
                
                if customer_name:
                    draw_arabic_text(x_left, y, f"العميل: {customer_name}", size=10)
                    y -= line_height
                
                if sale_type == 'آجل':
                    type_display = "آجل"
                    c.setFillColorRGB(0.83, 0.33, 0)
                elif sale_type == 'مرتجع':
                    type_display = "مرتجع"
                    c.setFillColorRGB(0.65, 0.33, 0.10)
                else:
                    type_display = "نقدي"
                    c.setFillColorRGB(0.15, 0.68, 0.38)
                
                draw_arabic_text(x_left, y, f"نوع الفاتورة: {type_display}", size=10)
                c.setFillColorRGB(0, 0, 0)
                y -= line_height
                
                c.line(x_left, y, x_right, y)
                y -= line_height
                
                draw_right_aligned_arabic(x_left + 15 * mm, y, "المنتج", size=9, bold=True)
                c.drawString(45 * mm, y, "الكمية")
                draw_right_aligned_arabic(75 * mm, y, "السعر", size=9, bold=True)
                y -= 4 * mm
                
                c.line(x_left, y, x_right, y)
                y -= 4 * mm
                
                for name, qty, price in items:
                    if y < 30 * mm:
                        c.showPage()
                        y = 235 * mm
                        try:
                            c.setFont(font_name, 10)
                        except Exception:
                            c.setFont('Helvetica', 10)
                    
                    qty_display = str(int(qty)) if qty % 1 < 0.001 else f"{qty:.3f}".rstrip('0').rstrip('.')
                    
                    draw_right_aligned_arabic(x_left + 15 * mm, y, name[:25], size=8)
                    c.drawString(45 * mm, y, qty_display)
                    draw_right_aligned_arabic(75 * mm, y, f"{qty * price:.2f}", size=9)
                    y -= line_height
                
                y -= 2 * mm
                c.line(x_left, y, x_right, y)
                y -= line_height
                
                draw_right_aligned_arabic(x_left, y, f"المجموع الفرعي: {subtotal:.2f} ج.م", size=10)
                y -= line_height
                
                if discount > 0:
                    draw_right_aligned_arabic(x_left, y, f"الخصم: {discount:.2f} ج.م", size=10)
                    y -= line_height
                
                c.line(x_left, y, x_right, y)
                y -= line_height
                
                draw_right_aligned_arabic(x_left, y, f"الإجمالي النهائي: {total:.2f} ج.م", size=12, bold=True)
                y -= 7 * mm
                
                if payment_data:
                    draw_right_aligned_arabic(x_left, y, "تفاصيل الدفع:", size=10)
                    y -= line_height
                    if payment_data.get('cash', 0) > 0:
                        draw_right_aligned_arabic(x_left + 5 * mm, y, f"كاش: {payment_data['cash']:.2f} ج.م", size=9)
                        y -= 4 * mm
                    if payment_data.get('visa', 0) > 0:
                        draw_right_aligned_arabic(x_left + 5 * mm, y, f"فيزا: {payment_data['visa']:.2f} ج.م", size=9)
                        y -= 4 * mm
                    if payment_data.get('wallet', 0) > 0:
                        draw_right_aligned_arabic(x_left + 5 * mm, y, f"محفظة: {payment_data['wallet']:.2f} ج.م", size=9)
                        y -= 4 * mm
                    y -= 2 * mm
                
                c.line(x_left, y, x_right, y)
                y -= 7 * mm
                
                draw_arabic_centered(x_center, y, "شكراً لتسوقكم معنا", size=10)
                y -= line_height
                draw_arabic_centered(x_center, y, "نتمنى زيارتكم مرة أخرى", size=9)
                
                c.save()
            except Exception as e:
                logger.error(f"خطأ في رسم PDF: {e}")
                self.show_toast("⚠️ تعذر إنشاء PDF، تم حفظ البيع بنجاح")
                return
            
            try:
                if os.name == 'nt':
                    os.startfile(filename)
                else:
                    subprocess.run(['xdg-open', filename], check=False)
            except Exception:
                pass
            
            self.show_toast(f"✅ تم توليد فاتورة PDF: {os.path.basename(filename)}")
            
        except Exception as e:
            logger.error(f"خطأ في generate_invoice_pdf: {e}")
            try:
                self.show_toast(f"⚠️ تعذر إنشاء PDF، تم حفظ البيع بنجاح")
            except Exception:
                pass
    
    def reprint_last_invoice(self):
        try:
            self.show_toast("🖨️ جاري طباعة الفاتورة...")
            current_tab = self.get_current_tab()
            if current_tab and len(current_tab.cart_items) > 0:
                items_for_db, items_for_pdf, total, discount, error = self.get_sale_data_from_tab(current_tab)
                if not error and items_for_pdf:
                    subtotal = current_tab.get_subtotal()
                    self.generate_invoice_pdf('temp', items_for_pdf, total, discount, subtotal)
                    self.show_toast("🖨️ تم طباعة الفاتورة الحالية")
            else:
                self.show_toast("⚠️ لا توجد فاتورة للطباعة")
        except Exception as e:
            logger.error(f"خطأ في reprint_last_invoice: {e}")
            self.show_toast(f"❌ خطأ في طباعة الفاتورة: {str(e)}")
    
    def closeEvent(self, event):
        """إغلاق شاشة عرض العميل عند إغلاق النافذة الرئيسية"""
        try:
            if self.customer_display and self.customer_display.isVisible():
                self.customer_display.close()
                self.customer_display = None
        except Exception as e:
            logger.error(f"خطأ في إغلاق شاشة العرض: {e}")
        event.accept()


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        window = POSWindow()
        window.showMaximized()
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"خطأ في تشغيل التطبيق: {e}")