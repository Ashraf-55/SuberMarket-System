# ================= reports_ui.py - لوحة التقارير والإحصائيات المتطورة (نسخة مصححة - PDF) =================
"""
لوحة التقارير والإحصائيات الشاملة
تدعم 6 أنواع من التقارير مع فلاتر زمنية وتصدير PDF و Excel
📌 تعمل فقط مع قاعدة البيانات الفعلية - لا توجد بيانات افتراضية
"""

import os
import csv
import logging
import traceback
import subprocess
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGraphicsDropShadowEffect, QPushButton, QComboBox,
                             QScrollArea, QSizePolicy, QDateEdit, QFileDialog,
                             QProgressBar, QApplication, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer, QDate, pyqtSignal
from PyQt5.QtGui import QFont, QColor as QGColor, QIcon

from back.database import get_expenses, get_expenses_summary, get_connection
# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== محاولة استيراد مكتبات التصدير ==========
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm, cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

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
        "/System/Library/Fonts/Helvetica.ttc"
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
    except:
        pass
except:
    pass

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
    'accent_hover': '#0369a1',
    'success': '#16a34a',
    'success_hover': '#15803d',
    'info': '#0284c7',
    'info_hover': '#0369a1',
    'warning': '#d97706',
    'warning_hover': '#b45309',
    'purple': '#9333ea',
    'danger': '#dc2626',
    'danger_hover': '#b91c1c',
    'border': '#cbd5e1',
    'border_light': '#e2e8f0',
    'header': '#FFFFFF',
    'gold': '#d97706',
    'cyan': '#0891b2',
    'pink': '#db2777'
}

# ========== نظام Toast موحد (لون واحد ثابت) ==========
class ToastMessage(QLabel):
    def __init__(self, parent, message, duration=2500):
        # لون موحد للجميع
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


# ========== نافذة التقارير الرئيسية ==========
class ReportsWindow(QWidget):
    sale_deleted = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.current_data = []
        self.current_headers = []
        self.current_report_type = "profits"
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.init_ui()
        
        self.show_info_toast("📋 جاري تحميل البيانات...")
        QTimer.singleShot(500, self.generate_report)
    
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

    def init_ui(self):
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setStyleSheet("border: none; background-color: transparent;")
        
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)

        # ===== لوحة التحكم =====
        control_frame = QFrame()
        control_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                padding: 12px;
            }}
        """)
        control_layout = QHBoxLayout(control_frame)
        control_layout.setSpacing(15)
        
        control_layout.addWidget(QLabel("📊 نوع التقرير:"))
        self.report_type = QComboBox()
        self.report_type.addItems([
            "💰 الأرباح اليومية والمبيعات",
            "🏦 تقرير حركة الخزينة والإيرادات",
            "👥 تقرير أداء الموظفين والكاشيرية",
            "📦 تقرير المنتجات الناقصة",
            "🐢 تقرير المنتجات الراكدة",
            "💰 تقرير المصروفات"
        ])
        self.report_type.setMinimumWidth(220)
        self.report_type.setMinimumHeight(38)
        self.report_type.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 25px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
            }}
        """)
        self.report_type.currentIndexChanged.connect(self.on_report_type_changed)
        control_layout.addWidget(self.report_type)
        
        control_layout.addWidget(QLabel(" | "))
        
        control_layout.addWidget(QLabel("📅 من:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setMinimumWidth(120)
        self.start_date.setMinimumHeight(35)
        self.start_date.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QDateEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        control_layout.addWidget(self.start_date)
        
        control_layout.addWidget(QLabel("إلى:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setMinimumWidth(120)
        self.end_date.setMinimumHeight(35)
        self.end_date.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QDateEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        control_layout.addWidget(self.end_date)
        
        control_layout.addStretch()
        
        self.generate_btn = QPushButton("🔄 توليد التقرير")
        self.generate_btn.setMinimumHeight(38)
        self.generate_btn.setMinimumWidth(140)
        self.generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                padding: 8px 20px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        self.generate_btn.clicked.connect(self.generate_report)
        control_layout.addWidget(self.generate_btn)
        
        self.reset_btn = QPushButton("🗑️ تصفير الشاشة")
        self.reset_btn.setMinimumHeight(38)
        self.reset_btn.setMinimumWidth(140)
        self.reset_btn.setStyleSheet(f"""
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
        self.reset_btn.clicked.connect(self.reset_all)
        control_layout.addWidget(self.reset_btn)
        
        self.main_layout.addWidget(control_frame)

        # ===== بطاقات KPI =====
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(12)
        
        self.kpi_cards = []
        kpi_defaults = [
            {'title': '💰 إجمالي المبيعات', 'value': '0.00 ج.م', 'color': COLORS['success']},
            {'title': '📈 صافي الربح الحقيقي', 'value': '0.00 ج.م', 'color': COLORS['warning']},
            {'title': '📊 صافي المبيعات', 'value': '0.00 ج.م', 'color': COLORS['info']},
            {'title': '📄 عدد الطلبات', 'value': '0', 'color': COLORS['purple']},
        ]
        
        for default in kpi_defaults:
            card = self.create_kpi_card(default['title'], default['value'], default['color'])
            self.kpi_cards.append(card)
            self.kpi_layout.addWidget(card)
        
        self.main_layout.addLayout(self.kpi_layout)

        # ===== جدول البيانات مع دعم Scroll =====
        table_container = QFrame()
        table_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        table_layout = QVBoxLayout(table_container)
        table_layout.setSpacing(0)
        
        table_title_layout = QHBoxLayout()
        table_title = QLabel("📋 بيانات التقرير")
        table_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['accent']}; padding: 12px 15px; background-color: {COLORS['header']}; border-top-left-radius: 15px; border-top-right-radius: 15px;")
        table_title_layout.addWidget(table_title)
        
        table_title_layout.addStretch()
        
        export_btn_style = f"""
            QPushButton {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                padding: 6px 14px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid {COLORS['border']};
            }}
            QPushButton:hover {{
                border: 1px solid {COLORS['accent']};
                color: {COLORS['accent']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['bg_card_dark']};
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']};
            }}
        """
        
        self.btn_excel = QPushButton("📊 Excel")
        self.btn_excel.setStyleSheet(export_btn_style)
        self.btn_excel.setMinimumHeight(32)
        self.btn_excel.setEnabled(False)
        self.btn_excel.clicked.connect(self.export_excel)
        table_title_layout.addWidget(self.btn_excel)
        
        self.btn_pdf = QPushButton("📄 PDF")
        self.btn_pdf.setStyleSheet(export_btn_style)
        self.btn_pdf.setMinimumHeight(32)
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.clicked.connect(self.export_pdf)
        table_title_layout.addWidget(self.btn_pdf)
        
        table_layout.addLayout(table_title_layout)

        # ====== تعديل الريسبونسيف: تغليف الجدول بـ ScrollArea ======
        table_scroll = QScrollArea()
        table_scroll.setWidgetResizable(True)
        table_scroll.setStyleSheet("border: none; background-color: transparent;")
        
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(False)
        self.data_table.setShowGrid(False)
        self.data_table.verticalHeader().setVisible(False)
        self.data_table.setMinimumHeight(300)
        
        self.data_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: none;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(56, 189, 248, 0.2);
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['accent']};
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        
        table_scroll.setWidget(self.data_table)
        table_layout.addWidget(table_scroll)
        
        self.main_layout.addWidget(table_container)

        main_scroll.setWidget(container)
        
        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.addWidget(main_scroll)

    def create_kpi_card(self, title, value, color):
        card = QFrame()
        card.setMinimumHeight(100)
        card.setMaximumHeight(120)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card_dark']};
                border-left: 5px solid {color};
                border-radius: 12px;
                border-right: 1px solid {COLORS['border_light']};
                border-top: 1px solid {COLORS['border_light']};
                border-bottom: 1px solid {COLORS['border_light']};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(Qt.GlobalColor.black)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: bold;")
        lbl_title.setObjectName("kpi_title")
        
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 900;")
        lbl_value.setObjectName("kpi_value")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        layout.addStretch()
        return card

    def update_kpi_cards(self, kpi_values):
        for i, card in enumerate(self.kpi_cards):
            if i < len(kpi_values):
                title_label = card.findChild(QLabel, "kpi_title")
                value_label = card.findChild(QLabel, "kpi_value")
                if title_label and value_label:
                    title_label.setText(kpi_values[i]['title'])
                    value_label.setText(kpi_values[i]['value'])
                    color = kpi_values[i].get('color', COLORS['accent'])
                    value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 900;")
                    card.setStyleSheet(f"""
                        QFrame {{
                            background-color: {COLORS['bg_card_dark']};
                            border-left: 5px solid {color};
                            border-radius: 12px;
                            border-right: 1px solid {COLORS['border_light']};
                            border-top: 1px solid {COLORS['border_light']};
                            border-bottom: 1px solid {COLORS['border_light']};
                        }}
                    """)
            else:
                title_label = card.findChild(QLabel, "kpi_title")
                value_label = card.findChild(QLabel, "kpi_value")
                if title_label and value_label:
                    title_label.setText("لا توجد بيانات")
                    value_label.setText("0")

    def reset_all(self):
        self.current_data = []
        self.current_headers = []
        
        self.data_table.setRowCount(0)
        self.data_table.setColumnCount(0)
        
        default_kpis = [
            {'title': '💰 إجمالي المبيعات', 'value': '0.00 ج.م', 'color': COLORS['success']},
            {'title': '📈 صافي الربح الحقيقي', 'value': '0.00 ج.م', 'color': COLORS['warning']},
            {'title': '📊 صافي المبيعات', 'value': '0.00 ج.م', 'color': COLORS['info']},
            {'title': '📄 عدد الطلبات', 'value': '0', 'color': COLORS['purple']},
        ]
        self.update_kpi_cards(default_kpis)
        
        self.btn_excel.setEnabled(False)
        self.btn_pdf.setEnabled(False)
        
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())
        
        self.show_info_toast("🔄 تم تصفير الشاشة بالكامل")

    def on_report_type_changed(self, index):
        report_types = ["profits", "cash", "employees", "low_stock", "stagnant", "expenses"]
        self.current_report_type = report_types[index] if index < len(report_types) else "profits"

    def get_date_filter(self):
        start = self.start_date.date().toPyDate()
        end = self.end_date.date().toPyDate()
        return start, end

    def generate_report(self):
        self.btn_excel.setEnabled(False)
        self.btn_pdf.setEnabled(False)
        
        try:
            if self.current_report_type == "profits":
                self.generate_profits_report()
            elif self.current_report_type == "cash":
                self.generate_cash_report()
            elif self.current_report_type == "employees":
                self.generate_employees_report()
            elif self.current_report_type == "low_stock":
                self.generate_low_stock_report()
            elif self.current_report_type == "stagnant":
                self.generate_stagnant_report()
            elif self.current_report_type == "expenses":
                self.generate_expenses_report()
            
            if self.current_data:
                self.btn_excel.setEnabled(True)
                self.btn_pdf.setEnabled(True)
                self.show_success_toast(f"✅ تم توليد التقرير بنجاح - {len(self.current_data)} سجل")
            else:
                self.show_warning_toast("⚠️ لا توجد بيانات في الفترة المحددة")
        except Exception as e:
            logger.error(f"خطأ في generate_report: {e}")
            self.show_error_toast(f"❌ خطأ في توليد التقرير: {str(e)}")

    def format_date_for_query(self, date_obj):
        if hasattr(date_obj, 'toPyDate'):
            return date_obj.toPyDate().strftime('%Y-%m-%d')
        return date_obj.strftime('%Y-%m-%d')

    def generate_profits_report(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            start, end = self.get_date_filter()
            start_str = self.format_date_for_query(start)
            end_str = self.format_date_for_query(end)
            
            # استعلام محسن لحساب الربح الحقيقي من تكلفة الشراء
            cursor.execute('''
                SELECT 
                    DATE(s.sale_date) as date,
                    COUNT(DISTINCT s.id) as orders,
                    COALESCE(SUM(s.total_amount), 0) as sales,
                    COALESCE(SUM(s.discount), 0) as discounts,
                    COALESCE(SUM(s.total_amount) - SUM(s.discount), 0) as net_sales,
                    COALESCE(SUM((si.price_at_sale - p.purchase_price) * si.quantity), 0) as real_profit
                FROM sales s
                LEFT JOIN sale_items si ON s.id = si.sale_id
                LEFT JOIN products p ON si.product_id = p.id
                WHERE DATE(s.sale_date) BETWEEN ? AND ?
                GROUP BY DATE(s.sale_date)
                ORDER BY DATE(s.sale_date) DESC
            ''', (start_str, end_str))
            
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                self.current_data = []
                self.current_headers = ["التاريخ", "عدد الطلبات", "المبيعات (ج.م)", "الخصومات (ج.م)", "صافي المبيعات (ج.م)", "صافي الربح (ج.م)"]
                self.display_table(self.current_headers, [], [])
                self.update_kpi_cards([
                    {'title': '💰 إجمالي المبيعات', 'value': '0.00 ج.م', 'color': COLORS['success']},
                    {'title': '📈 صافي الربح الحقيقي', 'value': '0.00 ج.م', 'color': COLORS['warning']},
                    {'title': '📊 صافي المبيعات', 'value': '0.00 ج.م', 'color': COLORS['info']},
                    {'title': '📄 عدد الطلبات', 'value': '0', 'color': COLORS['purple']},
                ])
                return
            
            headers = ["التاريخ", "عدد الطلبات", "المبيعات (ج.م)", "الخصومات (ج.م)", "صافي المبيعات (ج.م)", "صافي الربح (ج.م)"]
            self.current_headers = headers
            self.current_data = data
            
            total_sales = sum(row[2] for row in data)
            total_discounts = sum(row[3] for row in data)
            total_net = sum(row[4] for row in data)
            total_orders = sum(row[1] for row in data)
            total_profit = sum(row[5] for row in data)
            
            self.update_kpi_cards([
                {'title': '💰 إجمالي المبيعات', 'value': f"{total_sales:,.2f} ج.م", 'color': COLORS['success']},
                {'title': '📈 صافي الربح الحقيقي', 'value': f"{total_profit:,.2f} ج.م", 'color': COLORS['warning']},
                {'title': '📊 صافي المبيعات', 'value': f"{total_net:,.2f} ج.م", 'color': COLORS['info']},
                {'title': '📄 عدد الطلبات', 'value': str(total_orders), 'color': COLORS['purple']},
            ])
            
            self.display_table(headers, data, [
                lambda d: d[0],
                lambda d: str(d[1]),
                lambda d: f"{d[2]:,.2f}",
                lambda d: f"{d[3]:,.2f}",
                lambda d: f"{d[4]:,.2f}",
                lambda d: f"{d[5]:,.2f}"
            ])
        except Exception as e:
            logger.error(f"خطأ في تقرير الأرباح: {e}")
            self.show_error_toast(f"❌ خطأ في جلب بيانات الأرباح: {str(e)}")

    def generate_cash_report(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            start, end = self.get_date_filter()
            start_str = self.format_date_for_query(start)
            end_str = self.format_date_for_query(end)
            
            cursor.execute('''
                SELECT 
                    DATE(sale_date) as date,
                    COUNT(id) as orders,
                    COALESCE(SUM(total_amount), 0) as total_sales,
                    COALESCE(SUM(CASE WHEN payment_method = 'نقدي' THEN total_amount ELSE 0 END), 0) as cash_sales,
                    COALESCE(SUM(CASE WHEN payment_method = 'فيزا' THEN total_amount ELSE 0 END), 0) as visa_sales,
                    COALESCE(SUM(CASE WHEN payment_method = 'محفظة' THEN total_amount ELSE 0 END), 0) as wallet_sales
                FROM sales
                WHERE DATE(sale_date) BETWEEN ? AND ?
                GROUP BY DATE(sale_date)
                ORDER BY DATE(sale_date) DESC
            ''', (start_str, end_str))
            
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                self.current_data = []
                self.current_headers = ["التاريخ", "عدد الطلبات", "إجمالي (ج.م)", "كاش (ج.م)", "فيزا (ج.م)", "محفظة (ج.م)"]
                self.display_table(self.current_headers, [], [])
                self.update_kpi_cards([
                    {'title': '💰 إجمالي الإيرادات', 'value': '0.00 ج.م', 'color': COLORS['success']},
                    {'title': '💳 كاش', 'value': '0.00 ج.م', 'color': COLORS['info']},
                    {'title': '📄 عدد الطلبات', 'value': '0', 'color': COLORS['warning']},
                ])
                return
            
            headers = ["التاريخ", "عدد الطلبات", "إجمالي (ج.م)", "كاش (ج.م)", "فيزا (ج.م)", "محفظة (ج.م)"]
            self.current_headers = headers
            self.current_data = data
            
            total_orders = sum(row[1] for row in data)
            total_sales = sum(row[2] for row in data)
            total_cash = sum(row[3] for row in data)
            
            self.update_kpi_cards([
                {'title': '💰 إجمالي الإيرادات', 'value': f"{total_sales:,.2f} ج.م", 'color': COLORS['success']},
                {'title': '💳 كاش', 'value': f"{total_cash:,.2f} ج.م", 'color': COLORS['info']},
                {'title': '📄 عدد الطلبات', 'value': str(total_orders), 'color': COLORS['warning']},
            ])
            
            self.display_table(headers, data, [
                lambda d: d[0],
                lambda d: str(d[1]),
                lambda d: f"{d[2]:,.2f}",
                lambda d: f"{d[3]:,.2f}",
                lambda d: f"{d[4]:,.2f}",
                lambda d: f"{d[5]:,.2f}"
            ])
        except Exception as e:
            logger.error(f"خطأ في تقرير الخزينة: {e}")
            self.show_error_toast(f"❌ خطأ في جلب بيانات الخزينة: {str(e)}")

    def generate_employees_report(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            start, end = self.get_date_filter()
            start_str = self.format_date_for_query(start)
            end_str = self.format_date_for_query(end)
            
            cursor.execute('''
                SELECT 
                    s.cashier_name as username,
                    COUNT(s.id) as orders,
                    COALESCE(SUM(s.total_amount), 0) as sales,
                    COALESCE(SUM(s.discount), 0) as discounts,
                    COALESCE(AVG(s.total_amount), 0) as avg_sale
                FROM sales s
                WHERE DATE(s.sale_date) BETWEEN ? AND ?
                  AND s.cashier_name IS NOT NULL 
                  AND s.cashier_name != ''
                GROUP BY s.cashier_name
                ORDER BY sales DESC
            ''', (start_str, end_str))
            
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                self.current_data = []
                self.current_headers = ["اسم الموظف", "عدد الطلبات", "المبيعات (ج.م)", "الخصومات (ج.م)", "متوسط الطلب (ج.م)"]
                self.display_table(self.current_headers, [], [])
                self.update_kpi_cards([
                    {'title': '👥 عدد الموظفين', 'value': '0', 'color': COLORS['info']},
                    {'title': '📄 إجمالي الطلبات', 'value': '0', 'color': COLORS['warning']},
                    {'title': '💰 إجمالي المبيعات', 'value': '0.00 ج.م', 'color': COLORS['gold']},
                ])
                return
            
            headers = ["اسم الموظف", "عدد الطلبات", "المبيعات (ج.م)", "الخصومات (ج.م)", "متوسط الطلب (ج.م)"]
            self.current_headers = headers
            self.current_data = data
            
            total_orders = sum(row[1] for row in data)
            total_sales = sum(row[2] for row in data)
            
            self.update_kpi_cards([
                {'title': '👥 عدد الموظفين', 'value': str(len(data)), 'color': COLORS['info']},
                {'title': '📄 إجمالي الطلبات', 'value': str(total_orders), 'color': COLORS['warning']},
                {'title': '💰 إجمالي المبيعات', 'value': f"{total_sales:,.2f} ج.م", 'color': COLORS['gold']},
            ])
            
            self.display_table(headers, data, [
                lambda d: d[0] if d[0] else "غير محدد",
                lambda d: str(d[1]),
                lambda d: f"{d[2]:,.2f}",
                lambda d: f"{d[3]:,.2f}",
                lambda d: f"{d[4]:,.2f}"
            ])
        except Exception as e:
            logger.error(f"خطأ في تقرير الموظفين: {e}")
            self.show_error_toast(f"❌ خطأ في جلب بيانات الموظفين: {str(e)}")

    def generate_low_stock_report(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    p.id,
                    p.name,
                    p.stock,
                    p.reorder_level,
                    p.unit,
                    p.category,
                    COALESCE(SUM(si.quantity), 0) as total_sold
                FROM products p
                LEFT JOIN sale_items si ON p.id = si.product_id
                GROUP BY p.id
                HAVING p.stock <= p.reorder_level OR p.stock <= 5
                ORDER BY (p.stock / NULLIF(p.reorder_level, 0)) ASC
            ''')
            
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                self.current_data = []
                self.current_headers = ["اسم المنتج", "الكمية الحالية", "حد الطلب", "الوحدة", "التصنيف", "إجمالي المبيعات"]
                self.display_table(self.current_headers, [], [])
                self.update_kpi_cards([
                    {'title': '🚨 منتجات حرجة', 'value': '0', 'color': COLORS['danger']},
                    {'title': '⚠️ منتجات منخفضة', 'value': '0', 'color': COLORS['warning']},
                    {'title': '📦 إجمالي المنتجات', 'value': '0', 'color': COLORS['info']},
                ])
                return
            
            headers = ["اسم المنتج", "الكمية الحالية", "حد الطلب", "الوحدة", "التصنيف", "إجمالي المبيعات"]
            self.current_headers = headers
            self.current_data = data
            
            critical = len([row for row in data if row[2] <= 0 or row[2] <= row[3]])
            low = len([row for row in data if row[2] > 0 and row[2] <= row[3] + 5])
            
            self.update_kpi_cards([
                {'title': '🚨 منتجات حرجة', 'value': str(critical), 'color': COLORS['danger']},
                {'title': '⚠️ منتجات منخفضة', 'value': str(low), 'color': COLORS['warning']},
                {'title': '📦 إجمالي المنتجات', 'value': str(len(data)), 'color': COLORS['info']},
            ])
            
            self.display_table(headers, data, [
                lambda d: d[1],
                lambda d: str(d[2]),
                lambda d: str(d[3]),
                lambda d: d[4] if d[4] else "قطعة",
                lambda d: d[5] if d[5] else "غير مصنف",
                lambda d: str(d[6])
            ])
        except Exception as e:
            logger.error(f"خطأ في تقرير المنتجات الناقصة: {e}")
            self.show_error_toast(f"❌ خطأ في جلب بيانات المنتجات الناقصة: {str(e)}")

    def generate_stagnant_report(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            start, end = self.get_date_filter()
            end_str = self.format_date_for_query(end)
            
            cursor.execute('''
                SELECT 
                    p.id,
                    p.name,
                    p.stock,
                    p.unit,
                    p.category,
                    MAX(s.sale_date) as last_sale,
                    COALESCE(SUM(si.quantity), 0) as total_sold,
                    julianday(?) - julianday(COALESCE(MAX(s.sale_date), ?)) as days_stagnant
                FROM products p
                LEFT JOIN sale_items si ON p.id = si.product_id
                LEFT JOIN sales s ON si.sale_id = s.id
                GROUP BY p.id
                HAVING (days_stagnant > 30 OR days_stagnant IS NULL) AND p.stock > 0
                ORDER BY days_stagnant DESC
            ''', (end_str, end_str))
            
            data = cursor.fetchall()
            conn.close()
            
            if not data:
                self.current_data = []
                self.current_headers = ["اسم المنتج", "الكمية المتبقية", "الوحدة", "التصنيف", "آخر عملية بيع", "أيام راكدة", "إجمالي المبيعات"]
                self.display_table(self.current_headers, [], [])
                self.update_kpi_cards([
                    {'title': '📦 إجمالي الكميات', 'value': '0', 'color': COLORS['info']},
                    {'title': '⏳ متوسط الأيام الراكدة', 'value': '0 يوم', 'color': COLORS['pink']},
                    {'title': '📄 عدد المنتجات الراكدة', 'value': '0', 'color': COLORS['warning']},
                ])
                return
            
            headers = ["اسم المنتج", "الكمية المتبقية", "الوحدة", "التصنيف", "آخر عملية بيع", "أيام راكدة", "إجمالي المبيعات"]
            self.current_headers = headers
            self.current_data = data
            
            total_qty = sum(row[2] for row in data)
            avg_days = sum(row[7] for row in data) / len(data) if data else 0
            
            self.update_kpi_cards([
                {'title': '📦 إجمالي الكميات', 'value': str(total_qty), 'color': COLORS['info']},
                {'title': '⏳ متوسط الأيام الراكدة', 'value': f"{avg_days:.0f} يوم", 'color': COLORS['pink']},
                {'title': '📄 عدد المنتجات الراكدة', 'value': str(len(data)), 'color': COLORS['warning']},
            ])
            
            self.display_table(headers, data, [
                lambda d: d[1],
                lambda d: str(d[2]),
                lambda d: d[3] if d[3] else "قطعة",
                lambda d: d[4] if d[4] else "غير مصنف",
                lambda d: d[5] if d[5] else "لم تباع بعد",
                lambda d: str(int(d[7])) if d[7] else "جديد",
                lambda d: str(d[6])
            ])
        except Exception as e:
            logger.error(f"خطأ في تقرير المنتجات الراكدة: {e}")
            self.show_error_toast(f"❌ خطأ في جلب بيانات المنتجات الراكدة: {str(e)}")

    def generate_expenses_report(self):
        """
        تقرير المصروفات - يستدعي دوال من back/database.py
        get_expenses(date_from, date_to) و get_expenses_summary(date_from, date_to)
        """
        try:
            from back.database import get_expenses, get_expenses_summary
            
            start, end = self.get_date_filter()
            start_str = self.format_date_for_query(start)
            end_str = self.format_date_for_query(end)
            
            # جلب تفاصيل المصروفات
            expenses_data = get_expenses(start_str, end_str)
            
            if not expenses_data:
                self.current_data = []
                self.current_headers = ["التاريخ", "البند", "المبلغ (ج.م)", "طريقة الدفع", "ملاحظات"]
                self.display_table(self.current_headers, [], [])
                self.update_kpi_cards([
                    {'title': '💰 إجمالي المصروفات', 'value': '0.00 ج.م', 'color': COLORS['danger']},
                    {'title': '📊 أكبر بند', 'value': 'لا يوجد', 'color': COLORS['warning']},
                    {'title': '📄 عدد العمليات', 'value': '0', 'color': COLORS['info']},
                ])
                return
            
            # جلب الملخص
            summary = get_expenses_summary(start_str, end_str)
            
            headers = ["التاريخ", "البند", "المبلغ (ج.م)", "طريقة الدفع", "ملاحظات"]
            self.current_headers = headers
            self.current_data = expenses_data
            
            total_expenses = summary.get('total', 0) if summary else 0
            largest_item = summary.get('largest_item', 'لا يوجد') if summary else 'لا يوجد'
            item_count = summary.get('count', 0) if summary else 0
            
            self.update_kpi_cards([
                {'title': '💰 إجمالي المصروفات', 'value': f"{total_expenses:,.2f} ج.م", 'color': COLORS['danger']},
                {'title': '📊 أكبر بند', 'value': largest_item, 'color': COLORS['warning']},
                {'title': '📄 عدد العمليات', 'value': str(item_count), 'color': COLORS['info']},
            ])
            
            # عرض البيانات في الجدول
            self.display_table(headers, expenses_data, [
                lambda d: d.get('date', '') if isinstance(d, dict) else d[0],
                lambda d: d.get('item', '') if isinstance(d, dict) else d[1],
                lambda d: f"{d.get('amount', 0):,.2f}" if isinstance(d, dict) else f"{d[2]:,.2f}",
                lambda d: d.get('payment_method', '') if isinstance(d, dict) else d[3],
                lambda d: d.get('notes', '') if isinstance(d, dict) else d[4],
            ])
            
        except ImportError:
            logger.error("تعذر استيراد دوال المصروفات من back.database")
            self.show_error_toast("❌ تعذر استيراد دوال المصروفات. تأكد من وجودها في back/database.py")
        except Exception as e:
            logger.error(f"خطأ في تقرير المصروفات: {e}")
            self.show_error_toast(f"❌ خطأ في جلب بيانات المصروفات: {str(e)}")

    def display_table(self, headers, data, extractors):
        if not headers:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            return
            
        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)
        
        header = self.data_table.horizontalHeader()
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        if not data:
            self.data_table.setRowCount(0)
            return
            
        self.data_table.setRowCount(len(data))
        
        for row, item in enumerate(data):
            self.data_table.setRowHeight(row, 40)
            for col, extractor in enumerate(extractors):
                try:
                    value = extractor(item)
                    table_item = QTableWidgetItem(str(value))
                    table_item.setTextAlignment(Qt.AlignCenter)
                    self.data_table.setItem(row, col, table_item)
                except Exception as e:
                    logger.error(f"خطأ في عرض البيانات: {e}")
                    table_item = QTableWidgetItem("خطأ")
                    table_item.setTextAlignment(Qt.AlignCenter)
                    self.data_table.setItem(row, col, table_item)

    def reshape_arabic_text(self, text):
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

    def export_excel(self):
        if not self.current_data:
            self.show_warning_toast("⚠️ لا توجد بيانات للتصدير")
            return
        
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "حفظ ملف Excel", "", "CSV Files (*.csv);;All Files (*)"
            )
            if not filename:
                return
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(self.current_headers)
                for row in self.current_data:
                    if isinstance(row, dict):
                        # التعامل مع حالة البيانات من get_expenses (dict)
                        writer.writerow([row.get(h, '') for h in self.current_headers])
                    else:
                        writer.writerow(row)
            
            self.show_success_toast(f"✅ تم تصدير التقرير إلى Excel بنجاح")
        
        except Exception as e:
            logger.error(f"خطأ في تصدير Excel: {e}")
            self.show_error_toast(f"❌ خطأ في تصدير Excel: {str(e)}")

    def export_pdf(self):
        if not self.current_data:
            self.show_warning_toast("⚠️ لا توجد بيانات للتصدير")
            return
        
        if not REPORTLAB_AVAILABLE:
            self.show_error_toast("❌ مكتبة reportlab غير مثبتة. قم بتثبيتها: pip install reportlab")
            return
        
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "حفظ ملف PDF", 
                f"تقرير_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "PDF Files (*.pdf);;All Files (*)"
            )
            
            if not filename:
                self.show_info_toast("❌ تم إلغاء عملية التصدير")
                return
            
            doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
            elements = []
            
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=colors.HexColor('#38bdf8')
            )
            
            report_names = {
                'profits': 'تقرير الأرباح اليومية والمبيعات',
                'cash': 'تقرير حركة الخزينة والإيرادات',
                'employees': 'تقرير أداء الموظفين والكاشيرية',
                'low_stock': 'تقرير المنتجات الناقصة',
                'stagnant': 'تقرير المنتجات الراكدة',
                'expenses': 'تقرير المصروفات'
            }
            
            report_name = report_names.get(self.current_report_type, 'تقرير')
            elements.append(Paragraph(report_name, title_style))
            
            date_style = ParagraphStyle(
                'DateStyle',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#94a3b8')
            )
            elements.append(Paragraph(f"تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}", date_style))
            elements.append(Spacer(1, 20))
            
            # تجهيز البيانات للجدول
            table_data = [self.current_headers]
            for row in self.current_data:
                if isinstance(row, dict):
                    # التعامل مع حالة البيانات من get_expenses (dict)
                    row_values = [str(row.get(h, '')) for h in self.current_headers]
                else:
                    row_values = [str(val) for val in row]
                table_data.append(row_values)
            
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#38bdf8')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#0f172a')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#334155')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(table)
            
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#94a3b8'),
                spaceTop=20
            )
            elements.append(Paragraph("تم إنشاء هذا التقرير بواسطة نظام إدارة المبيعات", footer_style))
            
            doc.build(elements)
            
            self.show_success_toast("✅ تم توليد وتصدير تقرير الـ PDF بنجاح")
            
            try:
                if os.name == 'nt':
                    os.startfile(filename)
                else:
                    subprocess.run(['xdg-open', filename], check=False)
                logger.info(f"تم فتح الملف: {filename}")
            except Exception as e:
                logger.error(f"تعذر فتح الملف تلقائياً: {e}")
                self.show_warning_toast(f"⚠️ تم حفظ الملف في: {os.path.basename(filename)}")
        
        except Exception as e:
            logger.error(f"خطأ في تصدير PDF: {e}")
            self.show_error_toast(f"❌ خطأ في تصدير PDF: {str(e)}")


if __name__ == "__main__":
    app = QApplication([])
    window = ReportsWindow()
    window.showMaximized()
    app.exec_()