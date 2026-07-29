# ================= transfer_ui.py - نظام التحويلات وكارت حركة الصنف المتطور (نسخة محسنة) =================
"""
📡 نظام التحويلات بين المخازن وكارت حركة الصنف
📌 تعمل فقط مع قاعدة البيانات الفعلية - لا توجد بيانات افتراضية
✨ تم إعادة هيكلة StockTransferDialog بالكامل ليكون احترافياً وخالياً من الأخطاء
"""

import logging
import traceback
from datetime import datetime

from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer, QDate
from PyQt5.QtGui import QFont, QColor, QBrush
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel,
    QPushButton, QDialog, QComboBox, QSpinBox,
    QLineEdit, QTextEdit, QFrame, QTabWidget,
    QDateEdit, QGroupBox, QSplitter,
    QApplication, QSizePolicy, QFormLayout, QMessageBox
)

from back import database as db

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
    'border': '#cbd5e1',
    'border_light': '#e2e8f0',
    'success': '#16a34a',
    'success_hover': '#15803d',
    'danger': '#dc2626',
    'danger_hover': '#b91c1c',
    'warning': '#d97706',
    'warning_hover': '#b45309',
    'info': '#0284c7',
    'info_hover': '#0369a1',
}

FONTS = {
    'title': QFont("Segoe UI", 20, QFont.Bold),
    'button': QFont("Segoe UI", 12, QFont.Medium),
    'table': QFont("Segoe UI", 11),
}


# ========== نظام Toast موحد ==========
class ToastMessage(QLabel):
    def __init__(self, parent, message, duration=2500):
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


# ========== نافذة تحويل المخزون ==========
class StockTransferDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚚 تحويل مخزني")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setFixedSize(int(screen_geometry.width() * 0.35), int(screen_geometry.height() * 0.55))
        self.setLayoutDirection(Qt.RightToLeft)

        # تنسيق الألوان
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; }}
            QLabel {{ color: {COLORS['text']}; font-weight: bold; font-size: 14px; }}
            QGroupBox {{ 
                color: {COLORS['accent']}; border: 2px solid {COLORS['border_light']}; 
                border-radius: 10px; margin-top: 15px; padding-top: 15px; font-weight: bold;
            }}
            QComboBox, QSpinBox, QTextEdit {{
                background-color: {COLORS['bg_input']}; color: {COLORS['text']};
                border: 1px solid {COLORS['border']}; border-radius: 5px; padding: 8px;
            }}
            QPushButton {{
                background-color: {COLORS['accent']}; color: white; font-weight: bold;
                border-radius: 5px; padding: 10px;
            }}
            QPushButton:disabled {{ background-color: #555555; color: #888888; }}
        """)

        main_layout = QVBoxLayout(self)

        # 1. المنتج
        self.product_combo = QComboBox()
        self.quantity = QSpinBox()
        self.quantity.setRange(0, 9999)
        self.stock_status_label = QLabel("📊 الرصيد الحالي: 0")
        
        g1 = QGroupBox("📦 معلومات المنتج")
        l1 = QFormLayout(g1)
        l1.addRow("المنتج:", self.product_combo)
        l1.addRow("الكمية:", self.quantity)
        l1.addRow(self.stock_status_label)
        main_layout.addWidget(g1)

        # 2. المخازن
        self.from_warehouse = QComboBox()
        self.from_warehouse.addItems(["المخزن الرئيسي (أ)", "المخزن الفرعي (ب)"])
        self.to_warehouse = QComboBox()
        self.to_warehouse.addItems(["المخزن الرئيسي (أ)", "المخزن الفرعي (ب)"])
        self.validation_label = QLabel("⚠️ يرجى اختيار مخازن مختلفة")
        
        g2 = QGroupBox("🏢 المخازن")
        l2 = QFormLayout(g2)
        l2.addRow("من:", self.from_warehouse)
        l2.addRow("إلى:", self.to_warehouse)
        l2.addRow(self.validation_label)
        main_layout.addWidget(g2)

        # 3. ملاحظات
        self.transfer_reason = QComboBox()
        self.transfer_reason.addItems(["توزيع مخزون", "نقل للبيع", "إعادة تخزين", "طلب فرع", "أخرى"])
        self.notes = QTextEdit()
        
        g3 = QGroupBox("📋 تفاصيل إضافية")
        l3 = QFormLayout(g3)
        l3.addRow("السبب:", self.transfer_reason)
        l3.addRow("ملاحظات:", self.notes)
        main_layout.addWidget(g3)

        # الأزرار
        self.confirm_btn = QPushButton("✅ تأكيد النقل")
        self.cancel_btn = QPushButton("❌ إلغاء")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        # المتغيرات
        self.product_data = {}
        self.warehouse_map = {"المخزن الرئيسي (أ)": "A", "المخزن الفرعي (ب)": "B"}

        # الربط
        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.product_combo.currentIndexChanged.connect(self.update_ui_state)
        self.from_warehouse.currentIndexChanged.connect(self.update_ui_state)
        self.to_warehouse.currentIndexChanged.connect(self.update_ui_state)
        self.quantity.valueChanged.connect(self.validate_transfer)

        self.load_products()
        self.update_ui_state()

    def load_products(self):
        self.product_combo.clear()
        try:
            products = db.get_all_products() or []
            for p in products:
                pid = p.get('id')
                name = p.get('name', 'بدون اسم')
                stock = p.get('stock', 0) or 0
                self.product_data[pid] = {'name': name, 'stock': stock}
                self.product_combo.addItem(f"{name} (الرصيد المتاح: {stock})", pid)
        except Exception as e:
            logger.error(f"Error loading products: {e}")

    def update_ui_state(self):
        """تحديث كل شيء عند حدوث أي تغيير"""
        pid = self.product_combo.currentData()
        if pid not in self.product_data:
            self.quantity.setEnabled(False)
            self.quantity.setValue(0)
            self.stock_status_label.setText("📊 الرصيد المتاح: 0")
            self.validate_transfer()
            return

        available = self.product_data[pid]['stock']

        self.quantity.setEnabled(True)
        self.quantity.setRange(0, int(available))
        self.quantity.setValue(0)
        self.stock_status_label.setText(f"📊 الرصيد المتاح: {available}")

        self.validate_transfer()

    def validate_transfer(self):
        pid = self.product_combo.currentData()
        from_idx = self.from_warehouse.currentIndex()
        to_idx = self.to_warehouse.currentIndex()
        is_same_wh = (from_idx == to_idx)
        
        self.validation_label.setText("⚠️ لا يمكن النقل لنفس المخزن" if is_same_wh else "✅ جاهز")
        can_confirm = (pid is not None and self.quantity.value() > 0 and not is_same_wh)
        self.confirm_btn.setEnabled(can_confirm)

    def get_data(self):
        return {
            'product_id': self.product_combo.currentData(),
            'product_name': self.product_data.get(self.product_combo.currentData(), {}).get('name', ''),
            'quantity': self.quantity.value(),
            'from_warehouse': self.from_warehouse.currentText(),
            'to_warehouse': self.to_warehouse.currentText(),
            'transfer_reason': self.transfer_reason.currentText(),
            'notes': self.notes.toPlainText()
        }


# ========== كارت حركة الصنف ==========
class StockCardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.movements = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
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

        # الجزء العلوي - الفلاتر
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(0, 0, 0, 0)

        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 12px;
                padding: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(15)

        # حقل البحث
        search_container = QVBoxLayout()
        search_label = QLabel("🔍 بحث")
        search_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: bold;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("اسم المنتج أو الباركود...")
        self.search_input.setMinimumHeight(35)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:hover {{
                border: 2px solid {COLORS['border_light']};
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.search_input.textChanged.connect(self.filter_movements)
        search_container.addWidget(search_label)
        search_container.addWidget(self.search_input)
        filter_layout.addLayout(search_container, 2)

        # تاريخ من
        from_container = QVBoxLayout()
        from_label = QLabel("📅 من")
        from_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: bold;")
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self.from_date.setMinimumHeight(35)
        self.from_date.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.from_date.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                min-width: 120px;
            }}
            QDateEdit:hover {{
                border: 2px solid {COLORS['border_light']};
            }}
            QDateEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.from_date.dateChanged.connect(self.filter_movements)
        from_container.addWidget(from_label)
        from_container.addWidget(self.from_date)
        filter_layout.addLayout(from_container, 1)

        # تاريخ إلى
        to_container = QVBoxLayout()
        to_label = QLabel("📅 إلى")
        to_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: bold;")
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self.to_date.setMinimumHeight(35)
        self.to_date.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.to_date.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                min-width: 120px;
            }}
            QDateEdit:hover {{
                border: 2px solid {COLORS['border_light']};
            }}
            QDateEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.to_date.dateChanged.connect(self.filter_movements)
        to_container.addWidget(to_label)
        to_container.addWidget(self.to_date)
        filter_layout.addLayout(to_container, 1)

        self.filter_btn = QPushButton("🔄 تطبيق")
        self.filter_btn.setMinimumHeight(35)
        self.filter_btn.setMinimumWidth(100)
        self.filter_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        self.filter_btn.clicked.connect(self.filter_movements)
        filter_layout.addWidget(self.filter_btn)

        top_layout.addWidget(filter_frame)
        top_widget.setMinimumHeight(120)
        main_splitter.addWidget(top_widget)

        # الجزء السفلي - الجدول
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
                background-color: rgba(56, 189, 248, 0.2);
            }}
            QTableWidget::item:alternate {{
                background-color: {COLORS['bg_sidebar']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['accent']};
                padding: 10px;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }}
            QTableCornerButton::section {{
                background-color: {COLORS['bg_card']};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_dark']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border_light']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "التاريخ والوقت", "نوع العملية", "الكمية الواردة",
            "الكمية الصادرة", "الرصيد المتبقي", "الموظف", "المنتج", "حذف"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 70)

        self.table.setLayoutDirection(Qt.RightToLeft)
        header.setDefaultAlignment(Qt.AlignCenter)

        bottom_layout.addWidget(self.table, stretch=1)

        # الملخص
        summary_frame = QFrame()
        summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                padding: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        summary_layout = QHBoxLayout(summary_frame)

        self.total_in_label = QLabel("📥 إجمالي الوارد: 0")
        self.total_in_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; font-size: 13px;")
        summary_layout.addWidget(self.total_in_label)

        self.total_out_label = QLabel("📤 إجمالي الصادر: 0")
        self.total_out_label.setStyleSheet(f"color: {COLORS['danger']}; font-weight: bold; font-size: 13px;")
        summary_layout.addWidget(self.total_out_label)

        self.balance_label = QLabel("📊 الرصيد الحالي: 0")
        self.balance_label.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 13px;")
        summary_layout.addWidget(self.balance_label)

        summary_layout.addStretch()
        bottom_layout.addWidget(summary_frame)

        bottom_widget.setMinimumHeight(200)
        main_splitter.addWidget(bottom_widget)

        main_splitter.setSizes([150, 350])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        layout.addWidget(main_splitter)

        self.load_movements()

    def filter_movements(self):
        try:
            search_text = self.search_input.text().strip().lower()
            from_date = self.from_date.date()
            to_date = self.to_date.date()

            filtered = []
            for movement in self.movements:
                try:
                    movement_date = QDate.fromString(movement.get('date', '').split(' ')[0], "yyyy-MM-dd")
                    if movement_date < from_date or movement_date > to_date:
                        continue
                except:
                    pass

                if search_text:
                    product = self.get_product_name(movement.get('product_id', 0))
                    if search_text not in product.lower() and search_text not in movement.get('type', '').lower():
                        continue

                filtered.append(movement)

            self.load_movements(filtered)

        except Exception as e:
            logger.error(f"خطأ في filter_movements: {e}")

    def get_product_name(self, product_id):
        try:
            products = db.get_all_products()
            if products:
                for product in products:
                    if product.get('id') == product_id:
                        return product.get('name', f'منتج {product_id}')
            return f"منتج {product_id}"
        except:
            return f"منتج {product_id}"

    def load_movements(self, movements=None):
        try:
            if movements is None:
                movements = self.movements

            self.table.setRowCount(len(movements))

            total_in = 0
            total_out = 0
            current_balance = 0

            movements_sorted = sorted(movements, key=lambda x: x.get('date', ''))

            for row, movement in enumerate(movements_sorted):
                self.table.setRowHeight(row, 45)

                product_name = self.get_product_name(movement.get('product_id', 0))

                # التاريخ
                date_item = QTableWidgetItem(movement.get('date', ''))
                date_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, date_item)

                # نوع العملية
                type_item = QTableWidgetItem(movement.get('type', ''))
                type_item.setTextAlignment(Qt.AlignCenter)
                movement_type = movement.get('type', '')
                if movement_type == 'شراء':
                    type_item.setForeground(QBrush(QColor(COLORS['success'])))
                elif movement_type == 'بيع':
                    type_item.setForeground(QBrush(QColor(COLORS['danger'])))
                elif movement_type == 'تحويل':
                    type_item.setForeground(QBrush(QColor(COLORS['accent'])))
                elif movement_type == 'تالف':
                    type_item.setForeground(QBrush(QColor(COLORS['warning'])))
                self.table.setItem(row, 1, type_item)

                # الكمية الواردة
                in_qty = movement.get('in_qty', 0) or 0
                in_item = QTableWidgetItem(str(in_qty) if in_qty > 0 else "-")
                in_item.setTextAlignment(Qt.AlignCenter)
                if in_qty > 0:
                    in_item.setForeground(QBrush(QColor(COLORS['success'])))
                self.table.setItem(row, 2, in_item)

                # الكمية الصادرة
                out_qty = movement.get('out_qty', 0) or 0
                out_item = QTableWidgetItem(str(out_qty) if out_qty > 0 else "-")
                out_item.setTextAlignment(Qt.AlignCenter)
                if out_qty > 0:
                    out_item.setForeground(QBrush(QColor(COLORS['danger'])))
                self.table.setItem(row, 3, out_item)

                # الرصيد المتبقي
                balance = movement.get('balance', 0) or 0
                balance_item = QTableWidgetItem(str(balance))
                balance_item.setTextAlignment(Qt.AlignCenter)
                if balance < 10:
                    balance_item.setForeground(QBrush(QColor(COLORS['warning'])))
                self.table.setItem(row, 4, balance_item)

                # الموظف
                user_item = QTableWidgetItem(movement.get('user', ''))
                user_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, user_item)

                # المنتج
                product_item = QTableWidgetItem(product_name)
                product_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 6, product_item)

                # زر الحذف
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(30, 28)
                delete_btn.setCursor(Qt.PointingHandCursor)
                delete_btn.setToolTip("حذف الحركة")
                delete_btn.setStyleSheet(f"""
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
                delete_btn.clicked.connect(lambda checked, idx=row: self.delete_movement(idx))

                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setAlignment(Qt.AlignCenter)
                container_layout.addWidget(delete_btn)
                self.table.setCellWidget(row, 7, container)

                total_in += in_qty
                total_out += out_qty
                current_balance = balance

            self.total_in_label.setText(f"📥 إجمالي الوارد: {total_in}")
            self.total_out_label.setText(f"📤 إجمالي الصادر: {total_out}")
            self.balance_label.setText(f"📊 الرصيد الحالي: {current_balance}")
            
            # ===== تحديث الجدول وإعادة الرسم الفورية =====
            self.table.viewport().update()
            self.table.resizeRowsToContents()

        except Exception as e:
            logger.error(f"خطأ في load_movements: {e}")

    def delete_movement(self, row):
        try:
            if row < len(self.movements):
                movement = self.movements[row]
                product_name = self.get_product_name(movement.get('product_id', 0))
                del self.movements[row]
                self.load_movements()
                if self.parent_window:
                    self.parent_window.show_toast(f"🗑️ تم حذف حركة {product_name}")
        except Exception as e:
            logger.error(f"خطأ في delete_movement: {e}")

    def add_movement(self, product_id, qty, movement_type, user="Admin"):
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M')

            last_balance = 0
            for movement in reversed(self.movements):
                if movement.get('product_id') == product_id:
                    last_balance = movement.get('balance', 0) or 0
                    break

            new_balance = last_balance + qty if movement_type == 'شراء' else last_balance - qty

            new_movement = {
                'product_id': product_id,
                'date': now,
                'type': movement_type,
                'in_qty': qty if movement_type == 'شراء' else 0,
                'out_qty': qty if movement_type != 'شراء' else 0,
                'balance': new_balance,
                'user': user
            }

            self.movements.append(new_movement)
            self.load_movements()

        except Exception as e:
            logger.error(f"خطأ في add_movement: {e}")


# ========== النافذة الرئيسية ==========
class StockTransferWindow(QWidget):
    def __init__(self):
        super().__init__()

        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))

        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.setLayoutDirection(Qt.RightToLeft)

        self.transfers = []
        self.init_ui()
        self.load_transfers()

    def show_toast(self, message, duration=2500):
        ToastMessage(self, message, duration)

    def show_success_toast(self, message):
        self.show_toast(message)

    def show_warning_toast(self, message):
        self.show_toast(message)

    def show_info_toast(self, message):
        self.show_toast(message)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        title = QLabel("🚚 نقل مخزني وحركة الصنف")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['text']}; padding: 8px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                padding: 5px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_muted']};
                border-radius: 8px;
                padding: 10px 20px;
                margin-right: 5px;
                font-weight: bold;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['accent']};
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLORS['border']};
                color: {COLORS['text']};
            }}
        """)

        # تبويب عمليات النقل
        self.transfers_tab = QWidget()
        transfers_layout = QVBoxLayout(self.transfers_tab)
        transfers_layout.setContentsMargins(12, 12, 12, 12)
        transfers_layout.setSpacing(10)

        transfers_splitter = QSplitter(Qt.Vertical)
        transfers_splitter.setHandleWidth(4)
        transfers_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS['border']};
                border-radius: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS['accent']};
            }}
        """)

        # الجزء العلوي - الأزرار
        top_transfer_widget = QWidget()
        top_transfer_layout = QHBoxLayout(top_transfer_widget)
        top_transfer_layout.setContentsMargins(0, 0, 0, 0)

        info_label = QLabel("🔄 إدارة عمليات التحويل بين المخازن")
        info_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; padding: 8px; background-color: {COLORS['bg_card']}; border-radius: 8px;")
        top_transfer_layout.addWidget(info_label)
        top_transfer_layout.addStretch()

        add_btn = QPushButton("➕ نقل جديد")
        add_btn.setFont(FONTS['button'])
        add_btn.setMinimumHeight(38)
        add_btn.setStyleSheet(f"""
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
        add_btn.clicked.connect(self.add_transfer)
        top_transfer_layout.addWidget(add_btn)

        clear_btn = QPushButton("🗑️ تصفير الجدول")
        clear_btn.setFont(FONTS['button'])
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
        clear_btn.clicked.connect(self.clear_transfers)
        top_transfer_layout.addWidget(clear_btn)

        top_transfer_widget.setMinimumHeight(60)
        transfers_splitter.addWidget(top_transfer_widget)

        # الجزء السفلي - الجدول
        bottom_transfer_widget = QWidget()
        bottom_transfer_layout = QVBoxLayout(bottom_transfer_widget)
        bottom_transfer_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
                background-color: rgba(56, 189, 248, 0.2);
            }}
            QTableWidget::item:alternate {{
                background-color: {COLORS['bg_sidebar']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['accent']};
                padding: 10px 8px;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }}
            QTableCornerButton::section {{
                background-color: {COLORS['bg_card']};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_dark']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border_light']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "رقم النقل", "المنتج", "التاريخ", "الكمية",
            "من مخزن", "إلى مخزن", "السبب", "الإجراءات"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 130)

        self.table.setLayoutDirection(Qt.RightToLeft)
        header.setDefaultAlignment(Qt.AlignCenter)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        bottom_transfer_layout.addWidget(self.table, stretch=1)
        bottom_transfer_widget.setMinimumHeight(200)
        transfers_splitter.addWidget(bottom_transfer_widget)

        transfers_splitter.setSizes([80, 420])
        transfers_splitter.setStretchFactor(0, 0)
        transfers_splitter.setStretchFactor(1, 1)
        transfers_layout.addWidget(transfers_splitter)

        self.tab_widget.addTab(self.transfers_tab, "🔄 عمليات النقل")

        # تبويب كارت الحركة
        self.stock_card_tab = StockCardTab(self)
        self.tab_widget.addTab(self.stock_card_tab, "📊 كارت حركة الصنف")

        layout.addWidget(self.tab_widget)

    def load_transfers(self):
        """تحميل عمليات النقل من قاعدة البيانات"""
        try:
            # مسح الجدول بالكامل
            self.table.clearContents()
            self.table.setRowCount(0)
            
            # جلب البيانات
            self.transfers = db.get_all_transfers()
            
            if not self.transfers:
                self.show_info_toast("📭 لا توجد عمليات نقل")
                return
            
            self.table.setRowCount(len(self.transfers))
            
            for row, transfer in enumerate(self.transfers):
                self.table.setRowHeight(row, 50)
                
                number_item = QTableWidgetItem(f"TR-{transfer.get('id', 0):04d}")
                number_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, number_item)
                
                product_item = QTableWidgetItem(str(transfer.get('product_name', '')))
                product_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, product_item)
                
                date_item = QTableWidgetItem(str(transfer.get('transfer_date', '')))
                date_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, date_item)
                
                qty_item = QTableWidgetItem(str(transfer.get('quantity', 0)))
                qty_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, qty_item)
                
                from_item = QTableWidgetItem(str(transfer.get('from_warehouse', '')))
                from_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 4, from_item)
                
                to_item = QTableWidgetItem(str(transfer.get('to_warehouse', '')))
                to_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, to_item)
                
                reason_item = QTableWidgetItem(str(transfer.get('transfer_reason', '')))
                reason_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 6, reason_item)
                
                delete_btn = QPushButton("🗑️ حذف")
                delete_btn.setFixedSize(75, 30)
                delete_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['danger']};
                        color: white;
                        border-radius: 5px;
                        font-size: 11px;
                        font-weight: bold;
                        border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['danger_hover']};
                    }}
                """)
                delete_btn.clicked.connect(lambda checked, tid=transfer.get('id'): self.delete_transfer(tid))
                self.table.setCellWidget(row, 7, delete_btn)
            
            # تحديث قوي للجدول
            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
            self.table.viewport().update()
            self.table.repaint()
            QApplication.processEvents()
            
            self.show_success_toast(f"✅ تم تحميل {len(self.transfers)} عملية نقل")
            
        except Exception as e:
            logger.error(f"خطأ في load_transfers: {e}")
            self.show_warning_toast(f"❌ خطأ في تحميل التحويلات: {str(e)}")

    def delete_transfer(self, transfer_id):
        try:
            success, msg = db.delete_transfer(transfer_id)
            if success:
                self.show_success_toast(f"✅ {msg}")
                self.load_transfers()
            else:
                self.show_warning_toast(f"❌ {msg}")
        except Exception as e:
            logger.error(f"خطأ في delete_transfer: {e}")
            self.show_warning_toast(f"❌ خطأ في حذف التحويل: {str(e)}")

    def clear_transfers(self):
        if not self.transfers:
            self.show_warning_toast("⚠️ لا توجد عمليات نقل لحذفها")
            return

        try:
            success, msg = db.clear_all_transfers()
            if success:
                self.show_success_toast(f"✅ {msg}")
                self.load_transfers()
            else:
                self.show_warning_toast(f"❌ {msg}")
        except Exception as e:
            logger.error(f"خطأ في clear_transfers: {e}")
            self.show_warning_toast(f"❌ خطأ في تصفير التحويلات: {str(e)}")

    def add_transfer(self):
        try:
            products = db.get_all_products()
            if not products:
                self.show_warning_toast("⚠️ لا توجد منتجات في النظام للتحويل")
                return
        except Exception as e:
            logger.error(f"خطأ في add_transfer: {e}")
            self.show_warning_toast("⚠️ لا توجد منتجات في النظام للتحويل")
            return

        dlg = StockTransferDialog(self)

        if dlg.exec():
            data = dlg.get_data()

            if not data:
                self.show_warning_toast("⚠️ الرجاء اختيار منتج صحيح")
                return

            if data['from_warehouse'] == data['to_warehouse']:
                self.show_warning_toast("⚠️ لا يمكن النقل لنفس المخزن\nالرجاء اختيار مخازن مختلفة")
                return

            if data['quantity'] <= 0:
                self.show_warning_toast("⚠️ الكمية يجب أن تكون أكبر من صفر")
                return

            try:
                success, msg = db.add_transfer(
                    product_id=data['product_id'],
                    product_name=data['product_name'],
                    quantity=data['quantity'],
                    from_warehouse=data['from_warehouse'],
                    to_warehouse=data['to_warehouse'],
                    reason=data['transfer_reason'],
                    notes=data.get('notes', '')
                )

                if success:
                    # تحديث كارت حركة الصنف
                    self.stock_card_tab.add_movement(
                        data['product_id'], data['quantity'], 'تحويل', 'Admin'
                    )

                    # عرض رسالة النجاح
                    self.show_success_toast(
                        f"✅ {msg}\n"
                        f"📤 من: {data['from_warehouse']}\n"
                        f"📥 إلى: {data['to_warehouse']}",
                        4000
                    )
                    
                    # ===== التعديل هنا: تحميل البيانات وتحديث الواجهة فوراً =====
                    self.transfers = db.get_all_transfers()
                    self.table.setRowCount(0)
                    self.table.clearContents()
                    self.table.setRowCount(len(self.transfers))

                    for row, transfer in enumerate(self.transfers):
                        self.table.setRowHeight(row, 50)
                        
                        number_item = QTableWidgetItem(f"TR-{transfer.get('id', 0):04d}")
                        number_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, 0, number_item)
                        
                        product_item = QTableWidgetItem(str(transfer.get('product_name', '')))
                        product_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, 1, product_item)
                        
                        date_item = QTableWidgetItem(str(transfer.get('transfer_date', '')))
                        date_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, 2, date_item)
                        
                        qty_item = QTableWidgetItem(str(transfer.get('quantity', 0)))
                        qty_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, 3, qty_item)
                        
                        from_item = QTableWidgetItem(str(transfer.get('from_warehouse', '')))
                        from_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, 4, from_item)
                        
                        to_item = QTableWidgetItem(str(transfer.get('to_warehouse', '')))
                        to_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, 5, to_item)
                        
                        reason_item = QTableWidgetItem(str(transfer.get('transfer_reason', '')))
                        reason_item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, 6, reason_item)
                        
                        delete_btn = QPushButton("🗑️ حذف")
                        delete_btn.setFixedSize(75, 30)
                        delete_btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {COLORS['danger']};
                                color: white;
                                border-radius: 5px;
                                font-size: 11px;
                                font-weight: bold;
                                border: none;
                            }}
                            QPushButton:hover {{
                                background-color: {COLORS['danger_hover']};
                            }}
                        """)
                        delete_btn.clicked.connect(lambda checked, tid=transfer.get('id'): self.delete_transfer(tid))
                        self.table.setCellWidget(row, 7, delete_btn)

                    self.table.resizeColumnsToContents()
                    self.table.resizeRowsToContents()
                    self.table.viewport().update()
                    self.table.repaint()
                    QApplication.processEvents()
                    # ===== نهاية التعديل =====
                    
                else:
                    self.show_warning_toast(f"❌ {msg}")

            except Exception as e:
                logger.error(f"خطأ في add_transfer: {e}")
                logger.error(traceback.format_exc())
                self.show_warning_toast(f"❌ خطأ في إضافة التحويل: {str(e)}")


if __name__ == "__main__":
    app = QApplication([])
    window = StockTransferWindow()
    window.showMaximized()
    app.exec_()