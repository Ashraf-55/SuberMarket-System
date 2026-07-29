# ================= damaged_ui.py - نظام إدارة البضائع التالفة المتطور (نسخة مصححة نهائياً) =================
"""
📡 نظام إدارة البضائع التالفة والهالك مع حساب تكلفة الخسارة الفورية
📌 تعمل فقط مع قاعدة البيانات الفعلية - لا توجد بيانات افتراضية
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel,
                             QPushButton, QDialog, QFormLayout, QComboBox,
                             QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit,
                             QFrame, QScrollArea, QGroupBox, QSplitter,
                             QApplication)
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QColor, QBrush

from datetime import datetime
import logging

# ========== استيراد قاعدة البيانات ==========
from back import database as db

logger = logging.getLogger(__name__)

# ========== الألوان الموحدة ==========
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
    'delete_btn': '#dc2626',
    'delete_btn_hover': '#b91c1c',
    'add_btn': '#dc2626',
    'add_btn_hover': '#b91c1c'
}

FONTS = {
    'title': QFont("Segoe UI", 20, QFont.Bold),
    'button': QFont("Segoe UI", 12, QFont.Medium),
    'table': QFont("Segoe UI", 11),
}


class ToastMessage(QLabel):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    
    TOAST_ICONS = {
        SUCCESS: '✅ ',
        WARNING: '⚠️ ',
        ERROR: '❌ ',
        INFO: 'ℹ️ '
    }
    
    def __init__(self, parent, message, toast_type=SUCCESS, duration=2500):
        icon = self.TOAST_ICONS.get(toast_type, self.TOAST_ICONS[self.SUCCESS])
        formatted_message = f"{icon} {message}"
        
        super().__init__(formatted_message, parent)
        self.duration = duration
        self.setFont(QFont("Segoe UI", 11, QFont.Medium))
        
        toast_color = COLORS['bg_card']
        border_color = COLORS['accent']
        
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
        
        parent_width = parent.width()
        self.adjustSize()
        
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry() if screen else None
        if screen_geometry:
            self.setFixedWidth(min(350, screen_geometry.width() - 40))
        else:
            self.setFixedWidth(min(350, parent_width - 40))
        
        x = (parent_width - self.width()) // 2
        y = parent.height() - 80
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


class AddDamagedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("تسجيل منتج تالف")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.4)
        height = int(screen_geometry.height() * 0.65)
        self.setMinimumSize(int(screen_geometry.width() * 0.35), int(screen_geometry.height() * 0.5))
        self.resize(max(500, width), max(500, height))
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border-radius: 15px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 12px;
                font-weight: bold;
            }}
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                min-height: 36px;
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
            QTextEdit {{
                min-height: 60px;
            }}
            QTextEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
            QGroupBox {{
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                margin-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: {COLORS['danger']};
            }}
        """)
        
        # ====== تعديل الريسبونسيف: تغليف المحتوى بـ ScrollArea ======
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(25, 25, 25, 25)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("⚠️ تسجيل منتج تالف")
        title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['danger']};")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        product_group = QGroupBox(" معلومات المنتج ")
        product_layout = QFormLayout(product_group)
        product_layout.setSpacing(12)
        
        self.product_combo = QComboBox()
        self.product_dict = {}
        self.load_products()
        
        product_layout.addRow("📦 المنتج:", self.product_combo)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 9999)
        self.quantity_spin.setMinimumHeight(36)
        self.quantity_spin.valueChanged.connect(self.update_loss)
        product_layout.addRow("🔢 الكمية التالفة:", self.quantity_spin)
        
        layout.addWidget(product_group)
        
        damage_group = QGroupBox(" معلومات التلف ")
        damage_layout = QFormLayout(damage_group)
        damage_layout.setSpacing(12)
        
        self.damage_reason = QComboBox()
        self.damage_reason.addItems(["انتهاء الصلاحية", "تلف في التبريد", "كسر", 
                                     "تلف أثناء النقل", "عيوب تصنيع", "أخرى"])
        damage_layout.addRow("📋 سبب التلف:", self.damage_reason)
        
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("ملاحظات إضافية عن التلف...")
        damage_layout.addRow("📝 ملاحظات:", self.notes)
        
        layout.addWidget(damage_group)
        
        loss_group = QGroupBox(" 💰 تكلفة الخسارة ")
        loss_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text']};
                border: 2px solid {COLORS['danger']};
                border-radius: 10px;
                margin-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: {COLORS['danger']};
            }}
        """)
        
        loss_layout = QFormLayout(loss_group)
        loss_layout.setSpacing(12)
        
        self.purchase_price_label = QLabel("0.00 ج.م")
        self.purchase_price_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-size: 14px;
            font-weight: bold;
        """)
        loss_layout.addRow("💵 سعر الشراء للوحدة:", self.purchase_price_label)
        
        self.loss_amount_label = QLabel("0.00 ج.م")
        self.loss_amount_label.setStyleSheet(f"""
            color: {COLORS['danger']};
            font-size: 18px;
            font-weight: bold;
            background-color: rgba(239, 68, 68, 0.1);
            padding: 5px 10px;
            border-radius: 8px;
        """)
        loss_layout.addRow("💸 إجمالي تكلفة الخسارة:", self.loss_amount_label)
        
        layout.addWidget(loss_group)
        
        self.product_combo.currentIndexChanged.connect(self.update_loss)
        self.update_loss()
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        save_btn = QPushButton("⚠️ تسجيل التالف")
        save_btn.setMinimumHeight(45)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['add_btn']};
                color: white;
                padding: 10px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['add_btn_hover']};
            }}
        """)
        save_btn.clicked.connect(self.on_confirm)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setMinimumHeight(45)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['border']};
                color: white;
                padding: 10px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border_light']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
    
    def load_products(self):
        self.product_combo.clear()
        self.product_dict = {}
        try:
            products = db.get_all_products()
            for product in products:
                stock = product.get('stock', 0)
                if stock > 0:
                    self.product_combo.addItem(
                        f"{product.get('name', '')} (المتبقي: {stock})", 
                        product.get('id')
                    )
                    self.product_dict[product.get('id')] = {
                        'name': product.get('name', ''),
                        'stock': stock,
                        'purchase_price': product.get('purchase_price', 0)
                    }
        except Exception as e:
            logger.error(f"خطأ في تحميل المنتجات: {e}", exc_info=True)
    
    def show_toast(self, message, toast_type=ToastMessage.SUCCESS, duration=2500):
        ToastMessage(self, message, toast_type, duration)
    
    def show_warning_toast(self, message):
        self.show_toast(message, ToastMessage.WARNING)
    
    def show_success_toast(self, message):
        self.show_toast(message, ToastMessage.SUCCESS)
    
    def update_loss(self):
        product_id = self.product_combo.currentData()
        if product_id and product_id in self.product_dict:
            price = self.product_dict[product_id]['purchase_price']
            qty = self.quantity_spin.value()
            loss = float(price) * float(qty)
            
            self.purchase_price_label.setText(f"{price:,.2f} ج.م")
            self.loss_amount_label.setText(f"{loss:,.2f} ج.م")
        else:
            self.purchase_price_label.setText("0.00 ج.م")
            self.loss_amount_label.setText("0.00 ج.م")
    
    def on_confirm(self):
        """
        معالج الضغط على زر تسجيل التالف
        """
        try:
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
            
            loss = float(product_info['purchase_price']) * float(qty)
            
            confirm_msg = (
                f"⚠️ سيتم خصم {qty} {product_info['name']} من المخزون\n"
                f"💸 قيمة الخسارة: {loss:,.2f} ج.م"
            )
            
            self.show_toast(confirm_msg, ToastMessage.WARNING, 3000)
            
            QTimer.singleShot(1500, self.accept)
            
        except Exception as e:
            logger.error(f"خطأ في on_confirm: {e}", exc_info=True)
            self.show_warning_toast(f"❌ حدث خطأ: {str(e)}")
    
    def get_data(self):
        product_id = self.product_combo.currentData()
        
        if not product_id or product_id not in self.product_dict:
            return None
        
        product_info = self.product_dict[product_id]
        quantity = self.quantity_spin.value()
        price = product_info['purchase_price']
        
        loss_amount = float(price) * float(quantity)
        
        return {
            'product_id': int(product_id),
            'product_name': str(product_info['name']),
            'quantity': int(quantity),
            'damage_reason': str(self.damage_reason.currentText()),
            'loss_amount': loss_amount,
            'notes': str(self.notes.toPlainText())
        }


class DamagedGoodsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.damaged_items = []
        self.damaged_counter = 1
        self.init_ui()
        self.load_damaged()
    
    def show_toast(self, message, toast_type=ToastMessage.SUCCESS, duration=2500):
        ToastMessage(self, message, toast_type, duration)
    
    def show_success_toast(self, message):
        self.show_toast(message, ToastMessage.SUCCESS)
    
    def show_warning_toast(self, message):
        self.show_toast(message, ToastMessage.WARNING)
    
    def show_info_toast(self, message):
        self.show_toast(message, ToastMessage.INFO)
    
    def show_error_toast(self, message):
        self.show_toast(message, ToastMessage.ERROR)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
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
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("⚠️ تالف / هالك")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['text']}; padding: 8px;")
        top_layout.addWidget(title)
        
        info_label = QLabel("ℹ️ سجل المنتجات التالفة أو المنتهية الصلاحية لخصمها من المخزون وحساب الخسائر")
        info_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px; padding: 10px; background-color: {COLORS['bg_card']}; border-radius: 10px; border: 1px solid {COLORS['border']};")
        info_label.setWordWrap(True)
        top_layout.addWidget(info_label)
        
        top_widget.setMinimumHeight(100)
        main_splitter.addWidget(top_widget)
        
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_frame = QFrame()
        btn_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
                padding: 8px;
            }}
        """)
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setSpacing(12)
        
        add_btn = QPushButton("➕ تسجيل تالف")
        add_btn.setMinimumHeight(38)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['add_btn']};
                color: white;
                padding: 8px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['add_btn_hover']};
            }}
        """)
        add_btn.clicked.connect(self.add_damaged)
        btn_layout.addWidget(add_btn)
        
        btn_layout.addStretch()
        
        clear_btn = QPushButton("🗑️ تصفير الجدول")
        clear_btn.setMinimumHeight(38)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 8px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        clear_btn.clicked.connect(self.clear_table)
        btn_layout.addWidget(clear_btn)
        
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setMinimumHeight(38)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                padding: 8px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        refresh_btn.clicked.connect(self.load_damaged)
        btn_layout.addWidget(refresh_btn)
        
        bottom_layout.addWidget(btn_frame)
        
        table_container = QScrollArea()
        table_container.setWidgetResizable(True)
        table_container.setStyleSheet("border: none; background-color: transparent;")
        
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(239, 68, 68, 0.2);
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 10px;
                border: none;
                font-size: 11px;
                font-weight: bold;
            }}
            QTableCornerButton::section {{
                background-color: {COLORS['bg_sidebar']};
                border: none;
            }}
        """)
        
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "المنتج", "الكمية", "السبب", "مبلغ الخسارة", 
            "التاريخ", "المسؤول", "الإجراءات"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 90)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        
        table_container.setWidget(self.table)
        bottom_layout.addWidget(table_container, stretch=1)
        
        bottom_widget.setMinimumHeight(200)
        main_splitter.addWidget(bottom_widget)
        
        main_splitter.setSizes([120, 480])
        layout.addWidget(main_splitter)
        
        self.load_damaged()
    
    def load_damaged(self):
        try:
            self.damaged_items = db.get_all_damaged()
            self.table.setRowCount(len(self.damaged_items))
            
            total_loss = 0
            
            for row, item in enumerate(self.damaged_items):
                self.table.setRowHeight(row, 45)
                
                id_item = QTableWidgetItem(str(item.get('id', '')))
                id_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, id_item)
                
                product_item = QTableWidgetItem(item.get('product_name', ''))
                product_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, product_item)
                
                qty_item = QTableWidgetItem(str(item.get('quantity', 0)))
                qty_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, qty_item)
                
                reason_item = QTableWidgetItem(item.get('damage_reason', ''))
                reason_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, reason_item)
                
                loss = item.get('loss_amount', 0)
                loss_item = QTableWidgetItem(f"{loss:,.2f} ج.م")
                loss_item.setTextAlignment(Qt.AlignRight)
                loss_item.setForeground(QBrush(QColor(COLORS['danger'])))
                loss_item.setFont(QFont("Segoe UI", 11, QFont.Bold))
                self.table.setItem(row, 4, loss_item)
                
                total_loss += loss
                
                date_item = QTableWidgetItem(item.get('damage_date', ''))
                date_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, date_item)
                
                responsible_item = QTableWidgetItem(item.get('reported_by', ''))
                responsible_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 6, responsible_item)
                
                btn_delete = QPushButton("🗑️ حذف")
                btn_delete.setFixedSize(75, 28)
                btn_delete.setCursor(Qt.PointingHandCursor)
                btn_delete.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['delete_btn']};
                        color: white;
                        border-radius: 5px;
                        font-size: 11px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['delete_btn_hover']};
                    }}
                """)
                btn_delete.clicked.connect(lambda checked, did=item.get('id', 0): self.delete_damaged_entry(did))
                
                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setAlignment(Qt.AlignCenter)
                container_layout.addStretch()
                container_layout.addWidget(btn_delete)
                container_layout.addStretch()
                
                self.table.setCellWidget(row, 7, container)
            
            if self.damaged_items:
                self.setWindowTitle(f"⚠️ تالف / هالك - إجمالي الخسائر: {total_loss:,.2f} ج.م")
            else:
                self.setWindowTitle("⚠️ تالف / هالك")
                self.show_info_toast("📋 لا توجد سجلات تالف")
        except Exception as e:
            logger.error(f"خطأ في load_damaged: {e}", exc_info=True)
            self.show_warning_toast(f"❌ خطأ في تحميل البيانات: {str(e)}")
    
    def delete_damaged_entry(self, damaged_id):
        """
        حذف سجل تالف مع إعادة الكمية إلى المخزون الرئيسي
        """
        try:
            damaged_item = None
            for item in self.damaged_items:
                if item.get('id') == damaged_id:
                    damaged_item = item
                    break
            
            if not damaged_item:
                self.show_warning_toast("⚠️ السجل غير موجود")
                return
            
            product_id = damaged_item.get('product_id')
            quantity = damaged_item.get('quantity', 0)
            product_name = damaged_item.get('product_name', '')
            
            if not product_id or quantity <= 0:
                self.show_warning_toast("⚠️ بيانات السجل غير صالحة")
                return
            
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE products 
                SET stock = stock + ? 
                WHERE id = ?
            ''', (quantity, product_id))
            
            conn.commit()
            
            success, msg = db.delete_damaged(damaged_id)
            
            conn.close()
            
            if success:
                self.show_success_toast(
                    f"✅ تم حذف السجل وإعادة {quantity} {product_name} إلى المخزون"
                )
                self.load_damaged()
            else:
                self.show_warning_toast(f"❌ {msg}")
                
        except Exception as e:
            logger.error(f"خطأ في delete_damaged_entry: {e}", exc_info=True)
            self.show_warning_toast(f"❌ خطأ في حذف السجل: {str(e)}")
    
    def clear_table(self):
        if not self.damaged_items:
            self.show_warning_toast("⚠️ لا توجد سجلات لحذفها")
            return
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            restored_count = 0
            for item in self.damaged_items:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 0)
                if product_id and quantity > 0:
                    cursor.execute('''
                        UPDATE products 
                        SET stock = stock + ? 
                        WHERE id = ?
                    ''', (quantity, product_id))
                    restored_count += 1
            
            conn.commit()
            
            success, msg = db.clear_all_damaged()
            
            conn.close()
            
            if success:
                self.show_success_toast(
                    f"✅ تم تصفير جميع السجلات وإعادة {restored_count} منتج إلى المخزون"
                )
                self.load_damaged()
            else:
                self.show_warning_toast(f"❌ {msg}")
                
        except Exception as e:
            logger.error(f"خطأ في clear_table: {e}", exc_info=True)
            self.show_warning_toast(f"❌ خطأ في تصفير السجلات: {str(e)}")
    
    # ===== دالة add_damaged المصححة (بدون duration في show_success_toast) =====
    def add_damaged(self):
        """
        فتح نافذة تسجيل التالف ومعالجة النتيجة مع تحديث الجدول فوراً
        تم إصلاح مشكلة duration في show_success_toast
        """
        try:
            products = db.get_all_products()
            if not products:
                self.show_warning_toast("⚠️ لا توجد منتجات في النظام لتسجيل تالف")
                return
        except Exception as e:
            logger.error(f"خطأ في جلب المنتجات: {e}", exc_info=True)
            self.show_warning_toast("⚠️ لا توجد منتجات في النظام لتسجيل تالف")
            return
        
        dlg = AddDamagedDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            
            if not data:
                self.show_warning_toast("⚠️ الرجاء اختيار منتج صحيح")
                return
            
            try:
                # ===== حفظ البيانات في قاعدة البيانات =====
                success, msg = db.add_damaged(
                    product_id=data['product_id'],
                    product_name=data['product_name'],
                    quantity=data['quantity'],
                    damage_reason=data['damage_reason'],
                    loss_amount=data['loss_amount'],
                    notes=data['notes']
                )
                
                if success:
                    # ===== عرض رسالة نجاح بدون duration =====
                    self.show_success_toast(
                        f"✅ {msg}\n"
                        f"💸 قيمة الخسارة: {data['loss_amount']:,.2f} ج.م\n"
                        f"📋 السبب: {data['damage_reason']}"
                    )
                    # ===== تحديث الجدول فوراً =====
                    self.load_damaged()
                else:
                    self.show_warning_toast(f"❌ {msg}")
                    
            except Exception as e:
                logger.error(f"خطأ في add_damaged (حفظ البيانات): {e}", exc_info=True)
                self.show_warning_toast(f"❌ خطأ في تسجيل التالف: {str(e)}")
    
    def refresh_all(self):
        self.load_damaged()
        self.show_info_toast("🔄 تم تحديث البيانات")


if __name__ == "__main__":
    app = QApplication([])
    window = DamagedGoodsWindow()
    window.showMaximized()
    app.exec_()