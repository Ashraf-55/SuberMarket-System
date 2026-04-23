from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel, QMessageBox,
                             QPushButton, QDialog, QFormLayout, QComboBox, QSpinBox,
                             QLineEdit, QTextEdit, QFrame)
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer
from back import database as db
from PyQt6.QtGui import QFont, QColor

# ========== الألوان الموحدة ==========
COLORS = {
    'bg_dark': '#121212',
    'bg_card': '#1e1e2e',
    'text': '#e0e0e0',
    'text_muted': '#a0a0a0',
    'accent': '#00d4ff',
    'accent_dark': '#0099cc',
    'border': '#2d2d5c',
    'success': '#27ae60',
    'danger': '#c0392b',
    'danger_hover': '#a93226',
    'warning': '#d35400',
    'info': '#2980b9',
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


# ========== نافذة نقل مخزني محسنة ==========
class StockTransferDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("نقل مخزني")
        self.setModal(True)
        self.resize(600, 550)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
            }}
            QComboBox, QSpinBox, QLineEdit, QTextEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                min-height: 20px;
            }}
            QComboBox:focus, QSpinBox:focus, QLineEdit:focus, QTextEdit:focus {{
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
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: {COLORS['bg_card']};
                width: 20px;
                border: none;
            }}
            QTextEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # مجموعة معلومات المنتج
        product_group = QFrame()
        product_group.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 12px; padding: 10px; border: 1px solid {COLORS['border']}; }}")
        product_layout = QFormLayout(product_group)
        product_layout.setSpacing(10)
        
        self.product_combo = QComboBox()
        self.product_dict = {}  # product_id -> {'name': name, 'stock': stock}
        
        # تحميل المنتجات من قاعدة البيانات
        products = db.get_all_products()
        for product in products:
            # التعامل مع sqlite3.Row أو tuple
            if isinstance(product, (tuple, list)):
                product_id = product[0]
                name = product[1]
                stock = int(product[5]) if len(product) > 5 and product[5] else 0
            else:  # sqlite3.Row object
                product_id = product['id']
                name = product['name']
                stock = int(product['stock']) if product['stock'] else 0
            
            # عرض فقط المنتجات التي لها كمية في المخزون
            if stock > 0:
                self.product_combo.addItem(f"{name} (المتبقي: {stock})", product_id)
                self.product_dict[product_id] = {
                    'name': name,
                    'stock': stock
                }
        
        product_layout.addRow("المنتج:", self.product_combo)
        
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 9999)
        product_layout.addRow("الكمية:", self.quantity)
        
        layout.addWidget(product_group)
        
        # مجموعة معلومات النقل
        transfer_group = QFrame()
        transfer_group.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 12px; padding: 10px; border: 1px solid {COLORS['border']}; }}")
        transfer_layout = QFormLayout(transfer_group)
        transfer_layout.setSpacing(10)
        
        # قوائم المخازن - تم إزالة "فرع المهندسين" و "فرع الدقي"
        warehouses = ["المخزن الرئيسي", "المحل"]
        
        self.from_warehouse = QComboBox()
        self.from_warehouse.addItems(warehouses)
        transfer_layout.addRow("من مخزن:", self.from_warehouse)
        
        self.to_warehouse = QComboBox()
        self.to_warehouse.addItems(warehouses)
        transfer_layout.addRow("إلى مخزن:", self.to_warehouse)
        
        self.transfer_reason = QComboBox()
        self.transfer_reason.addItems(["توزيع مخزون", "نقل للبيع", "إعادة تخزين", "طلب فرع", "أخرى"])
        transfer_layout.addRow("سبب النقل:", self.transfer_reason)
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        self.notes.setPlaceholderText("ملاحظات عن عملية النقل...")
        transfer_layout.addRow("ملاحظات:", self.notes)
        
        layout.addWidget(transfer_group)
        
        # ربط الإشارات
        self.product_combo.currentIndexChanged.connect(self.update_max_quantity)
        self.update_max_quantity()  # تحديث القيمة الأولية
        
        # الأزرار
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        confirm_btn = QPushButton("✅ تأكيد النقل")
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                min-height: 45px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_dark']};
            }}
        """)
        confirm_btn.clicked.connect(self.accept)
        
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
        """إظهار رسالة منبثقة داخل النافذة"""
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_warning_toast(self, message):
        ToastMessage(self, message, COLORS['warning'])
    
    def update_max_quantity(self):
        """تحديث الحد الأقصى للكمية بناءً على المخزون المتاح"""
        product_id = self.product_combo.currentData()
        if product_id and product_id in self.product_dict:
            available_stock = self.product_dict[product_id]['stock']
            self.quantity.setMaximum(available_stock)
            self.quantity.setToolTip(f"الكمية المتاحة: {available_stock}")
        else:
            self.quantity.setMaximum(0)
    
    def get_data(self):
        """جمع البيانات من النموذج مع التأكد من تحويل الأنواع"""
        product_id = self.product_combo.currentData()
        
        if not product_id or product_id not in self.product_dict:
            return None
        
        product_info = self.product_dict[product_id]
        quantity = self.quantity.value()
        from_warehouse = self.from_warehouse.currentText()
        to_warehouse = self.to_warehouse.currentText()
        
        # التحقق من صحة البيانات
        if quantity <= 0:
            return None
        
        if quantity > product_info['stock']:
            return None
        
        return {
            'product_id': int(product_id),
            'product_name': str(product_info['name']),
            'quantity': int(quantity),
            'from_warehouse': str(from_warehouse),
            'to_warehouse': str(to_warehouse),
            'transfer_reason': str(self.transfer_reason.currentText()),
            'notes': str(self.notes.toPlainText())
        }


# ========== شاشة نقل مخزني محسنة ==========
class StockTransferWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("🚚 نقل مخزني")
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
                background-color: {COLORS['bg_card']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['accent']};
                padding: 12px;
                border: none;
                font-size: 13px;
                font-weight: bold;
            }}
            QTableCornerButton::section {{
                background-color: {COLORS['bg_card']};
                border: none;
            }}
        """)
        
        # الأعمدة: المنتج، التاريخ، الكمية، من مخزن، إلى مخزن، السبب، الإجراءات
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["المنتج", "التاريخ", "الكمية", "من مخزن", "إلى مخزن", "السبب", "الإجراءات"])
        
        # ضبط عرض الأعمدة
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 100)
        
        layout.addWidget(self.table)
        
        add_btn = QPushButton("➕ نقل جديد")
        add_btn.setFont(FONTS['button'])
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                padding: 14px 30px;
                border-radius: 10px;
                font-weight: bold;
                border: none;
                min-height: 45px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_dark']};
            }}
        """)
        add_btn.clicked.connect(self.add_transfer)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(add_btn)
        layout.addLayout(btn_layout)
        
        self.load_transfers()
    
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
    
    def load_transfers(self):
        """تحميل وعرض عمليات النقل المخزني في الجدول"""
        transfers = db.get_stock_transfers()
        self.table.setRowCount(len(transfers))
        
        for row, transfer in enumerate(transfers):
            self.table.setRowHeight(row, 55)
            
            # التعامل مع sqlite3.Row أو tuple للحصول على ID
            if isinstance(transfer, (tuple, list)):
                transfer_id = transfer[0]
                product_name = str(transfer[3]) if len(transfer) > 3 else "-"
                transfer_date = str(transfer[7])[:10] if len(transfer) > 7 and transfer[7] else "-"
                quantity = int(transfer[4]) if len(transfer) > 4 and transfer[4] else 0
                from_warehouse = str(transfer[5]) if len(transfer) > 5 else "-"
                to_warehouse = str(transfer[6]) if len(transfer) > 6 else "-"
                transfer_reason = str(transfer[8]) if len(transfer) > 8 and transfer[8] else "-"
            else:  # sqlite3.Row object
                transfer_id = transfer['id']
                product_name = str(transfer['product_name']) if transfer['product_name'] else "-"
                transfer_date = str(transfer['transfer_date'])[:10] if transfer['transfer_date'] else "-"
                quantity = int(transfer['quantity']) if transfer['quantity'] else 0
                from_warehouse = str(transfer['from_warehouse']) if transfer['from_warehouse'] else "-"
                to_warehouse = str(transfer['to_warehouse']) if transfer['to_warehouse'] else "-"
                transfer_reason = str(transfer['transfer_reason']) if transfer['transfer_reason'] else "-"
            
            # المنتج
            product_item = QTableWidgetItem(product_name)
            product_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, product_item)
            
            # التاريخ
            date_item = QTableWidgetItem(transfer_date)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, date_item)
            
            # الكمية
            qty_item = QTableWidgetItem(str(quantity))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, qty_item)
            
            # من مخزن
            from_item = QTableWidgetItem(from_warehouse)
            from_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, from_item)
            
            # إلى مخزن
            to_item = QTableWidgetItem(to_warehouse)
            to_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, to_item)
            
            # السبب
            reason_item = QTableWidgetItem(transfer_reason)
            reason_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, reason_item)
            
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
                QPushButton:pressed {{
                    background-color: #8b1a1a;
                }}
            """)
            delete_btn.clicked.connect(lambda checked, tid=transfer_id: self.delete_transfer(tid))
            
            # توسيط الزر داخل الخلية
            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.addStretch()
            container_layout.addWidget(delete_btn)
            container_layout.addStretch()
            
            self.table.setCellWidget(row, 6, container)
    
    def delete_transfer(self, transfer_id):
        """حذف عملية نقل مخزني"""
        try:
            # استدعاء دالة الحذف من قاعدة البيانات
            # ملاحظة: ستحتاج إلى إضافة دالة delete_stock_transfer في database.py
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stock_transfers WHERE id = ?", (transfer_id,))
            conn.commit()
            conn.close()
            
            self.show_success_toast(f"✅ تم حذف عملية النقل رقم {transfer_id} بنجاح")
            self.load_transfers()  # تحديث الجدول فوراً
            
        except Exception as e:
            self.show_warning_toast(f"❌ فشل حذف العملية: {str(e)}")
    
    def add_transfer(self):
        """إضافة عملية نقل مخزني جديدة"""
        dlg = StockTransferDialog(self)
        
        if dlg.exec():
            data = dlg.get_data()
            
            # التحقق من صحة البيانات
            if not data:
                dlg.show_warning_toast("⚠️ الرجاء اختيار منتج صحيح")
                return
            
            # التحقق من عدم النقل لنفس المخزن
            if data['from_warehouse'] == data['to_warehouse']:
                dlg.show_warning_toast("⚠️ لا يمكن النقل لنفس المخزن\nالرجاء اختيار مخازن مختلفة")
                return
            
            if data['quantity'] <= 0:
                dlg.show_warning_toast("⚠️ الكمية يجب أن تكون أكبر من صفر")
                return
            
            # التأكد من وجود الكمية الكافية في المخزون
            product_info = dlg.product_dict.get(data['product_id'])
            if product_info:
                available_stock = product_info.get('stock', 0)
                if data['quantity'] > available_stock:
                    dlg.show_warning_toast(f"⚠️ الكمية المطلوب نقلها ({data['quantity']}) تتجاوز الكمية المتاحة في المخزون ({available_stock})")
                    return
            
            # استدعاء دالة إضافة النقل المخزني من قاعدة البيانات
            success, msg = db.add_stock_transfer(
                product_id=data['product_id'],
                product_name=data['product_name'],
                quantity=data['quantity'],
                from_warehouse=data['from_warehouse'],
                to_warehouse=data['to_warehouse'],
                transfer_reason=data['transfer_reason'],
                transferred_by="Admin",
                notes=data['notes']
            )
            
            if success:
                self.show_success_toast(f"✅ {msg}")
                self.load_transfers()
            else:
                self.show_warning_toast(f"❌ {msg}")