# ================= add_product_ui.py - إدارة المنتجات والمخزون =================
"""
add_product_ui.py - واجهة إدارة المنتجات والمخزون
مع دعم: تواريخ الصلاحية (بداية الاستلام + نهاية الصلاحية)، حد الطلب الأدنى،
نظام الجرد الذكي، التصنيف اليدوي، قوائم الأسعار، العروض
📌 تعمل فقط مع قاعدة البيانات الفعلية - لا توجد بيانات افتراضية
"""

import logging
import random
import re
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFrame, QSizePolicy, QScrollArea, QSplitter,
    QDateEdit, QCheckBox, QSpinBox, QApplication, QDialog,
    QMessageBox, QGroupBox, QDoubleSpinBox, QGridLayout, QInputDialog
)
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer, pyqtSignal, QDate

from back.database import (
    add_product, get_all_products, update_product, delete_product,
    get_price_lists, get_product_prices, set_product_price,
    get_applicable_promotion, add_promotion, update_promotion,
    delete_promotion, get_product_promotions
)

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== الألوان ==========
COLORS = {
    'bg_dark': '#F3F7F7',            # الخلفية الأساسية (فاتحة)
    'bg_sidebar': '#FFFFFF',         # خلفية القائمة الجانبية (بيضاء نقية)
    'bg_card': '#FFFFFF',            # خلفية الكروت والكتل (بيضاء)
    'text': '#1e293b',               # نصوص رئيسية واضحة وغامقة
    'text_muted': '#64748b',         # نصوص فرعية هادئة
    'accent': '#0284c7',             # اللون الأساسي المتناسق
    'accent_hover': '#0369a1',
    'success': '#16a34a',            # أخضر للنجاح
    'success_hover': '#15803d',
    'danger': '#dc2626',             # أحمر للحذف والتنبيهات
    'danger_hover': '#b91c1c',
    'warning': '#d97706',            # برتقالي للتحذيرات
    'warning_hover': '#b45309',
    'info': '#0284c7',
    'info_hover': '#0369a1',
    'border': '#cbd5e1',             # حدود واضحة ومناسبة للفاتح
    'warning_bg': 'rgba(217, 119, 6, 0.12)',  # خلفيات تحذيرية خفيفة وواضحة عالفاتح
    'danger_bg': 'rgba(220, 38, 38, 0.12)',   # خلفيات خطأ خفيفة
    'success_bg': 'rgba(22, 163, 74, 0.12)',  # خلفيات نجاح خفيفة
}
FIELD_STYLE = f"""
    QLineEdit {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 13px;
        min-height: 32px;
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
        padding: 8px 10px;
        font-size: 13px;
        min-height: 32px;
    }}
    QComboBox:focus {{
        border: 2px solid {COLORS['accent']};
    }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox::down-arrow {{ image: none; }}
    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text']};
        selection-background-color: {COLORS['accent']};
        border: 1px solid {COLORS['border']};
    }}
    QDateEdit {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 13px;
        min-height: 32px;
    }}
    QDateEdit:focus {{
        border: 2px solid {COLORS['accent']};
    }}
    QDateEdit::drop-down {{ border: none; }}
    QCheckBox {{
        color: {COLORS['text']};
        font-size: 12px;
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {COLORS['border']};
        background-color: {COLORS['bg_dark']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {COLORS['accent']};
        border: 2px solid {COLORS['accent']};
    }}
    QDoubleSpinBox {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 13px;
        min-height: 32px;
    }}
    QDoubleSpinBox:focus {{
        border: 2px solid {COLORS['accent']};
    }}
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        background-color: {COLORS['bg_sidebar']};
        border: none;
        width: 16px;
    }}
    QSpinBox {{
        background-color: {COLORS['bg_dark']};
        color: {COLORS['text']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px 10px;
        font-size: 13px;
        min-height: 32px;
    }}
    QSpinBox:focus {{
        border: 2px solid {COLORS['accent']};
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {COLORS['bg_sidebar']};
        border: none;
        width: 16px;
    }}
"""

LABEL_STYLE = f"""
    QLabel {{
        color: {COLORS['text_muted']};
        font-size: 11px;
        font-weight: bold;
    }}
"""

TOTAL_PIECES_STYLE = f"""
    QLabel {{
        background-color: {COLORS['accent']};
        color: {COLORS['bg_dark']};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
        font-weight: bold;
    }}
"""

WARNING_PIECES_STYLE = f"""
    QLabel {{
        background-color: {COLORS['warning']};
        color: white;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
        font-weight: bold;
    }}
"""

DANGER_PIECES_STYLE = f"""
    QLabel {{
        background-color: {COLORS['danger']};
        color: white;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
        font-weight: bold;
    }}
"""


# ========== نظام Toast موحد ==========
class ToastMessage(QLabel):
    def __init__(self, parent, message, duration=2500):
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


# ========== نافذة إدارة قوائم الأسعار (ضمن المنتج) ==========
class PriceListManagerWidget(QWidget):
    def __init__(self, product_id=None, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.price_list_widgets = {}
        self.init_ui()
        if product_id:
            self.load_prices()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title = QLabel("📊 أسعار قوائم الأسعار")
        title.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 13px;")
        layout.addWidget(title)
        
        self.price_list_container = QWidget()
        self.price_list_layout = QVBoxLayout(self.price_list_container)
        self.price_list_layout.setContentsMargins(0, 0, 0, 0)
        self.price_list_layout.setSpacing(6)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        scroll.setWidget(self.price_list_container)
        scroll.setMaximumHeight(200)
        layout.addWidget(scroll)
        
        self.load_price_lists()
    
    def set_product_id(self, product_id):
        self.product_id = product_id
        if product_id:
            self.load_prices()
    
    def load_price_lists(self):
        """تحميل قوائم الأسعار المتاحة"""
        try:
            # مسح الحقول الحالية
            for widget in self.price_list_widgets.values():
                self.price_list_layout.removeWidget(widget['widget'])
                widget['widget'].deleteLater()
            self.price_list_widgets.clear()
            
            price_lists = get_price_lists()
            if not price_lists:
                no_lists = QLabel("لا توجد قوائم أسعار. يمكنك إضافتها من الإعدادات.")
                no_lists.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
                self.price_list_layout.addWidget(no_lists)
                return
            
            for pl in price_lists:
                pl_id = pl.get('id')
                pl_name = pl.get('name')
                
                # إنشاء صف لكل قائمة
                row_widget = QFrame()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 2, 0, 2)
                row_layout.setSpacing(10)
                
                label = QLabel(pl_name)
                label.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px; min-width: 120px;")
                row_layout.addWidget(label)
                
                price_spin = QDoubleSpinBox()
                price_spin.setRange(0, 999999999)
                price_spin.setPrefix("ج.م ")
                price_spin.setDecimals(2)
                price_spin.setMinimumWidth(130)
                price_spin.setStyleSheet(FIELD_STYLE)
                price_spin.valueChanged.connect(lambda v, pid=pl_id: self.on_price_changed(pid, v))
                row_layout.addWidget(price_spin)
                
                row_layout.addStretch()
                self.price_list_layout.addWidget(row_widget)
                
                self.price_list_widgets[pl_id] = {
                    'widget': row_widget,
                    'spin': price_spin,
                    'name': pl_name
                }
            
        except Exception as e:
            logger.error(f"خطأ في load_price_lists: {e}")
    
    def load_prices(self):
        """تحميل أسعار المنتج في قوائم الأسعار"""
        if not self.product_id:
            return
        
        try:
            prices = get_product_prices(self.product_id)
            for pl_id, price in prices.items():
                if pl_id in self.price_list_widgets:
                    self.price_list_widgets[pl_id]['spin'].blockSignals(True)
                    self.price_list_widgets[pl_id]['spin'].setValue(price)
                    self.price_list_widgets[pl_id]['spin'].blockSignals(False)
        except Exception as e:
            logger.error(f"خطأ في load_prices: {e}")
    
    def on_price_changed(self, pl_id, value):
        """تغيير السعر في قائمة السعر"""
        if not self.product_id:
            return
        
        try:
            set_product_price(self.product_id, pl_id, value)
        except Exception as e:
            logger.error(f"خطأ في on_price_changed: {e}")
    
    def clear_prices(self):
        """مسح الأسعار عند تفريغ النموذج"""
        for pl_id, data in self.price_list_widgets.items():
            data['spin'].blockSignals(True)
            data['spin'].setValue(0)
            data['spin'].blockSignals(False)


# ========== نافذة إدارة العروض (ضمن المنتج) ==========
class PromotionManagerWidget(QWidget):
    def __init__(self, product_id=None, parent=None):
        super().__init__(parent)
        self.product_id = product_id
        self.promotion_id = None
        self.init_ui()
        if product_id:
            self.load_promotion()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        title = QLabel("🎯 ربط عرض بالمنتج")
        title.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold; font-size: 13px;")
        layout.addWidget(title)
        
        # نوع العرض
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        
        promo_label = QLabel("نوع العرض:")
        promo_label.setStyleSheet(LABEL_STYLE)
        row1.addWidget(promo_label)
        
        self.promo_type_combo = QComboBox()
        self.promo_type_combo.addItems(["بدون عرض", "اشتري X واحصل على Y", "خصم نسبة مئوية", "خصم مبلغ ثابت"])
        self.promo_type_combo.setStyleSheet(FIELD_STYLE)
        self.promo_type_combo.currentIndexChanged.connect(self.toggle_promo_fields)
        row1.addWidget(self.promo_type_combo)
        row1.addStretch()
        layout.addLayout(row1)
        
        # حقول العروض - جميعها متاحة دائماً
        self.promo_fields_widget = QWidget()
        promo_fields_layout = QGridLayout(self.promo_fields_widget)
        promo_fields_layout.setSpacing(8)
        promo_fields_layout.setContentsMargins(0, 5, 0, 5)
        
        # اشتري X (إدخال يدوي) - متاح دائماً
        lbl_buy = QLabel("الكمية المشتراة:")
        lbl_buy.setStyleSheet(LABEL_STYLE)
        promo_fields_layout.addWidget(lbl_buy, 0, 0)
        self.buy_qty_input = QLineEdit()
        self.buy_qty_input.setPlaceholderText("مثال: 2")
        self.buy_qty_input.setText("2")
        self.buy_qty_input.setStyleSheet(FIELD_STYLE)
        promo_fields_layout.addWidget(self.buy_qty_input, 0, 1)
        
        # احصل على Y (إدخال يدوي) - متاح دائماً
        lbl_free = QLabel("الكمية المجانية:")
        lbl_free.setStyleSheet(LABEL_STYLE)
        promo_fields_layout.addWidget(lbl_free, 0, 2)
        self.free_qty_input = QLineEdit()
        self.free_qty_input.setPlaceholderText("مثال: 1")
        self.free_qty_input.setText("1")
        self.free_qty_input.setStyleSheet(FIELD_STYLE)
        promo_fields_layout.addWidget(self.free_qty_input, 0, 3)
        
        # قيمة الخصم (إدخال يدوي) - متاح دائماً
        lbl_value = QLabel("قيمة الخصم:")
        lbl_value.setStyleSheet(LABEL_STYLE)
        promo_fields_layout.addWidget(lbl_value, 1, 0)
        
        # إطار لحقل الخصم مع تلميح النوع
        value_container = QWidget()
        value_layout = QHBoxLayout(value_container)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(5)
        
        self.promo_value_input = QLineEdit()
        self.promo_value_input.setPlaceholderText("أدخل قيمة الخصم")
        self.promo_value_input.setStyleSheet(FIELD_STYLE)
        value_layout.addWidget(self.promo_value_input, 1)
        
        self.promo_value_suffix = QLabel("%")
        self.promo_value_suffix.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: bold;")
        self.promo_value_suffix.setVisible(False)
        value_layout.addWidget(self.promo_value_suffix)
        
        promo_fields_layout.addWidget(value_container, 1, 1)
        
        # وصف العرض
        lbl_desc = QLabel("وصف العرض:")
        lbl_desc.setStyleSheet(LABEL_STYLE)
        promo_fields_layout.addWidget(lbl_desc, 1, 2)
        self.promo_desc_input = QLineEdit()
        self.promo_desc_input.setPlaceholderText("وصف العرض (اختياري)")
        self.promo_desc_input.setStyleSheet(FIELD_STYLE)
        promo_fields_layout.addWidget(self.promo_desc_input, 1, 3)
        
        layout.addWidget(self.promo_fields_widget)
        self.toggle_promo_fields(0)
    
    def set_product_id(self, product_id):
        self.product_id = product_id
        if product_id:
            self.load_promotion()
    
    def toggle_promo_fields(self, index):
        """تغيير تلميحات الحقول حسب نوع العرض (جميع الحقل متاحة دائماً)"""
        
        # جميع الحقول متاحة دائماً للإدخال (ما عدا حالة "بدون عرض")
        if index == 0:  # بدون عرض
            self.buy_qty_input.setEnabled(False)
            self.buy_qty_input.setPlaceholderText("غير مطلوب")
            self.free_qty_input.setEnabled(False)
            self.free_qty_input.setPlaceholderText("غير مطلوب")
            self.promo_value_input.setEnabled(False)
            self.promo_value_input.setPlaceholderText("غير مطلوب")
            self.promo_value_suffix.setVisible(False)
            self.promo_desc_input.setEnabled(False)
            self.promo_desc_input.setPlaceholderText("غير مطلوب")
        
        elif index == 1:  # اشتري X واحصل على Y
            # جميع الحقول متاحة
            self.buy_qty_input.setEnabled(True)
            self.buy_qty_input.setPlaceholderText("أدخل الكمية المشتراة (مثال: 2)")
            self.free_qty_input.setEnabled(True)
            self.free_qty_input.setPlaceholderText("أدخل الكمية المجانية (مثال: 1)")
            self.promo_value_input.setEnabled(True)
            self.promo_value_input.setPlaceholderText("أدخل قيمة الخصم (اختياري)")
            self.promo_value_suffix.setText("ج.م")
            self.promo_value_suffix.setVisible(True)
            self.promo_desc_input.setEnabled(True)
            self.promo_desc_input.setPlaceholderText("وصف العرض (اختياري)")
        
        elif index == 2:  # خصم نسبة مئوية
            # جميع الحقول متاحة، مع تغيير تلميحات الخصم
            self.buy_qty_input.setEnabled(True)
            self.buy_qty_input.setPlaceholderText("الكمية المشتراة (اختياري)")
            self.free_qty_input.setEnabled(True)
            self.free_qty_input.setPlaceholderText("الكمية المجانية (اختياري)")
            self.promo_value_input.setEnabled(True)
            self.promo_value_input.setPlaceholderText("أدخل نسبة الخصم (مثال: 10)")
            self.promo_value_suffix.setText("%")
            self.promo_value_suffix.setVisible(True)
            self.promo_desc_input.setEnabled(True)
            self.promo_desc_input.setPlaceholderText("وصف العرض (اختياري)")
        
        elif index == 3:  # خصم مبلغ ثابت
            # جميع الحقول متاحة، مع تغيير تلميحات الخصم
            self.buy_qty_input.setEnabled(True)
            self.buy_qty_input.setPlaceholderText("الكمية المشتراة (اختياري)")
            self.free_qty_input.setEnabled(True)
            self.free_qty_input.setPlaceholderText("الكمية المجانية (اختياري)")
            self.promo_value_input.setEnabled(True)
            self.promo_value_input.setPlaceholderText("أدخل قيمة الخصم بالجنيه (مثال: 5.50)")
            self.promo_value_suffix.setText("ج.م")
            self.promo_value_suffix.setVisible(True)
            self.promo_desc_input.setEnabled(True)
            self.promo_desc_input.setPlaceholderText("وصف العرض (اختياري)")
    
    def load_promotion(self):
        """تحميل العرض المرتبط بالمنتج"""
        if not self.product_id:
            return
        
        try:
            promotion = get_product_promotions(self.product_id)
            if promotion:
                self.promotion_id = promotion.get('id')
                promo_type = promotion.get('promo_type', '')
                
                # تحميل القيم حسب النوع
                if promo_type == 'buy_x_get_y':
                    self.promo_type_combo.setCurrentIndex(1)
                    self.buy_qty_input.setText(str(promotion.get('buy_qty', 2)))
                    self.free_qty_input.setText(str(promotion.get('get_qty', 1)))
                    self.promo_value_input.setText(str(promotion.get('discount_value', 0)))
                elif promo_type == 'percent':
                    self.promo_type_combo.setCurrentIndex(2)
                    self.buy_qty_input.setText(str(promotion.get('buy_qty', 0)) if promotion.get('buy_qty', 0) > 0 else "")
                    self.free_qty_input.setText(str(promotion.get('get_qty', 0)) if promotion.get('get_qty', 0) > 0 else "")
                    self.promo_value_input.setText(str(promotion.get('discount_value', 0)))
                elif promo_type == 'fixed_amount':
                    self.promo_type_combo.setCurrentIndex(3)
                    self.buy_qty_input.setText(str(promotion.get('buy_qty', 0)) if promotion.get('buy_qty', 0) > 0 else "")
                    self.free_qty_input.setText(str(promotion.get('get_qty', 0)) if promotion.get('get_qty', 0) > 0 else "")
                    self.promo_value_input.setText(str(promotion.get('discount_value', 0)))
                else:
                    self.promo_type_combo.setCurrentIndex(0)
                
                self.promo_desc_input.setText(promotion.get('name', ''))
                
                # تحديث حالة الحقول
                self.toggle_promo_fields(self.promo_type_combo.currentIndex())
        except Exception as e:
            logger.error(f"خطأ في load_promotion: {e}")
    
    def get_promotion_data(self):
        """الحصول على بيانات العرض لحفظها"""
        promo_type_index = self.promo_type_combo.currentIndex()
        
        if promo_type_index == 0:
            return None
        
        promo_name = self.promo_desc_input.text().strip()
        if not promo_name:
            promo_name = f"عرض {datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        data = {
            'name': promo_name,
            'product_id': self.product_id,
            'promo_type': '',
            'discount_value': 0,
            'buy_qty': 0,
            'get_qty': 0
        }
        
        # قراءة القيم من جميع الحقول (بغض النظر عن النوع)
        try:
            buy_qty_text = self.buy_qty_input.text().strip()
            data['buy_qty'] = int(buy_qty_text) if buy_qty_text and buy_qty_text.isdigit() else 0
        except ValueError:
            data['buy_qty'] = 0
        
        try:
            free_qty_text = self.free_qty_input.text().strip()
            data['get_qty'] = int(free_qty_text) if free_qty_text and free_qty_text.isdigit() else 0
        except ValueError:
            data['get_qty'] = 0
        
        try:
            value_text = self.promo_value_input.text().strip()
            data['discount_value'] = float(value_text) if value_text else 0
        except ValueError:
            data['discount_value'] = 0
        
        # تعيين نوع العرض
        if promo_type_index == 1:
            data['promo_type'] = 'buy_x_get_y'
        elif promo_type_index == 2:
            data['promo_type'] = 'percent'
        elif promo_type_index == 3:
            data['promo_type'] = 'fixed_amount'
        
        return data
    
    def save_promotion(self):
        """حفظ العرض مباشرة في قاعدة البيانات"""
        if not self.product_id:
            return False, "لا يوجد منتج محدد"
        
        promo_data = self.get_promotion_data()
        if not promo_data:
            # حذف العرض إذا كان موجوداً
            if self.promotion_id:
                try:
                    delete_promotion(self.promotion_id)
                    self.promotion_id = None
                    return True, "تم حذف العرض"
                except Exception as e:
                    logger.error(f"خطأ في حذف العرض: {e}")
                    return False, f"خطأ في حذف العرض: {str(e)}"
            return True, "لا يوجد عرض للحفظ"
        
        # التحقق من صحة البيانات حسب نوع العرض
        if promo_data['promo_type'] == 'buy_x_get_y':
            if promo_data['buy_qty'] <= 0 or promo_data['get_qty'] <= 0:
                return False, "يرجى إدخال قيم صحيحة للكمية المشتراة والمجانية"
        elif promo_data['promo_type'] in ['percent', 'fixed_amount']:
            if promo_data['discount_value'] <= 0:
                return False, "يرجى إدخال قيمة خصم صحيحة"
        
        try:
            # حذف العرض القديم إذا كان موجوداً
            if self.promotion_id:
                delete_promotion(self.promotion_id)
                self.promotion_id = None
            
            # إضافة العرض الجديد
            result = add_promotion(
                name=promo_data['name'],
                promo_type=promo_data['promo_type'],
                product_id=self.product_id,
                buy_qty=promo_data.get('buy_qty', 0),
                get_qty=promo_data.get('get_qty', 0),
                discount_value=promo_data.get('discount_value', 0),
                is_active=True
            )
            
            if result[0]:
                # تحديث promotion_id
                promotions = get_product_promotions(self.product_id)
                if promotions:
                    self.promotion_id = promotions.get('id')
                return True, "تم حفظ العرض بنجاح"
            else:
                return False, result[1]
        except Exception as e:
            logger.error(f"خطأ في save_promotion: {e}")
            return False, str(e)
    
    def clear_promotion(self):
        """مسح بيانات العرض عند تفريغ النموذج"""
        self.promotion_id = None
        self.promo_type_combo.setCurrentIndex(0)
        self.buy_qty_input.setText("2")
        self.free_qty_input.setText("1")
        self.promo_value_input.clear()
        self.promo_desc_input.clear()
        
        # إعادة تعيين حالة الحقول
        self.toggle_promo_fields(0)


class AddProductWindow(QWidget):
    product_saved = pyqtSignal()
    product_deleted = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.current_product_id = None
        self.inventory_mode = False
        self.modified_items = {}
        self.products = []
        self.price_list_manager = None
        self.promotion_manager = None
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة الفعلي ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        # حساب حجم النافذة بناءً على حجم الشاشة الفعلي
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(1024, 700)        
        self.init_ui()
        self.setup_connections()
        self.load_data()

    # ===== دوال Toast الموحدة =====
    def show_toast(self, message, duration=2500):
        ToastMessage(self, message, duration)
    
    def show_success_toast(self, message):
        self.show_toast(message)
    
    def show_warning_toast(self, message):
        self.show_toast(message)
    
    def show_info_toast(self, message):
        self.show_toast(message)
    
    def show_danger_toast(self, message):
        self.show_toast(message)

    def setup_connections(self):
        self.cartons_input.textChanged.connect(self.update_total_quantity)
        self.pieces_per_carton_input.textChanged.connect(self.update_total_quantity)
        self.pieces_in_carton_input.textChanged.connect(self.update_total_quantity)
        self.alert_limit_input.textChanged.connect(self.update_total_quantity)
        self.reorder_level_input.textChanged.connect(self.update_total_quantity)
        self.has_expiry_check.toggled.connect(self.toggle_expiry_date)
        self.category_input.textChanged.connect(self.update_total_quantity)
        
        for widget in [self.name_input, self.barcode_input, self.purchase_price_input,
                       self.wholesale_price_input, self.sell_price_input, 
                       self.cartons_input, self.pieces_per_carton_input,
                       self.pieces_in_carton_input, self.alert_limit_input,
                       self.reorder_level_input, self.category_input]:
            if hasattr(widget, 'returnPressed'):
                widget.returnPressed.connect(self.save_handle)

    def toggle_expiry_date(self, checked):
        self.receive_date_edit.setEnabled(checked)
        self.expiry_date_edit.setEnabled(checked)
        if not checked:
            self.receive_date_edit.setDate(QDate.currentDate())
            self.expiry_date_edit.setDate(QDate.currentDate().addDays(180))

    def update_total_quantity(self):
        try:
            weight_unit = self.weight_unit_combo.currentText()
            
            if weight_unit in ["قطعة", "كرتونة"]:
                cartons_text = self.cartons_input.text().strip()
                pieces_per_carton_text = self.pieces_per_carton_input.text().strip()
                extra_pieces_text = self.pieces_in_carton_input.text().strip()
                
                cartons = int(cartons_text) if cartons_text and cartons_text.isdigit() else 0
                pieces_per_carton = int(pieces_per_carton_text) if pieces_per_carton_text and pieces_per_carton_text.isdigit() else 1
                extra_pieces = int(extra_pieces_text) if extra_pieces_text and extra_pieces_text.isdigit() else 0
                
                if pieces_per_carton <= 0:
                    pieces_per_carton = 1
                
                total = (cartons * pieces_per_carton) + extra_pieces
                self.total_pieces_label.setText(f"📦 إجمالي القطع في المخزن: {total:,} قطعة")
                self.stock_input.setText(str(total))
                
            else:
                weight_text = self.cartons_input.text().strip()
                weight = float(weight_text) if weight_text and self._is_float(weight_text) else 0
                self.total_pieces_label.setText(f"📦 إجمالي الكمية: {weight:.2f} {weight_unit}")
                self.stock_input.setText(str(weight))
            
            alert_limit = int(self.alert_limit_input.text()) if self.alert_limit_input.text().isdigit() else 5
            reorder_level = int(self.reorder_level_input.text()) if self.reorder_level_input.text().isdigit() else 10
            current_total = float(self.stock_input.text()) if self.stock_input.text() else 0
            
            if current_total <= alert_limit:
                self.total_pieces_label.setStyleSheet(DANGER_PIECES_STYLE)
            elif current_total <= reorder_level:
                self.total_pieces_label.setStyleSheet(WARNING_PIECES_STYLE)
            else:
                self.total_pieces_label.setStyleSheet(TOTAL_PIECES_STYLE)
                
        except ValueError:
            self.total_pieces_label.setText("📦 إجمالي الكمية: خطأ في الإدخال")
            self.total_pieces_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {COLORS['warning']};
                    color: white;
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 14px;
                    font-weight: bold;
                }}
            """)
        except Exception as e:
            logger.error(f"خطأ في update_total_quantity: {e}")

    def _is_float(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def parse_stock_to_cartons_and_pieces(self, total_stock, sub_unit_qty):
        try:
            sub_qty = int(sub_unit_qty) if sub_unit_qty else 1
            if sub_qty <= 0:
                sub_qty = 1
            
            if sub_qty == 1:
                return 0, int(total_stock)
            
            cartons = int(total_stock) // sub_qty
            remaining_pieces = int(total_stock) % sub_qty
            return cartons, remaining_pieces
        except Exception:
            return 0, int(total_stock)

    def get_total_stock_from_form(self):
        weight_unit = self.weight_unit_combo.currentText()
        
        if weight_unit not in ["قطعة", "كرتونة"]:
            try:
                stock_text = self.cartons_input.text().strip()
                stock = float(stock_text) if stock_text and self._is_float(stock_text) else 0
                return stock, 1
            except ValueError:
                return 0, 1
        
        try:
            cartons_text = self.cartons_input.text().strip()
            pieces_per_carton_text = self.pieces_per_carton_input.text().strip()
            extra_pieces_text = self.pieces_in_carton_input.text().strip()
            
            cartons = int(cartons_text) if cartons_text and cartons_text.isdigit() else 0
            pieces_per_carton = int(pieces_per_carton_text) if pieces_per_carton_text and pieces_per_carton_text.isdigit() else 1
            extra_pieces = int(extra_pieces_text) if extra_pieces_text and extra_pieces_text.isdigit() else 0
            
            if pieces_per_carton <= 0:
                pieces_per_carton = 1
            
            total_pieces = (cartons * pieces_per_carton) + extra_pieces
            return float(total_pieces), pieces_per_carton
        except ValueError:
            return 0, 1

    def on_unit_changed(self, unit):
        if unit in ["قطعة", "كرتونة"]:
            self.lbl_cartons.setText("عدد الكراتين")
            self.cartons_input.setVisible(True)
            self.lbl_pieces_per_carton.setVisible(True)
            self.pieces_per_carton_input.setVisible(True)
            self.lbl_extra_pieces.setVisible(True)
            self.pieces_in_carton_input.setVisible(True)
            
            if not self.cartons_input.text().strip():
                self.cartons_input.setText("0")
            if not self.pieces_per_carton_input.text().strip():
                self.pieces_per_carton_input.setText("1")
            if not self.pieces_in_carton_input.text().strip():
                self.pieces_in_carton_input.setText("0")
        else:
            self.lbl_cartons.setText(f"الكمية ({unit})")
            self.cartons_input.setVisible(True)
            self.lbl_pieces_per_carton.setVisible(False)
            self.pieces_per_carton_input.setVisible(False)
            self.lbl_extra_pieces.setVisible(False)
            self.pieces_in_carton_input.setVisible(False)
            
            if not self.cartons_input.text().strip():
                self.cartons_input.setText("0")
            self.pieces_per_carton_input.setText("1")
            self.pieces_in_carton_input.setText("0")
        
        self.update_total_quantity()

    def generate_barcode(self):
        barcode = str(random.randint(1000000000000, 9999999999999))
        self.barcode_input.setText(barcode)
        self.show_info_toast("🎯 تم توليد باركود جديد")

    def load_data(self):
        self.table.setRowCount(0)
        self.table.blockSignals(True)
        
        try:
            db_products = get_all_products()
            if db_products:
                self.products = db_products
            else:
                self.products = []
        except Exception as e:
            logger.error(f"خطأ في تحميل البيانات: {e}")
            self.products = []
            self.show_warning_toast(f"❌ خطأ في تحميل البيانات: {str(e)}")
        
        for p in self.products:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 45)
            
            def centered(text):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignCenter)
                return item
            
            product_id = p.get('id', 0)
            product_name = p.get('name', '')
            barcode = p.get('barcode', '-')
            purchase_price = p.get('purchase_price', 0)
            sell_price = p.get('sell_price', 0)
            price_wholesale = p.get('price_wholesale', 0)
            stock = float(p.get('stock', 0))
            actual_stock = float(p.get('actual_stock', stock))
            alert_limit = p.get('alert_limit', 5)
            reorder_level = p.get('reorder_level', 10)
            weight_unit = p.get('weight_unit', 'قطعة')
            sub_unit_qty = p.get('sub_unit_qty', 1)
            expiry_date = p.get('expiry_date', '')
            receive_date = p.get('receive_date', '')
            category = p.get('category', '')
            
            variance = actual_stock - stock
            
            self.table.setItem(row, 0, centered(product_id))
            self.table.setItem(row, 1, QTableWidgetItem(product_name))
            self.table.setItem(row, 2, centered(barcode))
            
            purchase_item = QTableWidgetItem(f"{float(purchase_price):.2f}")
            purchase_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, purchase_item)
            
            wholesale_item = QTableWidgetItem(f"{float(price_wholesale):.2f}")
            wholesale_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 4, wholesale_item)
            
            price_item = QTableWidgetItem(f"{float(sell_price):.2f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 5, price_item)
            
            stock_item = QTableWidgetItem(f"{stock:.2f}" if weight_unit != "قطعة" else f"{stock:.0f}")
            stock_item.setTextAlignment(Qt.AlignCenter)
            stock_item.setFlags(stock_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 6, stock_item)
            
            actual_item = QTableWidgetItem(f"{actual_stock:.2f}" if weight_unit != "قطعة" else f"{actual_stock:.0f}")
            actual_item.setTextAlignment(Qt.AlignCenter)
            if self.inventory_mode:
                actual_item.setFlags(actual_item.flags() | Qt.ItemIsEditable)
            else:
                actual_item.setFlags(actual_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 7, actual_item)
            
            variance_item = QTableWidgetItem(f"{variance:+.2f}" if variance != 0 else "0.00")
            variance_item.setTextAlignment(Qt.AlignCenter)
            variance_item.setFlags(variance_item.flags() & ~Qt.ItemIsEditable)
            if variance < 0:
                variance_item.setForeground(QBrush(QColor(239, 68, 68)))
            elif variance > 0:
                variance_item.setForeground(QBrush(QColor(34, 197, 94)))
            self.table.setItem(row, 8, variance_item)
            
            reorder_item = QTableWidgetItem(str(reorder_level))
            reorder_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 9, reorder_item)
            
            self.table.setItem(row, 10, centered(weight_unit))
            self.table.setItem(row, 11, centered(receive_date if receive_date else "-"))
            self.table.setItem(row, 12, centered(expiry_date if expiry_date else "-"))
            self.table.setItem(row, 13, centered(category if category else "غير مصنف"))
            
            if stock <= alert_limit:
                self._color_row(row, COLORS['danger_bg'])
            elif stock <= reorder_level:
                self._color_row(row, COLORS['warning_bg'])
            
            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            c_layout = QHBoxLayout(container)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setAlignment(Qt.AlignCenter)
            
            btn_del = QPushButton("🗑️ حذف")
            btn_del.setFixedSize(75, 30)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet(f"""
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
            btn_del.clicked.connect(lambda _, pid=product_id: self.delete_handle(pid))
            c_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 14, container)
        
        self.table.blockSignals(False)

    def _color_row(self, row, color):
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush(QColor(color)))

    def on_cell_changed(self, row, col):
        if col == 7 and self.inventory_mode:
            try:
                stock_item = self.table.item(row, 6)
                if stock_item:
                    stock_text = re.sub(r'[^\d.]', '', stock_item.text().strip())
                    book_stock = float(stock_text) if stock_text else 0
                else:
                    book_stock = 0
                
                actual_item = self.table.item(row, 7)
                if actual_item:
                    actual_text = re.sub(r'[^\d.]', '', actual_item.text().strip())
                    actual_stock = float(actual_text) if actual_text else 0
                else:
                    actual_stock = 0
                
                variance = actual_stock - book_stock
                
                variance_item = QTableWidgetItem(f"{variance:+.2f}" if variance != 0 else "0.00")
                variance_item.setTextAlignment(Qt.AlignCenter)
                variance_item.setFlags(variance_item.flags() & ~Qt.ItemIsEditable)
                if variance < 0:
                    variance_item.setForeground(QBrush(QColor(239, 68, 68)))
                elif variance > 0:
                    variance_item.setForeground(QBrush(QColor(34, 197, 94)))
                self.table.setItem(row, 8, variance_item)
                
                product_id = int(self.table.item(row, 0).text())
                if variance != 0:
                    self.modified_items[product_id] = {
                        'row': row,
                        'book_stock': book_stock,
                        'actual_stock': actual_stock,
                        'variance': variance
                    }
                else:
                    if product_id in self.modified_items:
                        del self.modified_items[product_id]
                
                self.btn_apply_inventory.setEnabled(len(self.modified_items) > 0)
            except Exception as e:
                logger.error(f"خطأ في حساب الفارق: {e}")

    def load_to_form(self, row, col):
        try:
            p_id = int(self.table.item(row, 0).text())
            product = next((p for p in self.products if p.get('id') == p_id), None)
            
            if product:
                self.current_product_id = product.get('id')
                self.name_input.setText(product.get('name', ''))
                self.barcode_input.setText(product.get('barcode', ''))
                self.purchase_price_input.setText(str(product.get('purchase_price', 0)))
                self.wholesale_price_input.setText(str(product.get('price_wholesale', 0)))
                self.sell_price_input.setText(str(product.get('sell_price', 0)))
                
                total_stock = float(product.get('stock', 0))
                
                # تعيين التصنيف (حقل نصي)
                category = product.get('category', '')
                self.category_input.setText(category)
                
                alert_limit = product.get('alert_limit', 5)
                self.alert_limit_input.setText(str(alert_limit))
                reorder_level = product.get('reorder_level', 10)
                self.reorder_level_input.setText(str(reorder_level))
                weight_unit = product.get('weight_unit', 'قطعة')
                sub_unit_qty = product.get('sub_unit_qty', 1)
                
                has_expiry = product.get('has_expiry', False)
                self.has_expiry_check.setChecked(has_expiry)
                
                # تحميل تواريخ الصلاحية
                if has_expiry:
                    if product.get('receive_date'):
                        try:
                            receive_date = QDate.fromString(product['receive_date'], "yyyy-MM-dd")
                            if receive_date.isValid():
                                self.receive_date_edit.setDate(receive_date)
                        except Exception:
                            pass
                    
                    if product.get('expiry_date'):
                        try:
                            expiry_date = QDate.fromString(product['expiry_date'], "yyyy-MM-dd")
                            if expiry_date.isValid():
                                self.expiry_date_edit.setDate(expiry_date)
                        except Exception:
                            pass
                
                self.toggle_expiry_date(has_expiry)
                
                self.weight_unit_combo.setCurrentText(weight_unit)
                
                if weight_unit in ["قطعة", "كرتونة"]:
                    cartons, remaining_pieces = self.parse_stock_to_cartons_and_pieces(total_stock, sub_unit_qty)
                    self.cartons_input.setText(str(cartons))
                    self.pieces_per_carton_input.setText(str(int(sub_unit_qty)))
                    self.pieces_in_carton_input.setText(str(remaining_pieces))
                else:
                    self.cartons_input.setText(f"{total_stock:.2f}")
                    self.pieces_per_carton_input.setText("1")
                    self.pieces_in_carton_input.setText("0")
                
                self.update_total_quantity()
                
                # تحديث قوائم الأسعار والعروض
                if self.price_list_manager:
                    self.price_list_manager.set_product_id(self.current_product_id)
                    self.price_list_manager.load_prices()
                
                if self.promotion_manager:
                    self.promotion_manager.set_product_id(self.current_product_id)
                    self.promotion_manager.load_promotion()
                
                self.btn_save.setText("✏️ تحديث")
                self.label_title.setText("✏️ تعديل منتج")
                self.btn_save.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['warning']};
                        color: white;
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 14px;
                        border: none;
                    }}
                    QPushButton:hover {{ background-color: {COLORS['warning_hover']}; }}
                """)
        except Exception as e:
            logger.error(f"خطأ في load_to_form: {e}")

    def toggle_inventory_mode(self):
        self.inventory_mode = not self.inventory_mode
        
        if self.inventory_mode:
            self.btn_start_inventory.setText("🔒 إنهاء الجرد")
            self.btn_start_inventory.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['danger']};
                    color: white;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 12px;
                    border: none;
                    padding: 0 15px;
                }}
                QPushButton:hover {{ background-color: {COLORS['danger_hover']}; }}
            """)
            self.show_info_toast("📋 تم تفعيل وضع الجرد - يمكنك تعديل الكميات الفعلية")
        else:
            self.btn_start_inventory.setText("📋 بدء جرد")
            self.btn_start_inventory.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['info']};
                    color: white;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 12px;
                    border: none;
                    padding: 0 15px;
                }}
                QPushButton:hover {{ background-color: {COLORS['info_hover']}; }}
            """)
            self.modified_items.clear()
            self.btn_apply_inventory.setEnabled(False)
            self.load_data()
            self.show_info_toast("🔒 تم إنهاء وضع الجرد")
        
        for row in range(self.table.rowCount()):
            actual_item = self.table.item(row, 7)
            if actual_item:
                if self.inventory_mode:
                    actual_item.setFlags(actual_item.flags() | Qt.ItemIsEditable)
                else:
                    actual_item.setFlags(actual_item.flags() & ~Qt.ItemIsEditable)

    def apply_inventory(self):
        if not self.modified_items:
            self.show_warning_toast("⚠️ لا توجد تعديلات في الجرد")
            return
        
        self.show_info_toast(f"📋 جاري اعتماد {len(self.modified_items)} تعديلاً...")
        
        total_variance = 0
        all_success = True
        
        for product_id, data in self.modified_items.items():
            try:
                success = update_product(product_id, stock=data['actual_stock'], actual_stock=data['actual_stock'])
                if not success:
                    raise Exception("فشل تحديث المخزون في قاعدة البيانات")
                
                for product in self.products:
                    if product.get('id') == product_id:
                        product['stock'] = data['actual_stock']
                        product['actual_stock'] = data['actual_stock']
                        break
                
                total_variance += data['variance']
                
            except Exception as e:
                logger.error(f"خطأ في تحديث المنتج {product_id}: {e}")
                self.show_warning_toast(f"⚠️ خطأ في تحديث المنتج {product_id}: {str(e)}")
                all_success = False
        
        self.modified_items.clear()
        self.btn_apply_inventory.setEnabled(False)
        self.load_data()
        
        if all_success:
            self.show_success_toast(f"✅ تم اعتماد الجرد - إجمالي الفروقات: {total_variance:+.2f}")
        else:
            self.show_warning_toast(f"⚠️ تم اعتماد الجرد مع بعض الأخطاء - إجمالي الفروقات: {total_variance:+.2f}")

    def save_handle(self):
        name = self.name_input.text().strip()
        barcode = self.barcode_input.text().strip()
        category = self.category_input.text().strip()
        alert_limit = self.alert_limit_input.text().strip()
        reorder_level = self.reorder_level_input.text().strip()
        weight_unit = self.weight_unit_combo.currentText()
        has_expiry = self.has_expiry_check.isChecked()
        receive_date = self.receive_date_edit.date().toString("yyyy-MM-dd") if has_expiry else None
        expiry_date = self.expiry_date_edit.date().toString("yyyy-MM-dd") if has_expiry else None
        
        total_stock, sub_unit_qty = self.get_total_stock_from_form()
        
        if not name:
            self.show_warning_toast("⚠️ يرجى إدخال اسم المنتج")
            self.name_input.setFocus()
            return
        
        try:
            purchase_price = float(self.purchase_price_input.text()) if self.purchase_price_input.text() else 0.0
            wholesale_price = float(self.wholesale_price_input.text()) if self.wholesale_price_input.text() else 0.0
            sell_price = float(self.sell_price_input.text()) if self.sell_price_input.text() else 0.0
            
            alert_limit_int = int(alert_limit) if alert_limit and alert_limit.isdigit() else 5
            reorder_level_int = int(reorder_level) if reorder_level and reorder_level.isdigit() else 10
            sub_unit_qty_int = int(sub_unit_qty) if sub_unit_qty and int(sub_unit_qty) > 0 else 1
            
            barcode_value = barcode if barcode else None
            
            if self.current_product_id:
                success = update_product(
                    self.current_product_id,
                    name=name,
                    barcode=barcode_value,
                    purchase_price=purchase_price,
                    sell_price=sell_price,
                    price_wholesale=wholesale_price,
                    stock=total_stock,
                    category=category,
                    alert_limit=alert_limit_int,
                    reorder_level=reorder_level_int,
                    weight_unit=weight_unit,
                    sub_unit_qty=sub_unit_qty_int,
                    has_expiry=has_expiry,
                    receive_date=receive_date,
                    expiry_date=expiry_date
                )
                msg = "تم تحديث المنتج بنجاح" if success else "فشل تحديث المنتج"
                
                # حفظ العرض إذا كان موجوداً
                if success and self.promotion_manager:
                    promo_success, promo_msg = self.promotion_manager.save_promotion()
                    if not promo_success:
                        logger.warning(f"خطأ في حفظ العرض: {promo_msg}")
            else:
                success, msg = add_product(
                    name=name,
                    barcode=barcode_value,
                    purchase_price=purchase_price,
                    sell_price=sell_price,
                    price_wholesale=wholesale_price,
                    stock=total_stock,
                    category=category,
                    alert_limit=alert_limit_int,
                    reorder_level=reorder_level_int,
                    weight_unit=weight_unit,
                    sub_unit_qty=sub_unit_qty_int,
                    has_expiry=has_expiry,
                    receive_date=receive_date,
                    expiry_date=expiry_date
                )
                msg = "تم إضافة المنتج بنجاح" if success else "فشل حفظ المنتج"
                
                # إضافة العرض للمنتج الجديد
                if success and self.promotion_manager:
                    # الحصول على ID المنتج الجديد
                    product_id = None
                    if barcode_value:
                        from back.database import get_product_by_barcode
                        prod = get_product_by_barcode(barcode_value)
                        if prod:
                            product_id = prod.get('id')
                    
                    if product_id:
                        self.promotion_manager.set_product_id(product_id)
                        promo_success, promo_msg = self.promotion_manager.save_promotion()
                        if not promo_success:
                            logger.warning(f"خطأ في حفظ العرض: {promo_msg}")
            
            if success:
                self.load_data()
                self.clear_fields()
                self.show_success_toast(f"✅ {msg}")
                self.product_saved.emit()
            else:
                self.show_warning_toast(f"⚠️ {msg}")
                
        except ValueError as e:
            self.show_warning_toast(f"❌ تأكد من إدخال أرقام صحيحة: {str(e)}")
        except Exception as e:
            logger.error(f"خطأ في save_handle: {e}")
            self.show_warning_toast(f"❌ خطأ غير متوقع: {str(e)}")

    def delete_handle(self, p_id):
        try:
            product_name = None
            for product in self.products:
                if product.get('id') == p_id:
                    product_name = product.get('name', '')
                    break
            
            success = delete_product(p_id)
            
            if success:
                self.products = [p for p in self.products if p.get('id') != p_id]
                self.load_data()
                
                if self.current_product_id == p_id:
                    self.clear_fields()
                
                self.show_success_toast(f"✅ تم حذف المنتج: {product_name if product_name else f'ID:{p_id}'}")
                self.product_deleted.emit()
            else:
                self.show_warning_toast(f"⚠️ فشل حذف المنتج")
        except Exception as e:
            logger.error(f"خطأ في delete_handle: {e}")
            self.show_warning_toast(f"❌ خطأ في الحذف: {str(e)}")

    def clear_fields(self):
        """تفريغ حقول النموذج"""
        # إذا كان هناك منتج محدد، اسأل المستخدم إذا كان يريد حذفه
        if self.current_product_id is not None:
            reply = QMessageBox.question(
                self, "تأكيد الحذف",
                f"هل تريد حذف المنتج الحالي '{self.name_input.text().strip()}'؟",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                # حذف المنتج
                success = delete_product(self.current_product_id)
                if success:
                    self.products = [p for p in self.products if p.get('id') != self.current_product_id]
                    self.load_data()
                    self.show_success_toast(f"✅ تم حذف المنتج بنجاح")
                    self.product_deleted.emit()
                else:
                    self.show_warning_toast(f"⚠️ فشل حذف المنتج")
                    return
            elif reply == QMessageBox.Cancel:
                return
        
        # تفريغ الحقول (بغض النظر عن الحذف أو عدمه)
        self.current_product_id = None
        self.name_input.clear()
        self.barcode_input.clear()
        self.purchase_price_input.clear()
        self.wholesale_price_input.clear()
        self.sell_price_input.clear()
        
        self.cartons_input.setText("0")
        self.pieces_per_carton_input.setText("1")
        self.pieces_in_carton_input.setText("0")
        self.stock_input.clear()
        
        self.category_input.clear()
        self.alert_limit_input.setText("5")
        self.reorder_level_input.setText("10")
        self.weight_unit_combo.setCurrentIndex(0)
        
        self.has_expiry_check.setChecked(True)
        self.receive_date_edit.setDate(QDate.currentDate())
        self.expiry_date_edit.setDate(QDate.currentDate().addDays(180))
        
        self.update_total_quantity()
        
        # مسح قوائم الأسعار والعروض
        if self.price_list_manager:
            self.price_list_manager.set_product_id(None)
            self.price_list_manager.clear_prices()
        
        if self.promotion_manager:
            self.promotion_manager.set_product_id(None)
            self.promotion_manager.clear_promotion()
        
        self.btn_save.setText("💾 حفظ")
        self.label_title.setText("➕ إضافة منتج جديد")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
        """)
        
        self.show_info_toast("🗑️ تم تفريغ النموذج")

    def init_ui(self):
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        main_layout.addWidget(main_splitter)
        
        # ====== تعديل الريسبونسيف: الجزء الأيسر: نموذج الإدخال مع ScrollArea ======
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        # ====== تعديل الريسبونسيف: جعل العرض مرناً بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        form_scroll.setMinimumWidth(int(screen_geometry.width() * 0.35))
        form_scroll.setMaximumWidth(int(screen_geometry.width() * 0.55))
        # ===== الجزء الأيسر: نموذج الإدخال مع ScrollArea =====
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setMinimumWidth(550)
        form_scroll.setMaximumWidth(800)
        form_scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { width: 8px; background: #1e293b; border-radius: 4px; }
        """)
        
        form_frame = QFrame()
        form_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        form_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        outer_layout = QVBoxLayout(form_frame)
        outer_layout.setContentsMargins(20, 20, 20, 20)
        outer_layout.setSpacing(12)
        
        self.label_title = QLabel("➕ إضافة منتج جديد")
        self.label_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']}; margin-bottom: 6px;")
        outer_layout.addWidget(self.label_title)
        
        # ===== الصف الأول: اسم المنتج والباركود =====
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(12)
        
        name_container = QVBoxLayout()
        lbl_name = QLabel("اسم المنتج")
        lbl_name.setStyleSheet(LABEL_STYLE)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("أدخل اسم المنتج")
        self.name_input.setStyleSheet(FIELD_STYLE)
        name_container.addWidget(lbl_name)
        name_container.addWidget(self.name_input)
        
        barcode_container = QVBoxLayout()
        lbl_barcode = QLabel("الباركود")
        lbl_barcode.setStyleSheet(LABEL_STYLE)
        barcode_row = QHBoxLayout()
        barcode_row.setSpacing(6)
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("الباركود")
        self.barcode_input.setStyleSheet(FIELD_STYLE)
        self.btn_generate_barcode = QPushButton("🔲 توليد")
        self.btn_generate_barcode.setFixedWidth(65)
        self.btn_generate_barcode.setMinimumHeight(34)
        self.btn_generate_barcode.setCursor(Qt.PointingHandCursor)
        self.btn_generate_barcode.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {COLORS['info_hover']}; }}
        """)
        self.btn_generate_barcode.clicked.connect(self.generate_barcode)
        barcode_row.addWidget(self.barcode_input, 1)
        barcode_row.addWidget(self.btn_generate_barcode)
        barcode_container.addWidget(lbl_barcode)
        barcode_container.addLayout(barcode_row)
        
        row1_layout.addLayout(name_container, 1)
        row1_layout.addLayout(barcode_container, 1)
        outer_layout.addLayout(row1_layout)
        
        # ===== الصف الثاني: الأسعار الثلاثة =====
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(12)
        
        purchase_container = QVBoxLayout()
        lbl_purchase = QLabel("سعر الشراء")
        lbl_purchase.setStyleSheet(LABEL_STYLE)
        self.purchase_price_input = QLineEdit()
        self.purchase_price_input.setPlaceholderText("0.00")
        self.purchase_price_input.setStyleSheet(FIELD_STYLE)
        purchase_container.addWidget(lbl_purchase)
        purchase_container.addWidget(self.purchase_price_input)
        
        wholesale_container = QVBoxLayout()
        lbl_wholesale = QLabel("سعر الجملة")
        lbl_wholesale.setStyleSheet(LABEL_STYLE)
        self.wholesale_price_input = QLineEdit()
        self.wholesale_price_input.setPlaceholderText("0.00")
        self.wholesale_price_input.setStyleSheet(FIELD_STYLE)
        wholesale_container.addWidget(lbl_wholesale)
        wholesale_container.addWidget(self.wholesale_price_input)
        
        sell_container = QVBoxLayout()
        lbl_sell = QLabel("سعر البيع")
        lbl_sell.setStyleSheet(LABEL_STYLE)
        self.sell_price_input = QLineEdit()
        self.sell_price_input.setPlaceholderText("0.00")
        self.sell_price_input.setStyleSheet(FIELD_STYLE)
        sell_container.addWidget(lbl_sell)
        sell_container.addWidget(self.sell_price_input)
        
        row2_layout.addLayout(purchase_container, 1)
        row2_layout.addLayout(wholesale_container, 1)
        row2_layout.addLayout(sell_container, 1)
        outer_layout.addLayout(row2_layout)
        
        # ===== الصف الثالث: الكميات =====
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(12)
        
        cartons_container = QVBoxLayout()
        self.lbl_cartons = QLabel("عدد الكراتين")
        self.lbl_cartons.setStyleSheet(LABEL_STYLE)
        self.cartons_input = QLineEdit()
        self.cartons_input.setPlaceholderText("0")
        self.cartons_input.setText("0")
        self.cartons_input.setStyleSheet(FIELD_STYLE)
        cartons_container.addWidget(self.lbl_cartons)
        cartons_container.addWidget(self.cartons_input)
        
        pieces_per_carton_container = QVBoxLayout()
        self.lbl_pieces_per_carton = QLabel("عدد القطع في الكرتونة")
        self.lbl_pieces_per_carton.setStyleSheet(LABEL_STYLE)
        self.pieces_per_carton_input = QLineEdit()
        self.pieces_per_carton_input.setPlaceholderText("1")
        self.pieces_per_carton_input.setText("1")
        self.pieces_per_carton_input.setStyleSheet(FIELD_STYLE)
        pieces_per_carton_container.addWidget(self.lbl_pieces_per_carton)
        pieces_per_carton_container.addWidget(self.pieces_per_carton_input)
        
        extra_pieces_container = QVBoxLayout()
        self.lbl_extra_pieces = QLabel("قطع فردية إضافية")
        self.lbl_extra_pieces.setStyleSheet(LABEL_STYLE)
        self.pieces_in_carton_input = QLineEdit()
        self.pieces_in_carton_input.setPlaceholderText("0")
        self.pieces_in_carton_input.setText("0")
        self.pieces_in_carton_input.setStyleSheet(FIELD_STYLE)
        extra_pieces_container.addWidget(self.lbl_extra_pieces)
        extra_pieces_container.addWidget(self.pieces_in_carton_input)
        
        row3_layout.addLayout(cartons_container, 1)
        row3_layout.addLayout(pieces_per_carton_container, 1)
        row3_layout.addLayout(extra_pieces_container, 1)
        outer_layout.addLayout(row3_layout)
        
        # ===== إجمالي الكمية =====
        self.total_pieces_label = QLabel("📦 إجمالي القطع في المخزن: 0 قطعة")
        self.total_pieces_label.setStyleSheet(TOTAL_PIECES_STYLE)
        self.total_pieces_label.setAlignment(Qt.AlignCenter)
        self.total_pieces_label.setMinimumHeight(45)
        outer_layout.addWidget(self.total_pieces_label)
        
        self.stock_input = QLineEdit()
        self.stock_input.setVisible(False)
        
        # ===== الصف الرابع: حدود التنبيه والوحدة =====
        row4_layout = QHBoxLayout()
        row4_layout.setSpacing(12)
        
        alert_container = QVBoxLayout()
        lbl_alert = QLabel("حد التنبيه")
        lbl_alert.setStyleSheet(LABEL_STYLE)
        self.alert_limit_input = QLineEdit()
        self.alert_limit_input.setPlaceholderText("5")
        self.alert_limit_input.setText("5")
        self.alert_limit_input.setStyleSheet(FIELD_STYLE)
        alert_container.addWidget(lbl_alert)
        alert_container.addWidget(self.alert_limit_input)
        
        reorder_container = QVBoxLayout()
        lbl_reorder = QLabel("حد الطلب الأدنى")
        lbl_reorder.setStyleSheet(LABEL_STYLE)
        self.reorder_level_input = QLineEdit()
        self.reorder_level_input.setPlaceholderText("10")
        self.reorder_level_input.setText("10")
        self.reorder_level_input.setStyleSheet(FIELD_STYLE)
        reorder_container.addWidget(lbl_reorder)
        reorder_container.addWidget(self.reorder_level_input)
        
        unit_container = QVBoxLayout()
        lbl_unit = QLabel("وحدة الأوزان")
        lbl_unit.setStyleSheet(LABEL_STYLE)
        self.weight_unit_combo = QComboBox()
        self.weight_unit_combo.addItems(["قطعة", "كرتونة", "كيلو", "لتر"])
        self.weight_unit_combo.setStyleSheet(FIELD_STYLE)
        self.weight_unit_combo.currentTextChanged.connect(self.on_unit_changed)
        unit_container.addWidget(lbl_unit)
        unit_container.addWidget(self.weight_unit_combo)
        
        row4_layout.addLayout(alert_container, 1)
        row4_layout.addLayout(reorder_container, 1)
        row4_layout.addLayout(unit_container, 1)
        outer_layout.addLayout(row4_layout)
        
        # ===== الصف الخامس: التصنيف (إدخال يدوي) =====
        row5_layout = QHBoxLayout()
        row5_layout.setSpacing(12)
        
        category_container = QVBoxLayout()
        lbl_cat = QLabel("التصنيف")
        lbl_cat.setStyleSheet(LABEL_STYLE)
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("أدخل التصنيف يدوياً")
        self.category_input.setStyleSheet(FIELD_STYLE)
        category_container.addWidget(lbl_cat)
        category_container.addWidget(self.category_input)
        
        # ===== تواريخ الصلاحية =====
        expiry_container = QVBoxLayout()
        expiry_row = QHBoxLayout()
        expiry_row.setSpacing(8)
        
        self.has_expiry_check = QCheckBox("يوجد تاريخ انتهاء")
        self.has_expiry_check.setStyleSheet(FIELD_STYLE)
        self.has_expiry_check.setChecked(True)
        expiry_row.addWidget(self.has_expiry_check)
        expiry_container.addLayout(expiry_row)
        
        expiry_dates_layout = QHBoxLayout()
        expiry_dates_layout.setSpacing(10)
        
        receive_container = QVBoxLayout()
        lbl_receive = QLabel("بداية الاستلام")
        lbl_receive.setStyleSheet(LABEL_STYLE)
        self.receive_date_edit = QDateEdit()
        self.receive_date_edit.setDate(QDate.currentDate())
        self.receive_date_edit.setCalendarPopup(True)
        self.receive_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.receive_date_edit.setStyleSheet(FIELD_STYLE)
        receive_container.addWidget(lbl_receive)
        receive_container.addWidget(self.receive_date_edit)
        
        expiry_end_container = QVBoxLayout()
        lbl_expiry_end = QLabel("نهاية الصلاحية")
        lbl_expiry_end.setStyleSheet(LABEL_STYLE)
        self.expiry_date_edit = QDateEdit()
        self.expiry_date_edit.setDate(QDate.currentDate().addDays(180))
        self.expiry_date_edit.setCalendarPopup(True)
        self.expiry_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.expiry_date_edit.setStyleSheet(FIELD_STYLE)
        expiry_end_container.addWidget(lbl_expiry_end)
        expiry_end_container.addWidget(self.expiry_date_edit)
        
        expiry_dates_layout.addLayout(receive_container, 1)
        expiry_dates_layout.addLayout(expiry_end_container, 1)
        expiry_container.addLayout(expiry_dates_layout)
        
        row5_layout.addLayout(category_container, 1)
        row5_layout.addLayout(expiry_container, 2)
        outer_layout.addLayout(row5_layout)
        
        # ===== إدارة قوائم الأسعار =====
        price_list_group = QGroupBox("📊 قوائم الأسعار")
        price_list_group.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                margin-top: 8px;
                padding-top: 12px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                background-color: {COLORS['bg_card']};
            }}
        """)
        price_list_layout = QVBoxLayout(price_list_group)
        price_list_layout.setContentsMargins(10, 5, 10, 10)
        
        self.price_list_manager = PriceListManagerWidget(None, self)
        price_list_layout.addWidget(self.price_list_manager)
        
        outer_layout.addWidget(price_list_group)
        
        # ===== إدارة العروض =====
        promotion_group = QGroupBox("🎯 العروض")
        promotion_group.setStyleSheet(price_list_group.styleSheet())
        promotion_layout = QVBoxLayout(promotion_group)
        promotion_layout.setContentsMargins(10, 5, 10, 10)
        
        self.promotion_manager = PromotionManagerWidget(None, self)
        promotion_layout.addWidget(self.promotion_manager)
        
        outer_layout.addWidget(promotion_group)
        
        outer_layout.addStretch()
        
        # ===== أزرار التحكم =====
        btn_row = QHBoxLayout()
        btn_row.setSpacing(15)
        btn_row.setContentsMargins(0, 10, 0, 0)
        
        self.btn_save = QPushButton("💾 حفظ")
        self.btn_save.setMinimumHeight(45)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setDefault(True)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
        """)
        self.btn_save.clicked.connect(self.save_handle)
        
        self.btn_clear = QPushButton("🗑️ تفريغ")
        self.btn_clear.setMinimumHeight(45)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {COLORS['danger_hover']}; }}
        """)
        self.btn_clear.clicked.connect(self.clear_fields)
        
        btn_row.addWidget(self.btn_save, 2)
        btn_row.addWidget(self.btn_clear, 1)
        outer_layout.addLayout(btn_row)
        
        form_scroll.setWidget(form_frame)
        main_splitter.addWidget(form_scroll)
        
        # ===== الجزء الأيمن: جدول المنتجات =====
        table_scroll = QScrollArea()
        table_scroll.setWidgetResizable(True)
        table_scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
        """)
        
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
        
        control_frame = QFrame()
        control_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
                padding: 10px 15px;
            }}
        """)
        control_layout = QHBoxLayout(control_frame)
        
        table_title = QLabel("📋 قائمة المنتجات")
        table_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['accent']};")
        control_layout.addWidget(table_title)
        
        control_layout.addStretch()
        
        self.btn_start_inventory = QPushButton("📋 بدء جرد")
        self.btn_start_inventory.setMinimumHeight(35)
        self.btn_start_inventory.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                padding: 0 15px;
            }}
            QPushButton:hover {{ background-color: {COLORS['info_hover']}; }}
        """)
        self.btn_start_inventory.clicked.connect(self.toggle_inventory_mode)
        control_layout.addWidget(self.btn_start_inventory)
        
        self.btn_apply_inventory = QPushButton("💾 اعتماد الجرد")
        self.btn_apply_inventory.setMinimumHeight(35)
        self.btn_apply_inventory.setEnabled(False)
        self.btn_apply_inventory.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['warning']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                padding: 0 15px;
            }}
            QPushButton:hover {{ background-color: {COLORS['warning_hover']}; }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
        """)
        self.btn_apply_inventory.clicked.connect(self.apply_inventory)
        control_layout.addWidget(self.btn_apply_inventory)
        
        table_layout.addWidget(control_frame)
        
        # ===== جدول المنتجات (محدث بـ 15 عمود) =====
        self.table = QTableWidget(0, 15)
        self.table.setHorizontalHeaderLabels([
            "ID", "المنتج", "الباركود", "سعر الشراء", "سعر الجملة",
            "سعر البيع", "الكمية الدفترية", "الكمية الفعلية", "الفارق", 
            "حد الطلب", "الوحدة", "بداية الاستلام", "نهاية الصلاحية", "التصنيف", ""
        ])
        
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(11, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(12, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(13, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(14, QHeaderView.Fixed)
        self.table.setColumnWidth(14, 90)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: none;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QTableWidget::item:selected {{
                background-color: rgba(56, 189, 248, 0.2);
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        
        self.table.cellClicked.connect(self.load_to_form)
        self.table.cellChanged.connect(self.on_cell_changed)
        table_layout.addWidget(self.table)
        
        table_scroll.setWidget(table_frame)
        main_splitter.addWidget(table_scroll)
        
        main_splitter.setSizes([600, 700])


if __name__ == "__main__":
    app = QApplication([])
    window = AddProductWindow()
    window.showMaximized()
    app.exec_()