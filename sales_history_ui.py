# ================= ملف sales_history_ui.py بعد التعديل النهائي =================

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel, 
                             QLineEdit, QFrame, QDialog, QTextEdit)
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer
from PyQt6.QtGui import QColor, QFont
from back.database import get_all_sales, get_cash_sales, get_deferred_sales, get_returned_sales, get_sale_details, delete_sale
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

# محاولة تحميل خط عربي
try:
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc"
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
            break
except:
    pass

# ========== الألوان الثابتة المحسنة ==========
COLORS = {
    'bg_dark': '#121212',
    'bg_sidebar': '#1a1a2e',
    'bg_card': '#1e1e2e',
    'text': '#e0e0e0',
    'text_muted': '#a0a0a0',
    'accent': '#00d4ff',
    'success': '#27ae60',
    'success_hover': '#219a52',
    'danger': '#c0392b',
    'danger_hover': '#a93226',
    'warning': '#d35400',
    'warning_hover': '#ba4a00',
    'info': '#2980b9',
    'info_hover': '#1f618d',
    'border': '#2d2d5c',
    'deferred_color': '#d35400',
    'cash_color': '#27ae60',
    'return_color': '#8e44ad'
}

# ========== رسالة Toast ==========
class ToastMessage(QLabel):
    def __init__(self, parent, message, color):
        super().__init__(message, parent)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 10px;
                padding: 15px 25px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(50)
        
        parent_width = parent.width()
        self.setFixedWidth(min(400, parent_width - 40))
        self.move((parent_width - self.width()) // 2, parent.height() - 80)
        
        self.show()
        QTimer.singleShot(2000, self.fade_out)
    
    def fade_out(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()


# ========== نافذة عرض التفاصيل ==========
class SaleDetailsDialog(QDialog):
    def __init__(self, sale_id, details, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📄 تفاصيل الفاتورة رقم {sale_id}")
        self.setModal(True)
        self.resize(550, 500)
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
                font-family: monospace;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        title = QLabel(f"📋 تفاصيل الفاتورة #{sale_id}")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        formatted_text = self.format_details_text(sale_id, details)
        self.details_text.setPlainText(formatted_text)
        layout.addWidget(self.details_text)
        
        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                padding: 12px 25px;
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
    
    def format_details_text(self, sale_id, details):
        text = ""
        text += "═" * 55 + "\n"
        text += f"  فاتورة رقم: {sale_id}\n"
        text += "═" * 55 + "\n\n"
        text += "المنتجات:\n"
        text += "─" * 55 + "\n"
        
        for idx, d in enumerate(details, 1):
            product_name = d[1]
            quantity = d[2]
            price = d[3]
            item_total = quantity * price
            text += f"{idx}. {product_name}\n"
            text += f"   الكمية: {quantity}  ×  {price:,.2f} ج.م\n"
            text += f"   الإجمالي: {item_total:,.2f} ج.م\n"
            text += "─" * 55 + "\n"
        
        if details:
            total_amount = float(details[0][4]) if details[0][4] else 0
            discount = float(details[0][5]) if details[0][5] else 0
            sale_type = details[0][7] if len(details[0]) > 7 else 'نقدي'
            subtotal = sum(d[2] * d[3] for d in details)
            text += "\n" + "═" * 55 + "\n"
            text += f"المجموع الفرعي: {subtotal:,.2f} ج.م\n"
            if discount > 0:
                text += f"الخصم: {discount:,.2f} ج.م\n"
            text += f"الإجمالي النهائي: {total_amount:,.2f} ج.م\n"
            text += f"نوع الفاتورة: {sale_type}\n"
            text += "═" * 55 + "\n"
        return text


# ========== نافذة سجل الفواتير ==========
class SalesHistoryWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.all_sales = []
        self.current_filter = 'all'
        self.init_ui()

    def show_toast(self, message, is_success=True):
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_info_toast(self, message):
        ToastMessage(self, message, COLORS['info'])
    
    def show_warning_toast(self, message):
        ToastMessage(self, message, COLORS['warning'])
    
    def show_success_toast(self, message):
        ToastMessage(self, message, COLORS['success'])

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                padding: 15px;
                margin: 20px 20px 0 20px;
            }}
        """)
        header_layout = QVBoxLayout(header_frame)
        
        title = QLabel("📜 سجل الفواتير السابقة")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLORS['accent']};")
        header_layout.addWidget(title)
        
        # فلتر
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        filter_label = QLabel("تصفية حسب نوع الفاتورة:")
        filter_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        filter_layout.addWidget(filter_label)
        
        self.btn_all = QPushButton("📋 الكل")
        self.btn_all.setFixedSize(100, 35)
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
        self.btn_all.clicked.connect(self.load_all_sales)
        filter_layout.addWidget(self.btn_all)
        
        self.btn_cash = QPushButton("💰 نقدي")
        self.btn_cash.setFixedSize(100, 35)
        self.btn_cash.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['cash_color']};
                color: white;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: #1e8449; }}
        """)
        self.btn_cash.clicked.connect(self.load_cash_sales)
        filter_layout.addWidget(self.btn_cash)
        
        self.btn_deferred = QPushButton("📋 آجل")
        self.btn_deferred.setFixedSize(100, 35)
        self.btn_deferred.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['deferred_color']};
                color: white;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: #ba4a00; }}
        """)
        self.btn_deferred.clicked.connect(self.load_deferred_sales)
        filter_layout.addWidget(self.btn_deferred)
        
        self.btn_returned = QPushButton("🔄 مرتجع")
        self.btn_returned.setFixedSize(100, 35)
        self.btn_returned.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['return_color']};
                color: white;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: #6c3483; }}
        """)
        self.btn_returned.clicked.connect(self.load_returned_sales)
        filter_layout.addWidget(self.btn_returned)
        
        filter_layout.addStretch()
        
        # بحث
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 بحث:")
        search_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        search_layout.addWidget(search_label)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("رقم الفاتورة...")
        self.search_input.setFixedWidth(200)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.search_input.textChanged.connect(self.filter_sales)
        search_layout.addWidget(self.search_input)
        search_layout.addStretch()
        
        header_layout.addLayout(filter_layout)
        header_layout.addLayout(search_layout)
        layout.addWidget(header_frame)

        # جدول المبيعات
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["رقم الفاتورة", "الإجمالي", "الخصم", "التاريخ", "طريقة الدفع", "نوع الفاتورة", "الإجراءات"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 280)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                font-size: 13px;
                gridline-color: {COLORS['border']};
                margin: 0 20px 20px 20px;
            }}
            QTableWidget::item {{
                padding: 12px 8px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['bg_sidebar']};
            }}
            QHeaderView::section {{
                background-color: #0d0d1a;
                color: white;
                padding: 14px 8px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }}
            QTableCornerButton::section {{
                background-color: #0d0d1a;
                border: none;
            }}
        """)
        
        layout.addWidget(self.table)
        layout.setStretchFactor(self.table, 1)
        self.load_all_sales()
    
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
                    except:
                        continue
                return date_value
            return str(date_value)
        except:
            return str(date_value)

    def create_centered_item(self, text, alignment=Qt.AlignmentFlag.AlignCenter):
        item = QTableWidgetItem(text)
        item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
        return item

    def load_all_sales(self):
        try:
            self.current_filter = 'all'
            self.all_sales = get_all_sales()
            self.filter_sales()
            self.update_button_styles('all')
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ في تحميل الفواتير: {str(e)}")

    def load_cash_sales(self):
        try:
            self.current_filter = 'cash'
            self.all_sales = get_cash_sales()
            self.filter_sales()
            self.update_button_styles('cash')
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ في تحميل الفواتير النقدية: {str(e)}")

    def load_deferred_sales(self):
        try:
            self.current_filter = 'deferred'
            self.all_sales = get_deferred_sales()
            self.filter_sales()
            self.update_button_styles('deferred')
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ في تحميل الفواتير الآجلة: {str(e)}")

    def load_returned_sales(self):
        try:
            self.current_filter = 'returned'
            self.all_sales = get_returned_sales()
            self.filter_sales()
            self.update_button_styles('returned')
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ في تحميل الفواتير المرتجعة: {str(e)}")

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
        self.btn_cash.setStyleSheet(reset_style % (COLORS['cash_color'], '#1e8449'))
        self.btn_deferred.setStyleSheet(reset_style % (COLORS['deferred_color'], '#ba4a00'))
        self.btn_returned.setStyleSheet(reset_style % (COLORS['return_color'], '#6c3483'))
        
        active_style = "border: 2px solid %s; background-color: %s;"
        if active == 'all':
            self.btn_all.setStyleSheet(self.btn_all.styleSheet() + active_style % (COLORS['accent'], '#1f618d'))
        elif active == 'cash':
            self.btn_cash.setStyleSheet(self.btn_cash.styleSheet() + active_style % (COLORS['accent'], '#1e8449'))
        elif active == 'deferred':
            self.btn_deferred.setStyleSheet(self.btn_deferred.styleSheet() + active_style % (COLORS['accent'], '#ba4a00'))
        elif active == 'returned':
            self.btn_returned.setStyleSheet(self.btn_returned.styleSheet() + active_style % (COLORS['accent'], '#6c3483'))

    def filter_sales(self):
        search_text = self.search_input.text().strip()
        self.table.setRowCount(0)
        
        for sale in self.all_sales:
            if isinstance(sale, dict):
                sale_id = sale['id']
                total_val = float(sale.get('total_amount', 0) or 0)
                discount_val = float(sale.get('discount', 0) or 0)
                sale_date = sale.get('sale_date', '')
                payment_method = sale.get('payment_method', 'نقدي')
                sale_type = sale.get('sale_type', 'نقدي')
                customer_name = sale.get('customer_name', '')
            else:
                sale_id = sale[0]
                total_val = float(sale[1] if sale[1] else 0)
                discount_val = float(sale[2] if sale[2] else 0)
                sale_date = sale[8] if len(sale) > 8 else ''
                payment_method = sale[5] if len(sale) > 5 else 'نقدي'
                sale_type = sale[7] if len(sale) > 7 else 'نقدي'
                customer_name = sale[9] if len(sale) > 9 else ''
            
            if search_text and str(sale_id) != search_text:
                continue
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            is_returned = (sale_type == 'مرتجع')
            
            id_item = self.create_centered_item(str(sale_id))
            if is_returned:
                id_item.setForeground(QColor(COLORS['return_color']))
            self.table.setItem(row, 0, id_item)
            
            total_item = QTableWidgetItem(f"{total_val:,.2f} ج.م")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item.setForeground(QColor(COLORS['success']))
            total_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            if is_returned:
                total_item.setForeground(QColor(COLORS['return_color']))
            self.table.setItem(row, 1, total_item)
            
            discount_item = QTableWidgetItem(f"{discount_val:,.2f} ج.م")
            discount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if discount_val > 0:
                discount_item.setForeground(QColor(COLORS['warning']))
            self.table.setItem(row, 2, discount_item)
            
            formatted_date = self.format_datetime(sale_date)
            date_item = self.create_centered_item(formatted_date)
            self.table.setItem(row, 3, date_item)
            
            method_item = self.create_centered_item(payment_method)
            if payment_method == 'آجل':
                method_item.setForeground(QColor(COLORS['deferred_color']))
                method_item.setToolTip(f"فاتورة آجلة - العميل: {customer_name}")
            else:
                method_item.setForeground(QColor(COLORS['cash_color']))
                method_item.setToolTip("فاتورة نقدية")
            self.table.setItem(row, 4, method_item)
            
            type_item = self.create_centered_item(sale_type)
            if sale_type == 'مرتجع':
                type_item.setForeground(QColor(COLORS['return_color']))
                type_item.setToolTip("فاتورة مرتجعة")
            elif sale_type == 'آجل':
                type_item.setForeground(QColor(COLORS['deferred_color']))
                type_item.setToolTip("فاتورة آجلة")
            else:
                type_item.setForeground(QColor(COLORS['cash_color']))
                type_item.setToolTip("فاتورة نقدية")
            self.table.setItem(row, 5, type_item)
            
            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            layout_btns = QHBoxLayout(container)
            layout_btns.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout_btns.setSpacing(8)
            layout_btns.setContentsMargins(0, 5, 0, 5)
            
            btn_print = QPushButton("🖨️ طباعة")
            btn_print.setFixedSize(80, 32)
            btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_print.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['success']};
                    color: white;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
            """)
            btn_print.clicked.connect(lambda ch, sid=sale_id: self.reprint_invoice(sid))
            
            btn_details = QPushButton("📋 تفاصيل")
            btn_details.setFixedSize(80, 32)
            btn_details.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_details.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['info']};
                    color: white;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {COLORS['info_hover']}; }}
            """)
            btn_details.clicked.connect(lambda ch, sid=sale_id: self.show_details(sid))
            
            btn_delete = QPushButton("🗑️ حذف")
            btn_delete.setFixedSize(80, 32)
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['danger']};
                    color: white;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {COLORS['danger_hover']}; }}
            """)
            btn_delete.clicked.connect(lambda ch, sid=sale_id: self.delete_sale(sid))
            
            layout_btns.addWidget(btn_print)
            layout_btns.addWidget(btn_details)
            layout_btns.addWidget(btn_delete)
            
            self.table.setCellWidget(row, 6, container)

    def show_details(self, sale_id):
        try:
            details = get_sale_details(sale_id)
            if not details:
                self.show_warning_toast("لا توجد تفاصيل لهذه الفاتورة")
                return
            dialog = SaleDetailsDialog(sale_id, details, self)
            dialog.exec()
        except Exception as e:
            self.show_warning_toast(f"خطأ في عرض التفاصيل: {str(e)}")

    def reprint_invoice(self, sale_id):
        try:
            details = get_sale_details(sale_id)
            if not details:
                self.show_warning_toast("لا توجد تفاصيل لهذه الفاتورة")
                return
            
            items = []
            for d in details:
                items.append((d[1], d[2], d[3]))
            
            total_amount = float(details[0][4]) if details[0][4] else 0
            discount = float(details[0][5]) if details[0][5] else 0
            sale_type = details[0][7] if len(details[0]) > 7 else 'نقدي'
            subtotal = sum(q * p for _, q, p in items)
            
            if not os.path.exists('invoices'):
                os.makedirs('invoices')
            
            filename = f"invoices/invoice_{sale_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            self.generate_professional_invoice(filename, sale_id, items, total_amount, discount, subtotal, sale_type)
            
            try:
                os.startfile(filename)
                self.show_success_toast(f"✅ تمت طباعة الفاتورة رقم {sale_id}")
            except:
                self.show_info_toast(f"تم حفظ الفاتورة في: {filename}")
        except Exception as e:
            self.show_warning_toast(f"خطأ في طباعة الفاتورة: {str(e)}")

    def generate_professional_invoice(self, filename, sale_id, items, total, discount, subtotal, sale_type="نقدي"):
        try:
            page_width = 80 * mm
            page_height = 150 * mm + (len(items) * 5 * mm)
            c = canvas.Canvas(filename, pagesize=(page_width, page_height))
            
            y_position = page_height - 10 * mm
            margin = 5 * mm
            center_x = page_width / 2
            
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(center_x, y_position, "SMART MARKET")
            y_position -= 6 * mm
            c.setFont("Helvetica", 9)
            c.drawCentredString(center_x, y_position, "سوبر ماركت")
            y_position -= 5 * mm
            c.setFont("Helvetica", 8)
            c.drawCentredString(center_x, y_position, f"فاتورة رقم: {sale_id}")
            y_position -= 5 * mm
            c.drawCentredString(center_x, y_position, f"التاريخ: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
            y_position -= 5 * mm
            
            c.setFont("Helvetica-Bold", 9)
            if sale_type == 'مرتجع':
                c.setFillColorRGB(0.55, 0.27, 0.07)
                c.drawCentredString(center_x, y_position, "فاتورة مرتجعة")
            elif sale_type == 'آجل':
                c.setFillColorRGB(0.83, 0.33, 0)
                c.drawCentredString(center_x, y_position, "فاتورة آجلة")
            else:
                c.setFillColorRGB(0.15, 0.68, 0.38)
                c.drawCentredString(center_x, y_position, "فاتورة نقدية")
            
            c.setFillColorRGB(0, 0, 0)
            y_position -= 5 * mm
            c.line(margin, y_position, page_width - margin, y_position)
            y_position -= 5 * mm
            
            c.setFont("Helvetica-Bold", 8)
            c.drawString(margin, y_position, "الصنف")
            c.drawRightString(page_width - margin - 25*mm, y_position, "الكمية")
            c.drawRightString(page_width - margin, y_position, "السعر")
            y_position -= 5 * mm
            c.line(margin, y_position, page_width - margin, y_position)
            y_position -= 3 * mm
            
            c.setFont("Helvetica", 8)
            for name, qty, price in items:
                if y_position < 30 * mm:
                    c.showPage()
                    y_position = page_height - 10 * mm
                    c.setFont("Helvetica", 8)
                
                product_line = name[:25] + ("..." if len(name) > 25 else "")
                c.drawString(margin, y_position, product_line)
                line_text = f"{qty} × {price:,.2f} = {qty * price:,.2f}"
                c.drawRightString(page_width - margin, y_position, line_text)
                y_position -= 6 * mm
            
            y_position -= 2 * mm
            c.line(margin, y_position, page_width - margin, y_position)
            y_position -= 5 * mm
            
            c.setFont("Helvetica", 9)
            c.drawString(margin, y_position, f"المجموع: {subtotal:,.2f} ج.م")
            y_position -= 5 * mm
            if discount > 0:
                c.drawString(margin, y_position, f"الخصم: {discount:,.2f} ج.م")
                y_position -= 5 * mm
            c.line(margin, y_position, page_width - margin, y_position)
            y_position -= 5 * mm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margin, y_position, f"الإجمالي: {total:,.2f} ج.م")
            y_position -= 10 * mm
            c.setFont("Helvetica", 8)
            c.drawCentredString(center_x, y_position, "شكراً لتسوقكم معنا")
            c.save()
        except Exception as e:
            raise Exception(f"خطأ في إنشاء PDF: {str(e)}")

    def delete_sale(self, sale_id):
        """حذف فاتورة مع ظهور Toast وتحديث الجدول فوراً"""
        success, msg = delete_sale(sale_id)
        if success:
            self.show_success_toast(f"✅ {msg}")
            self.load_all_sales()  # تحديث الجدول فوراً بعد الحذف
        else:
            self.show_warning_toast(f"❌ {msg}")

    def load_sales(self):
        self.load_all_sales()