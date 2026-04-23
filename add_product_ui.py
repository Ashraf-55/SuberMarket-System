"""
نافذة إدارة المنتجات - تدعم إضافة وتعديل وحذف المنتجات
مع توحيد الهوية البصرية ونظام الـ Toast واختصارات لوحة المفاتيح
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QComboBox, QFrame)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QPropertyAnimation, QTimer
from back.database import add_product, get_all_products, update_product, delete_product

# ========== الألوان الموحدة (مطابقة مع pos_ui.py) ==========
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
    'border': '#2d2d5c'
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


class AddProductWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_product_id = None
        self.init_ui()

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
        """إظهار رسالة نجاح"""
        ToastMessage(self, message, COLORS['success'])

    def init_ui(self):
        # خلفية داكنة
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ========== الفورم الأيمن ==========
        form_frame = QFrame()
        form_frame.setFixedWidth(400)
        form_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(25, 25, 25, 25)
        
        self.label_title = QLabel("➕ إضافة منتج جديد")
        self.label_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['accent']};")
        form_layout.addWidget(self.label_title)
        
        form_layout.addSpacing(10)
        
        # حقول الإدخال
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم المنتج")
        
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("الباركود")
        
        self.purchase_input = QLineEdit()
        self.purchase_input.setPlaceholderText("سعر الجملة")
        
        self.sell_input = QLineEdit()
        self.sell_input.setPlaceholderText("سعر البيع")
        
        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("الكمية")
        
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["عام", "أغذية", "منظفات", "مشروبات", "مجمدات", "خضروات", "فواكه", "لحوم"])
        
        # ستايل الحقول
        style_input = f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                min-height: 20px;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
                font-weight: bold;
            }}
        """
        
        for inp in [self.name_input, self.barcode_input, self.purchase_input, self.sell_input, self.stock_input]:
            inp.setStyleSheet(style_input)
            # ✅ إضافة اختصار Enter لكل حقل إدخال
            inp.returnPressed.connect(self.save_handle)
        
        self.cat_combo.setStyleSheet(style_input)
        
        # إضافة الحقول للفورم مع labels
        name_label = QLabel("اسم المنتج")
        name_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: bold;")
        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)
        
        barcode_label = QLabel("الباركود")
        barcode_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: bold;")
        form_layout.addWidget(barcode_label)
        form_layout.addWidget(self.barcode_input)
        
        purchase_label = QLabel("سعر الجملة")
        purchase_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: bold;")
        form_layout.addWidget(purchase_label)
        form_layout.addWidget(self.purchase_input)
        
        sell_label = QLabel("سعر البيع")
        sell_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: bold;")
        form_layout.addWidget(sell_label)
        form_layout.addWidget(self.sell_input)
        
        stock_label = QLabel("الكمية")
        stock_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: bold;")
        form_layout.addWidget(stock_label)
        form_layout.addWidget(self.stock_input)
        
        cat_label = QLabel("التصنيف")
        cat_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; font-weight: bold;")
        form_layout.addWidget(cat_label)
        form_layout.addWidget(self.cat_combo)
        
        form_layout.addSpacing(20)
        
        # الأزرار
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_save = QPushButton("💾 حفظ")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                padding: 12px;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                min-height: 45px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
        """)
        self.btn_save.clicked.connect(self.save_handle)
        
        # ✅ جعل زر الحفظ هو الزر الافتراضي في النافذة
        self.btn_save.setDefault(True)
        
        self.btn_clear = QPushButton("🗑️ تفريغ")
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 12px;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                min-height: 45px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {COLORS['danger_hover']}; }}
        """)
        self.btn_clear.clicked.connect(self.clear_fields)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_clear)
        form_layout.addLayout(btn_layout)
        form_layout.addStretch()
        
        main_layout.addWidget(form_frame)
        
        # ========== الجدول الأيسر ==========
        table_frame = QFrame()
        table_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)
        
        table_title = QLabel("📋 قائمة المنتجات")
        table_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']}; padding: 15px; background-color: {COLORS['bg_sidebar']}; border-top-left-radius: 15px; border-top-right-radius: 15px;")
        table_layout.addWidget(table_title)
        
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "المنتج", "الباركود", "سعر البيع", "المخزن", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(False)  # ✅ إلغاء الألوان المتبادلة
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: none;
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
                min-height: 45px;
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['bg_sidebar']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        
        # تعيين ارتفاع الصفوف
        self.table.verticalHeader().setDefaultSectionSize(55)
        
        self.table.cellClicked.connect(self.load_to_form)
        table_layout.addWidget(self.table)
        main_layout.addWidget(table_frame)
        
        self.load_data()

    def load_data(self):
        """تحميل البيانات في الجدول (تحديث تلقائي)"""
        self.table.setRowCount(0)
        products = get_all_products()
        
        for p in products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 55)
            
            # p[0]=id, p[1]=name, p[2]=barcode, p[3]=purchase_price, p[4]=selling_price, p[5]=stock, p[6]=category
            id_item = QTableWidgetItem(str(p[0]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)
            
            name_item = QTableWidgetItem(p[1])
            self.table.setItem(row, 1, name_item)
            
            barcode_item = QTableWidgetItem(p[2])
            barcode_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, barcode_item)
            
            price_item = QTableWidgetItem(f"{p[4]:.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self.table.setItem(row, 3, price_item)
            
            # تلوين المخزون
            stock_item = QTableWidgetItem(str(p[5]))
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if p[5] <= 5:
                stock_item.setForeground(QColor(231, 76, 60))  # أحمر
            elif p[5] <= 10:
                stock_item.setForeground(QColor(241, 196, 15))  # أصفر
            else:
                stock_item.setForeground(QColor(46, 204, 113))  # أخضر
            self.table.setItem(row, 4, stock_item)
            
            # ✅ زر الحذف - مصغر ومتوسط داخل الخلية
            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            btn_del = QPushButton("🗑️ حذف")
            btn_del.setFixedSize(80, 32)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['danger']};
                    color: white;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{ background-color: {COLORS['danger_hover']}; }}
            """)
            btn_del.clicked.connect(lambda ch, id=p[0]: self.delete_handle(id))
            
            container_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 5, container)

    def load_to_form(self, row, col):
        """تحميل بيانات المنتج للتعديل"""
        p_id = int(self.table.item(row, 0).text())
        products = get_all_products()
        product = next((p for p in products if p[0] == p_id), None)
        
        if product:
            self.current_product_id = product[0]
            self.name_input.setText(product[1])
            self.barcode_input.setText(product[2])
            self.purchase_input.setText(str(product[3]))
            self.sell_input.setText(str(product[4]))
            self.stock_input.setText(str(product[5]))
            self.cat_combo.setCurrentText(product[6])
            self.btn_save.setText("✏️ تحديث")
            self.label_title.setText("✏️ تعديل منتج")
            self.btn_save.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: white;
                    padding: 12px;
                    border-radius: 8px;
                    font-weight: bold;
                    border: none;
                    min-height: 45px;
                    font-size: 14px;
                }}
                QPushButton:hover {{ background-color: {COLORS['warning_hover']}; }}
            """)

    def save_handle(self):
        """حفظ المنتج - يتم استدعاؤها من زر الحفظ أو من ضغط Enter"""
        name = self.name_input.text().strip()
        barcode = self.barcode_input.text().strip()
        
        try:
            purchase = float(self.purchase_input.text()) if self.purchase_input.text() else 0
            sell = float(self.sell_input.text()) if self.sell_input.text() else 0
            stock = int(self.stock_input.text()) if self.stock_input.text() else 0
            category = self.cat_combo.currentText()
            
            if not name:
                self.show_warning_toast("⚠️ يرجى إدخال اسم المنتج")
                return
            
            if self.current_product_id:
                success, msg = update_product(self.current_product_id, name, barcode, purchase, sell, stock, category)
            else:
                success, msg = add_product(name, barcode, purchase, sell, stock, category)
            
            if success:
                self.load_data()
                self.clear_fields()
                self.show_success_toast(f"✅ {msg}")
            else:
                self.show_warning_toast(f"⚠️ {msg}")
                
        except ValueError:
            self.show_warning_toast("❌ تأكد من إدخال أرقام صحيحة")

    def delete_handle(self, p_id):
        """حذف منتج - بدون QMessageBox"""
        success, msg = delete_product(p_id)
        if success:
            self.load_data()
            self.clear_fields()
            self.show_success_toast(f"✅ {msg}")
        else:
            self.show_warning_toast(f"⚠️ {msg}")

    def clear_fields(self):
        """تفريغ الحقول"""
        self.current_product_id = None
        self.name_input.clear()
        self.barcode_input.clear()
        self.purchase_input.clear()
        self.sell_input.clear()
        self.stock_input.clear()
        self.cat_combo.setCurrentIndex(0)
        self.btn_save.setText("💾 حفظ")
        self.label_title.setText("➕ إضافة منتج جديد")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                padding: 12px;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                min-height: 45px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
        """)