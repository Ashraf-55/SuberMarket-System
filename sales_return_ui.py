# ================= sales_return_ui.py - نظام مرتجع المبيعات المتطور =================
"""
نافذة مرتجع المبيعات الذكية - تدعم الإرجاع الجزئي والكلي
مع خيارات رد الأموال المتقدمة (نقداً / حساب العميل)
📌 تعمل فقط مع قاعدة البيانات الفعلية - لا توجد بيانات افتراضية
"""

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel,
                             QPushButton, QDialog, QGroupBox, 
                             QDoubleSpinBox, QTextEdit, QFrame, QLineEdit,
                             QScrollArea, QSizePolicy, QComboBox, QRadioButton,
                             QButtonGroup, QSplitter, QApplication)
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor

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
    'return_btn': '#d97706',
    'return_btn_hover': '#b45309',
    'cash_color': '#16a34a',
    'deferred_color': '#d97706',
}


# ========== رسالة Toast موحدة ==========
class ToastMessage(QLabel):
    def __init__(self, parent, message, duration=2500):
        # لون موحد للجميع
        toast_color = COLORS['bg_card']
        border_color = COLORS['accent']
        
        super().__init__(message, parent)
        self.duration = duration
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {toast_color};
                color: {COLORS['text']};
                border-radius: 12px;
                padding: 14px 24px;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid {border_color};
            }}
        """)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumHeight(50)
        self.setMaximumWidth(420)
        
        # حساب الموقع بناءً على حجم الشاشة
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setFixedWidth(min(350, screen_geometry.width() - 40))
        
        x = (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.height() - 120
        self.move(x, y)
        self.raise_()
        self.show()
        
        QTimer.singleShot(duration, self.fade_out)
    
    def fade_out(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(400)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()


# ========== نافذة تنفيذ مرتجع مبيعات ==========
class SalesReturnForm(QDialog):
    return_completed = pyqtSignal(dict)
    
    def __init__(self, sale_id, sale_items_data, customer_name="", parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.sale_id = sale_id
        self.customer_name = customer_name
        self.setWindowTitle(f"🔄 تنفيذ مرتجع مبيعات - فاتورة رقم {sale_id}")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.8)
        height = int(screen_geometry.height() * 0.8)
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        self.resize(max(900, width), max(750, height))
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 12px;
            }}
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
                padding: 0 8px 0 8px;
            }}
            QDoubleSpinBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px;
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
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QTextEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }}
            QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
            }}
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 13px;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid {COLORS['accent']};
                background-color: {COLORS['accent']};
            }}
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
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
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['accent']};
            }}
            QPushButton {{
                border-radius: 8px;
                font-weight: bold;
                border: none;
            }}
        """)
        
        self.return_items = []
        self.init_ui(sale_items_data)
    
    def init_ui(self, sale_items_data):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_label = QLabel(f"مرتجع مبيعات - الفاتورة رقم {self.sale_id}")
        title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['accent']}; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
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
        top_layout.setSpacing(12)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        info_group = QGroupBox("📋 معلومات الفاتورة")
        info_layout = QHBoxLayout(info_group)
        info_layout.setSpacing(20)
        
        total_amount = sum(item.get('price', 0) * item.get('quantity', 0) for item in sale_items_data)
        
        info_layout.addWidget(QLabel(f"رقم الفاتورة: {self.sale_id}"))
        if self.customer_name:
            info_layout.addWidget(QLabel(f"العميل: {self.customer_name}"))
        info_layout.addWidget(QLabel(f"الإجمالي: {total_amount:,.2f} ج.م"))
        info_layout.addWidget(QLabel(f"عدد الأصناف: {len(sale_items_data)}"))
        info_layout.addStretch()
        
        top_layout.addWidget(info_group)
        
        products_group = QGroupBox("📦 اختر المنتجات المراد إرجاعها")
        products_layout = QVBoxLayout(products_group)
        products_layout.setSpacing(10)
        
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(12, 5, 12, 5)
        header_layout.setSpacing(10)
        
        # أوزان نسبية (stretch) تحافظ تقريبًا على نفس النسب القديمة بين الأعمدة
        headers = ["المنتج", "السعر", "الكمية المباعة", "المتبقي للإرجاع", "كمية المرتجع"]
        header_stretches = [4, 2, 2, 2, 3]
        header_min_widths = [140, 70, 70, 80, 130]
        
        for idx, (h, stretch) in enumerate(zip(headers, header_stretches)):
            lbl = QLabel(h)
            lbl.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 12px;")
            lbl.setMinimumWidth(header_min_widths[idx])
            lbl.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(lbl, stretch)
        
        products_layout.addWidget(header_widget)
        
        # ===== إضافة ScrollArea لدعم الشاشات الصغيرة =====
        products_scroll = QScrollArea()
        products_scroll.setWidgetResizable(True)
        products_scroll.setStyleSheet("border: none; background-color: transparent;")
        
        products_widget = QWidget()
        products_inner_layout = QVBoxLayout(products_widget)
        products_inner_layout.setSpacing(6)
        
        for item in sale_items_data:
            item_frame = QFrame()
            item_frame.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 8px; margin: 2px; border: 1px solid {COLORS['border']}; }}")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setSpacing(10)
            item_layout.setContentsMargins(12, 6, 12, 6)
            
            unit = item.get('unit', 'قطعة')
            name_text = f"🛒 {item['name']} ({unit})"
            name_label = QLabel(name_text)
            name_label.setMinimumWidth(header_min_widths[0])
            name_label.setWordWrap(True)
            name_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
            
            price_label = QLabel(f"{item.get('price', 0):,.2f} ج.م")
            price_label.setMinimumWidth(header_min_widths[1])
            price_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; font-size: 13px;")
            price_label.setAlignment(Qt.AlignCenter)
            
            qty_sold = item.get('quantity', 0)
            qty_sold_label = QLabel(str(int(qty_sold) if qty_sold == int(qty_sold) else f"{qty_sold:.3f}"))
            qty_sold_label.setMinimumWidth(header_min_widths[2])
            qty_sold_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px;")
            qty_sold_label.setAlignment(Qt.AlignCenter)
            
            remaining_qty = item.get('remaining_quantity', item.get('quantity', 0))
            remaining_label = QLabel(str(int(remaining_qty) if remaining_qty == int(remaining_qty) else f"{remaining_qty:.3f}"))
            remaining_label.setMinimumWidth(header_min_widths[3])
            remaining_label.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold; font-size: 12px;")
            remaining_label.setAlignment(Qt.AlignCenter)
            
            qty_spin = QDoubleSpinBox()
            qty_spin.setRange(0, remaining_qty)
            qty_spin.setValue(0)
            qty_spin.setSingleStep(1.0 if unit == "قطعة" else 0.250)
            qty_spin.setDecimals(3)
            qty_spin.setMinimumWidth(header_min_widths[4])
            qty_spin.setSuffix(f" {unit}")
            qty_spin.setStyleSheet(f"""
                QDoubleSpinBox {{
                    background-color: {COLORS['bg_dark']};
                    color: {COLORS['text']};
                    border: 2px solid {COLORS['border']};
                    border-radius: 8px;
                    padding: 6px;
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
            
            item_layout.addWidget(name_label, header_stretches[0])
            item_layout.addWidget(price_label, header_stretches[1])
            item_layout.addWidget(qty_sold_label, header_stretches[2])
            item_layout.addWidget(remaining_label, header_stretches[3])
            item_layout.addWidget(qty_spin, header_stretches[4])
            
            products_inner_layout.addWidget(item_frame)
            
            self.return_items.append({
                'product_id': item.get('product_id'),
                'name': item.get('name'),
                'price': item.get('price', 0),
                'max_qty': remaining_qty,
                'unit': unit,
                'spin': qty_spin,
                'quantity_sold': item.get('quantity', 0)
            })
        
        products_scroll.setWidget(products_widget)
        products_layout.addWidget(products_scroll)
        top_layout.addWidget(products_group)
        
        top_widget.setMinimumHeight(400)
        main_splitter.addWidget(top_widget)
        
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(12)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        financial_group = QGroupBox("💰 خيارات رد الأموال")
        financial_layout = QVBoxLayout(financial_group)
        financial_layout.setSpacing(12)
        
        method_label = QLabel("طريقة إرجاع المبلغ:")
        method_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold; font-size: 13px;")
        financial_layout.addWidget(method_label)
        
        self.refund_method_group = QButtonGroup(self)
        
        refund_layout = QHBoxLayout()
        refund_layout.setSpacing(25)
        
        self.radio_cash = QRadioButton("💵 نقداً من الخزينة")
        self.radio_cash.setChecked(True)
        self.radio_cash.setStyleSheet(f"""
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 13px;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid {COLORS['accent']};
                background-color: {COLORS['accent']};
            }}
        """)
        refund_layout.addWidget(self.radio_cash)
        self.refund_method_group.addButton(self.radio_cash, 0)
        
        self.radio_customer_account = QRadioButton("📊 إضافة إلى حساب العميل")
        self.radio_customer_account.setStyleSheet(f"""
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 13px;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid {COLORS['accent']};
                background-color: {COLORS['accent']};
            }}
        """)
        refund_layout.addWidget(self.radio_customer_account)
        self.refund_method_group.addButton(self.radio_customer_account, 1)
        
        refund_layout.addStretch()
        financial_layout.addLayout(refund_layout)
        
        summary_frame = QFrame()
        summary_frame.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_dark']}; border-radius: 8px; border: 1px solid {COLORS['border']}; }}")
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(15, 10, 15, 10)
        
        self.total_refund_label = QLabel("💰 إجمالي المبلغ المسترد: 0.00 ج.م")
        self.total_refund_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; font-size: 16px;")
        summary_layout.addWidget(self.total_refund_label)
        summary_layout.addStretch()
        
        financial_layout.addWidget(summary_frame)
        bottom_layout.addWidget(financial_group)
        
        reason_group = QGroupBox("📝 سبب المرتجع")
        reason_layout = QVBoxLayout(reason_group)
        self.return_reason = QTextEdit()
        self.return_reason.setPlaceholderText("مثال: منتج به عيب، انتهاء الصلاحية، خطأ في الصنف، تغيير رأي العميل...")
        self.return_reason.setMaximumHeight(65)
        self.return_reason.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }}
            QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        reason_layout.addWidget(self.return_reason)
        bottom_layout.addWidget(reason_group)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        update_btn = QPushButton("🔄 تحديث المبلغ")
        update_btn.setMinimumHeight(38)
        update_btn.setMinimumWidth(140)
        update_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                padding: 8px 20px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_hover']};
            }}
        """)
        update_btn.clicked.connect(self.update_total_refund)
        buttons_layout.addWidget(update_btn)
        
        buttons_layout.addStretch()
        
        confirm_btn = QPushButton("✅ تأكيد المرتجع")
        confirm_btn.setMinimumHeight(42)
        confirm_btn.setMinimumWidth(160)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                padding: 10px 25px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        confirm_btn.clicked.connect(self.on_confirm)
        buttons_layout.addWidget(confirm_btn)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setMinimumHeight(42)
        cancel_btn.setMinimumWidth(140)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 10px 25px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        bottom_layout.addLayout(buttons_layout)
        
        bottom_widget.setMinimumHeight(250)
        main_splitter.addWidget(bottom_widget)
        
        main_splitter.setSizes([550, 300])
        layout.addWidget(main_splitter)
        
        for item in self.return_items:
            item['spin'].valueChanged.connect(self.update_total_refund)
        
        self.update_total_refund()
    
    def show_toast(self, message, duration=2500):
        ToastMessage(self, message, duration)
    
    def show_warning_toast(self, message):
        self.show_toast(message)
    
    def show_info_toast(self, message):
        self.show_toast(message)
    
    def update_total_refund(self):
        try:
            total = 0
            for item in self.return_items:
                qty = item['spin'].value()
                price = item['price']
                total += qty * price
            
            self.total_refund_label.setText(f"💰 إجمالي المبلغ المسترد: {total:,.2f} ج.م")
            
            if total > 0:
                self.total_refund_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; font-size: 16px;")
            else:
                self.total_refund_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; font-size: 16px;")
        except Exception as e:
            logger.error(f"خطأ في update_total_refund: {e}")
    
    def on_confirm(self):
        try:
            items = self.get_return_items()
            if not items:
                self.show_warning_toast("⚠️ لم يتم اختيار أي منتجات للمرتجع")
                return
            
            total_refund = sum(qty * price for _, qty, price in items)
            refund_method = "نقداً" if self.radio_cash.isChecked() else "حساب العميل"
            reason = self.return_reason.toPlainText().strip()
            
            result = {
                'sale_id': self.sale_id,
                'items': items,
                'total_refund': total_refund,
                'refund_method': refund_method,
                'reason': reason,
                'customer_name': self.customer_name
            }
            
            self.return_completed.emit(result)
            self.accept()
            
        except Exception as e:
            logger.error(f"خطأ في on_confirm: {e}")
            self.show_warning_toast(f"❌ خطأ: {str(e)}")
    
    def get_return_items(self):
        try:
            items = []
            for item in self.return_items:
                qty = item['spin'].value()
                if qty > 0.001:
                    items.append((item['product_id'], qty, item['price']))
            return items
        except Exception as e:
            logger.error(f"خطأ في get_return_items: {e}")
            return []
    
    def get_refund_method(self):
        return "نقداً" if self.radio_cash.isChecked() else "حساب العميل"
    
    def get_reason(self):
        return self.return_reason.toPlainText().strip()
    
    def reset_all(self):
        try:
            for item in self.return_items:
                item['spin'].setValue(0)
            self.return_reason.clear()
            self.update_total_refund()
            self.show_info_toast("🔄 تم تصفير جميع كميات المرتجع")
        except Exception as e:
            logger.error(f"خطأ في reset_all: {e}")


# ========== شاشة مرتجع مبيعات الرئيسية ==========
class SalesReturnWindow(QWidget):
    return_processed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.all_sales = []
        self.current_sale_items = []
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.init_ui()
        self.show_info_toast("📋 ابحث عن فاتورة لعرض تفاصيلها")
    
    def show_toast(self, message, duration=2500):
        ToastMessage(self, message, duration)
    
    def show_info_toast(self, message):
        self.show_toast(message)
    
    def show_warning_toast(self, message):
        self.show_toast(message)
    
    def show_success_toast(self, message):
        self.show_toast(message)
    
    def show_danger_toast(self, message):
        self.show_toast(message)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        title = QLabel("↩️ مرتجع مبيعات")
        title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {COLORS['accent']}; padding: 8px;")
        layout.addWidget(title)
        
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
        
        search_frame = QFrame()
        search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(15, 12, 15, 12)
        search_layout.setSpacing(12)
        
        search_label = QLabel("🔍 رقم الفاتورة:")
        search_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold; font-size: 13px;")
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("أدخل رقم الفاتورة...")
        self.search_input.setMinimumHeight(38)
        self.search_input.setMinimumWidth(200)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.search_input.returnPressed.connect(self.search_sale)
        search_layout.addWidget(self.search_input)
        
        self.btn_search = QPushButton("🔍 بحث")
        self.btn_search.setMinimumHeight(38)
        self.btn_search.setMinimumWidth(100)
        self.btn_search.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        self.btn_search.clicked.connect(self.search_sale)
        search_layout.addWidget(self.btn_search)
        
        self.btn_clear_search = QPushButton("🗑️ إلغاء البحث")
        self.btn_clear_search.setMinimumHeight(38)
        self.btn_clear_search.setMinimumWidth(120)
        self.btn_clear_search.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['warning']};
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['warning_hover']};
            }}
        """)
        self.btn_clear_search.clicked.connect(self.clear_search)
        search_layout.addWidget(self.btn_clear_search)
        
        search_layout.addStretch()
        top_layout.addWidget(search_frame)
        
        info_label = QLabel("ℹ️ أدخل رقم الفاتورة ثم اضغط بحث لعرض تفاصيلها وإمكانية إرجاع منتجاتها")
        info_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; padding: 8px 12px; background-color: {COLORS['bg_card']}; border-radius: 8px;")
        info_label.setWordWrap(True)
        top_layout.addWidget(info_label)
        
        details_group = QGroupBox("📋 تفاصيل الفاتورة")
        details_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['accent']};
                font-weight: bold;
                font-size: 14px;
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                margin-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
            }}
        """)
        details_layout = QVBoxLayout(details_group)
        
        info_frame = QFrame()
        info_frame.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 8px; }}")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(15, 10, 15, 10)
        info_layout.setSpacing(20)
        
        self.invoice_id_label = QLabel("رقم الفاتورة: -")
        self.invoice_id_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self.invoice_id_label)
        
        self.customer_name_label = QLabel("العميل: -")
        self.customer_name_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px;")
        info_layout.addWidget(self.customer_name_label)
        
        self.invoice_total_label = QLabel("الإجمالي: -")
        self.invoice_total_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self.invoice_total_label)
        
        self.invoice_status_label = QLabel("الحالة: -")
        self.invoice_status_label.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self.invoice_status_label)
        
        info_layout.addStretch()
        details_layout.addWidget(info_frame)
        
        # ===== جدول مع دعم Scroll =====
        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["المنتج", "السعر", "الكمية المباعة", "كمية المرتجع", ""])
        self.items_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
                font-size: 12px;
                gridline-color: {COLORS['border']};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(56, 189, 248, 0.2);
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.items_table.setColumnWidth(4, 100)
        
        details_layout.addWidget(self.items_table)
        top_layout.addWidget(details_group)
        
        top_widget.setMinimumHeight(350)
        main_splitter.addWidget(top_widget)
        
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 10, 0, 0)
        bottom_layout.setSpacing(15)
        
        bottom_layout.addStretch()
        
        self.btn_process_return = QPushButton("🔄 تنفيذ مرتجع")
        self.btn_process_return.setMinimumHeight(48)
        self.btn_process_return.setMinimumWidth(180)
        self.btn_process_return.setEnabled(False)
        self.btn_process_return.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['return_btn']};
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['return_btn_hover']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
        """)
        self.btn_process_return.clicked.connect(self.process_return)
        bottom_layout.addWidget(self.btn_process_return)
        
        self.btn_reset_return = QPushButton("🗑️ إلغاء عملية الارتجاع")
        self.btn_reset_return.setMinimumHeight(48)
        self.btn_reset_return.setMinimumWidth(180)
        self.btn_reset_return.setEnabled(False)
        self.btn_reset_return.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
        """)
        self.btn_reset_return.clicked.connect(self.reset_return_process)
        bottom_layout.addWidget(self.btn_reset_return)
        
        bottom_widget.setMinimumHeight(80)
        main_splitter.addWidget(bottom_widget)
        
        main_splitter.setSizes([500, 100])
        layout.addWidget(main_splitter)
    
    def search_sale(self):
        search_text = self.search_input.text().strip()
        
        if not search_text:
            self.show_warning_toast("⚠️ الرجاء إدخال رقم الفاتورة")
            return
        
        try:
            sale_id = int(search_text)
        except ValueError:
            self.show_warning_toast("⚠️ الرجاء إدخال رقم فاتورة صحيح")
            return
        
        try:
            sale = db.get_sale_by_id(sale_id)
            if sale:
                self.display_invoice(sale)
                self.show_success_toast(f"✅ تم العثور على الفاتورة رقم {sale_id}")
            else:
                self.show_warning_toast(f"❌ لم يتم العثور على فاتورة رقم {sale_id}")
                self.clear_invoice_display()
        except Exception as e:
            logger.error(f"خطأ في search_sale: {e}")
            self.show_warning_toast(f"❌ خطأ في البحث: {str(e)}")
    
    def clear_search(self):
        self.search_input.clear()
        self.clear_invoice_display()
        self.btn_process_return.setEnabled(False)
        self.btn_reset_return.setEnabled(False)
        self.show_info_toast("🔄 تم إلغاء البحث وتصفير الشاشة")
    
    def clear_invoice_display(self):
        self.invoice_id_label.setText("رقم الفاتورة: -")
        self.customer_name_label.setText("العميل: -")
        self.invoice_total_label.setText("الإجمالي: -")
        self.invoice_status_label.setText("الحالة: -")
        self.invoice_status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; font-size: 13px;")
        self.items_table.setRowCount(0)
        self.current_sale_items = []
        self.btn_process_return.setEnabled(False)
        self.btn_reset_return.setEnabled(False)
    
    def display_invoice(self, sale):
        self.items_table.setRowCount(0)
        
        sale_id = sale.get('id')
        customer_name = sale.get('customer_name', '')
        total_amount = sale.get('total_amount', 0)
        return_status = sale.get('return_status', 0)
        items = sale.get('items', [])
        
        self.invoice_id_label.setText(f"رقم الفاتورة: {sale_id}")
        self.customer_name_label.setText(f"العميل: {customer_name}")
        self.invoice_total_label.setText(f"الإجمالي: {total_amount:,.2f} ج.م")
        
        status_text = {0: "قابل للإرجاع", 1: "مرتجع جزئي", 2: "مرتجع كلي"}
        status_color = {0: COLORS['success'], 1: COLORS['warning'], 2: COLORS['text_muted']}
        status = status_text.get(return_status, "غير معروف")
        self.invoice_status_label.setText(f"الحالة: {status}")
        self.invoice_status_label.setStyleSheet(f"color: {status_color.get(return_status, COLORS['text_muted'])}; font-weight: bold; font-size: 13px;")
        
        if return_status == 2:
            self.btn_process_return.setEnabled(False)
            self.btn_process_return.setToolTip("هذه الفاتورة تم إرجاعها بالكامل")
            self.show_warning_toast("⚠️ هذه الفاتورة تم إرجاعها بالكامل ولا يمكن إرجاعها مرة أخرى")
        else:
            self.btn_process_return.setEnabled(True)
            self.btn_process_return.setToolTip("تنفيذ مرتجع للفاتورة المحددة")
        
        self.btn_reset_return.setEnabled(True)
        
        self.current_sale_items = items
        for row, item in enumerate(items):
            self.items_table.insertRow(row)
            self.items_table.setRowHeight(row, 40)
            
            name_item = QTableWidgetItem(f"🛒 {item.get('name', '')}")
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.items_table.setItem(row, 0, name_item)
            
            price_item = QTableWidgetItem(f"{item.get('price', 0):,.2f} ج.م")
            price_item.setTextAlignment(Qt.AlignCenter)
            price_item.setForeground(QColor(COLORS['success']))
            self.items_table.setItem(row, 1, price_item)
            
            qty_sold = item.get('quantity', 0)
            qty_item = QTableWidgetItem(str(int(qty_sold) if qty_sold == int(qty_sold) else f"{qty_sold:.3f}"))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.items_table.setItem(row, 2, qty_item)
            
            return_qty_item = QTableWidgetItem("0")
            return_qty_item.setTextAlignment(Qt.AlignCenter)
            return_qty_item.setForeground(QColor(COLORS['warning']))
            self.items_table.setItem(row, 3, return_qty_item)
            
            btn_add = QPushButton("➕ إرجاع")
            btn_add.setFixedSize(80, 28)
            btn_add.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['warning']};
                    color: white;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: bold;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['warning_hover']};
                }}
            """)
            btn_add.clicked.connect(lambda _, r=row: self.add_item_to_return(r))
            self.items_table.setCellWidget(row, 4, btn_add)
    
    def add_item_to_return(self, row):
        try:
            item = self.current_sale_items[row] if row < len(self.current_sale_items) else None
            if item:
                self.show_info_toast(f"📦 تم إضافة {item.get('name', '')} لقائمة المرتجع")
                qty_item = self.items_table.item(row, 3)
                if qty_item:
                    current_qty = float(qty_item.text()) if qty_item.text() else 0
                    qty_item.setText(str(current_qty + 1))
                    qty_item.setForeground(QColor(COLORS['success']))
        except Exception as e:
            logger.error(f"خطأ في add_item_to_return: {e}")
    
    def process_return(self):
        try:
            sale_id = self.invoice_id_label.text().replace("رقم الفاتورة: ", "")
            if not sale_id or sale_id == "-":
                self.show_warning_toast("⚠️ لا توجد فاتورة محددة")
                return
            
            sale = db.get_sale_by_id(int(sale_id))
            if not sale:
                self.show_warning_toast("❌ الفاتورة غير موجودة")
                return
            
            if sale.get('return_status', 0) == 2:
                self.show_warning_toast("❌ هذه الفاتورة تم إرجاعها بالكامل")
                return
            
            items = sale.get('items', [])
            customer_name = sale.get('customer_name', '')
            
            dlg = SalesReturnForm(sale.get('id'), items, customer_name, self)
            dlg.return_completed.connect(self.on_return_completed)
            dlg.exec()
            
        except Exception as e:
            logger.error(f"خطأ في process_return: {e}")
            self.show_warning_toast(f"❌ خطأ في معالجة المرتجع: {str(e)}")
    
    def on_return_completed(self, result):
        try:
            sale_id = result.get('sale_id')
            items = result.get('items', [])
            total_refund = result.get('total_refund', 0)
            refund_method = result.get('refund_method', '')
            reason = result.get('reason', '')
            customer_name = result.get('customer_name', '')
            
            success, msg = db.process_sales_return(sale_id, items, reason, "Admin")
            if success:
                method_display = "نقداً من الخزينة" if refund_method == "نقداً" else "رصيد في حساب العميل"
                
                msg_text = f"✅ تم تنفيذ المرتجع بنجاح!\n"
                msg_text += f"📦 عدد المنتجات: {len(items)}\n"
                msg_text += f"💰 المبلغ المسترد: {total_refund:,.2f} ج.م\n"
                msg_text += f"💳 طريقة الإرجاع: {method_display}\n"
                msg_text += f"👤 العميل: {customer_name if customer_name else 'غير محدد'}"
                
                if reason:
                    msg_text += f"\n📝 السبب: {reason}"
                
                self.show_toast(msg_text, 4000)
                self.return_processed.emit(result)
                self.search_input.clear()
                self.clear_invoice_display()
                self.show_info_toast(f"🔄 تم تحديث حالة الفاتورة رقم {sale_id}")
            else:
                self.show_warning_toast(f"❌ فشل تنفيذ المرتجع: {msg}")
                
        except Exception as e:
            logger.error(f"خطأ في on_return_completed: {e}")
            self.show_warning_toast(f"❌ خطأ في تنفيذ المرتجع: {str(e)}")
    
    def reset_return_process(self):
        self.search_input.clear()
        self.clear_invoice_display()
        self.btn_process_return.setEnabled(False)
        self.btn_reset_return.setEnabled(False)
        self.show_info_toast("🔄 تم إلغاء عملية الارتجاع وتصفير الشاشة")


if __name__ == "__main__":
    app = QApplication([])
    window = SalesReturnWindow()
    window.showMaximized()
    app.exec_()