# ================= ملف damaged_ui.py بعد التعديل النهائي =================

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel,
                             QPushButton, QDialog, QFormLayout, QComboBox,
                             QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit)
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
    'success': '#27ae60',
    'success_hover': '#219a52',
    'danger': '#c0392b',
    'danger_hover': '#a93226',
    'warning': '#d35400',
    'warning_hover': '#ba4a00',
    'info': '#2980b9',
    'info_hover': '#1f618d',
    'border': '#2d2d5c',
    'delete_btn': '#c0392b',
    'delete_btn_hover': '#a93226',
    'add_btn': '#c0392b',
    'add_btn_hover': '#a93226'
}

FONTS = {
    'title': QFont("Segoe UI", 24, QFont.Weight.Bold),
    'button': QFont("Segoe UI", 13, QFont.Weight.Medium),
    'table': QFont("Segoe UI", 12),
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


# ========== نافذة إضافة تالف جديد ==========
class AddDamagedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("تسجيل منتج تالف")
        self.setModal(True)
        self.resize(600, 550)
        self.setMinimumSize(500, 500)
        
        # ستايل النافذة بالكامل
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
                font-weight: bold;
            }}
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                min-height: 25px;
            }}
            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
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
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # عنوان
        title_label = QLabel("⚠️ تسجيل منتج تالف")
        title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['danger']}; padding: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # حاوية معلومات المنتج
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(10, 10, 10, 10)
        
        self.product_combo = QComboBox()
        self.product_dict = {}  # product_id -> {'name': name, 'price': sell_price, 'stock': stock}
        
        products = db.get_all_products()
        for product in products:
            if isinstance(product, (tuple, list)):
                product_id = product[0]
                name = product[1]
                stock = product[5] if len(product) > 5 else 0
                sell_price = product[4] if len(product) > 4 else 0
            else:
                product_id = product['id']
                name = product['name']
                stock = product['stock']
                sell_price = product['sell_price']
            
            if stock > 0:
                self.product_combo.addItem(f"{name} (المتبقي: {stock})", product_id)
                self.product_dict[product_id] = {
                    'name': name, 
                    'price': float(sell_price) if sell_price else 0.0,
                    'stock': int(stock) if stock else 0
                }
        
        # تنسيق الـ ComboBox
        self.product_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                min-height: 35px;
            }}
        """)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 9999)
        self.quantity_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                min-height: 35px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {COLORS['bg_sidebar']};
                width: 20px;
            }}
        """)
        
        self.damage_reason = QComboBox()
        self.damage_reason.addItems(["انتهاء الصلاحية", "تلف في التبريد", "كسر", "تلف أثناء النقل", "عيوب تصنيع", "أخرى"])
        self.damage_reason.setStyleSheet(self.product_combo.styleSheet())
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(100)
        self.notes.setPlaceholderText("ملاحظات إضافية...")
        
        form_layout.addRow("📦 المنتج:", self.product_combo)
        form_layout.addRow("🔢 الكمية التالفة:", self.quantity_spin)
        form_layout.addRow("📋 سبب التلف:", self.damage_reason)
        form_layout.addRow("📝 ملاحظات:", self.notes)
        
        # قيمة الخسارة
        loss_frame = QWidget()
        loss_layout = QHBoxLayout(loss_frame)
        loss_layout.setContentsMargins(0, 10, 0, 10)
        
        loss_label = QLabel("💸 قيمة الخسارة المتوقعة:")
        loss_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text']};")
        loss_layout.addWidget(loss_label)
        
        self.loss_amount = QLabel("0.00 ج.م")
        self.loss_amount.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['danger']}; padding: 5px;")
        self.loss_amount.setAlignment(Qt.AlignmentFlag.AlignRight)
        loss_layout.addStretch()
        loss_layout.addWidget(self.loss_amount)
        
        form_layout.addRow(loss_frame)
        
        layout.addWidget(form_widget)
        
        # ربط الإشارات لتحديث قيمة الخسارة
        self.product_combo.currentIndexChanged.connect(self.update_loss)
        self.quantity_spin.valueChanged.connect(self.update_loss)
        
        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        save_btn = QPushButton("⚠️ تسجيل التالف")
        save_btn.setStyleSheet(f"""
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
            QPushButton:pressed {{
                background-color: #8b1a1a;
            }}
        """)
        save_btn.clicked.connect(self.on_confirm)
        
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
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
    
    def show_toast(self, message, is_success=True):
        """إظهار رسالة منبثقة داخل النافذة"""
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_warning_toast(self, message):
        ToastMessage(self, message, COLORS['warning'])
    
    def update_loss(self):
        """تحديث قيمة الخسارة بناءً على المنتج والكمية المختارة"""
        product_id = self.product_combo.currentData()
        if product_id and product_id in self.product_dict:
            price = self.product_dict[product_id]['price']
            qty = self.quantity_spin.value()
            loss = float(price) * float(qty)
            self.loss_amount.setText(f"{loss:,.2f} ج.م")
        else:
            self.loss_amount.setText("0.00 ج.م")
    
    def on_confirm(self):
        """التحقق من صحة البيانات والحفظ"""
        product_id = self.product_combo.currentData()
        
        if not product_id or product_id not in self.product_dict:
            self.show_warning_toast("⚠️ الرجاء اختيار منتج صحيح")
            return
        
        if self.quantity_spin.value() <= 0:
            self.show_warning_toast("⚠️ الرجاء إدخال كمية صالحة (أكبر من صفر)")
            return
        
        product_info = self.product_dict[product_id]
        max_qty = product_info['stock']
        qty = self.quantity_spin.value()
        
        if qty > max_qty:
            self.show_warning_toast(f"⚠️ الكمية المطلوبة ({qty}) تتجاوز المتوفر في المخزون ({max_qty})")
            return
        
        self.accept()
    
    def get_data(self):
        """جمع البيانات من النموذج"""
        product_id = self.product_combo.currentData()
        
        if not product_id or product_id not in self.product_dict:
            return None
        
        product_info = self.product_dict[product_id]
        quantity = self.quantity_spin.value()
        price = product_info['price']
        
        loss_amount = float(price) * float(quantity)
        
        return {
            'product_id': int(product_id),
            'product_name': str(product_info['name']),
            'quantity': int(quantity),
            'damage_reason': str(self.damage_reason.currentText()),
            'loss_amount': loss_amount,
            'notes': str(self.notes.toPlainText())
        }


# ========== شاشة تالف / هالك ==========
class DamagedGoodsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # عنوان
        title = QLabel("⚠️ تالف / هالك")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
        layout.addWidget(title)
        
        # معلومات توضيحية
        info_label = QLabel("ℹ️ سجل المنتجات التالفة أو المنتهية الصلاحية لخصمها من المخزون")
        info_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 13px; padding: 12px; background-color: {COLORS['bg_card']}; border-radius: 10px;")
        layout.addWidget(info_label)
        
        # ========== جدول المنتجات التالفة ==========
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
            QTableCornerButton::section {{
                background-color: {COLORS['bg_sidebar']};
                border: none;
            }}
        """)
        
        # الأعمدة: المعرف، الاسم، الكمية، السبب، مبلغ الخسارة، التاريخ، المسؤول، الإجراءات
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "المنتج", "الكمية", "السبب", "مبلغ الخسارة", "التاريخ", "المسؤول", "الإجراءات"])
        
        # ضبط عرض الأعمدة
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # المنتج
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # الكمية
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # السبب
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # مبلغ الخسارة
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # التاريخ
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # المسؤول
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # الإجراءات
        self.table.setColumnWidth(7, 100)
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # زر إضافة
        add_btn = QPushButton("➕ تسجيل تالف")
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
            QPushButton:pressed {{
                background-color: #8b1a1a;
            }}
        """)
        add_btn.clicked.connect(self.add_damaged)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.load_damaged()
    
    # ========== دوال الـ Toast ==========
    def show_toast(self, message, is_success=True):
        """إظهار رسالة منبثقة"""
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_info_toast(self, message):
        ToastMessage(self, message, COLORS['info'])
    
    def show_warning_toast(self, message):
        ToastMessage(self, message, COLORS['warning'])
    
    def show_success_toast(self, message):
        ToastMessage(self, message, COLORS['success'])
    
    def load_damaged(self):
        """تحميل وعرض المنتجات التالفة في الجدول"""
        try:
            damaged_items = db.get_damaged_products()
            self.table.setRowCount(len(damaged_items))
            
            for row, item in enumerate(damaged_items):
                self.table.setRowHeight(row, 55)
                
                # التعامل مع sqlite3.Row object أو tuple
                if isinstance(item, (tuple, list)):
                    damaged_id = item[0]
                    product_id = item[1]
                    product_name = item[2]
                    quantity = item[3]
                    damage_reason = item[5] if len(item) > 5 else ""
                    loss_amount = float(item[6]) if len(item) > 6 and item[6] else 0.0
                    damage_date = item[7] if len(item) > 7 else ""
                    reported_by = item[9] if len(item) > 9 else "-"
                else:
                    damaged_id = item['id']
                    product_id = item['product_id']
                    product_name = item['product_name']
                    quantity = item['quantity']
                    damage_reason = item['damage_reason'] if item['damage_reason'] else "-"
                    loss_amount = float(item['loss_amount']) if item['loss_amount'] else 0.0
                    damage_date = item['damage_date'] if item['damage_date'] else "-"
                    reported_by = item['reported_by'] if item['reported_by'] else "-"
                
                # ID
                id_item = QTableWidgetItem(str(damaged_id))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, id_item)
                
                # المنتج
                product_item = QTableWidgetItem(str(product_name))
                product_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 1, product_item)
                
                # الكمية
                qty_item = QTableWidgetItem(str(int(quantity)) if quantity else "0")
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 2, qty_item)
                
                # السبب
                reason_item = QTableWidgetItem(str(damage_reason))
                reason_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 3, reason_item)
                
                # مبلغ الخسارة
                loss_item = QTableWidgetItem(f"{loss_amount:,.2f} ج.م")
                loss_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                loss_item.setForeground(QColor(COLORS['danger']))
                loss_item.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                self.table.setItem(row, 4, loss_item)
                
                # التاريخ
                date_str = str(damage_date)[:10] if damage_date and damage_date != "-" else "-"
                date_item = QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 5, date_item)
                
                # المسؤول
                responsible_item = QTableWidgetItem(str(reported_by) if reported_by and reported_by != "-" else "غير محدد")
                responsible_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 6, responsible_item)
                
                # زر الحذف
                btn_delete = QPushButton("🗑️ حذف")
                btn_delete.setFixedSize(85, 35)
                btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_delete.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['delete_btn']};
                        color: white;
                        border-radius: 6px;
                        font-size: 12px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['delete_btn_hover']};
                    }}
                    QPushButton:pressed {{
                        background-color: #8b1a1a;
                    }}
                """)
                btn_delete.clicked.connect(lambda checked, did=damaged_id: self.delete_damaged_entry(did))
                
                # توسيط الزر داخل الخلية
                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                container_layout.addStretch()
                container_layout.addWidget(btn_delete)
                container_layout.addStretch()
                
                self.table.setCellWidget(row, 7, container)
                
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ في تحميل البيانات: {str(e)}")
    
    def add_damaged(self):
        """إضافة منتج تالف جديد"""
        dlg = AddDamagedDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            
            if not data:
                self.show_warning_toast("⚠️ الرجاء اختيار منتج صحيح")
                return
            
            # استدعاء دالة إضافة المنتج التالف
            success, msg = db.add_damaged_product(
                product_id=data['product_id'],
                product_name=data['product_name'],
                quantity=data['quantity'],
                damage_reason=data['damage_reason'],
                loss_amount=data['loss_amount'],
                reported_by="Admin",
                notes=data['notes']
            )
            
            if success:
                self.show_success_toast(f"✅ {msg}")
                self.load_damaged()
            else:
                self.show_warning_toast(f"❌ {msg}")
    
    def delete_damaged_entry(self, damaged_id):
        """حذف سجل منتج تالف"""
        success, msg = db.delete_damaged_entry(damaged_id)
        
        if success:
            self.show_success_toast(f"✅ {msg}")
            self.load_damaged()
        else:
            self.show_warning_toast(f"❌ {msg}")