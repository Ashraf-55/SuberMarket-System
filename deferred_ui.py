# ================= deferred_ui.py - نظام الحسابات الآجلة المتطور (نسخة مع مطابقة أذكى للأسماء) =================
"""
نافذة الحسابات الآجلة المتكاملة - تدعم إدارة حسابات العملاء والموردين
مع تبويبات منفصلة وتصفية متقدمة
📌 تعمل فقط مع قاعدة البيانات الفعلية - لا توجد بيانات افتراضية
"""

import logging
import traceback
import re
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel,
                             QPushButton, QFrame, QDialog, QFormLayout, QLineEdit,
                             QDateEdit, QDoubleSpinBox, QComboBox, QTextEdit,
                             QScrollArea, QTabWidget, QGroupBox, QCheckBox,
                             QSplitter, QToolButton, QMenu, QApplication,
                             QInputDialog)
from PyQt5.QtCore import Qt, QDate, QPropertyAnimation, QTimer, QDateTime, pyqtSignal
from PyQt5.QtGui import QFont, QColor as QGColor, QIcon, QPixmap

from back import database as db
from back.database import get_connection

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== الألوان الثابتة الموحدة ==========
COLORS = {
    'bg_dark': '#F3F7F7',
    'bg_sidebar': '#FFFFFF',
    'bg_card': '#FFFFFF',
    'bg_input': '#FFFFFF',
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
    'border_light': '#e2e8f0',
    'loyalty_color': '#ec4899',
    'debt_color': '#dc2626',
    'paid_color': '#16a34a',
    'urgent_color': '#dc2626'
}

FONTS = {
    'title': QFont("Segoe UI", 20, QFont.Bold),
    'subtitle': QFont("Segoe UI", 14, QFont.Bold),
    'button': QFont("Segoe UI", 12, QFont.Medium),
    'table': QFont("Segoe UI", 11),
    'toast': QFont("Segoe UI", 11, QFont.Medium)
}


# ========== دوال مطابقة الأسماء الذكية ==========
def normalize_name(name):
    """
    تطبيع الاسم لإزالة المسافات الزائدة والتشكيل
    """
    if not name:
        return ""
    # إزالة المسافات الزائدة
    name = re.sub(r'\s+', ' ', name.strip())
    # إزالة التشكيل (حركات)
    name = re.sub(r'[\u064B-\u065F]', '', name)
    return name


def get_name_parts(name):
    """
    استخراج أجزاء الاسم (الاسم الأول، الاسم الأخير، الأسماء الوسطى)
    """
    if not name:
        return [], []
    normalized = normalize_name(name)
    parts = normalized.split()
    if len(parts) == 0:
        return [], []
    if len(parts) == 1:
        return [parts[0]], []
    return [parts[0]], parts[1:]  # الاسم الأول، باقي الأسماء


def is_name_match(name1, name2):
    """
    التحقق مما إذا كان الاسمين متطابقين بشكل ذكي
    - مقارنة بعد التطبيع
    - مقارنة الاسم الأول والأخير
    - مقارنة نسبة التشابه
    """
    if not name1 or not name2:
        return False
    
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    
    # تطابق تام بعد التطبيع
    if n1 == n2:
        return True
    
    # استخراج الأجزاء
    first1, rest1 = get_name_parts(n1)
    first2, rest2 = get_name_parts(n2)
    
    if not first1 or not first2:
        return False
    
    # مقارنة الاسم الأول
    if first1[0] != first2[0]:
        return False
    
    # مقارنة الاسم الأخير (آخر جزء)
    if rest1 and rest2:
        if rest1[-1] != rest2[-1]:
            return False
    elif rest1 or rest2:
        # واحد له اسم أخير والآخر لا
        # قد يكون اسم ثنائي مقابل ثلاثي
        pass
    
    # حساب نسبة التشابه
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, n1, n2).ratio()
    
    # إذا كانت نسبة التشابه عالية (أكثر من 80%) اعتبرهم متطابقين
    return similarity >= 0.8


def find_matching_customer(customers, name):
    """
    البحث عن عميل مطابق للاسم باستخدام المطابقة الذكية
    """
    if not customers or not name:
        return None
    
    name = normalize_name(name)
    
    for customer in customers:
        customer_name = normalize_name(customer.get('name', ''))
        if is_name_match(name, customer_name):
            return customer
    
    return None


def find_matching_supplier(suppliers, name):
    """
    البحث عن مورد مطابق للاسم باستخدام المطابقة الذكية
    """
    if not suppliers or not name:
        return None
    
    name = normalize_name(name)
    
    for supplier in suppliers:
        supplier_name = normalize_name(supplier.get('name', ''))
        if is_name_match(name, supplier_name):
            return supplier
    
    return None


# ========== نظام Toast موحد (لون واحد ثابت) ==========
class ToastMessage(QLabel):
    def __init__(self, parent, message, duration=2500):
        # لون موحد للجميع
        toast_color = COLORS['bg_card']
        border_color = COLORS['accent']
        
        super().__init__(message, parent)
        self.duration = duration
        self.setFont(FONTS['toast'])
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {toast_color};
                color: {COLORS['text']};
                border-radius: 12px;
                padding: 12px 24px;
                font-size: 12px;
                font-weight: bold;
                border: 2px solid {border_color};
            }}
        """)
        
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(45)
        self.setMaximumWidth(400)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # حساب الموقع بناءً على حجم الشاشة
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setFixedWidth(min(350, screen_geometry.width() - 40))
        
        x = (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.height() - 100
        self.move(x, y)
        
        self.setWindowOpacity(0)
        self.show()
        
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(0.95)
        self.fade_in_animation.start()
        
        QTimer.singleShot(duration, self.fade_out)
    
    def fade_out(self):
        self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_animation.setDuration(400)
        self.fade_out_animation.setStartValue(0.95)
        self.fade_out_animation.setEndValue(0)
        self.fade_out_animation.finished.connect(self.deleteLater)
        self.fade_out_animation.start()


# ========== نافذة كشف الحساب للعميل ==========
class CustomerStatementDialog(QDialog):
    def __init__(self, customer, parent=None):
        super().__init__(parent)
        self.customer = customer
        self.setWindowTitle(f"📊 كشف حساب - {customer['name']}")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.5)
        height = int(screen_geometry.height() * 0.6)
        self.setMinimumSize(int(screen_geometry.width() * 0.45), int(screen_geometry.height() * 0.5))
        self.resize(max(700, width), max(500, height))
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 12px;
            }}
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
            QPushButton {{
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                color: white;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        
        name_label = QLabel(f"👤 {customer['name']}")
        name_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        
        phone_label = QLabel(f"📞 {customer.get('phone', 'غير مسجل')}")
        phone_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        header_layout.addWidget(phone_label)
        
        layout.addLayout(header_layout)
        
        summary_frame = QFrame()
        summary_frame.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 10px; border: 1px solid {COLORS['border']}; }}")
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(15, 10, 15, 10)
        
        total_debt = customer.get('total_debt', 0)
        paid = customer.get('paid_amount', 0)
        remaining = customer.get('remaining', 0)
        
        summary_layout.addWidget(QLabel(f"💳 إجمالي المديونية: {total_debt:,.2f} ج.م"))
        summary_layout.addWidget(QLabel(f"✅ المدفوع: {paid:,.2f} ج.م"))
        summary_layout.addWidget(QLabel(f"⚠️ المتبقي: {remaining:,.2f} ج.م"))
        summary_layout.addWidget(QLabel(f"⭐ نقاط الولاء: {customer.get('loyalty_points', 0)}"))
        
        layout.addWidget(summary_frame)
        
        table_label = QLabel("📋 سجل الفواتير والحركات")
        table_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold; font-size: 14px;")
        layout.addWidget(table_label)
        
        # ====== تعديل الريسبونسيف: تغليف الجدول بـ ScrollArea ======
        table_scroll = QScrollArea()
        table_scroll.setWidgetResizable(True)
        table_scroll.setStyleSheet("border: none; background-color: transparent;")
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["رقم الفاتورة", "التاريخ", "المبلغ", "المدفوع", "المتبقي"])
        self.table.setAlternatingRowColors(False)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        invoices = customer.get('invoices', [])
        self.table.setRowCount(len(invoices))
        
        for row, invoice in enumerate(invoices):
            inv_id = invoice.get('id', '')
            date = invoice.get('date', '')
            amount = float(invoice.get('amount', 0))
            paid = float(invoice.get('paid', 0))
            remaining = amount - paid
            
            self.table.setItem(row, 0, QTableWidgetItem(str(inv_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(date)))
            
            amount_item = QTableWidgetItem(f"{amount:,.2f} ج.م")
            amount_item.setTextAlignment(Qt.AlignRight)
            self.table.setItem(row, 2, amount_item)
            
            paid_item = QTableWidgetItem(f"{paid:,.2f} ج.م")
            paid_item.setTextAlignment(Qt.AlignRight)
            paid_item.setForeground(QGColor(34, 197, 94))
            self.table.setItem(row, 3, paid_item)
            
            remaining_item = QTableWidgetItem(f"{remaining:,.2f} ج.م")
            remaining_item.setTextAlignment(Qt.AlignRight)
            if remaining > 0:
                remaining_item.setForeground(QGColor(239, 68, 68))
            else:
                remaining_item.setForeground(QGColor(34, 197, 94))
            self.table.setItem(row, 4, remaining_item)
        
        table_scroll.setWidget(self.table)
        layout.addWidget(table_scroll)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        close_btn = QPushButton("❌ إغلاق")
        close_btn.setMinimumHeight(38)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 8px 20px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)


# ========== نافذة إضافة عميل جديد (مع مطابقة ذكية) ==========
class AddCustomerDialog(QDialog):
    def __init__(self, parent=None, existing_customers=None):
        super().__init__(parent)
        self.existing_customers = existing_customers or []
        self.matched_customer = None
        self.setWindowTitle("👤 إضافة عميل جديد")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.35)
        height = int(screen_geometry.height() * 0.4)
        self.setMinimumSize(int(screen_geometry.width() * 0.3), int(screen_geometry.height() * 0.35))
        self.resize(max(400, width), max(350, height))
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 12px;
            }}
            QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QTextEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
                min-height: 32px;
            }}
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QTextEdit {{
                min-height: 60px;
            }}
            QPushButton {{
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                color: white;
            }}
        """)
        
        # ====== تعديل الريسبونسيف: تغليف المحتوى بـ ScrollArea ======
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("👤 إضافة عميل جديد")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.match_warning_label = QLabel("")
        self.match_warning_label.setWordWrap(True)
        self.match_warning_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px;")
        self.match_warning_label.setVisible(False)
        layout.addWidget(self.match_warning_label)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("الاسم الكامل")
        self.name_input.textChanged.connect(self.check_name_match)
        form_layout.addRow("اسم العميل:", self.name_input)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("رقم الهاتف")
        form_layout.addRow("رقم الهاتف:", self.phone_input)
        
        self.debt_input = QDoubleSpinBox()
        self.debt_input.setRange(0, 1000000)
        self.debt_input.setPrefix("ج.م ")
        self.debt_input.setDecimals(2)
        self.debt_input.setValue(0)
        form_layout.addRow("المديونية الابتدائية:", self.debt_input)
        
        layout.addLayout(form_layout)
        
        self.use_existing_btn = QPushButton("✅ استخدام الحساب الموجود")
        self.use_existing_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        self.use_existing_btn.clicked.connect(self.use_existing_account)
        self.use_existing_btn.setVisible(False)
        layout.addWidget(self.use_existing_btn)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        self.confirm_btn = QPushButton("✅ إضافة جديد")
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        self.confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.confirm_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
    
    def check_name_match(self):
        """التحقق من تطابق الاسم مع عميل موجود"""
        name = self.name_input.text().strip()
        if not name or not self.existing_customers:
            self.match_warning_label.setVisible(False)
            self.use_existing_btn.setVisible(False)
            self.matched_customer = None
            return
        
        matched = find_matching_customer(self.existing_customers, name)
        if matched:
            self.matched_customer = matched
            self.match_warning_label.setText(
                f"⚠️ يوجد عميل باسم مشابه: '{matched.get('name', '')}'\n"
                f"يمكنك إضافة الرصيد للحساب الموجود بدلاً من إنشاء حساب جديد."
            )
            self.match_warning_label.setVisible(True)
            self.use_existing_btn.setVisible(True)
            self.confirm_btn.setText("➕ إضافة جديد (مختلف)")
        else:
            self.match_warning_label.setVisible(False)
            self.use_existing_btn.setVisible(False)
            self.matched_customer = None
            self.confirm_btn.setText("✅ إضافة جديد")
    
    def use_existing_account(self):
        """استخدام الحساب الموجود وإضافة الرصيد إليه"""
        if self.matched_customer:
            self.accept()
    
    def get_data(self):
        return {
            'name': self.name_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'debt': self.debt_input.value(),
            'matched_customer': self.matched_customer
        }


# ========== نافذة إضافة مورد جديد (مع مطابقة ذكية) ==========
class AddSupplierDialog(QDialog):
    def __init__(self, parent=None, existing_suppliers=None):
        super().__init__(parent)
        self.existing_suppliers = existing_suppliers or []
        self.matched_supplier = None
        self.setWindowTitle("🏢 إضافة مورد جديد")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.35)
        height = int(screen_geometry.height() * 0.45)
        self.setMinimumSize(int(screen_geometry.width() * 0.3), int(screen_geometry.height() * 0.4))
        self.resize(max(400, width), max(400, height))
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 12px;
            }}
            QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QTextEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
                min-height: 32px;
            }}
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QTextEdit {{
                min-height: 60px;
            }}
            QPushButton {{
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                color: white;
            }}
        """)
        
        # ====== تعديل الريسبونسيف: تغليف المحتوى بـ ScrollArea ======
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("🏢 إضافة مورد جديد")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.match_warning_label = QLabel("")
        self.match_warning_label.setWordWrap(True)
        self.match_warning_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px;")
        self.match_warning_label.setVisible(False)
        layout.addWidget(self.match_warning_label)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم الشركة")
        self.name_input.textChanged.connect(self.check_name_match)
        form_layout.addRow("اسم المورد:", self.name_input)
        
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("اسم جهة الاتصال")
        form_layout.addRow("جهة الاتصال:", self.contact_input)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("رقم الهاتف")
        form_layout.addRow("رقم الهاتف:", self.phone_input)
        
        self.balance_input = QDoubleSpinBox()
        self.balance_input.setRange(0, 1000000)
        self.balance_input.setPrefix("ج.م ")
        self.balance_input.setDecimals(2)
        self.balance_input.setValue(0)
        form_layout.addRow("المستحقات الابتدائية:", self.balance_input)
        
        layout.addLayout(form_layout)
        
        self.use_existing_btn = QPushButton("✅ استخدام الحساب الموجود")
        self.use_existing_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        self.use_existing_btn.clicked.connect(self.use_existing_account)
        self.use_existing_btn.setVisible(False)
        layout.addWidget(self.use_existing_btn)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        self.confirm_btn = QPushButton("✅ إضافة جديد")
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        self.confirm_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.confirm_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
    
    def check_name_match(self):
        """التحقق من تطابق الاسم مع مورد موجود"""
        name = self.name_input.text().strip()
        if not name or not self.existing_suppliers:
            self.match_warning_label.setVisible(False)
            self.use_existing_btn.setVisible(False)
            self.matched_supplier = None
            return
        
        matched = find_matching_supplier(self.existing_suppliers, name)
        if matched:
            self.matched_supplier = matched
            self.match_warning_label.setText(
                f"⚠️ يوجد مورد باسم مشابه: '{matched.get('name', '')}'\n"
                f"يمكنك إضافة الرصيد للحساب الموجود بدلاً من إنشاء حساب جديد."
            )
            self.match_warning_label.setVisible(True)
            self.use_existing_btn.setVisible(True)
            self.confirm_btn.setText("➕ إضافة جديد (مختلف)")
        else:
            self.match_warning_label.setVisible(False)
            self.use_existing_btn.setVisible(False)
            self.matched_supplier = None
            self.confirm_btn.setText("✅ إضافة جديد")
    
    def use_existing_account(self):
        """استخدام الحساب الموجود وإضافة الرصيد إليه"""
        if self.matched_supplier:
            self.accept()
    
    def get_data(self):
        return {
            'name': self.name_input.text().strip(),
            'contact': self.contact_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'balance': self.balance_input.value(),
            'matched_supplier': self.matched_supplier
        }


# ========== شاشة الحسابات الآجلة المتكاملة (معدلة) ==========
class DeferredAccountsWindow(QWidget):
    customer_deleted = pyqtSignal(int)
    supplier_deleted = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.customers = []
        self.suppliers = []
        self.debts = []
        self.customer_id_counter = 1
        self.supplier_id_counter = 1
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        self.init_ui()
        self.load_customers()
        self.load_suppliers()
        self.load_debts()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        title = QLabel("💳 إدارة الحسابات والذمم المالية")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['text']}; padding: 8px;")
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {COLORS['bg_dark']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                padding: 8px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['text_muted']};
                padding: 10px 20px;
                border: 1px solid {COLORS['border']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['accent']};
                border-bottom: 3px solid {COLORS['accent']};
            }}
            QTabBar::tab:hover {{
                color: {COLORS['text']};
            }}
        """)
        
        # ===== تبويب العملاء =====
        customer_tab = QWidget()
        customer_layout = QVBoxLayout(customer_tab)
        customer_layout.setSpacing(10)
        customer_layout.setContentsMargins(0, 0, 0, 0)
        
        customer_filter_frame = QFrame()
        customer_filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        customer_filter_layout = QHBoxLayout(customer_filter_frame)
        customer_filter_layout.setContentsMargins(12, 8, 12, 8)
        customer_filter_layout.setSpacing(10)
        
        customer_filter_layout.addWidget(QLabel("🔍 بحث:"))
        self.customer_search = QLineEdit()
        self.customer_search.setPlaceholderText("ابحث باسم العميل...")
        self.customer_search.setMinimumHeight(35)
        self.customer_search.setMinimumWidth(200)
        self.customer_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.customer_search.textChanged.connect(self.filter_customers)
        customer_filter_layout.addWidget(self.customer_search)
        
        customer_filter_layout.addWidget(QLabel(" | "))
        customer_filter_layout.addWidget(QLabel("📊 فلتر:"))
        
        self.customer_filter = QComboBox()
        self.customer_filter.addItems(["الكل", "العملاء المديونين فقط", "العملاء الأكثر نقاطاً"])
        self.customer_filter.setMinimumWidth(170)
        self.customer_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 5px 10px;
                min-height: 30px;
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
        self.customer_filter.currentTextChanged.connect(self.filter_customers)
        customer_filter_layout.addWidget(self.customer_filter)
        
        customer_filter_layout.addStretch()
        
        btn_add_customer = QPushButton("➕ إضافة عميل")
        btn_add_customer.setMinimumHeight(35)
        btn_add_customer.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        btn_add_customer.clicked.connect(self.add_customer)
        customer_filter_layout.addWidget(btn_add_customer)
        
        customer_layout.addWidget(customer_filter_frame)
        
        # ===== جدول العملاء مع دعم Scroll =====
        customer_table_container = QScrollArea()
        customer_table_container.setWidgetResizable(True)
        customer_table_container.setStyleSheet("border: none; background-color: transparent;")
        
        self.customer_table = QTableWidget()
        self.customer_table.setAlternatingRowColors(False)
        self.customer_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(56, 189, 248, 0.2);
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        
        self.customer_table.setColumnCount(8)
        self.customer_table.setHorizontalHeaderLabels([
            "معرف العميل", "اسم العميل", "الهاتف", "رصيد المديونية", 
            "نقاط الولاء", "آخر حركة", "الحالة", "الإجراءات"
        ])
        
        header = self.customer_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.customer_table.setColumnWidth(7, 350)
        
        customer_table_container.setWidget(self.customer_table)
        customer_layout.addWidget(customer_table_container)
        
        self.tabs.addTab(customer_tab, "👥 حسابات العملاء والآجل")
        
        # ===== تبويب الموردين =====
        supplier_tab = QWidget()
        supplier_layout = QVBoxLayout(supplier_tab)
        supplier_layout.setSpacing(10)
        supplier_layout.setContentsMargins(0, 0, 0, 0)
        
        supplier_filter_frame = QFrame()
        supplier_filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        supplier_filter_layout = QHBoxLayout(supplier_filter_frame)
        supplier_filter_layout.setContentsMargins(12, 8, 12, 8)
        supplier_filter_layout.setSpacing(10)
        
        supplier_filter_layout.addWidget(QLabel("🔍 بحث:"))
        self.supplier_search = QLineEdit()
        self.supplier_search.setPlaceholderText("ابحث باسم المورد...")
        self.supplier_search.setMinimumHeight(35)
        self.supplier_search.setMinimumWidth(200)
        self.supplier_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.supplier_search.textChanged.connect(self.filter_suppliers)
        supplier_filter_layout.addWidget(self.supplier_search)
        
        supplier_filter_layout.addWidget(QLabel(" | "))
        supplier_filter_layout.addWidget(QLabel("📊 فلتر:"))
        
        self.supplier_filter = QComboBox()
        self.supplier_filter.addItems(["الكل", "المستحق سدادهم هذا الأسبوع", "الموردين الدائنين"])
        self.supplier_filter.setMinimumWidth(200)
        self.supplier_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 5px 10px;
                min-height: 30px;
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
        self.supplier_filter.currentTextChanged.connect(self.filter_suppliers)
        supplier_filter_layout.addWidget(self.supplier_filter)
        
        supplier_filter_layout.addStretch()
        
        btn_add_supplier = QPushButton("➕ إضافة مورد")
        btn_add_supplier.setMinimumHeight(35)
        btn_add_supplier.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        btn_add_supplier.clicked.connect(self.add_supplier)
        supplier_filter_layout.addWidget(btn_add_supplier)
        
        supplier_layout.addWidget(supplier_filter_frame)
        
        # ===== جدول الموردين مع دعم Scroll =====
        supplier_table_container = QScrollArea()
        supplier_table_container.setWidgetResizable(True)
        supplier_table_container.setStyleSheet("border: none; background-color: transparent;")
        
        self.supplier_table = QTableWidget()
        self.supplier_table.setAlternatingRowColors(False)
        self.supplier_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(56, 189, 248, 0.2);
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        
        self.supplier_table.setColumnCount(9)
        self.supplier_table.setHorizontalHeaderLabels([
            "معرف المورد", "اسم الشركة", "جهة الاتصال", "الهاتف",
            "إجمالي المستحقات", "المدفوع", "المتبقي", "موعد السداد", "الإجراءات"
        ])
        
        header = self.supplier_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        self.supplier_table.setColumnWidth(8, 300)
        
        supplier_table_container.setWidget(self.supplier_table)
        supplier_layout.addWidget(supplier_table_container)
        
        self.tabs.addTab(supplier_tab, "🏢 حسابات الموردين والجدولة")
        
        layout.addWidget(self.tabs)
    
    def show_toast(self, message, duration=2500):
        ToastMessage(self, message, duration)
    
    def show_success_toast(self, message):
        self.show_toast(message)
    
    def show_warning_toast(self, message):
        self.show_toast(message)
    
    def show_error_toast(self, message):
        self.show_toast(message)
    
    def show_info_toast(self, message):
        self.show_toast(message)
    
    # =====================================================
    # ===== دالة تحميل الديون =====
    # =====================================================
    def load_debts(self):
        try:
            self.debts = db.get_all_debts()
            self.customer_table.setRowCount(0)
            
            if not self.debts:
                self.show_info_toast("📭 لا توجد ديون مسجلة")
                return
            
            # تجميع الديون حسب اسم العميل (مثل deferred_uif.py)
            customer_aggregated = {}
            for debt in self.debts:
                customer_name = debt.get('customer_name', '')
                if not customer_name:
                    continue
                
                if customer_name not in customer_aggregated:
                    customer_aggregated[customer_name] = {
                        'id': debt.get('id'),
                        'name': customer_name,
                        'phone': debt.get('customer_phone', ''),
                        'total_debt': 0.0,
                        'paid_amount': 0.0,
                        'remaining': 0.0,
                        'invoice_count': 0,
                        'debts_ids': [],
                        'last_date': debt.get('debt_date', '')
                    }
                
                amount = float(debt.get('amount', 0))
                paid = float(debt.get('paid_amount', 0))
                remaining = float(debt.get('remaining_amount', 0))
                
                customer_aggregated[customer_name]['total_debt'] += amount
                customer_aggregated[customer_name]['paid_amount'] += paid
                customer_aggregated[customer_name]['remaining'] += remaining
                customer_aggregated[customer_name]['invoice_count'] += 1
                customer_aggregated[customer_name]['debts_ids'].append(debt.get('id'))
                
                # تحديث آخر تاريخ
                debt_date = debt.get('debt_date', '')
                if debt_date and debt_date > customer_aggregated[customer_name]['last_date']:
                    customer_aggregated[customer_name]['last_date'] = debt_date
            
            self.customer_table.setRowCount(len(customer_aggregated))
            
            for row, (customer_name, data) in enumerate(customer_aggregated.items()):
                self.customer_table.setRowHeight(row, 50)
                
                id_item = QTableWidgetItem(str(data.get('id', '')))
                id_item.setTextAlignment(Qt.AlignCenter)
                self.customer_table.setItem(row, 0, id_item)
                
                name_item = QTableWidgetItem(customer_name)
                name_item.setTextAlignment(Qt.AlignCenter)
                self.customer_table.setItem(row, 1, name_item)
                
                phone_item = QTableWidgetItem(data.get('phone', ''))
                phone_item.setTextAlignment(Qt.AlignCenter)
                self.customer_table.setItem(row, 2, phone_item)
                
                remaining = data.get('remaining', 0)
                debt_item = QTableWidgetItem(f"{remaining:,.2f} ج.م")
                debt_item.setTextAlignment(Qt.AlignRight)
                if remaining > 0:
                    debt_item.setForeground(QGColor(239, 68, 68))
                else:
                    debt_item.setForeground(QGColor(34, 197, 94))
                self.customer_table.setItem(row, 3, debt_item)
                
                points_item = QTableWidgetItem("0")
                points_item.setTextAlignment(Qt.AlignCenter)
                self.customer_table.setItem(row, 4, points_item)
                
                date_item = QTableWidgetItem(str(data.get('last_date', '')))
                date_item.setTextAlignment(Qt.AlignCenter)
                self.customer_table.setItem(row, 5, date_item)
                
                if remaining <= 0:
                    status = "مدفوع بالكامل"
                    color = QGColor(34, 197, 94)
                elif remaining > 0:
                    status = "مستحق"
                    color = QGColor(245, 158, 11)
                else:
                    status = "غير محدد"
                    color = QGColor(148, 163, 184)
                
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setForeground(color)
                self.customer_table.setItem(row, 6, status_item)
                
                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                btn_layout = QHBoxLayout(container)
                btn_layout.setAlignment(Qt.AlignCenter)
                btn_layout.setSpacing(4)
                btn_layout.setContentsMargins(2, 2, 2, 2)
                
                # دمج بيانات العميل للمطابقة مع deferred_uif.py
                customer_data = {
                    'id': data.get('id'),
                    'name': customer_name,
                    'phone': data.get('phone', ''),
                    'total_debt': data.get('total_debt', 0),
                    'paid_amount': data.get('paid_amount', 0),
                    'remaining': remaining,
                    'loyalty_points': 0,
                    'invoices': [{
                        'id': d_id,
                        'date': data.get('last_date', ''),
                        'amount': data.get('total_debt', 0) / max(1, data.get('invoice_count', 1)),
                        'paid': data.get('paid_amount', 0) / max(1, data.get('invoice_count', 1))
                    } for d_id in data.get('debts_ids', [])]
                }
                
                btn_statement = QPushButton("📊")
                btn_statement.setFixedSize(30, 28)
                btn_statement.setCursor(Qt.PointingHandCursor)
                btn_statement.setToolTip("كشف حساب")
                btn_statement.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['info']};
                        color: white;
                        border-radius: 5px;
                        font-size: 13px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['info_hover']};
                    }}
                """)
                btn_statement.clicked.connect(lambda _, c=customer_data: self.show_customer_statement(c))
                btn_layout.addWidget(btn_statement)
                
                btn_pay = QPushButton("💰")
                btn_pay.setFixedSize(30, 28)
                btn_pay.setCursor(Qt.PointingHandCursor)
                btn_pay.setToolTip("تسجيل دفعة")
                btn_pay.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['success']};
                        color: white;
                        border-radius: 5px;
                        font-size: 13px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['success_hover']};
                    }}
                """)
                if remaining <= 0:
                    btn_pay.setEnabled(False)
                    btn_pay.setStyleSheet(btn_pay.styleSheet() + f"background-color: {COLORS['text_muted']};")
                first_debt_id = data.get('debts_ids', [None])[0] if data.get('debts_ids') else None
                btn_pay.clicked.connect(lambda _, did=first_debt_id, cname=customer_name: 
                                       self.process_debt_payment(did, cname))
                btn_layout.addWidget(btn_pay)
                
                btn_delete = QPushButton("🗑️")
                btn_delete.setFixedSize(30, 28)
                btn_delete.setCursor(Qt.PointingHandCursor)
                btn_delete.setToolTip("حذف الدين")
                btn_delete.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['danger']};
                        color: white;
                        border-radius: 5px;
                        font-size: 13px;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['danger_hover']};
                    }}
                """)
                # حذف كل ديون العميل (مثل deferred_uif.py)
                btn_delete.clicked.connect(lambda _, d_ids=data.get('debts_ids', []): self.delete_customer_debts(d_ids))
                btn_layout.addWidget(btn_delete)
                
                self.customer_table.setCellWidget(row, 7, container)
            
            self.show_success_toast(f"✅ تم تحميل {len(customer_aggregated)} عميل")
            
        except Exception as e:
            logger.error(f"خطأ في load_debts: {e}")
            self.show_error_toast(f"❌ خطأ في تحميل الديون: {str(e)}")
    
    def delete_customer_debts(self, debt_ids):
        """حذف جميع ديون عميل (مثل deferred_uif.py)"""
        if not debt_ids:
            self.show_warning_toast("لا توجد ديون للحذف")
            return
        
        # نافذة تأكيد
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("تأكيد الحذف")
        confirm_dialog.setModal(True)
        confirm_dialog.setFixedSize(400, 180)
        confirm_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border: 2px solid {COLORS['danger']};
                border-radius: 15px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
            }}
            QPushButton {{
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 8px 20px;
                min-height: 35px;
            }}
        """)
        
        confirm_layout = QVBoxLayout(confirm_dialog)
        confirm_layout.setSpacing(15)
        confirm_layout.setContentsMargins(20, 20, 20, 20)
        
        msg_label = QLabel(f"هل أنت متأكد من حذف {len(debt_ids)} دين؟")
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignCenter)
        confirm_layout.addWidget(msg_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        yes_btn = QPushButton("نعم، حذف")
        yes_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        yes_btn.clicked.connect(confirm_dialog.accept)
        
        no_btn = QPushButton("إلغاء")
        no_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['border']};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border_light']};
            }}
        """)
        no_btn.clicked.connect(confirm_dialog.reject)
        
        btn_layout.addWidget(yes_btn)
        btn_layout.addWidget(no_btn)
        confirm_layout.addLayout(btn_layout)
        
        if confirm_dialog.exec() == QDialog.Accepted:
            all_success = True
            for debt_id in debt_ids:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM debt_payments WHERE debt_id = ?", (debt_id,))
                    cursor.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"خطأ في حذف الدين {debt_id}: {e}")
                    all_success = False
            
            if all_success:
                self.show_success_toast(f"✅ تم حذف {len(debt_ids)} دين بنجاح")
                self.load_debts()
                self.load_customers()
            else:
                self.show_error_toast("❌ حدث خطأ في حذف بعض الديون")
    
    # =====================================================
    # ===== دالة تسجيل دفعة على دين =====
    # =====================================================
    def process_debt_payment(self, debt_id, customer_name=""):
        try:
            logger.info(f"جاري معالجة دفعة للدين ID: {debt_id}")
            
            if debt_id is None:
                self.show_warning_toast("⚠️ لا يوجد دين محدد للدفعة")
                return
            
            debts = db.get_all_debts()
            debt = next((d for d in debts if d.get('id') == debt_id), None)
            
            if not debt:
                self.show_warning_toast("⚠️ الدين غير موجود")
                return
            
            remaining = float(debt.get('remaining_amount', 0))
            logger.info(f"المبلغ المتبقي: {remaining}")
            
            if remaining <= 0:
                self.show_warning_toast("✅ هذا الدين مدفوع بالكامل")
                return
            
            amount, ok = QInputDialog.getDouble(
                self,
                "💰 تسجيل دفعة",
                f"أدخل مبلغ الدفعة للعميل {customer_name or debt.get('customer_name', '')}\n(المتبقي: {remaining:,.2f} ج.م):",
                0.0,
                0.0,
                float(remaining),
                2
            )
            
            if not ok or amount <= 0:
                self.show_info_toast("❌ تم إلغاء عملية الدفعة")
                return
            
            logger.info(f"مبلغ الدفعة: {amount}")
            
            try:
                amount_float = float(amount)
                logger.info(f"تم تحويل المبلغ إلى float: {amount_float}")
            except ValueError as ve:
                logger.error(f"خطأ في تحويل المبلغ: {ve}")
                self.show_error_toast(f"❌ خطأ في صيغة المبلغ: {str(ve)}")
                return
            
            try:
                logger.info("جاري تسجيل الدفعة في قاعدة البيانات...")
                success, msg = db.add_debt_payment(
                    debt_id=debt_id,
                    payment_amount=amount_float,
                    payment_method='نقدي',
                    notes=f'دفعة من العميل {customer_name or debt.get("customer_name", "")}'
                )
                logger.info(f"نتيجة العملية: success={success}, msg={msg}")
                
            except Exception as db_error:
                logger.error(f"خطأ في دالة add_debt_payment: {db_error}")
                self.show_error_toast(f"❌ خطأ في قاعدة البيانات: {str(db_error)}")
                return
            
            if success:
                self.show_success_toast(f"✅ {msg}\n💰 المبلغ: {amount_float:,.2f} ج.م")
                logger.info("تم تسجيل الدفعة بنجاح")
                
                logger.info("جاري تحديث الجدول...")
                self.load_customers()
                self.load_debts()
                
                logger.info("تم تحديث الجدول بنجاح")
            else:
                self.show_error_toast(f"❌ فشل تسجيل الدفعة: {msg}")
                logger.error(f"فشل تسجيل الدفعة: {msg}")
                
        except Exception as e:
            logger.error(f"خطأ غير متوقع في process_debt_payment: {e}")
            self.show_error_toast(f"❌ خطأ غير متوقع: {str(e)}")
    
    # =====================================================
    # ===== دالة حذف دين (فردي) =====
    # =====================================================
    def delete_debt(self, debt_id):
        try:
            debts = db.get_all_debts()
            debt = next((d for d in debts if d.get('id') == debt_id), None)
            
            if not debt:
                self.show_warning_toast("⚠️ الدين غير موجود")
                return
            
            # استخدام نافذة تأكيد مخصصة بدلاً من QMessageBox
            confirm_dialog = QDialog(self)
            confirm_dialog.setWindowTitle("تأكيد الحذف")
            confirm_dialog.setModal(True)
            
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            confirm_dialog.setFixedSize(min(400, screen_geometry.width() - 40), min(180, screen_geometry.height() - 40))
            confirm_dialog.setStyleSheet(f"""
                QDialog {{
                    background-color: {COLORS['bg_dark']};
                    border: 2px solid {COLORS['danger']};
                    border-radius: 15px;
                }}
                QLabel {{
                    color: {COLORS['text']};
                    font-size: 13px;
                }}
                QPushButton {{
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    border: none;
                    padding: 8px 20px;
                    min-height: 35px;
                }}
            """)
            
            confirm_layout = QVBoxLayout(confirm_dialog)
            confirm_layout.setSpacing(15)
            confirm_layout.setContentsMargins(20, 20, 20, 20)
            
            msg_label = QLabel(f"هل أنت متأكد من حذف دين العميل {debt.get('customer_name', '')} بقيمة {debt.get('remaining_amount', 0):,.2f} ج.م؟")
            msg_label.setWordWrap(True)
            msg_label.setAlignment(Qt.AlignCenter)
            confirm_layout.addWidget(msg_label)
            
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(12)
            
            yes_btn = QPushButton("نعم، حذف")
            yes_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['danger']};
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['danger_hover']};
                }}
            """)
            yes_btn.clicked.connect(confirm_dialog.accept)
            
            no_btn = QPushButton("إلغاء")
            no_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['border']};
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['border_light']};
                }}
            """)
            no_btn.clicked.connect(confirm_dialog.reject)
            
            btn_layout.addWidget(yes_btn)
            btn_layout.addWidget(no_btn)
            confirm_layout.addLayout(btn_layout)
            
            if confirm_dialog.exec() == QDialog.Accepted:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM debt_payments WHERE debt_id = ?", (debt_id,))
                    cursor.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
                    conn.commit()
                    conn.close()
                    
                    self.show_success_toast("✅ تم حذف الدين بنجاح")
                    self.load_debts()
                    self.load_customers()
                    
                except Exception as e:
                    logger.error(f"خطأ في حذف الدين: {e}")
                    self.show_error_toast(f"❌ خطأ في حذف الدين: {str(e)}")
            
        except Exception as e:
            logger.error(f"خطأ في delete_debt: {e}")
            self.show_error_toast(f"❌ خطأ: {str(e)}")
    
    # =====================================================
    # ===== دوال تحميل وتحديث أخرى =====
    # =====================================================
    def load_customers(self):
        try:
            self.customers = db.get_all_customers()
            self.filter_customers()
            if not self.customers:
                self.show_info_toast("📭 لا يوجد عملاء مسجلين")
        except Exception as e:
            logger.error(f"خطأ في load_customers: {e}")
            self.show_warning_toast(f"❌ خطأ في تحميل العملاء: {str(e)}")
    
    def load_suppliers(self):
        try:
            self.suppliers = db.get_all_suppliers()
            self.filter_suppliers()
            if not self.suppliers:
                self.show_info_toast("📭 لا يوجد موردين مسجلين")
        except Exception as e:
            logger.error(f"خطأ في load_suppliers: {e}")
            self.show_warning_toast(f"❌ خطأ في تحميل الموردين: {str(e)}")
    
    def add_customer(self):
        """
        إضافة عميل جديد مع التحقق من عدم تكرار الأسماء
        - إذا كان الاسم موجوداً: تحديث الرصيد الحالي
        - إذا كان الاسم جديداً: إنشاء عميل جديد
        مستوحى من منطق deferred_uif.py لمنع التكرار
        """
        # تحميل العملاء الحاليين للمطابقة
        existing_customers = self.customers if self.customers else []
        dlg = AddCustomerDialog(self, existing_customers)
        
        if dlg.exec():
            data = dlg.get_data()
            
            if not data['name']:
                self.show_warning_toast("⚠️ اسم العميل مطلوب")
                return
            
            # التحقق من وجود عميل مطابق (تطابق تام للاسم)
            matched_customer = None
            name_normalized = normalize_name(data['name'])
            
            # البحث عن تطابق تام للاسم (وليس تشابه)
            for customer in existing_customers:
                if normalize_name(customer.get('name', '')) == name_normalized:
                    matched_customer = customer
                    break
            
            if matched_customer:
                # الاسم موجود -> تحديث الرصيد الحالي
                matched_id = matched_customer.get('id')
                debt_amount = data['debt']
                
                if debt_amount > 0:
                    try:
                        # الحصول على الرصيد الحالي للعميل
                        current_debt = matched_customer.get('remaining', 0)
                        new_debt = current_debt + debt_amount
                        
                        # تحديث رصيد العميل في قاعدة البيانات
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE customers SET total_debt = ? WHERE id = ?",
                            (new_debt, matched_id)
                        )
                        conn.commit()
                        conn.close()
                        
                        # تسجيل الدين الجديد في جدول الديون
                        success, msg = db.add_customer_debt(matched_id, debt_amount)
                        
                        if success:
                            self.show_success_toast(
                                f"✅ تم تحديث رصيد العميل {matched_customer['name']}\n"
                                f"تم إضافة {debt_amount:,.2f} ج.م (الرصيد الجديد: {new_debt:,.2f} ج.م)"
                            )
                            self.load_customers()
                            self.load_debts()
                        else:
                            self.show_warning_toast(f"❌ {msg}")
                    except Exception as e:
                        logger.error(f"خطأ في تحديث رصيد العميل: {e}")
                        self.show_error_toast(f"❌ خطأ في تحديث الرصيد: {str(e)}")
                else:
                    self.show_info_toast(f"ℹ️ العميل {matched_customer['name']} موجود بالفعل، لم يتم إضافة رصيد")
                
                return
            
            # الاسم غير موجود -> إنشاء عميل جديد
            try:
                success, msg = db.add_customer(
                    name=data['name'],
                    phone=data['phone'],
                    debt=data['debt']
                )
                
                if success:
                    self.show_success_toast(f"✅ {msg}")
                    self.load_customers()
                    self.load_debts()
                else:
                    self.show_warning_toast(f"❌ {msg}")
            except Exception as e:
                logger.error(f"خطأ في add_customer: {e}")
                self.show_error_toast(f"❌ خطأ: {str(e)}")
    
    def add_supplier(self):
        """
        إضافة مورد جديد مع التحقق من عدم تكرار الأسماء
        مستوحى من منطق deferred_uif.py لمنع التكرار
        """
        # تحميل الموردين الحاليين للمطابقة
        existing_suppliers = self.suppliers if self.suppliers else []
        dlg = AddSupplierDialog(self, existing_suppliers)
        
        if dlg.exec():
            data = dlg.get_data()
            
            if not data['name']:
                self.show_warning_toast("⚠️ اسم المورد مطلوب")
                return
            
            # التحقق من وجود مورد مطابق (تطابق تام للاسم)
            matched_supplier = None
            name_normalized = normalize_name(data['name'])
            
            for supplier in existing_suppliers:
                if normalize_name(supplier.get('name', '')) == name_normalized:
                    matched_supplier = supplier
                    break
            
            if matched_supplier:
                # الاسم موجود -> تحديث الرصيد الحالي
                matched_id = matched_supplier.get('id')
                balance_amount = data['balance']
                
                if balance_amount > 0:
                    try:
                        # الحصول على الرصيد الحالي للمورد
                        current_balance = matched_supplier.get('remaining', 0)
                        new_balance = current_balance + balance_amount
                        
                        # تحديث رصيد المورد في قاعدة البيانات
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE suppliers SET total_balance = ? WHERE id = ?",
                            (new_balance, matched_id)
                        )
                        conn.commit()
                        conn.close()
                        
                        # تسجيل المديونية الجديدة
                        success, msg = db.add_supplier_balance(matched_id, balance_amount)
                        
                        if success:
                            self.show_success_toast(
                                f"✅ تم تحديث رصيد المورد {matched_supplier['name']}\n"
                                f"تم إضافة {balance_amount:,.2f} ج.م (الرصيد الجديد: {new_balance:,.2f} ج.م)"
                            )
                            self.load_suppliers()
                        else:
                            self.show_warning_toast(f"❌ {msg}")
                    except Exception as e:
                        logger.error(f"خطأ في تحديث رصيد المورد: {e}")
                        self.show_error_toast(f"❌ خطأ في تحديث الرصيد: {str(e)}")
                else:
                    self.show_info_toast(f"ℹ️ المورد {matched_supplier['name']} موجود بالفعل، لم يتم إضافة رصيد")
                
                return
            
            # الاسم غير موجود -> إنشاء مورد جديد
            try:
                success, msg = db.add_supplier(
                    name=data['name'],
                    contact=data['contact'],
                    phone=data['phone'],
                    balance=data['balance']
                )
                
                if success:
                    self.show_success_toast(f"✅ {msg}")
                    self.load_suppliers()
                else:
                    self.show_warning_toast(f"❌ {msg}")
            except Exception as e:
                logger.error(f"خطأ في add_supplier: {e}")
                self.show_error_toast(f"❌ خطأ: {str(e)}")
    
    def delete_customer(self, customer_id):
        try:
            success, msg = db.delete_customer(customer_id)
            if success:
                self.show_success_toast(f"✅ {msg}")
                self.load_customers()
                self.load_debts()
            else:
                self.show_warning_toast(f"❌ {msg}")
        except Exception as e:
            logger.error(f"خطأ في delete_customer: {e}")
            self.show_warning_toast(f"❌ خطأ في حذف العميل: {str(e)}")
    
    def delete_supplier(self, supplier_id):
        try:
            success, msg = db.delete_supplier(supplier_id)
            if success:
                self.show_success_toast(f"✅ {msg}")
                self.load_suppliers()
            else:
                self.show_warning_toast(f"❌ {msg}")
        except Exception as e:
            logger.error(f"خطأ في delete_supplier: {e}")
            self.show_warning_toast(f"❌ خطأ في حذف المورد: {str(e)}")
    
    def filter_customers(self):
        search_text = self.customer_search.text().strip().lower()
        filter_type = self.customer_filter.currentText()
        
        filtered = self.customers.copy()
        
        if search_text:
            filtered = [c for c in filtered if search_text in c.get('name', '').lower()]
        
        if filter_type == "العملاء المديونين فقط":
            filtered = [c for c in filtered if c.get('remaining', 0) > 0]
        elif filter_type == "العملاء الأكثر نقاطاً":
            filtered = sorted(filtered, key=lambda x: x.get('loyalty_points', 0), reverse=True)
        
        self.display_customers(filtered)
    
    def filter_suppliers(self):
        search_text = self.supplier_search.text().strip().lower()
        filter_type = self.supplier_filter.currentText()
        
        filtered = self.suppliers.copy()
        
        if search_text:
            filtered = [s for s in filtered if search_text in s.get('name', '').lower()]
        
        if filter_type == "المستحق سدادهم هذا الأسبوع":
            today = datetime.now().date()
            filtered = []
            for s in self.suppliers:
                if s.get('next_payment_date'):
                    try:
                        due_date = datetime.strptime(s['next_payment_date'], "%Y-%m-%d").date()
                        if 0 <= (due_date - today).days <= 7:
                            filtered.append(s)
                    except:
                        pass
        elif filter_type == "الموردين الدائنين":
            filtered = [s for s in filtered if s.get('remaining', 0) <= 0]
        
        self.display_suppliers(filtered)
    
    def display_customers(self, customers):
        self.customer_table.setRowCount(len(customers))
        
        for row, customer in enumerate(customers):
            self.customer_table.setRowHeight(row, 50)
            
            id_item = QTableWidgetItem(str(customer.get('id', '')))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.customer_table.setItem(row, 0, id_item)
            
            name_item = QTableWidgetItem(customer.get('name', ''))
            name_item.setTextAlignment(Qt.AlignCenter)
            self.customer_table.setItem(row, 1, name_item)
            
            phone_item = QTableWidgetItem(customer.get('phone', ''))
            phone_item.setTextAlignment(Qt.AlignCenter)
            self.customer_table.setItem(row, 2, phone_item)
            
            remaining = customer.get('remaining', 0)
            debt_item = QTableWidgetItem(f"{remaining:,.2f} ج.م")
            debt_item.setTextAlignment(Qt.AlignRight)
            if remaining > 0:
                debt_item.setForeground(QGColor(239, 68, 68))
            else:
                debt_item.setForeground(QGColor(34, 197, 94))
            self.customer_table.setItem(row, 3, debt_item)
            
            points = customer.get('loyalty_points', 0)
            points_item = QTableWidgetItem(str(points))
            points_item.setTextAlignment(Qt.AlignCenter)
            if points >= 50:
                points_item.setForeground(QGColor(236, 72, 153))
                points_item.setToolTip("⭐ عميل مميز")
            self.customer_table.setItem(row, 4, points_item)
            
            last_date = customer.get('last_transaction', '')
            date_item = QTableWidgetItem(str(last_date))
            date_item.setTextAlignment(Qt.AlignCenter)
            self.customer_table.setItem(row, 5, date_item)
            
            if remaining <= 0:
                status = "مدفوع بالكامل"
                color = QGColor(34, 197, 94)
            elif remaining > 0:
                status = "مستحق"
                color = QGColor(245, 158, 11)
            else:
                status = "غير محدد"
                color = QGColor(148, 163, 184)
            
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(color)
            self.customer_table.setItem(row, 6, status_item)
            
            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            btn_layout = QHBoxLayout(container)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.setSpacing(4)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            btn_statement = QPushButton("📊")
            btn_statement.setFixedSize(30, 28)
            btn_statement.setCursor(Qt.PointingHandCursor)
            btn_statement.setToolTip("كشف حساب")
            btn_statement.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['info']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['info_hover']};
                }}
            """)
            btn_statement.clicked.connect(lambda _, c=customer: self.show_customer_statement(c))
            btn_layout.addWidget(btn_statement)
            
            btn_pay = QPushButton("💰")
            btn_pay.setFixedSize(30, 28)
            btn_pay.setCursor(Qt.PointingHandCursor)
            btn_pay.setToolTip("تسوية دفعة")
            btn_pay.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['success']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['success_hover']};
                }}
            """)
            if remaining <= 0:
                btn_pay.setEnabled(False)
                btn_pay.setStyleSheet(btn_pay.styleSheet() + f"background-color: {COLORS['text_muted']};")
            btn_pay.clicked.connect(lambda _, c=customer: self.process_customer_payment(c))
            btn_layout.addWidget(btn_pay)
            
            btn_delete = QPushButton("🗑️")
            btn_delete.setFixedSize(30, 28)
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.setToolTip("حذف العميل")
            btn_delete.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['danger']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['danger_hover']};
                }}
            """)
            btn_delete.clicked.connect(lambda _, cid=customer.get('id'): self.delete_customer(cid))
            btn_layout.addWidget(btn_delete)
            
            self.customer_table.setCellWidget(row, 7, container)
    
    def display_suppliers(self, suppliers):
        self.supplier_table.setRowCount(len(suppliers))
        
        for row, supplier in enumerate(suppliers):
            self.supplier_table.setRowHeight(row, 50)
            
            id_item = QTableWidgetItem(str(supplier.get('id', '')))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.supplier_table.setItem(row, 0, id_item)
            
            name_item = QTableWidgetItem(supplier.get('name', ''))
            name_item.setTextAlignment(Qt.AlignCenter)
            self.supplier_table.setItem(row, 1, name_item)
            
            contact_item = QTableWidgetItem(supplier.get('contact_person', ''))
            contact_item.setTextAlignment(Qt.AlignCenter)
            self.supplier_table.setItem(row, 2, contact_item)
            
            phone_item = QTableWidgetItem(supplier.get('phone', ''))
            phone_item.setTextAlignment(Qt.AlignCenter)
            self.supplier_table.setItem(row, 3, phone_item)
            
            total = supplier.get('total_balance', 0)
            total_item = QTableWidgetItem(f"{total:,.2f} ج.م")
            total_item.setTextAlignment(Qt.AlignRight)
            self.supplier_table.setItem(row, 4, total_item)
            
            paid = supplier.get('paid_amount', 0)
            paid_item = QTableWidgetItem(f"{paid:,.2f} ج.م")
            paid_item.setTextAlignment(Qt.AlignRight)
            paid_item.setForeground(QGColor(34, 197, 94))
            self.supplier_table.setItem(row, 5, paid_item)
            
            remaining = supplier.get('remaining', 0)
            remaining_item = QTableWidgetItem(f"{remaining:,.2f} ج.م")
            remaining_item.setTextAlignment(Qt.AlignRight)
            if remaining > 0:
                remaining_item.setForeground(QGColor(239, 68, 68))
            else:
                remaining_item.setForeground(QGColor(34, 197, 94))
            self.supplier_table.setItem(row, 6, remaining_item)
            
            next_date = supplier.get('next_payment_date', '')
            date_item = QTableWidgetItem(str(next_date))
            date_item.setTextAlignment(Qt.AlignCenter)
            
            if next_date:
                try:
                    due_date = datetime.strptime(next_date, "%Y-%m-%d").date()
                    today = datetime.now().date()
                    days_diff = (due_date - today).days
                    if 0 <= days_diff <= 7:
                        date_item.setForeground(QGColor(220, 38, 38))
                        date_item.setToolTip(f"⚠️ مستحق خلال {days_diff} أيام")
                    elif days_diff < 0:
                        date_item.setForeground(QGColor(220, 38, 38))
                        date_item.setToolTip("⛔ تاريخ السداد قد فات")
                except:
                    pass
            
            self.supplier_table.setItem(row, 7, date_item)
            
            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            btn_layout = QHBoxLayout(container)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.setSpacing(4)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            btn_schedule = QPushButton("📅")
            btn_schedule.setFixedSize(30, 28)
            btn_schedule.setCursor(Qt.PointingHandCursor)
            btn_schedule.setToolTip("جدولة دفعة")
            btn_schedule.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['warning_hover']};
                }}
            """)
            if remaining <= 0:
                btn_schedule.setEnabled(False)
                btn_schedule.setStyleSheet(btn_schedule.styleSheet() + f"background-color: {COLORS['text_muted']};")
            btn_schedule.clicked.connect(lambda _, s=supplier: self.schedule_supplier_payment(s))
            btn_layout.addWidget(btn_schedule)
            
            btn_record = QPushButton("📝")
            btn_record.setFixedSize(30, 28)
            btn_record.setCursor(Qt.PointingHandCursor)
            btn_record.setToolTip("تسجيل مديونية")
            btn_record.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['info_hover']};
                }}
            """)
            btn_record.clicked.connect(lambda _, s=supplier: self.record_supplier_debt(s))
            btn_layout.addWidget(btn_record)
            
            btn_delete = QPushButton("🗑️")
            btn_delete.setFixedSize(30, 28)
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.setToolTip("حذف المورد")
            btn_delete.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['danger']};
                    color: white;
                    border-radius: 5px;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['danger_hover']};
                }}
            """)
            btn_delete.clicked.connect(lambda _, sid=supplier.get('id'): self.delete_supplier(sid))
            btn_layout.addWidget(btn_delete)
            
            self.supplier_table.setCellWidget(row, 8, container)
    
    def show_customer_statement(self, customer):
        dlg = CustomerStatementDialog(customer, self)
        dlg.exec()
    
    def process_customer_payment(self, customer):
        if customer.get('remaining', 0) <= 0:
            self.show_warning_toast("هذا العميل ليس عليه مديونية")
            return
        
        amount, ok = QInputDialog.getDouble(
            self,
            "💰 تسوية دفعة",
            f"أدخل مبلغ الدفعة للعميل {customer['name']} (المتبقي: {customer.get('remaining', 0):,.2f} ج.م):",
            0.01,
            0.01,
            customer.get('remaining', 0),
            2
        )
        
        if ok and amount > 0:
            success, msg = db.add_customer_payment(customer['id'], amount)
            if success:
                self.show_success_toast(f"✅ {msg}")
                self.load_customers()
                self.load_debts()
            else:
                self.show_warning_toast(f"❌ {msg}")
    
    def schedule_supplier_payment(self, supplier):
        if supplier.get('remaining', 0) <= 0:
            self.show_warning_toast("هذا المورد ليس عليه مستحقات")
            return
        
        remaining = supplier.get('remaining', 0)
        amount, ok = QInputDialog.getDouble(
            self,
            "📅 جدولة دفعة",
            f"أدخل مبلغ الدفعة للمورد {supplier['name']} (المتبقي: {remaining:,.2f} ج.م):",
            0.01,
            0.01,
            remaining,
            2,
            Qt.WindowFlags(),
            10.0
        )
        
        if ok and amount > 0:
            date, ok = QInputDialog.getText(
                self, "📅 موعد السداد",
                "أدخل تاريخ السداد (YYYY-MM-DD):"
            )
            if ok and date:
                success, msg = db.update_supplier_payment_date(supplier['id'], date, amount)
                if success:
                    self.show_success_toast(f"✅ {msg}")
                    self.load_suppliers()
                else:
                    self.show_warning_toast(f"❌ {msg}")
    
    def record_supplier_debt(self, supplier):
        amount, ok = QInputDialog.getDouble(
            self,
            "📝 تسجيل مديونية مورد",
            f"أدخل مبلغ المديونية الجديدة لـ {supplier['name']}:",
            0.01,
            0.01,
            1000000.0,
            2,
            Qt.WindowFlags(),
            100.0
        )
        
        if ok and amount > 0:
            date, ok = QInputDialog.getText(
                self, "📅 موعد السداد",
                "أدخل تاريخ السداد (YYYY-MM-DD):"
            )
            if ok and date:
                success, msg = db.add_supplier_debt(supplier['id'], amount, date)
                if success:
                    self.show_success_toast(f"✅ {msg}")
                    self.load_suppliers()
                else:
                    self.show_warning_toast(f"❌ {msg}")


if __name__ == "__main__":
    app = QApplication([])
    window = DeferredAccountsWindow()
    window.showMaximized()
    app.exec_()