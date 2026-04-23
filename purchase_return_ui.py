from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel, QMessageBox,
                             QPushButton, QDialog, QFormLayout, QComboBox, QSpinBox,
                             QDoubleSpinBox, QLineEdit, QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer
from back import database as db
from PyQt6.QtGui import QFont, QColor

# ========== الألوان الموحدة ==========
COLORS = {
    'bg_dark': '#121212',
    'bg_sidebar': '#1a1a2e',
    'bg_card': '#1e1e2e',
    'text': '#e0e0e0',
    'text_muted': '#a0a0a0',
    'accent': '#00d4ff',
    'accent_hover': '#0099cc',
    'success': '#27ae60',
    'success_hover': '#219a52',
    'danger': '#c0392b',
    'danger_hover': '#a93226',
    'warning': '#d35400',
    'warning_hover': '#ba4a00',
    'info': '#2980b9',
    'info_hover': '#1f618d',
    'border': '#2d2d5c',
    'add_btn': '#d35400',
    'add_btn_hover': '#ba4a00'
}

FONTS = {
    'title': QFont("Segoe UI", 24, QFont.Weight.Bold),
    'button': QFont("Segoe UI", 13, QFont.Weight.Medium),
    'table_header': QFont("Segoe UI", 12, QFont.Weight.Bold),
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
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()


# ========== نافذة مرتجع مشتريات محسنة ==========
class PurchaseReturnDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("مرتجع مشتريات")
        self.setModal(True)
        self.resize(600, 620)
        
        # ستايل النافذة بالكامل - Dark Theme
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
                font-weight: bold;
            }}
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                min-height: 20px;
            }}
            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
            }}
            QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background-color: {COLORS['bg_sidebar']};
                width: 20px;
                border: none;
            }}
            QTextEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # مجموعة معلومات المورد
        supplier_group = QFrame()
        supplier_group.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 12px; padding: 10px; border: 1px solid {COLORS['border']}; }}")
        supplier_layout = QFormLayout(supplier_group)
        supplier_layout.setSpacing(10)
        
        self.supplier_name = QLineEdit()
        self.supplier_name.setPlaceholderText("مثال: شركة توزيع الأغذية")
        supplier_layout.addRow("اسم المورد:", self.supplier_name)
        
        layout.addWidget(supplier_group)
        
        # مجموعة المنتج
        product_group = QFrame()
        product_group.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 12px; padding: 10px; border: 1px solid {COLORS['border']}; }}")
        product_layout = QFormLayout(product_group)
        product_layout.setSpacing(10)
        
        self.product_combo = QComboBox()
        self.product_dict = {}
        
        # تحميل المنتجات من قاعدة البيانات
        products = db.get_all_products()
        for product in products:
            if isinstance(product, (tuple, list)):
                product_id = product[0]
                name = product[1]
                purchase_price = float(product[3]) if len(product) > 3 and product[3] else 0.0
                stock = int(product[5]) if len(product) > 5 and product[5] else 0
            else:
                product_id = product['id']
                name = product['name']
                purchase_price = float(product['purchase_price']) if product['purchase_price'] else 0.0
                stock = int(product['stock']) if product['stock'] else 0
            
            self.product_combo.addItem(f"{name} (سعر الشراء: {purchase_price:,.2f} ج.م - المتوفر: {stock})", product_id)
            self.product_dict[product_id] = {
                'name': name, 
                'purchase_price': purchase_price,
                'stock': stock
            }
        
        product_layout.addRow("المنتج:", self.product_combo)
        
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 9999)
        product_layout.addRow("الكمية:", self.quantity)
        
        self.return_price = QDoubleSpinBox()
        self.return_price.setRange(0, 1000000)
        self.return_price.setPrefix("ج.م ")
        self.return_price.setDecimals(2)
        product_layout.addRow("سعر المرتجع للوحدة:", self.return_price)
        
        self.total_label = QLabel("الإجمالي: 0.00 ج.م")
        self.total_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['warning']}; padding: 10px;")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        product_layout.addRow("", self.total_label)
        
        layout.addWidget(product_group)
        
        # مجموعة السبب والملاحظات
        reason_group = QFrame()
        reason_group.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 12px; padding: 10px; border: 1px solid {COLORS['border']}; }}")
        reason_layout = QFormLayout(reason_group)
        reason_layout.setSpacing(10)
        
        self.return_reason = QComboBox()
        self.return_reason.addItems(["منتج تالف", "خطأ في الصنف", "جودة غير مطابقة", "انتهاء الصلاحية", "سعر غير صحيح", "أخرى"])
        reason_layout.addRow("سبب المرتجع:", self.return_reason)
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        self.notes.setPlaceholderText("ملاحظات عن المرتجع...")
        reason_layout.addRow("ملاحظات:", self.notes)
        
        layout.addWidget(reason_group)
        
        # ربط الإشارات
        self.product_combo.currentIndexChanged.connect(self.update_product_info)
        self.quantity.valueChanged.connect(self.update_total)
        self.return_price.valueChanged.connect(self.update_total)
        
        self.update_product_info()
        
        # الأزرار
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        confirm_btn = QPushButton("✅ تأكيد مرتجع الشراء")
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['add_btn']};
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                min-height: 45px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['add_btn_hover']};
            }}
        """)
        confirm_btn.clicked.connect(self.on_confirm)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #6c757d;
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                min-height: 45px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #5a6268;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(confirm_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
    
    def show_toast(self, message, is_success=True):
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_warning_toast(self, message):
        ToastMessage(self, message, COLORS['warning'])
    
    def update_product_info(self):
        product_id = self.product_combo.currentData()
        if product_id and product_id in self.product_dict:
            purchase_price = self.product_dict[product_id]['purchase_price']
            self.return_price.setValue(purchase_price)
            self.update_total()
    
    def update_total(self):
        quantity = self.quantity.value()
        price = self.return_price.value()
        total = quantity * price
        self.total_label.setText(f"الإجمالي: {total:,.2f} ج.م")
    
    def on_confirm(self):
        product_id = self.product_combo.currentData()
        
        if not product_id or product_id not in self.product_dict:
            self.show_warning_toast("⚠️ الرجاء اختيار منتج صحيح")
            return
        
        if not self.supplier_name.text().strip():
            self.show_warning_toast("⚠️ الرجاء إدخال اسم المورد")
            return
        
        if self.quantity.value() <= 0:
            self.show_warning_toast("⚠️ الكمية يجب أن تكون أكبر من صفر")
            return
        
        if self.return_price.value() <= 0:
            self.show_warning_toast("⚠️ سعر المرتجع يجب أن يكون أكبر من صفر")
            return
        
        self.accept()
    
    def get_data(self):
        product_id = self.product_combo.currentData()
        
        if not product_id or product_id not in self.product_dict:
            return None
        
        product_info = self.product_dict[product_id]
        quantity = self.quantity.value()
        return_price = self.return_price.value()
        
        if quantity <= 0 or return_price < 0:
            return None
        
        return {
            'supplier_name': self.supplier_name.text().strip(),
            'product_id': int(product_id),
            'product_name': str(product_info['name']),
            'quantity': int(quantity),
            'return_price': float(return_price),
            'return_reason': self.return_reason.currentText(),
            'notes': self.notes.toPlainText().strip()
        }


# ========== شاشة مرتجع مشتريات محسنة ==========
class PurchaseReturnWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("🔃 مرتجع مشتريات")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
        layout.addWidget(title)
        
        # جدول العرض المحسن
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
            QTableCornerButton::section {{
                background-color: {COLORS['bg_sidebar']};
                border: none;
            }}
        """)
        
        # الأعمدة: رقم المرتجع، التاريخ، المورد، المبلغ، السبب، الإجراءات
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["رقم المرتجع", "التاريخ", "المورد", "المبلغ", "السبب", "الإجراءات"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 100)
        
        layout.addWidget(self.table)
        
        add_btn = QPushButton("➕ مرتجع جديد")
        add_btn.setFont(FONTS['button'])
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['add_btn']};
                color: white;
                padding: 14px 30px;
                border-radius: 10px;
                font-weight: bold;
                border: none;
                min-height: 45px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['add_btn_hover']};
            }}
        """)
        add_btn.clicked.connect(self.add_return)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(add_btn)
        layout.addLayout(btn_layout)
        
        self.load_returns()
    
    # ========== دوال الـ Toast ==========
    def show_toast(self, message, is_success=True):
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_info_toast(self, message):
        ToastMessage(self, message, COLORS['info'])
    
    def show_warning_toast(self, message):
        ToastMessage(self, message, COLORS['warning'])
    
    def show_success_toast(self, message):
        ToastMessage(self, message, COLORS['success'])
    
    def load_returns(self):
        try:
            returns = db.get_purchase_returns()
            self.table.setRowCount(len(returns))
            
            for row, ret in enumerate(returns):
                self.table.setRowHeight(row, 55)
                
                if isinstance(ret, (tuple, list)):
                    return_id = ret[0]
                    return_number = str(ret[1]) if len(ret) > 1 else "-"
                    supplier_name = str(ret[2]) if len(ret) > 2 else "-"
                    return_date = str(ret[3])[:10] if len(ret) > 3 and ret[3] else "-"
                    total_amount = float(ret[4]) if len(ret) > 4 and ret[4] else 0.0
                    return_reason = str(ret[5]) if len(ret) > 5 and ret[5] else "-"
                else:
                    return_id = ret['id']
                    return_number = str(ret['return_number']) if ret['return_number'] else "-"
                    supplier_name = str(ret['supplier_name']) if ret['supplier_name'] else "-"
                    return_date = str(ret['return_date'])[:10] if ret['return_date'] else "-"
                    total_amount = float(ret['total_return_amount']) if ret['total_return_amount'] else 0.0
                    return_reason = str(ret['return_reason']) if ret['return_reason'] else "-"
                
                # رقم المرتجع
                number_item = QTableWidgetItem(return_number)
                number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, number_item)
                
                # التاريخ
                date_item = QTableWidgetItem(return_date)
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 1, date_item)
                
                # المورد
                supplier_item = QTableWidgetItem(supplier_name)
                supplier_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 2, supplier_item)
                
                # المبلغ
                amount_item = QTableWidgetItem(f"{total_amount:,.2f} ج.م")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                amount_item.setForeground(QColor(COLORS['warning']))
                amount_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                self.table.setItem(row, 3, amount_item)
                
                # السبب
                reason_item = QTableWidgetItem(return_reason)
                reason_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, reason_item)
                
                # زر الحذف
                delete_btn = QPushButton("🗑️ حذف")
                delete_btn.setFixedSize(80, 32)
                delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                delete_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['danger']};
                        color: white;
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['danger_hover']};
                    }}
                """)
                delete_btn.clicked.connect(lambda checked, rid=return_id: self.delete_return(rid))
                
                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                container_layout.addStretch()
                container_layout.addWidget(delete_btn)
                container_layout.addStretch()
                
                self.table.setCellWidget(row, 5, container)
                
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ في تحميل البيانات: {str(e)}")
    
    def delete_return(self, return_id):
        try:
            success, msg = db.delete_purchase_return(return_id)
            
            if success:
                self.show_success_toast(f"✅ {msg}")
                self.load_returns()
            else:
                self.show_warning_toast(f"❌ {msg}")
                
        except Exception as e:
            self.show_warning_toast(f"❌ فشل حذف المرتجع: {str(e)}")
    
    def add_return(self):
        dlg = PurchaseReturnDialog(self)
        
        if dlg.exec():
            data = dlg.get_data()
            
            if not data:
                dlg.show_warning_toast("⚠️ الرجاء اختيار منتج صحيح")
                return
            
            if not data['supplier_name']:
                dlg.show_warning_toast("⚠️ الرجاء إدخال اسم المورد")
                return
            
            if data['quantity'] <= 0:
                dlg.show_warning_toast("⚠️ الكمية يجب أن تكون أكبر من صفر")
                return
            
            if data['return_price'] <= 0:
                dlg.show_warning_toast("⚠️ سعر المرتجع يجب أن يكون أكبر من صفر")
                return
            
            items = [(
                data['product_id'],
                data['product_name'],
                data['quantity'],
                data['return_price']
            )]
            
            success, msg = db.add_purchase_return(
                supplier_name=data['supplier_name'],
                return_items_list=items,
                return_reason=data['return_reason'],
                processed_by="Admin",
                notes=data['notes']
            )
            
            if success:
                self.show_success_toast(f"✅ {msg}")
                self.load_returns()
            else:
                self.show_warning_toast(f"❌ {msg}")