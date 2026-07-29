# ================= main_dashboard.py - Responsive with Permissions =================
"""
لوحة التحكم الرئيسية لنظام الماركت الذكي
تدعم نظام الصلاحيات، سجل الأنشطة، وإعدادات النظام
🔄 تعمل ببيانات حقيقية من قاعدة البيانات
"""

import sys
import os
import json
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget, 
                             QFrame, QScrollArea, QLineEdit, QDialog, QDialogButtonBox,
                             QComboBox, QDoubleSpinBox, QGroupBox, QFormLayout,
                             QFileDialog, QProgressBar, QTextEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QCheckBox, QGridLayout,
                             QDesktopWidget, QMessageBox, QDateEdit, QTextEdit)
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPropertyAnimation, QEasingCurve, QDate

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# استيراد الشاشات الأساسية
from add_product_ui import AddProductWindow 
from pos_ui import POSWindow
from reports_ui import ReportsWindow
from sales_history_ui import SalesHistoryWindow

# استيراد الشاشات المنفصلة
from deferred_ui import DeferredAccountsWindow
from damaged_ui import DamagedGoodsWindow
from sales_return_ui import SalesReturnWindow
from purchase_return_ui import PurchaseReturnWindow
from transfer_ui import StockTransferWindow

# استيراد قاعدة البيانات
from back.database import (get_dashboard_stats, get_all_low_stock_products,
                           get_all_sales, get_today_cash_sales,
                           get_today_deferred_sales, get_total_outstanding_debts,
                           log_user_activity, backup_database, list_backups,
                           get_theme_settings, save_theme_settings, record_logout,
                           add_expense, get_expenses, delete_expense,
                           get_all_categories, add_category, delete_category, update_category)

# استيراد مدير التصنيفات
from manage_categories_ui import CategoryManagerDialog

# ========== الألوان الثابتة ==========
COLORS = {
    'bg_dark': '#F3F7F7',
    'bg_sidebar': '#FFFFFF',
    'bg_card': '#FFFFFF',
    'bg_card_dark': '#e2e8f0',
    'bg_input': '#FFFFFF',
    'text': '#1e293b',
    'text_muted': '#64748b',
    'accent': '#0284c7',
    'success': '#16a34a',
    'success_hover': '#15803d',
    'danger': '#dc2626',
    'danger_dark': '#b91c1c',
    'warning': '#d97706',
    'warning_hover': '#b45309',
    'border': '#cbd5e1',
    'border_light': '#e2e8f0',
    'info': '#0284c7',
    'purple': '#9333ea',
}

FONTS = {
    'title': QFont("Segoe UI", 20, QFont.Bold),
    'subtitle': QFont("Segoe UI", 16, QFont.Medium),
    'button': QFont("Segoe UI", 13, QFont.Medium),
    'small': QFont("Segoe UI", 11),
}

# ========== قاموس صلاحيات الأدوار ==========
SCREEN_PERMISSIONS = {
    0:  {'title': "🛒 المبيعات",        'roles': ['مدير', 'محاسب', 'كاشير']},
    1:  {'title': "📜 سجل الفواتير",    'roles': ['مدير', 'محاسب', 'كاشير']},
    2:  {'title': "📦 المخزن",          'roles': ['مدير', 'محاسب']},
    3:  {'title': "📊 التقارير",        'roles': ['مدير', 'محاسب']},
    4:  {'title': "💳 الحسابات الآجلة", 'roles': ['مدير', 'محاسب']},
    5:  {'title': "↩️ مرتجع مبيعات",    'roles': ['مدير', 'محاسب', 'كاشير']},
    6:  {'title': "🔃 مرتجع مشتريات",   'roles': ['مدير']},
    7:  {'title': "🚚 نقل مخزني",       'roles': ['مدير']},
    8:  {'title': "⚠️ تالف / هالك",    'roles': ['مدير']},
    9:  {'title': "📋 سجل النشاط",      'roles': ['مدير', 'محاسب']},
    10: {'title': "⚙️ الإعدادات",      'roles': ['مدير']},
    11: {'title': "💰 المصروفات",      'roles': ['مدير', 'محاسب']},
    12: {'title': "🤖 الذكاء الاصطناعي التنبؤي", 'roles': ['مدير']},
}

ROLE_PERMISSIONS = {
    'كاشير': [0, 1, 5],
    'مندوب مبيعات': [0, 1, 5],
    'محاسب': [0, 1, 2, 3, 4, 5, 9, 11],
    'مدير': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
}

# ========== صلاحيات العمليات الدقيقة ==========
ACTION_PERMISSIONS = {
    'delete_product': ['مدير'],
    'edit_price': ['مدير', 'محاسب'],
    'manual_discount': ['مدير', 'محاسب'],
    'delete_sale': ['مدير'],
    'delete_expense': ['مدير'],
    'add_expense': ['مدير', 'محاسب'],
}


# ========== نظام Toast المتقدم (موحد) ==========
class ToastMessage(QLabel):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    
    def __init__(self, parent, message, toast_type=SUCCESS, duration=2500):
        toast_color = COLORS['bg_card']
        border_color = COLORS['accent']
        
        super().__init__(message, parent)
        self.duration = duration
        self.setFont(QFont("Segoe UI", 11, QFont.Medium))
        
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


# ========== دالة عرض الذكاء الاصطناعي ==========
def show_ai_market_predictions(self):
    """
    دالة موحدة لعرض صفحة توقعات الذكاء الاصطناعي وتحديث بياناتها مباشرة
    """
    try:
        # التحقق من وجود الصفحة
        if not hasattr(self, 'ai_page') or self.ai_page is None:
            from ai_predictions import AIPredictionsWidget
            self.ai_page = AIPredictionsWidget("database/supermarket.db")
            self.stack.addWidget(self.ai_page)
            logger.info("تم إنشاء صفحة الذكاء الاصطناعي")
        
        # الانتقال لصفحة الـ AI
        self.stack.setCurrentWidget(self.ai_page)
        self.header_title.setText("🤖 الذكاء الاصطناعي التنبؤي")
        
        # تحديث التوقعات
        self.ai_page.load_predictions()
        logger.info("تم فتح صفحة الذكاء الاصطناعي بنجاح")
        
    except Exception as e:
        logger.error(f"خطأ أثناء الانتقال لصفحة الذكاء الاصطناعي: {str(e)}")
        QMessageBox.warning(self, "خطأ", f"حدث خطأ أثناء فتح صفحة الذكاء الاصطناعي:\n{str(e)}")


# ========== شاشة المصروفات ==========
class ExpensesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dashboard = parent
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.init_ui()
        self.load_expenses()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("💰 المصروفات")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(title)
        
        # ===== نموذج إضافة مصروف =====
        form_group = QGroupBox("➕ إضافة مصروف جديد")
        form_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['accent']};
                font-weight: bold;
                font-size: 14px;
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                margin-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
            }}
        """)
        
        form_layout = QGridLayout(form_group)
        form_layout.setSpacing(12)
        
        input_style = f"""
            QLineEdit, QDateEdit, QTextEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                min-height: 30px;
            }}
            QLineEdit:focus, QDateEdit:focus, QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}
        """
        
        form_layout.addWidget(QLabel("البند:"), 0, 0)
        self.expense_item = QLineEdit()
        self.expense_item.setPlaceholderText("مثال: فاتورة كهرباء")
        self.expense_item.setStyleSheet(input_style)
        form_layout.addWidget(self.expense_item, 0, 1)
        
        form_layout.addWidget(QLabel("المبلغ (ج.م):"), 0, 2)
        self.expense_amount = QDoubleSpinBox()
        self.expense_amount.setRange(0, 999999999)
        self.expense_amount.setPrefix("ج.م ")
        self.expense_amount.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
                min-height: 30px;
            }}
            QDoubleSpinBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background-color: {COLORS['bg_card']};
                border: none;
                width: 18px;
            }}
        """)
        form_layout.addWidget(self.expense_amount, 0, 3)
        
        form_layout.addWidget(QLabel("التاريخ:"), 1, 0)
        self.expense_date = QDateEdit()
        self.expense_date.setDate(QDate.currentDate())
        self.expense_date.setCalendarPopup(True)
        self.expense_date.setDisplayFormat("yyyy-MM-dd")
        self.expense_date.setStyleSheet(input_style)
        form_layout.addWidget(self.expense_date, 1, 1)
        
        form_layout.addWidget(QLabel("ملاحظات:"), 1, 2)
        self.expense_notes = QLineEdit()
        self.expense_notes.setPlaceholderText("ملاحظات اختيارية")
        self.expense_notes.setStyleSheet(input_style)
        form_layout.addWidget(self.expense_notes, 1, 3)
        
        add_btn = QPushButton("➕ إضافة المصروف")
        add_btn.setMinimumHeight(38)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        add_btn.clicked.connect(self.add_expense)
        form_layout.addWidget(add_btn, 2, 0, 1, 4)
        
        layout.addWidget(form_group)
        
        # ===== جدول المصروفات =====
        table_group = QGroupBox("📋 قائمة المصروفات")
        table_group.setStyleSheet(form_group.styleSheet())
        table_layout = QVBoxLayout(table_group)
        
        self.expenses_table = QTableWidget()
        self.expenses_table.setColumnCount(5)
        self.expenses_table.setHorizontalHeaderLabels(["ID", "البند", "المبلغ (ج.م)", "التاريخ", "ملاحظات"])
        self.expenses_table.setAlternatingRowColors(False)
        self.expenses_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: none;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_card']};
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
        
        header = self.expenses_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        self.expenses_table.setColumnHidden(0, True)
        
        table_layout.addWidget(self.expenses_table)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setMinimumHeight(35)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info']};
            }}
        """)
        refresh_btn.clicked.connect(self.load_expenses)
        btn_layout.addWidget(refresh_btn)
        
        self.delete_expense_btn = QPushButton("🗑️ حذف المحدد")
        self.delete_expense_btn.setMinimumHeight(35)
        self.delete_expense_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_dark']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['border_light']};
                color: {COLORS['text_muted']};
            }}
        """)
        self.delete_expense_btn.clicked.connect(self.delete_selected_expense)
        btn_layout.addWidget(self.delete_expense_btn)
        
        self.apply_expense_permissions()
        
        btn_layout.addStretch()
        table_layout.addLayout(btn_layout)
        
        layout.addWidget(table_group)
    
    def apply_expense_permissions(self):
        role = self.parent_dashboard.user_info.get('role', 'زائر') if self.parent_dashboard else 'زائر'
        can_delete = role in ACTION_PERMISSIONS.get('delete_expense', [])
        self.delete_expense_btn.setEnabled(can_delete)
        if not can_delete:
            self.delete_expense_btn.setToolTip("غير متاح لصلاحيتك الحالية")
    
    def load_expenses(self):
        try:
            expenses = get_expenses()
            self.expenses_table.setRowCount(len(expenses))
            
            total = 0
            for row, exp in enumerate(expenses):
                expense_id = exp.get('id', row + 1)
                expense_type = exp.get('expense_type', exp.get('item', 'غير محدد'))
                amount = exp.get('amount', 0)
                expense_date = exp.get('expense_date', exp.get('date', ''))
                description = exp.get('description', exp.get('notes', ''))
                
                self.expenses_table.setItem(row, 0, QTableWidgetItem(str(expense_id)))
                self.expenses_table.setItem(row, 1, QTableWidgetItem(expense_type))
                self.expenses_table.setItem(row, 2, QTableWidgetItem(f"{amount:,.2f}"))
                self.expenses_table.setItem(row, 3, QTableWidgetItem(expense_date))
                self.expenses_table.setItem(row, 4, QTableWidgetItem(description))
                total += amount
            
            if self.parent_dashboard:
                self.parent_dashboard.show_toast(f"📊 إجمالي المصروفات: {total:,.2f} ج.م")
                
        except Exception as e:
            logger.error(f"خطأ في تحميل المصروفات: {e}")
            if self.parent_dashboard:
                self.parent_dashboard.show_toast(f"❌ خطأ في تحميل المصروفات: {str(e)}")
    
    def add_expense(self):
        if not self.parent_dashboard:
            return
        
        role = self.parent_dashboard.user_info.get('role', 'زائر')
        if role not in ACTION_PERMISSIONS.get('add_expense', []):
            self.parent_dashboard.show_toast("⚠️ غير مسموح بإضافة مصروفات", ToastMessage.WARNING)
            return
        
        item = self.expense_item.text().strip()
        amount = self.expense_amount.value()
        date = self.expense_date.date().toPyDate().strftime('%Y-%m-%d')
        notes = self.expense_notes.text().strip()
        
        if not item:
            self.parent_dashboard.show_toast("⚠️ الرجاء إدخال البند", ToastMessage.WARNING)
            return
        
        if amount <= 0:
            self.parent_dashboard.show_toast("⚠️ المبلغ يجب أن يكون أكبر من صفر", ToastMessage.WARNING)
            return
        
        try:
            success, message = add_expense(item, amount, date, notes)
            if success:
                self.parent_dashboard.show_toast("✅ تم إضافة المصروف بنجاح")
                self.parent_dashboard.log_activity(f"إضافة مصروف: {item} - {amount:,.2f} ج.م")
                self.expense_item.clear()
                self.expense_amount.setValue(0)
                self.expense_notes.clear()
                self.load_expenses()
            else:
                self.parent_dashboard.show_toast(f"❌ {message}")
        except Exception as e:
            logger.error(f"خطأ في إضافة المصروف: {e}")
            self.parent_dashboard.show_toast(f"❌ خطأ في إضافة المصروف: {str(e)}")
    
    def delete_selected_expense(self):
        if not self.parent_dashboard:
            return
        
        role = self.parent_dashboard.user_info.get('role', 'زائر')
        if role not in ACTION_PERMISSIONS.get('delete_expense', []):
            self.parent_dashboard.show_toast("⚠️ غير مسموح بحذف المصروفات", ToastMessage.WARNING)
            return
        
        selected_row = self.expenses_table.currentRow()
        if selected_row < 0:
            self.parent_dashboard.show_toast("⚠️ الرجاء تحديد مصروف للحذف", ToastMessage.WARNING)
            return
        
        id_item = self.expenses_table.item(selected_row, 0)
        item_item = self.expenses_table.item(selected_row, 1)
        
        if not id_item or not item_item:
            self.parent_dashboard.show_toast("⚠️ البيانات غير مكتملة", ToastMessage.WARNING)
            return
        
        exp_id = int(id_item.text())
        exp_item = item_item.text()
        
        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل أنت متأكد من حذف المصروف: {exp_item}؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success, message = delete_expense(exp_id)
                if success:
                    self.parent_dashboard.show_toast("✅ تم حذف المصروف بنجاح")
                    self.parent_dashboard.log_activity(f"حذف مصروف: {exp_item}")
                    self.load_expenses()
                else:
                    self.parent_dashboard.show_toast(f"❌ {message}")
            except Exception as e:
                logger.error(f"خطأ في حذف المصروف: {e}")
                self.parent_dashboard.show_toast(f"❌ خطأ في حذف المصروف: {str(e)}")


# ========== شاشة الإعدادات ==========
class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dashboard = parent
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("⚙️ إعدادات النظام")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(15)
        
        # ========== تبويب المظهر ==========
        theme_group = QGroupBox("🎨 المظهر")
        theme_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['accent']};
                font-weight: bold;
                font-size: 14px;
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                margin-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
            }}
        """)
        theme_layout = QFormLayout(theme_group)
        theme_layout.setSpacing(12)
        
        self.primary_color_combo = QComboBox()
        colors_list = [
            ('أزرق', '#38bdf8'),
            ('أخضر', '#22c55e'),
            ('بنفسجي', '#a855f7'),
            ('وردي', '#ec4899'),
            ('برتقالي', '#f59e0b'),
            ('أحمر', '#ef4444'),
            ('أبيض', '#f8fafc'),
        ]
        for name, color in colors_list:
            self.primary_color_combo.addItem(name)
            self.primary_color_combo.setItemData(self.primary_color_combo.count()-1, QColor(color), Qt.DecorationRole)
        self.primary_color_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px 10px;
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
        theme_layout.addRow("اللون الأساسي:", self.primary_color_combo)
        
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["صغير", "متوسط", "كبير"])
        self.font_size_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px 10px;
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
        theme_layout.addRow("حجم الخط:", self.font_size_combo)
        
        container_layout.addWidget(theme_group)
        
        # ========== بطاقة بيانات المتجر ==========
        store_group = QGroupBox("🏪 بيانات المتجر")
        store_group.setStyleSheet(theme_group.styleSheet())
        store_layout = QFormLayout(store_group)
        store_layout.setSpacing(12)
        
        input_style = f"""
            QLineEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                min-height: 30px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
        """
        
        self.store_name = QLineEdit()
        self.store_name.setPlaceholderText("اسم السوبر ماركت")
        self.store_name.setStyleSheet(input_style)
        store_layout.addRow("اسم المتجر:", self.store_name)
        
        self.store_phone = QLineEdit()
        self.store_phone.setPlaceholderText("رقم الهاتف")
        self.store_phone.setStyleSheet(input_style)
        store_layout.addRow("رقم الهاتف:", self.store_phone)
        
        self.store_address = QLineEdit()
        self.store_address.setPlaceholderText("العنوان")
        self.store_address.setStyleSheet(input_style)
        store_layout.addRow("العنوان:", self.store_address)
        
        self.store_currency = QLineEdit()
        self.store_currency.setPlaceholderText("مثال: ج.م, $, €")
        self.store_currency.setStyleSheet(input_style)
        store_layout.addRow("العملة:", self.store_currency)
        
        self.store_tax = QLineEdit()
        self.store_tax.setPlaceholderText("الرقم الضريبي")
        self.store_tax.setStyleSheet(input_style)
        store_layout.addRow("الرقم الضريبي:", self.store_tax)
        
        logo_layout = QHBoxLayout()
        self.logo_path = QLineEdit()
        self.logo_path.setPlaceholderText("مسار الشعار")
        self.logo_path.setStyleSheet(input_style)
        self.logo_path.setReadOnly(True)
        logo_layout.addWidget(self.logo_path)
        
        logo_btn = QPushButton("📁 اختيار")
        logo_btn.setFixedWidth(100)
        logo_btn.setMinimumHeight(35)
        logo_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info']};
            }}
        """)
        logo_btn.clicked.connect(self.select_logo)
        logo_layout.addWidget(logo_btn)
        store_layout.addRow("شعار المتجر:", logo_layout)
        
        container_layout.addWidget(store_group)
        
        # ========== بطاقة خيارات الفواتير والطباعة ==========
        invoice_group = QGroupBox("🧾 خيارات الفواتير والطباعة")
        invoice_group.setStyleSheet(store_group.styleSheet())
        invoice_layout = QFormLayout(invoice_group)
        invoice_layout.setSpacing(12)
        
        combo_style = f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 6px 10px;
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
        """
        
        spin_style = f"""
            QDoubleSpinBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
                min-height: 30px;
            }}
            QDoubleSpinBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background-color: {COLORS['bg_card']};
                border: none;
                width: 18px;
            }}
        """
        
        self.paper_size = QComboBox()
        self.paper_size.addItems(["58mm", "80mm"])
        self.paper_size.setStyleSheet(combo_style)
        invoice_layout.addRow("حجم ورق الفاتورة:", self.paper_size)
        
        self.default_printer = QComboBox()
        self.default_printer.addItems(["Printer 1 (افتراضي)", "Printer 2", "Printer 3", "Printer 4"])
        self.default_printer.setStyleSheet(combo_style)
        invoice_layout.addRow("الطابعة الافتراضية:", self.default_printer)
        
        self.vat_rate = QDoubleSpinBox()
        self.vat_rate.setRange(0, 100)
        self.vat_rate.setValue(14)
        self.vat_rate.setSuffix(" %")
        self.vat_rate.setStyleSheet(spin_style)
        invoice_layout.addRow("نسبة ضريبة القيمة المضافة:", self.vat_rate)
        
        container_layout.addWidget(invoice_group)
        
        # ========== إدارة التصنيفات ==========
        category_group = QGroupBox("📂 إدارة التصنيفات")
        category_group.setStyleSheet(store_group.styleSheet())
        category_layout = QVBoxLayout(category_group)
        
        category_desc = QLabel("إدارة تصنيفات المنتجات من مكان مركزي")
        category_desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        category_layout.addWidget(category_desc)
        
        manage_cat_btn = QPushButton("📂 فتح مدير التصنيفات")
        manage_cat_btn.setMinimumHeight(38)
        manage_cat_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['purple']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['purple']};
            }}
        """)
        manage_cat_btn.clicked.connect(self.open_category_manager)
        category_layout.addWidget(manage_cat_btn)
        
        container_layout.addWidget(category_group)
        
        # ========== بطاقة النسخ الاحتياطي ==========
        backup_group = QGroupBox("💾 النسخ الاحتياطي والاستعادة")
        backup_group.setStyleSheet(store_group.styleSheet())
        backup_layout = QVBoxLayout(backup_group)
        backup_layout.setSpacing(12)
        
        backup_btn_layout = QHBoxLayout()
        backup_btn_layout.setSpacing(12)
        
        self.backup_btn = QPushButton("📀 إنشاء نسخة احتياطية الآن")
        self.backup_btn.setMinimumHeight(40)
        self.backup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        self.backup_btn.clicked.connect(self.create_backup)
        backup_btn_layout.addWidget(self.backup_btn)
        
        self.restore_btn = QPushButton("🔄 استعادة نسخة سابقة")
        self.restore_btn.setMinimumHeight(40)
        self.restore_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['warning']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['warning_hover']};
            }}
        """)
        self.restore_btn.clicked.connect(self.restore_backup)
        backup_btn_layout.addWidget(self.restore_btn)
        
        backup_btn_layout.addStretch()
        backup_layout.addLayout(backup_btn_layout)
        
        self.backup_progress = QProgressBar()
        self.backup_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_input']};
                border-radius: 8px;
                text-align: center;
                color: {COLORS['text']};
                font-weight: bold;
                min-height: 25px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 8px;
            }}
        """)
        self.backup_progress.setValue(0)
        self.backup_progress.setVisible(False)
        backup_layout.addWidget(self.backup_progress)
        
        container_layout.addWidget(backup_group)
        
        # ========== زر حفظ الإعدادات ==========
        save_btn = QPushButton("💾 حفظ الإعدادات")
        save_btn.setMinimumHeight(45)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info']};
            }}
        """)
        save_btn.clicked.connect(self.save_settings)
        container_layout.addWidget(save_btn)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
    
    def select_logo(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "اختر شعار المتجر", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if filename:
            self.logo_path.setText(filename)
            if self.parent_dashboard:
                self.parent_dashboard.show_toast("تم اختيار الشعار بنجاح")
    
    def open_category_manager(self):
        dialog = CategoryManagerDialog(self)
        dialog.exec_()
        if self.parent_dashboard:
            self.parent_dashboard.show_toast("📂 تم تحديث التصنيفات")
    
    def load_settings(self):
        try:
            theme, success, msg = get_theme_settings()
            if success:
                color_hex = theme.get('primary_color', '#38bdf8')
                for i in range(self.primary_color_combo.count()):
                    color_data = self.primary_color_combo.itemData(i, Qt.DecorationRole)
                    if color_data and color_data.name() == color_hex:
                        self.primary_color_combo.setCurrentIndex(i)
                        break
                
                font_size = theme.get('font_size', 'medium')
                size_map = {'small': 0, 'medium': 1, 'large': 2}
                self.font_size_combo.setCurrentIndex(size_map.get(font_size, 1))
            
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.store_name.setText(settings.get("store_name", ""))
                    self.store_phone.setText(settings.get("store_phone", ""))
                    self.store_address.setText(settings.get("store_address", ""))
                    self.store_currency.setText(settings.get("store_currency", "ج.م"))
                    self.store_tax.setText(settings.get("store_tax", ""))
                    self.logo_path.setText(settings.get("logo_path", ""))
                    
                    paper = settings.get("paper_size", "58mm")
                    idx = self.paper_size.findText(paper)
                    if idx >= 0:
                        self.paper_size.setCurrentIndex(idx)
                    
                    printer = settings.get("default_printer", "Printer 1 (افتراضي)")
                    idx = self.default_printer.findText(printer)
                    if idx >= 0:
                        self.default_printer.setCurrentIndex(idx)
                    
                    self.vat_rate.setValue(settings.get("vat_rate", 14))
        except Exception as e:
            logger.error(f"خطأ في تحميل الإعدادات: {e}")
    
    def save_settings(self):
        try:
            color_names = ['#38bdf8', '#22c55e', '#a855f7', '#ec4899', '#f59e0b', '#ef4444', '#f8fafc']
            primary_color = color_names[self.primary_color_combo.currentIndex()]
            font_size_map = {0: 'small', 1: 'medium', 2: 'large'}
            font_size = font_size_map[self.font_size_combo.currentIndex()]
            
            success, msg = save_theme_settings(primary_color, font_size)
            if success and self.parent_dashboard:
                self.parent_dashboard.show_toast("تم حفظ إعدادات المظهر بنجاح")
                self.parent_dashboard.apply_theme(primary_color, font_size)
            elif self.parent_dashboard:
                self.parent_dashboard.show_toast(f"خطأ في حفظ المظهر: {msg}")
            
            settings = {
                "store_name": self.store_name.text().strip(),
                "store_phone": self.store_phone.text().strip(),
                "store_address": self.store_address.text().strip(),
                "store_currency": self.store_currency.text().strip() or "ج.م",
                "store_tax": self.store_tax.text().strip(),
                "logo_path": self.logo_path.text().strip(),
                "paper_size": self.paper_size.currentText(),
                "default_printer": self.default_printer.currentText(),
                "vat_rate": self.vat_rate.value()
            }
            
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            if self.parent_dashboard:
                self.parent_dashboard.show_toast("✅ تم حفظ الإعدادات بنجاح")
            
            logger.info("تم حفظ الإعدادات")
        except Exception as e:
            logger.error(f"خطأ في حفظ الإعدادات: {e}")
            if self.parent_dashboard:
                self.parent_dashboard.show_toast(f"❌ خطأ في حفظ الإعدادات: {str(e)}")
    
    def create_backup(self):
        self.backup_progress.setVisible(True)
        self.backup_progress.setValue(0)
        self.backup_btn.setEnabled(False)
        
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
        
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        def update_progress():
            current = self.backup_progress.value()
            if current < 100:
                self.backup_progress.setValue(current + 10)
                QTimer.singleShot(80, update_progress)
            else:
                try:
                    success, message = backup_database(backup_path)
                    self.backup_progress.setVisible(False)
                    self.backup_btn.setEnabled(True)
                    
                    if success:
                        if self.parent_dashboard:
                            self.parent_dashboard.show_toast(f"تم إنشاء نسخة احتياطية بنجاح: {backup_filename}")
                            log_user_activity(
                                self.parent_dashboard.user_info.get('username', 'Admin'),
                                'إنشاء نسخة احتياطية',
                                f'تم إنشاء نسخة احتياطية: {backup_filename}'
                            )
                    else:
                        if self.parent_dashboard:
                            self.parent_dashboard.show_toast(f"خطأ في إنشاء النسخة الاحتياطية: {message}")
                except Exception as e:
                    logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
                    self.backup_progress.setVisible(False)
                    self.backup_btn.setEnabled(True)
                    if self.parent_dashboard:
                        self.parent_dashboard.show_toast(f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}")
        
        QTimer.singleShot(100, update_progress)
    
    def restore_backup(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف النسخة الاحتياطية", "", "ZIP Files (*.zip)"
        )
        if not filename:
            return
        
        self.backup_progress.setVisible(True)
        self.backup_progress.setValue(0)
        self.restore_btn.setEnabled(False)
        self.backup_btn.setEnabled(False)
        
        def update_progress():
            current = self.backup_progress.value()
            if current < 100:
                self.backup_progress.setValue(current + 10)
                QTimer.singleShot(70, update_progress)
            else:
                from back.database import restore_database
                success, message = restore_database(filename)
                
                self.backup_progress.setVisible(False)
                self.restore_btn.setEnabled(True)
                self.backup_btn.setEnabled(True)
                
                if success:
                    if self.parent_dashboard:
                        self.parent_dashboard.show_toast("تم استعادة النسخة الاحتياطية بنجاح")
                        log_user_activity(
                            self.parent_dashboard.user_info.get('username', 'Admin'),
                            'استعادة نسخة احتياطية',
                            f'تم استعادة النسخة من: {os.path.basename(filename)}'
                        )
                else:
                    if self.parent_dashboard:
                        self.parent_dashboard.show_toast(f"خطأ: {message}")
        
        QTimer.singleShot(100, update_progress)


# ========== شاشة سجل النشاط ==========
class ActivityLogWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dashboard = parent
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("📋 سجل النشاط")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(title)
        
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(3)
        self.log_table.setHorizontalHeaderLabels(["الوقت", "المستخدم", "النشاط"])
        self.log_table.setAlternatingRowColors(False)
        self.log_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_card']};
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
        
        header = self.log_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        layout.addWidget(self.log_table)
        
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setMinimumHeight(38)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info']};
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_log)
        btn_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("🗑️ مسح السجل")
        clear_btn.setMinimumHeight(38)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_dark']};
            }}
        """)
        clear_btn.clicked.connect(self.clear_log)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def refresh_log(self):
        if self.parent_dashboard:
            self.parent_dashboard.update_activity_log_display()
    
    def clear_log(self):
        self.parent_dashboard.clear_activity_log()
        self.parent_dashboard.show_toast("تم مسح سجل النشاط بنجاح")


# ========== لوحة التحكم الرئيسية ==========
class MainDashboard(QMainWindow):
    def __init__(self, user_info=None):
        super().__init__()
        self.user_info = user_info if user_info else {'username': 'Guest', 'role': 'زائر'}
        self.ai_page = None  # تهيئة متغير صفحة AI
        
        self.activity_log = []
        self.current_primary_color = '#38bdf8'
        self.current_font_size = 'medium'
        
        log_user_activity(
            self.user_info.get('username', 'Guest'),
            'تسجيل الدخول',
            f'دور: {self.user_info.get("role", "غير معروف")}'
        )
        
        self.setWindowTitle("نظام الماركت الذكي - الإصدار الاحترافي")
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        self.setWindowState(Qt.WindowNoState)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLORS['bg_dark']}; }}")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== القائمة الجانبية ==========
        self.SIDEBAR_WIDE = 280
        self.SIDEBAR_NARROW = 72
        sidebar_container = QScrollArea()
        self.sidebar_container = sidebar_container
        sidebar_container.setWidgetResizable(True)
        sidebar_container.setFixedWidth(self.SIDEBAR_WIDE)
        sidebar_container.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #1e293b;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #38bdf8;
                border-radius: 4px;
            }
        """)
        
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setStyleSheet(f"""
            #Sidebar {{
                background-color: {COLORS['bg_sidebar']};
                border-right: 1px solid {COLORS['border']};
            }}
            #Sidebar QPushButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                border: none;
                padding: 12px 20px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                min-height: 44px;
            }}
            #Sidebar QPushButton:hover {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
            }}
            #Sidebar QPushButton:checked {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['accent']};
                border-left: 4px solid {COLORS['accent']};
                font-weight: bold;
            }}
            #Sidebar QPushButton:disabled {{
                color: {COLORS['border_light']};
                background-color: transparent;
            }}
            #Sidebar QPushButton:disabled:hover {{
                background-color: transparent;
                color: {COLORS['border_light']};
            }}
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 15, 0, 15)
        sidebar_layout.setSpacing(5)
        
        # معلومات المستخدم
        user_frame = QFrame()
        user_layout = QVBoxLayout(user_frame)
        user_layout.setSpacing(8)
        user_icon = QLabel("👤")
        user_icon.setAlignment(Qt.AlignCenter)
        user_icon.setStyleSheet(f"font-size: 48px; color: {COLORS['text_muted']};")
        
        role_display = self.user_info.get('role', 'زائر')
        user_name = QLabel(f"المستخدم: {self.user_info['username']}\nالصلاحية: {role_display}")
        user_name.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        user_name.setAlignment(Qt.AlignCenter)
        user_name.setWordWrap(True)
        user_layout.addWidget(user_icon)
        user_layout.addWidget(user_name)
        sidebar_layout.addWidget(user_frame)
        sidebar_layout.addSpacing(20)
        
        # الأزرار الرئيسية
        self.btn_pos = QPushButton("🛒 المبيعات")
        self.btn_pos.setCheckable(True)
        self.btn_history = QPushButton("📜 سجل الفواتير")
        self.btn_history.setCheckable(True)
        self.btn_inventory = QPushButton("📦 المخزن")
        self.btn_inventory.setCheckable(True)
        self.btn_reports = QPushButton("📊 التقارير")
        self.btn_reports.setCheckable(True)
        self.btn_ai = QPushButton("🤖 الذكاء الاصطناعي التنبؤي")
        self.btn_ai.setCheckable(True)
        
        # إضافة الأزرار الرئيسية
        for btn in [self.btn_pos, self.btn_history, self.btn_inventory, self.btn_reports]:
            sidebar_layout.addWidget(btn)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; margin: 10px 15px; max-height: 2px;")
        sidebar_layout.addWidget(sep)
        
        # أزرار الحسابات
        self.btn_deferred = QPushButton("💳 الحسابات الآجلة")
        self.btn_deferred.setCheckable(True)
        self.btn_sales_return = QPushButton("↩️ مرتجع مبيعات")
        self.btn_sales_return.setCheckable(True)
        self.btn_purchase_return = QPushButton("🔃 مرتجع مشتريات")
        self.btn_purchase_return.setCheckable(True)
        self.btn_transfer = QPushButton("🚚 نقل مخزني")
        self.btn_transfer.setCheckable(True)
        self.btn_damaged = QPushButton("⚠️ تالف / هالك")
        self.btn_damaged.setCheckable(True)
        
        for btn in [self.btn_deferred, self.btn_sales_return, self.btn_purchase_return, 
                    self.btn_transfer, self.btn_damaged]:
            sidebar_layout.addWidget(btn)
        
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"background-color: {COLORS['border']}; margin: 10px 15px; max-height: 2px;")
        sidebar_layout.addWidget(sep2)
        
        # أزرار النظام
        self.btn_expenses = QPushButton("💰 المصروفات")
        self.btn_expenses.setCheckable(True)
        self.btn_activity = QPushButton("📋 سجل النشاط")
        self.btn_activity.setCheckable(True)
        self.btn_settings = QPushButton("⚙️ الإعدادات")
        self.btn_settings.setCheckable(True)
        
        sidebar_layout.addWidget(self.btn_expenses)
        sidebar_layout.addWidget(self.btn_activity)
        sidebar_layout.addWidget(self.btn_settings)
        
        # إضافة زر AI في مكانه الصحيح
        sidebar_layout.addWidget(self.btn_ai)
        
        sidebar_layout.addStretch()
        
        self.btn_logout = QPushButton("🚪 تسجيل الخروج")
        self.btn_logout.setFont(FONTS['button'])
        self.btn_logout.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 12px;
                border-radius: 10px;
                margin: 10px;
                font-weight: bold;
                min-height: 45px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_dark']};
            }}
        """)
        self.btn_logout.clicked.connect(self.logout)
        sidebar_layout.addWidget(self.btn_logout)
        self._sidebar_expanded = True
        
        sidebar_container.setWidget(sidebar)
        main_layout.addWidget(sidebar_container)
        
        # ========== منطقة المحتوى ==========
        content = QVBoxLayout()
        content.setSpacing(0)
        
        # الهيدر
        header = QFrame()
        header.setObjectName("Header")
        header.setMinimumHeight(70)
        header.setMaximumHeight(80)
        header.setStyleSheet(f"""
            #Header {{
                background-color: {COLORS['bg_sidebar']};
                border-bottom: 2px solid {COLORS['border']};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        self.header_title = QLabel("المبيعات")
        self.header_title.setFont(FONTS['subtitle'])
        self.header_title.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold;")
        header_layout.addWidget(self.header_title)
        
        user_header_label = QLabel(f"👤 {self.user_info['username']} | {self.user_info.get('role', 'زائر')}")
        user_header_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        header_layout.addWidget(user_header_label)
        
        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        header_layout.addWidget(self.time_label)
        header_layout.addStretch()
        content.addWidget(header)
        
        # حاوية الشاشات
        stack_container = QScrollArea()
        stack_container.setWidgetResizable(True)
        stack_container.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0f172a;
            }
        """)
        
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        # إنشاء الشاشات
        self.pos_screen = POSWindow()
        self.history_screen = SalesHistoryWindow()
        self.inventory_screen = AddProductWindow()
        self.report_screen = ReportsWindow()
        self.deferred_screen = DeferredAccountsWindow()
        self.sales_return_screen = SalesReturnWindow()
        self.purchase_return_screen = PurchaseReturnWindow()
        self.transfer_screen = StockTransferWindow()
        self.damaged_screen = DamagedGoodsWindow()
        self.activity_screen = ActivityLogWindow(self)
        self.settings_screen = SettingsWindow(self)
        self.expenses_screen = ExpensesWidget(self)
        
        self.stack.addWidget(self.pos_screen)           # 0
        self.stack.addWidget(self.history_screen)       # 1
        self.stack.addWidget(self.inventory_screen)     # 2
        self.stack.addWidget(self.report_screen)        # 3
        self.stack.addWidget(self.deferred_screen)      # 4
        self.stack.addWidget(self.sales_return_screen)  # 5
        self.stack.addWidget(self.purchase_return_screen) # 6
        self.stack.addWidget(self.transfer_screen)      # 7
        self.stack.addWidget(self.damaged_screen)       # 8
        self.stack.addWidget(self.activity_screen)      # 9
        self.stack.addWidget(self.settings_screen)      # 10
        self.stack.addWidget(self.expenses_screen)      # 11
        
        stack_container.setWidget(self.stack)
        content.addWidget(stack_container)
        main_layout.addLayout(content, stretch=1)
        
        # ========== ربط الأزرار ==========
        self.nav_buttons = {
            0: self.btn_pos, 1: self.btn_history, 2: self.btn_inventory,
            3: self.btn_reports, 4: self.btn_deferred, 5: self.btn_sales_return,
            6: self.btn_purchase_return, 7: self.btn_transfer, 8: self.btn_damaged,
            9: self.btn_activity, 10: self.btn_settings, 11: self.btn_expenses,
            12: self.btn_ai,
        }
        self._nav_full_texts = {idx: b.text() for idx, b in self.nav_buttons.items()}
        self._nav_full_texts['logout'] = self.btn_logout.text()
        
        for idx, button in self.nav_buttons.items():
            button.clicked.connect(lambda checked, i=idx: self.switch(i))
            if not self.has_permission(idx):
                button.setToolTip("غير متاح لصلاحيتك الحالية")
        
        self.apply_user_permissions(self.user_info.get('role', 'زائر'))
        
        self.btn_pos.setChecked(True)
        
        self.update_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
        
        self.update_activity_log_display()
        
        # ===== تحديث لوحة التحكم الرئيسية =====
        self.update_dashboard_stats()
        
        # ===== تطبيق إعدادات المظهر =====
        self.load_theme_settings()
    
    def load_theme_settings(self):
        try:
            theme, success, msg = get_theme_settings()
            if success:
                primary_color = theme.get('primary_color', '#38bdf8')
                font_size = theme.get('font_size', 'medium')
                self.apply_theme(primary_color, font_size)
        except Exception as e:
            logger.error(f"خطأ في تحميل إعدادات المظهر: {e}")
    
    def apply_theme(self, primary_color, font_size):
        self.current_primary_color = primary_color
        self.current_font_size = font_size
        
        sidebar_style = f"""
            #Sidebar {{
                background-color: {COLORS['bg_sidebar']};
                border-right: 1px solid {COLORS['border']};
            }}
            #Sidebar QPushButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                border: none;
                padding: 12px 20px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                min-height: 44px;
            }}
            #Sidebar QPushButton:hover {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
            }}
            #Sidebar QPushButton:checked {{
                background-color: {COLORS['bg_card']};
                color: {primary_color};
                border-left: 4px solid {primary_color};
                font-weight: bold;
            }}
            #Sidebar QPushButton:disabled {{
                color: {COLORS['border_light']};
                background-color: transparent;
            }}
            #Sidebar QPushButton:disabled:hover {{
                background-color: transparent;
                color: {COLORS['border_light']};
            }}
        """
        self.sidebar_container.widget().setStyleSheet(sidebar_style)
        
        self.header_title.setStyleSheet(f"color: {primary_color}; font-weight: bold;")
        
        size_map = {'small': 10, 'medium': 12, 'large': 14}
        font_size_pt = size_map.get(font_size, 12)
        font = QFont("Segoe UI", font_size_pt)
        self.setFont(font)
    
    def update_dashboard_stats(self):
        try:
            stats = get_dashboard_stats()
            logger.info(f"مبيعات اليوم: {stats['daily_total']:.2f} ج.م")
            logger.info(f"فواتير اليوم: {stats['daily_invoices']}")
            logger.info(f"منتجات منخفضة المخزون: {stats['low_stock_count']}")
        except Exception as e:
            logger.error(f"خطأ في تحديث إحصائيات لوحة التحكم: {e}")
    
    def apply_user_permissions(self, role):
        allowed_indices = ROLE_PERMISSIONS.get(role, [])
        
        for idx, button in self.nav_buttons.items():
            if role == 'مدير':
                button.setEnabled(True)
                button.setToolTip("")
            else:
                if idx in allowed_indices:
                    button.setEnabled(True)
                    button.setToolTip("")
                else:
                    button.setEnabled(False)
                    button.setToolTip(f"❌ غير متاح لدور {role}")
                    if button.isChecked():
                        button.setChecked(False)
        
        if role != 'مدير' and not self.btn_pos.isEnabled():
            if self.btn_pos.isEnabled():
                self.switch(0)
    
    def check_permission(self, action_key):
        role = self.user_info.get('role', 'زائر')
        if role == 'مدير':
            return True
        allowed_roles = ACTION_PERMISSIONS.get(action_key, [])
        return role in allowed_roles
    
    def show_toast(self, message, toast_type=ToastMessage.SUCCESS):
        ToastMessage(self, message, toast_type)
    
    def log_activity(self, activity):
        timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        self.activity_log.append({
            'time': timestamp,
            'user': self.user_info['username'],
            'activity': activity
        })
        log_user_activity(self.user_info['username'], activity, '')
        logger.info(f"[{timestamp}] {self.user_info['username']}: {activity}")
    
    def clear_activity_log(self):
        self.activity_log.clear()
        self.update_activity_log_display()
        self.show_toast("تم مسح سجل النشاط")
    
    def update_activity_log_display(self):
        if hasattr(self, 'activity_screen'):
            table = self.activity_screen.log_table
            table.setRowCount(len(self.activity_log))
            
            for row, entry in enumerate(self.activity_log):
                time_item = QTableWidgetItem(entry['time'])
                time_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 0, time_item)
                
                user_item = QTableWidgetItem(entry['user'])
                user_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 1, user_item)
                
                activity_item = QTableWidgetItem(entry['activity'])
                activity_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 2, activity_item)
    
    def update_time(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(f"🕐 {current_time}")
    
    # ====== تعديل الريسبونسيف: دالة resizeEvent المحسنة للقائمة الجانبية ======
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        width = event.size().width()
        should_expand = width >= 1100
        
        if should_expand != self._sidebar_expanded:
            self._sidebar_expanded = should_expand
            target_width = self.SIDEBAR_WIDE if should_expand else self.SIDEBAR_NARROW
            self.sidebar_container.setFixedWidth(target_width)
            
            for idx, button in self.nav_buttons.items():
                full_text = self._nav_full_texts[idx]
                if should_expand:
                    button.setText(full_text)
                else:
                    # إظهار الأيقونة فقط
                    button.setText(full_text.split(" ", 1)[0])
            
            if should_expand:
                self.btn_logout.setText(self._nav_full_texts['logout'])
            else:
                self.btn_logout.setText(self._nav_full_texts['logout'].split(" ", 1)[0])
    
    def has_permission(self, index):
        role = self.user_info.get('role', 'زائر')
        if role == 'مدير':
            return True
        screen = SCREEN_PERMISSIONS.get(index)
        if not screen:
            return True
        return role in screen['roles']
    
    def logout(self):
        username = self.user_info.get('username', 'Guest')
        try:
            record_logout(username)
            self.log_activity("تسجيل الخروج من النظام")
        except Exception as e:
            logger.error(f"خطأ في تسجيل الخروج: {e}")
        
        self.close()
    
    def switch(self, index, btn=None):
        screen_info = SCREEN_PERMISSIONS.get(index, {'title': ''})
        title = screen_info['title']
        btn = btn or self.nav_buttons.get(index)
        
        # معالجة خاصة لزر AI
        if index == 12:
            show_ai_market_predictions(self)
            return
        
        if not self.has_permission(index):
            self.show_toast("⚠️ عذراً، هذه الشاشة غير متاحة لصلاحيتك الحالية", ToastMessage.WARNING)
            self.log_activity(f"محاولة دخول مرفوضة لشاشة: {title}")
            self.update_activity_log_display()
            return
        
        for b in self.nav_buttons.values():
            b.setChecked(False)
        if btn:
            btn.setChecked(True)
        
        self.stack.setCurrentIndex(index)
        self.header_title.setText(title)
        
        self.log_activity(f"فتح شاشة {title}")
        self.update_activity_log_display()
        
        # تحديث البيانات عند التبديل
        try:
            if index == 4:
                if hasattr(self.deferred_screen, 'load_debts'):
                    self.deferred_screen.load_debts()
            elif index == 5:
                if hasattr(self.sales_return_screen, 'load_sales'):
                    self.sales_return_screen.load_sales()
            elif index == 6:
                if hasattr(self.purchase_return_screen, 'load_returns'):
                    self.purchase_return_screen.load_returns()
            elif index == 7:
                if hasattr(self.transfer_screen, 'load_transfers'):
                    self.transfer_screen.load_transfers()
            elif index == 8:
                if hasattr(self.damaged_screen, 'load_damaged'):
                    self.damaged_screen.load_damaged()
            elif index == 1 and hasattr(self.history_screen, 'load_sales_from_db'):
                self.history_screen.load_sales_from_db()
            elif index == 3 and hasattr(self.report_screen, 'load_data'):
                self.report_screen.load_data()
            elif index == 2 and hasattr(self.inventory_screen, 'load_data'):
                self.inventory_screen.load_data()
            elif index == 9:
                self.update_activity_log_display()
            elif index == 11 and hasattr(self.expenses_screen, 'load_expenses'):
                self.expenses_screen.load_expenses()
            elif index == 0:
                self.update_dashboard_stats()
        except Exception as e:
            logger.error(f"خطأ في تحديث البيانات للتبويب {index}: {e}")
    
    def closeEvent(self, event):
        self.log_activity("تسجيل الخروج من النظام")
        self.show_toast("🚪 جاري الخروج من النظام...", ToastMessage.INFO)
        
        try:
            backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir, exist_ok=True)
            
            backup_filename = f"auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            from back.database import backup_database
            success, message = backup_database(backup_path)
            if success:
                logger.info(f"تم إنشاء نسخة احتياطية تلقائية: {backup_filename}")
            else:
                logger.error(message)
        except Exception as e:
            logger.error(f"خطأ في النسخ الاحتياطي التلقائي: {e}")
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    
    user_info = {
        'username': 'أحمد المدير',
        'role': 'مدير'
    }
    
    window = MainDashboard(user_info)
    window.show()
    sys.exit(app.exec_())