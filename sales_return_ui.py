"""
نافذة مرتجع المبيعات - تدعم إرجاع المنتجات من الفواتير
مع توحيد الهوية البصرية ونظام الـ Toast بدلاً من الـ QMessageBox
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel,
                             QPushButton, QDialog, QFormLayout, QGroupBox, QSpinBox,
                             QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer
from back import database as db
from PyQt6.QtGui import QFont

# ========== الألوان الموحدة ==========
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
    'return_btn': '#f39c12',
    'return_btn_hover': '#e67e22',
}

FONTS = {
    'title': QFont("Segoe UI", 24, QFont.Weight.Bold),
    'button': QFont("Segoe UI", 13, QFont.Weight.Medium),
}

# ========== رسالة Toast ==========
class ToastMessage(QLabel):
    """رسالة منبثقة تظهر وتختفي تلقائياً"""
    
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
        """اختفاء سلس للرسالة"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()


# ========== نافذة تنفيذ مرتجع مبيعات ==========
class SalesReturnForm(QDialog):
    """نافذة إدخال تفاصيل المرتجع - تظهر عند اختيار فاتورة"""
    
    def __init__(self, sale_id, sale_details, sale_items_data, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(f"🔄 تنفيذ مرتجع مبيعات - فاتورة رقم {sale_id}")
        self.setModal(True)
        self.resize(900, 750)
        self.setMinimumSize(800, 600)
        
        # ستايل النافذة بالكامل
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
            }}
            QGroupBox {{
                color: {COLORS['accent']};
                font-weight: bold;
                font-size: 15px;
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                margin-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
            }}
            QSpinBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['accent']};
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                min-height: 30px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {COLORS['bg_card']};
                border: none;
                width: 20px;
            }}
            QTextEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }}
            QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # عنوان
        title_label = QLabel(f"مرتجع مبيعات - الفاتورة رقم {sale_id}")
        title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['accent']}; padding: 15px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # معلومات الفاتورة
        info_group = QGroupBox("📋 معلومات الفاتورة")
        info_group.setStyleSheet(f"QGroupBox {{ color: {COLORS['accent']}; font-weight: bold; font-size: 14px; }}")
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(10)
        
        sale_id_label = QLabel(str(sale_id))
        sale_id_label.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold;")
        info_layout.addRow("رقم الفاتورة:", sale_id_label)
        
        total_amount = sale_details.get('total', 0) if isinstance(sale_details, dict) else sale_details[0] if sale_details else 0
        discount_val = sale_details.get('discount', 0) if isinstance(sale_details, dict) else sale_details[1] if sale_details else 0
        
        info_layout.addRow("إجمالي المبلغ:", QLabel(f"{total_amount:,.2f} ج.م"))
        info_layout.addRow("الخصم:", QLabel(f"{discount_val:,.2f} ج.م"))
        layout.addWidget(info_group)
        
        # المنتجات
        products_group = QGroupBox("📦 اختر المنتجات المراد إرجاعها")
        products_group.setStyleSheet(f"QGroupBox {{ color: {COLORS['accent']}; font-weight: bold; font-size: 14px; }}")
        products_layout = QVBoxLayout(products_group)
        products_layout.setSpacing(10)
        
        self.return_items = []
        for item in sale_items_data:
            item_frame = QFrame()
            item_frame.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 10px; margin: 5px; border: 1px solid {COLORS['border']}; }}")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setSpacing(15)
            item_layout.setContentsMargins(15, 10, 15, 10)
            
            name_label = QLabel(f"🛒 {item['name']}")
            name_label.setMinimumWidth(250)
            name_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
            
            price_label = QLabel(f"{item['price']:,.2f} ج.م")
            price_label.setMinimumWidth(120)
            price_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; font-size: 14px;")
            
            qty_val = item['quantity']
            qty_sold_label = QLabel(f"المباع: {qty_val}")
            qty_sold_label.setMinimumWidth(100)
            qty_sold_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
            
            qty_spin = QSpinBox()
            qty_spin.setRange(0, qty_val)
            qty_spin.setValue(0)
            qty_spin.setMinimumWidth(120)
            qty_spin.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {COLORS['bg_dark']};
                    color: {COLORS['text']};
                    border: 2px solid {COLORS['accent']};
                    border-radius: 8px;
                    padding: 8px;
                    min-height: 35px;
                }}
            """)
            
            item_layout.addWidget(name_label)
            item_layout.addWidget(price_label)
            item_layout.addWidget(qty_sold_label)
            item_layout.addStretch()
            item_layout.addWidget(QLabel("كمية المرتجع:"))
            item_layout.addWidget(qty_spin)
            
            products_layout.addWidget(item_frame)
            
            self.return_items.append({
                'product_id': item['product_id'],
                'name': item['name'],
                'price': item['price'],
                'max_qty': qty_val,
                'spin': qty_spin
            })
        
        layout.addWidget(products_group)
        
        # سبب المرتجع
        reason_group = QGroupBox("📝 سبب المرتجع")
        reason_group.setStyleSheet(f"QGroupBox {{ color: {COLORS['accent']}; font-weight: bold; font-size: 14px; }}")
        reason_layout = QVBoxLayout(reason_group)
        self.return_reason = QTextEdit()
        self.return_reason.setPlaceholderText("مثال: منتج به عيب، انتهاء الصلاحية، خطأ في الصنف...")
        self.return_reason.setMaximumHeight(100)
        reason_layout.addWidget(self.return_reason)
        layout.addWidget(reason_group)
        
        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        
        confirm_btn = QPushButton("✅ تأكيد المرتجع")
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['return_btn']};
                color: white;
                padding: 12px 30px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                min-height: 40px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['return_btn_hover']};
            }}
        """)
        confirm_btn.clicked.connect(self.on_confirm)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 12px 30px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                min-height: 40px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(confirm_btn)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
    
    def show_toast(self, message, is_success=True):
        """إظهار رسالة منبثقة داخل النافذة"""
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_warning_toast(self, message):
        ToastMessage(self, message, COLORS['warning'])
    
    def on_confirm(self):
        """التحقق من صحة البيانات قبل الإغلاق"""
        items = self.get_return_items()
        if not items:
            self.show_warning_toast("⚠️ لم يتم اختيار أي منتجات للمرتجع")
            return
        
        # التحقق من أن الكميات صالحة
        for item in self.return_items:
            qty = item['spin'].value()
            if qty > item['max_qty']:
                self.show_warning_toast(f"⚠️ الكمية المرتجعة من {item['name']} تتجاوز الكمية المباعة")
                return
        
        self.accept()
    
    def get_return_items(self):
        """إرجاع قائمة المنتجات المراد إرجاعها"""
        items = []
        for item in self.return_items:
            qty = item['spin'].value()
            if qty > 0:
                items.append((item['product_id'], qty, item['price']))
        return items
    
    def get_reason(self):
        return self.return_reason.toPlainText()


# ========== شاشة مرتجع مبيعات ==========
class SalesReturnWindow(QWidget):
    """النافذة الرئيسية لمرتجعات المبيعات"""
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # عنوان
        title = QLabel("↩️ مرتجع مبيعات")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
        layout.addWidget(title)
        
        # معلومات توضيحية
        info_label = QLabel("ℹ️ اختر الفاتورة ثم اضغط على زر 'تنفيذ مرتجع' لاختيار المنتجات المراد إرجاعها")
        info_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 13px; padding: 12px; background-color: {COLORS['bg_card']}; border-radius: 10px;")
        layout.addWidget(info_label)
        
        # جدول الفواتير - تم إزالة عمود حالة المرتجع
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 14px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['bg_sidebar']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 12px;
                border: none;
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        # 5 أعمدة فقط (تم إزالة عمود حالة المرتجع)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["رقم الفاتورة", "التاريخ", "المبلغ", "الخصم", "الإجراءات"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        self.load_sales()
    
    def show_toast(self, message, is_success=True):
        """إظهار رسالة منبثقة"""
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_info_toast(self, message):
        ToastMessage(self, message, COLORS['info'])
    
    def show_warning_toast(self, message):
        ToastMessage(self, message, COLORS['warning'])
    
    def show_success_toast(self, message):
        """إظهار رسالة نجاح"""
        ToastMessage(self, message, COLORS['success'])
    
    def load_sales(self):
        """تحميل قائمة الفواتير وعرضها في الجدول - تعرض فقط الفواتير النقدية والآجلة (غير المرتجعة)"""
        try:
            sales = db.get_all_sales()
            
            # تصفية الفواتير: عرض فقط الفواتير التي نوعها ليس 'مرتجع' (نقدي أو آجل)
            # وإخفاء الفواتير التي تم إرجاعها بالكامل
            visible_sales = []
            for sale in sales:
                if isinstance(sale, (tuple, list)):
                    sale_type = sale[7] if len(sale) > 7 else 'نقدي'
                    return_status = sale[6] if len(sale) > 6 else 0
                else:
                    sale_type = sale.get('sale_type', 'نقدي') if hasattr(sale, 'get') else 'نقدي'
                    return_status = sale.get('return_status', 0) if hasattr(sale, 'get') else 0
                
                # عرض فقط الفواتير اللي مش مرتجع واللي لم يتم إرجاعها بالكامل
                if sale_type != 'مرتجع' and return_status != 2:
                    visible_sales.append(sale)
            
            self.table.setRowCount(len(visible_sales))
            
            for row, sale in enumerate(visible_sales):
                self.table.setRowHeight(row, 55)
                
                # التعامل مع البيانات
                if isinstance(sale, (tuple, list)):
                    sale_id = sale[0]
                    total_amount = float(sale[1]) if sale[1] else 0
                    discount = float(sale[2]) if sale[2] else 0
                    sale_date = sale[8] if len(sale) > 8 else ''
                else:
                    sale_id = sale['id']
                    total_amount = float(sale['total_amount']) if sale['total_amount'] else 0
                    discount = float(sale['discount']) if sale['discount'] else 0
                    sale_date = sale['sale_date']
                
                # رقم الفاتورة
                id_item = QTableWidgetItem(str(sale_id))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, id_item)
                
                # التاريخ
                date_item = QTableWidgetItem(str(sale_date))
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 1, date_item)
                
                # المبلغ
                total_item = QTableWidgetItem(f"{total_amount:,.2f} ج.م")
                total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.table.setItem(row, 2, total_item)
                
                # الخصم
                discount_item = QTableWidgetItem(f"{discount:,.2f} ج.م")
                discount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.table.setItem(row, 3, discount_item)
                
                # زر تنفيذ المرتجع
                btn = QPushButton("🔄 تنفيذ مرتجع")
                btn.setFixedSize(130, 32)
                btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['return_btn']};
                        color: white;
                        border-radius: 6px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['return_btn_hover']};
                    }}
                """)
                btn.clicked.connect(lambda _, sid=sale_id: self.process_return(sid))
                
                # توسيط الزر داخل الخلية
                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                container_layout.addStretch()
                container_layout.addWidget(btn)
                container_layout.addStretch()
                
                self.table.setCellWidget(row, 4, container)
                
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ في تحميل الفواتير: {str(e)}")
    
    def process_return(self, sale_id):
        """معالجة عملية المرتجع"""
        try:
            # جلب تفاصيل الفاتورة من قاعدة البيانات
            details = db.get_sale_details(sale_id)
            
            if not details:
                self.show_warning_toast("لا توجد تفاصيل للفاتورة")
                return
            
            # جلب المنتجات مع product_id
            import sqlite3
            from back.database import get_connection
            
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT si.product_id, p.name, si.quantity, si.price_at_sale
                FROM sale_items si
                JOIN products p ON si.product_id = p.id
                WHERE si.sale_id = ?
            ''', (sale_id,))
            items_with_ids = cursor.fetchall()
            conn.close()
            
            if not items_with_ids:
                self.show_warning_toast("لا توجد منتجات في هذه الفاتورة")
                return
            
            # حساب إجمالي الفاتورة والخصم من details
            total_amount = float(details[0][4]) if details and len(details[0]) > 4 and details[0][4] else 0
            discount = float(details[0][5]) if details and len(details[0]) > 5 and details[0][5] else 0
            
            sale_details = {
                'total': total_amount,
                'discount': discount
            }
            
            # تجهيز بيانات المنتجات
            sale_items_data = []
            for item in items_with_ids:
                sale_items_data.append({
                    'product_id': int(item[0]),
                    'name': str(item[1]),
                    'quantity': int(float(item[2])) if item[2] else 0,
                    'price': float(item[3]) if item[3] else 0
                })
            
            # فتح نافذة المرتجع
            dlg = SalesReturnForm(sale_id, sale_details, sale_items_data, self)
            
            if dlg.exec():
                items = dlg.get_return_items()
                
                if not items:
                    self.show_warning_toast("لم يتم اختيار أي منتجات للمرتجع")
                    return
                
                # التأكد من صحة البيانات
                valid_items = []
                for product_id, quantity, price in items:
                    if quantity > 0 and price >= 0:
                        valid_items.append((product_id, quantity, price))
                
                if not valid_items:
                    self.show_warning_toast("البيانات غير صالحة للمرتجع")
                    return
                
                reason = dlg.get_reason()
                
                # استدعاء دالة معالجة المرتجع
                success, msg = db.process_sales_return(sale_id, valid_items, reason, "Admin")
                
                if success:
                    self.show_success_toast(f"✅ {msg}")
                    self.load_sales()  # تحديث الجدول - الفاتورة المرتجعة ستختفي فوراً
                else:
                    self.show_warning_toast(f"❌ فشل تنفيذ المرتجع: {msg}")
                    
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ في معالجة المرتجع: {str(e)}")