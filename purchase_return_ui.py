# ================= purchase_return_ui.py - نظام المشتريات ومرتجع المشتريات المتطور (نسخة مصححة نهائياً) =================
"""
📡 نظام المشتريات المزدوج وطريقة متوسط التكلفة المرجح (Weighted Average Cost)
📌 تعمل فقط مع قاعدة البيانات الفعلية - لا توجد بيانات افتراضية
"""

import logging
import traceback
import inspect
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel,
                             QPushButton, QDialog, QFormLayout, QComboBox, QSpinBox,
                             QDoubleSpinBox, QLineEdit, QTextEdit, QFrame, QScrollArea,
                             QTabWidget, QGroupBox, QGridLayout,
                             QCompleter, QSplitter, QApplication)
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer, pyqtSignal, QStringListModel, QDate
from PyQt5.QtGui import QFont, QColor, QBrush

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
    'add_btn': '#d97706',
    'add_btn_hover': '#b45309'
}
FONTS = {
    'title': QFont("Segoe UI", 20, QFont.Bold),
    'button': QFont("Segoe UI", 12, QFont.Medium),
    'table_header': QFont("Segoe UI", 11, QFont.Bold),
    'total': QFont("Segoe UI", 16, QFont.Bold),
}


# ========== نظام Toast موحد (لون واحد ثابت) ==========
class ToastMessage(QLabel):
    def __init__(self, parent, message, duration=2500):
        # لون موحد للجميع
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
        
        # حساب الموقع بناءً على حجم الشاشة
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


class PurchaseReturnDialog(QDialog):
    """
    نافذة إضافة مرتجع مشتريات - تصميم احترافي وجذاب
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("🔄 إجراء مرتجع مشتريات جديد")
        self.setModal(True)
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.42)
        height = int(screen_geometry.height() * 0.7)
        self.setMinimumSize(int(screen_geometry.width() * 0.35), int(screen_geometry.height() * 0.5))
        self.resize(max(520, width), max(580, height))
        
        # ===== ستايل النافذة الرئيسي =====
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border-radius: 16px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
                font-weight: bold;
                margin-bottom: 4px;
            }}
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                min-height: 42px;
                selection-background-color: {COLORS['accent']};
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
                background-color: {COLORS['bg_card']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
                selection-color: white;
                border: 1px solid {COLORS['border']};
                outline: none;
            }}
            QSpinBox::up-button, QSpinBox::down-button, 
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background-color: {COLORS['bg_sidebar']};
                width: 24px;
                border: none;
                border-radius: 3px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover,
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {COLORS['accent']};
            }}
            QTextEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
            QGroupBox {{
                color: {COLORS['accent']};
                border: 1px solid {COLORS['border_light']};
                border-radius: 10px;
                margin-top: 18px;
                font-size: 14px;
                font-weight: bold;
                padding-top: 20px;
                background-color: transparent;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top right;
                right: 18px;
                padding: 0 12px;
                background-color: {COLORS['bg_dark']};
                color: {COLORS['accent']};
                font-size: 14px;
                font-weight: bold;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)
        
        # ===== اتجاه الكتابة من اليمين لليسار =====
        self.setLayoutDirection(Qt.RightToLeft)
        
        # ===== التخطيط الرئيسي =====
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)
        
        # ===== العنوان الرئيسي =====
        title_label = QLabel("🔄 تسجيل مرتجع مشتريات جديد")
        title_label.setStyleSheet(f"""
            font-size: 20px; 
            font-weight: bold; 
            color: {COLORS['warning']};
            padding-bottom: 8px;
            border-bottom: 2px solid {COLORS['border_light']};
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # ====== تعديل الريسبونسيف: تغليف المحتوى بـ ScrollArea ======
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 8, 0, 8)
        scroll_layout.setSpacing(16)
        
        # ============================================================
        # 1. قسم المورد
        # ============================================================
        supplier_group = QGroupBox("🏢 بيانات المورد")
        supplier_layout = QVBoxLayout(supplier_group)
        supplier_layout.setContentsMargins(16, 20, 16, 12)
        supplier_layout.setSpacing(10)
        
        supplier_label = QLabel("اسم المورد")
        supplier_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['text']};")
        supplier_layout.addWidget(supplier_label)
        
        self.supplier_name = QLineEdit()
        self.supplier_name.setPlaceholderText("أدخل اسم المورد هنا...")
        self.supplier_name.setMinimumHeight(42)
        supplier_layout.addWidget(self.supplier_name)
        
        scroll_layout.addWidget(supplier_group)
        
        # ============================================================
        # 2. قسم المنتج والكمية
        # ============================================================
        product_group = QGroupBox("📦 معلومات المنتج المرتجع")
        product_layout = QVBoxLayout(product_group)
        product_layout.setContentsMargins(16, 20, 16, 12)
        product_layout.setSpacing(12)
        
        # المنتج
        product_label = QLabel("اختر المنتج")
        product_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['text']};")
        product_layout.addWidget(product_label)
        
        self.product_combo = QComboBox()
        self.product_combo.setMinimumHeight(42)
        self.product_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                min-height: 42px;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        product_layout.addWidget(self.product_combo)
        
        # الكمية
        quantity_label = QLabel("الكمية المرتجعة")
        quantity_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['text']};")
        product_layout.addWidget(quantity_label)
        
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 99999)
        self.quantity.setMinimumHeight(42)
        self.quantity.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                min-height: 42px;
            }}
            QSpinBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        product_layout.addWidget(self.quantity)
        
        # سعر الوحدة
        price_label = QLabel("سعر المرتجع للوحدة")
        price_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['text']};")
        product_layout.addWidget(price_label)
        
        self.return_price = QDoubleSpinBox()
        self.return_price.setRange(0.0, 1000000.0)
        self.return_price.setSuffix(" ج.م")
        self.return_price.setDecimals(2)
        self.return_price.setMinimumHeight(42)
        self.return_price.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                min-height: 42px;
            }}
            QDoubleSpinBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        product_layout.addWidget(self.return_price)
        
        # إجمالي المرتجع (يظهر بشكل بارز)
        total_container = QFrame()
        total_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 10px;
                border: 1px solid {COLORS['border_light']};
                margin-top: 4px;
            }}
        """)
        total_layout = QVBoxLayout(total_container)
        total_layout.setContentsMargins(16, 12, 16, 12)
        total_layout.setSpacing(0)
        
        total_title = QLabel("💰 إجمالي المرتجع")
        total_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['text_muted']};")
        total_title.setAlignment(Qt.AlignCenter)
        total_layout.addWidget(total_title)
        
        self.total_label = QLabel("0.00 ج.م")
        self.total_label.setStyleSheet(f"""
            font-size: 22px; 
            font-weight: bold; 
            color: {COLORS['warning']};
            padding: 4px 0;
        """)
        self.total_label.setAlignment(Qt.AlignCenter)
        total_layout.addWidget(self.total_label)
        
        product_layout.addWidget(total_container)
        
        scroll_layout.addWidget(product_group)
        
        # ============================================================
        # 3. قسم أسباب المرتجع
        # ============================================================
        reason_group = QGroupBox("📝 تفاصيل المرتجع")
        reason_layout = QVBoxLayout(reason_group)
        reason_layout.setContentsMargins(16, 20, 16, 12)
        reason_layout.setSpacing(12)
        
        # سبب المرتجع
        reason_label = QLabel("سبب المرتجع")
        reason_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['text']};")
        reason_layout.addWidget(reason_label)
        
        self.return_reason = QComboBox()
        self.return_reason.addItems(["منتج تالف", "خطأ في الصنف", "جودة غير مطابقة", "انتهاء الصلاحية", "سعر غير صحيح", "أخرى"])
        self.return_reason.setMinimumHeight(42)
        self.return_reason.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                min-height: 42px;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        reason_layout.addWidget(self.return_reason)
        
        # ملاحظات
        notes_label = QLabel("ملاحظات إضافية")
        notes_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['text']};")
        reason_layout.addWidget(notes_label)
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(70)
        self.notes.setPlaceholderText("اكتب أي ملاحظات إضافية هنا حول المرتجع...")
        self.notes.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                min-height: 70px;
            }}
            QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        reason_layout.addWidget(self.notes)
        
        scroll_layout.addWidget(reason_group)
        
        # ===== تعيين الـ ScrollArea =====
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # ============================================================
        # أزرار الإجراءات السفلية
        # ============================================================
        buttons_container = QFrame()
        buttons_container.setStyleSheet("border: none; background-color: transparent;")
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 8, 0, 0)
        buttons_layout.setSpacing(14)
        
        self.confirm_btn = QPushButton("✅ تأكيد المرتجع وحفظه")
        self.confirm_btn.setMinimumHeight(46)
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['add_btn']};
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 10px;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['add_btn_hover']};
            }}
            QPushButton:pressed {{
                background-color: #d97706;
            }}
        """)
        self.confirm_btn.clicked.connect(self.on_confirm)
        
        self.cancel_btn = QPushButton("❌ إلغاء")
        self.cancel_btn.setMinimumHeight(46)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['border']};
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 10px;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border_light']};
            }}
            QPushButton:pressed {{
                background-color: #475569;
            }}
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.confirm_btn, stretch=2)
        buttons_layout.addWidget(self.cancel_btn, stretch=1)
        main_layout.addWidget(buttons_container)
        
        # ===== ربط الإشارات =====
        self.product_combo.currentIndexChanged.connect(self.update_product_info)
        self.quantity.valueChanged.connect(self.update_total)
        self.return_price.valueChanged.connect(self.update_total)
        
        # ===== تهيئة البيانات =====
        self.product_dict = {}
        self.load_products()
        self.update_product_info()
        self.update_total()
    
    def load_products(self):
        """
        تحميل المنتجات المتاحة من قاعدة البيانات (المخزون > 0)
        وملء القائمة المنسدلة (product_combo)
        """
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
                        'purchase_price': product.get('purchase_price', 0),
                        'stock': stock,
                        'barcode': product.get('barcode', '')
                    }
        except Exception as e:
            logger.error(f"خطأ في تحميل المنتجات: {e}")
            self.show_warning_toast(f"⚠️ خطأ في تحميل المنتجات: {str(e)}")
    
    def update_product_info(self):
        """
        تحديث حقل السعر (return_price) وسقف الكمية المتاحة
        بناءً على المنتج المختار حالياً
        """
        try:
            product_id = self.product_combo.currentData()
            if product_id and product_id in self.product_dict:
                product_info = self.product_dict[product_id]
                # تحديث السعر
                self.return_price.setValue(product_info['purchase_price'])
                # تحديث الحد الأقصى للكمية
                self.quantity.setMaximum(product_info['stock'])
                self.update_total()
        except Exception as e:
            logger.error(f"خطأ في update_product_info: {e}")
    
    def update_total(self):
        """
        حساب الإجمالي فورياً (الكمية × سعر الوحدة) وعرضه بشكل منسق
        """
        try:
            quantity = self.quantity.value()
            price = self.return_price.value()
            total = quantity * price
            self.total_label.setText(f"{total:,.2f} ج.م")
        except Exception as e:
            logger.error(f"خطأ في update_total: {e}")
    
    def show_toast(self, message, duration=2500):
        ToastMessage(self, message, duration)
    
    def show_warning_toast(self, message):
        self.show_toast(message)
    
    def show_success_toast(self, message):
        self.show_toast(message)
    
    def on_confirm(self):
        """
        تأكيد مرتجع الشراء - التحقق من البيانات وحفظها في قاعدة البيانات
        """
        try:
            product_id = self.product_combo.currentData()
            
            # ===== التحقق من صحة البيانات =====
            if not product_id or product_id not in self.product_dict:
                self.show_warning_toast("⚠️ الرجاء اختيار منتج صحيح")
                return
            
            supplier_name = self.supplier_name.text().strip()
            if not supplier_name:
                self.show_warning_toast("⚠️ الرجاء إدخال اسم المورد")
                return
            
            quantity = self.quantity.value()
            if quantity <= 0:
                self.show_warning_toast("⚠️ الكمية يجب أن تكون أكبر من صفر")
                return
            
            return_price = self.return_price.value()
            if return_price <= 0:
                self.show_warning_toast("⚠️ سعر المرتجع يجب أن يكون أكبر من صفر")
                return
            
            product_info = self.product_dict[product_id]
            if quantity > product_info['stock']:
                self.show_warning_toast(f"⚠️ الكمية المطلوبة تتجاوز المتوفر ({product_info['stock']})")
                return
            
            # ===== حساب الإجمالي =====
            total_amount = quantity * return_price
            
            # ===== تجهيز البيانات للحفظ =====
            return_data = {
                'supplier_name': supplier_name,
                'product_id': product_id,
                'product_name': product_info['name'],
                'quantity': quantity,
                'return_price': return_price,
                'total_amount': total_amount,
                'reason': self.return_reason.currentText(),
                'notes': self.notes.toPlainText().strip(),
                'barcode': product_info.get('barcode', '')
            }
            
            logger.info(f"محاولة تسجيل مرتجع شراء: {return_data}")
            
            # ===== حفظ المرتجع في قاعدة البيانات =====
            success = False
            msg = ""
            
            try:
                # استخدام دالة add_purchase_return من database.py
                # نحاول استدعاء الدالة بالمعاملات المناسبة
                import inspect
                sig = inspect.signature(db.add_purchase_return)
                params = sig.parameters
                
                # تحضير المعاملات
                call_args = {
                    'supplier_name': return_data['supplier_name'],
                    'product_id': return_data['product_id'],
                    'product_name': return_data['product_name'],
                    'quantity': float(return_data['quantity']),
                    'return_price': float(return_data['return_price']),
                    'reason': return_data['reason'],
                    'notes': return_data['notes'],
                    'total_amount': float(return_data['total_amount'])
                }
                
                # تصفية المعاملات للتأكد من وجودها في الدالة
                filtered_args = {k: v for k, v in call_args.items() if k in params}
                
                # إذا كانت الدالة تقبل **kwargs، استخدم كل المعاملات
                if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
                    success, msg = db.add_purchase_return(**call_args)
                else:
                    success, msg = db.add_purchase_return(**filtered_args)
                    
            except TypeError as te:
                # إذا حدث خطأ في نوع المعاملات، نحاول باستخدام المعاملات الأساسية فقط
                logger.warning(f"خطأ في استدعاء add_purchase_return: {te}")
                try:
                    success, msg = db.add_purchase_return(
                        supplier_name=return_data['supplier_name'],
                        product_id=return_data['product_id'],
                        product_name=return_data['product_name'],
                        quantity=float(return_data['quantity']),
                        return_price=float(return_data['return_price']),
                        reason=return_data['reason'],
                        notes=return_data['notes']
                    )
                except Exception as e2:
                    logger.error(f"محاولة بديلة فشلت: {e2}")
                    success, msg = False, f"فشل تسجيل المرتجع: {str(e2)}"
                    
            except AttributeError as ae:
                # إذا كانت الدالة غير موجودة، نحاول استخدام طريقة بديلة
                logger.error(f"دالة add_purchase_return غير موجودة: {ae}")
                success, msg = False, "دالة حفظ المرتجع غير موجودة في قاعدة البيانات"
                
            except Exception as e:
                logger.error(f"خطأ غير متوقع في حفظ المرتجع: {e}")
                success, msg = False, f"خطأ غير متوقع: {str(e)}"
            
            # ===== معالجة النتيجة =====
            if success:
                # عرض رسالة النجاح على النافذة الرئيسية (بدلاً من الديالوج)
                if self.parent_window:
                    self.parent_window.show_toast(
                        f"✅ {msg}\n"
                        f"🏢 المورد: {supplier_name}\n"
                        f"📦 المنتج: {product_info['name']}\n"
                        f"💰 المبلغ: {total_amount:,.2f} ج.م",
                        4000
                    )
                    
                    # ===== تحديث جدول المرتجعات =====
                    if hasattr(self.parent_window, 'returns_tab'):
                        self.parent_window.returns_tab.load_returns()
                    elif hasattr(self.parent_window, 'load_returns'):
                        self.parent_window.load_returns()
                    elif hasattr(self.parent_window, 'refresh_all'):
                        self.parent_window.refresh_all()
                
                # إغلاق النافذة بعد 400 مللي ثانية لإعطاء وقت للـ Toast
                QTimer.singleShot(400, self.accept)
                    
            else:
                self.show_warning_toast(f"❌ {msg}")
                
        except Exception as e:
            logger.error(f"خطأ في on_confirm: {e}")
            logger.error(traceback.format_exc())
            self.show_warning_toast(f"❌ خطأ في تأكيد المرتجع: {str(e)}")
    
    def get_data(self):
        try:
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
                'total_amount': float(quantity * return_price),
                'return_reason': self.return_reason.currentText(),
                'notes': self.notes.toPlainText().strip()
            }
        except Exception as e:
            logger.error(f"خطأ في get_data: {e}")
            return None


class PurchaseInvoiceTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.invoice_items = []
        self.tax_rate = 14.0
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
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setSpacing(10)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 12px;
                padding: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        info_layout = QGridLayout(info_frame)
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(15, 15, 15, 15)
        
        info_layout.addWidget(QLabel("🏢 المورد:"), 0, 0)
        self.supplier_input = QLineEdit()
        self.supplier_input.setPlaceholderText("اسم المورد...")
        self.supplier_input.setMinimumHeight(36)
        self.supplier_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        info_layout.addWidget(self.supplier_input, 0, 1)
        
        info_layout.addWidget(QLabel("📄 رقم الفاتورة:"), 0, 2)
        self.invoice_number_input = QLineEdit()
        self.invoice_number_input.setPlaceholderText("رقم الفاتورة...")
        self.invoice_number_input.setMinimumHeight(36)
        self.invoice_number_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        info_layout.addWidget(self.invoice_number_input, 0, 3)
        
        info_layout.addWidget(QLabel("💳 طريقة الدفع:"), 1, 0)
        self.payment_method = QComboBox()
        self.payment_method.addItems(["كاش", "آجل", "تحويل بنكي", "شيك"])
        self.payment_method.setMinimumHeight(36)
        self.payment_method.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
            }}
        """)
        info_layout.addWidget(self.payment_method, 1, 1)
        
        generate_btn = QPushButton("🎲 توليد رقم")
        generate_btn.setMinimumHeight(36)
        generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_hover']};
            }}
        """)
        generate_btn.clicked.connect(self.generate_invoice_number)
        info_layout.addWidget(generate_btn, 1, 2)
        
        clear_btn = QPushButton("🗑️ مسح الفاتورة")
        clear_btn.setMinimumHeight(36)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
                border: none;
                padding: 0 15px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        clear_btn.clicked.connect(self.clear_invoice)
        info_layout.addWidget(clear_btn, 1, 3)
        
        top_layout.addWidget(info_frame)
        
        add_frame = QFrame()
        add_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 12px;
                padding: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        add_layout = QHBoxLayout(add_frame)
        add_layout.setSpacing(10)
        
        self.product_combo = QComboBox()
        self.product_combo.setMinimumHeight(36)
        self.product_combo.setMinimumWidth(200)
        self.product_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QComboBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
            }}
        """)
        self.load_products()
        add_layout.addWidget(QLabel("📦 المنتج:"))
        add_layout.addWidget(self.product_combo)
        
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 9999)
        self.qty_spin.setMinimumHeight(36)
        self.qty_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                min-width: 80px;
            }}
            QSpinBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        add_layout.addWidget(QLabel("🔢 الكمية:"))
        add_layout.addWidget(self.qty_spin)
        
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 1000000)
        self.price_spin.setPrefix("ج.م ")
        self.price_spin.setDecimals(2)
        self.price_spin.setMinimumHeight(36)
        self.price_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                min-width: 100px;
            }}
            QDoubleSpinBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        add_layout.addWidget(QLabel("💰 سعر الشراء:"))
        add_layout.addWidget(self.price_spin)
        
        add_item_btn = QPushButton("➕ إضافة")
        add_item_btn.setMinimumHeight(36)
        add_item_btn.setMinimumWidth(100)
        add_item_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        add_item_btn.clicked.connect(self.add_item_to_invoice)
        add_layout.addWidget(add_item_btn)
        
        top_layout.addWidget(add_frame)
        
        top_widget.setMinimumHeight(250)
        main_splitter.addWidget(top_widget)
        
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # ===== جدول مع دعم Scroll =====
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
            QTableCornerButton::section {{
                background-color: {COLORS['bg_sidebar']};
                border: none;
            }}
        """)
        
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["المنتج", "الكمية", "سعر الشراء", "الإجمالي", "حذف", "الباركود"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(4, 70)
        
        self.table.setLayoutDirection(Qt.RightToLeft)
        
        table_container.setWidget(self.table)
        bottom_layout.addWidget(table_container, stretch=1)
        
        totals_frame = QFrame()
        totals_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 12px;
                padding: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        totals_layout = QHBoxLayout(totals_frame)
        totals_layout.setSpacing(20)
        
        self.subtotal_label = QLabel("💰 إجمالي الفاتورة: 0.00 ج.م")
        self.subtotal_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['text']};")
        totals_layout.addWidget(self.subtotal_label)
        
        tax_layout = QHBoxLayout()
        tax_layout.setSpacing(5)
        tax_label = QLabel("📊 الضريبة (14%):")
        tax_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        self.tax_value_label = QLabel("0.00 ج.م")
        self.tax_value_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 13px; font-weight: bold;")
        tax_layout.addWidget(tax_label)
        tax_layout.addWidget(self.tax_value_label)
        totals_layout.addLayout(tax_layout)
        
        self.net_total_label = QLabel("✅ الصافي النهائي: 0.00 ج.م")
        self.net_total_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['success']};")
        totals_layout.addWidget(self.net_total_label)
        
        totals_layout.addStretch()
        
        save_btn = QPushButton("💾 اعتماد وحفظ الفاتورة")
        save_btn.setMinimumHeight(40)
        save_btn.setMinimumWidth(200)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                padding: 0 25px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        save_btn.clicked.connect(self.save_invoice)
        totals_layout.addWidget(save_btn)
        
        bottom_layout.addWidget(totals_frame)
        
        bottom_widget.setMinimumHeight(200)
        main_splitter.addWidget(bottom_widget)
        
        main_splitter.setSizes([300, 400])
        layout.addWidget(main_splitter)
        
        self.product_combo.currentIndexChanged.connect(self.update_price_from_product)
    
    def load_products(self):
        self.product_combo.clear()
        self.product_dict = {}
        try:
            products = db.get_all_products()
            for product in products:
                self.product_combo.addItem(f"{product.get('name', '')}", product.get('id'))
                self.product_dict[product.get('id')] = product
        except Exception as e:
            logger.error(f"خطأ في تحميل المنتجات: {e}")
            self.parent_window.show_toast(f"⚠️ خطأ في تحميل المنتجات: {str(e)}")
    
    def update_price_from_product(self):
        try:
            product_id = self.product_combo.currentData()
            if product_id and product_id in self.product_dict:
                self.price_spin.setValue(self.product_dict[product_id].get('purchase_price', 0))
        except Exception as e:
            logger.error(f"خطأ في update_price_from_product: {e}")
    
    def generate_invoice_number(self):
        import random
        invoice_num = f"INV-{random.randint(10000, 99999)}-{random.randint(100, 999)}"
        self.invoice_number_input.setText(invoice_num)
        self.parent_window.show_toast("🎯 تم توليد رقم فاتورة جديد")
    
    def add_item_to_invoice(self):
        try:
            product_id = self.product_combo.currentData()
            if not product_id or product_id not in self.product_dict:
                self.parent_window.show_toast("⚠️ الرجاء اختيار منتج صحيح")
                return
            
            qty = self.qty_spin.value()
            price = self.price_spin.value()
            
            if qty <= 0:
                self.parent_window.show_toast("⚠️ الكمية يجب أن تكون أكبر من صفر")
                return
            
            if price <= 0:
                self.parent_window.show_toast("⚠️ سعر الشراء يجب أن يكون أكبر من صفر")
                return
            
            product = self.product_dict[product_id]
            total = qty * price
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 45)
            
            name_item = QTableWidgetItem(product.get('name', ''))
            name_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, name_item)
            
            qty_item = QTableWidgetItem(str(qty))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, qty_item)
            
            price_item = QTableWidgetItem(f"{price:.2f}")
            price_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, price_item)
            
            total_item = QTableWidgetItem(f"{total:.2f}")
            total_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, total_item)
            
            barcode_item = QTableWidgetItem(product.get('barcode', '-'))
            barcode_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, barcode_item)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(35, 30)
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['danger']};
                    color: white;
                    border-radius: 6px;
                    font-size: 12px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['danger_hover']};
                }}
            """)
            delete_btn.clicked.connect(lambda checked, r=row: self.remove_item(r))
            
            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setAlignment(Qt.AlignCenter)
            container_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 4, container)
            
            self.invoice_items.append({
                'product_id': product_id,
                'product_name': product.get('name', ''),
                'qty': qty,
                'price': price,
                'total': total,
                'barcode': product.get('barcode', '')
            })
            
            self.update_totals()
            self.parent_window.show_toast(f"✅ تم إضافة {product.get('name', '')} إلى الفاتورة")
            
        except Exception as e:
            logger.error(f"خطأ في add_item_to_invoice: {e}")
            self.parent_window.show_toast(f"❌ خطأ: {str(e)}")
    
    def remove_item(self, row):
        try:
            if row < len(self.invoice_items):
                removed = self.invoice_items.pop(row)
                self.table.removeRow(row)
                self.update_totals()
                self.parent_window.show_toast(f"🗑️ تم حذف {removed['product_name']} من الفاتورة")
        except Exception as e:
            logger.error(f"خطأ في remove_item: {e}")
    
    def clear_invoice(self):
        if not self.invoice_items and self.table.rowCount() == 0:
            self.parent_window.show_toast("⚠️ الفاتورة فارغة بالفعل")
            return
        
        self.invoice_items.clear()
        self.table.setRowCount(0)
        self.update_totals()
        self.supplier_input.clear()
        self.invoice_number_input.clear()
        self.qty_spin.setValue(1)
        self.price_spin.setValue(0)
        
        self.parent_window.show_toast("🔄 تم مسح الفاتورة بالكامل")
    
    def update_totals(self):
        try:
            subtotal = sum(item['total'] for item in self.invoice_items)
            tax = subtotal * (self.tax_rate / 100)
            net_total = subtotal + tax
            
            self.subtotal_label.setText(f"💰 إجمالي الفاتورة: {subtotal:,.2f} ج.م")
            self.tax_value_label.setText(f"{tax:,.2f} ج.م")
            self.net_total_label.setText(f"✅ الصافي النهائي: {net_total:,.2f} ج.م")
        except Exception as e:
            logger.error(f"خطأ في update_totals: {e}")
    
    def save_invoice(self):
        try:
            if not self.invoice_items:
                self.parent_window.show_toast("⚠️ لا توجد أصناف في الفاتورة")
                return
            
            if not self.supplier_input.text().strip():
                self.parent_window.show_toast("⚠️ الرجاء إدخال اسم المورد")
                return
            
            if not self.invoice_number_input.text().strip():
                self.parent_window.show_toast("⚠️ الرجاء إدخال رقم الفاتورة")
                return
            
            total = sum(item['total'] for item in self.invoice_items)
            tax = total * (self.tax_rate / 100)
            net_total = total + tax
            
            success, msg = db.add_purchase(
                supplier=self.supplier_input.text().strip(),
                invoice_number=self.invoice_number_input.text().strip(),
                payment_method=self.payment_method.currentText(),
                items=self.invoice_items.copy(),
                subtotal=total,
                tax=tax,
                net_total=net_total
            )
            
            if success:
                self.parent_window.show_toast(
                    f"✅ {msg}\n"
                    f"🏢 المورد: {self.supplier_input.text()}\n"
                    f"💰 الصافي: {net_total:,.2f} ج.م",
                    4000
                )
                
                self.invoice_items.clear()
                self.table.setRowCount(0)
                self.update_totals()
                self.supplier_input.clear()
                self.invoice_number_input.clear()
                self.qty_spin.setValue(1)
                self.price_spin.setValue(0)
                self.load_products()
            else:
                self.parent_window.show_toast(f"❌ {msg}")
                
        except Exception as e:
            logger.error(f"خطأ في save_invoice: {e}")
            self.parent_window.show_toast(f"❌ خطأ في حفظ الفاتورة: {str(e)}")


class PurchaseReturnsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.returns = []
        self.return_counter = 1
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        
        info_label = QLabel("🔄 إدارة مرتجعات المشتريات - تسجيل وإدارة المرتجعات للموردين")
        info_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; padding: 8px; background-color: {COLORS['bg_card']}; border-radius: 8px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
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
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        add_btn = QPushButton("➕ مرتجع جديد")
        add_btn.setFont(FONTS['button'])
        add_btn.setMinimumHeight(45)
        add_btn.setMinimumWidth(180)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['add_btn']};
                color: white;
                padding: 12px 25px;
                border-radius: 10px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['add_btn_hover']};
            }}
        """)
        add_btn.clicked.connect(self.add_return)
        btn_layout.addWidget(add_btn)
        
        top_layout.addLayout(btn_layout)
        top_widget.setMinimumHeight(80)
        main_splitter.addWidget(top_widget)
        
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # ===== جدول مع دعم Scroll =====
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
                background-color: rgba(56, 189, 248, 0.2);
            }}
            QTableWidget::item:alternate {{
                background-color: {COLORS['bg_sidebar']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 10px 8px;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }}
            QTableCornerButton::section {{
                background-color: {COLORS['bg_sidebar']};
                border: none;
            }}
        """)
        
        # ===== أعمدة الجدول الجديدة 9 أعمدة =====
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "رقم السند", "التاريخ", "اسم المورد", "اسم المنتج", 
            "الكمية المرتجعة", "سعر الوحدة", "الإجمالي", "سبب المرتجع", "الإجراءات"
        ])
        
        header = self.table.horizontalHeader()
        # ضبط أحجام الأعمدة
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)   # رقم السند
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)   # التاريخ
        header.setSectionResizeMode(2, QHeaderView.Stretch)            # اسم المورد - يتمدد
        header.setSectionResizeMode(3, QHeaderView.Stretch)            # اسم المنتج - يتمدد
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)   # الكمية
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)   # سعر الوحدة
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)   # الإجمالي
        header.setSectionResizeMode(7, QHeaderView.Stretch)            # سبب المرتجع - يتمدد
        header.setSectionResizeMode(8, QHeaderView.Fixed)              # الإجراءات
        self.table.setColumnWidth(8, 100)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setLayoutDirection(Qt.RightToLeft)
        header.setDefaultAlignment(Qt.AlignCenter)
        
        table_container.setWidget(self.table)
        bottom_layout.addWidget(table_container)
        
        bottom_widget.setMinimumHeight(200)
        main_splitter.addWidget(bottom_widget)
        
        main_splitter.setSizes([100, 400])
        layout.addWidget(main_splitter)
        
        self.load_returns()
    
    def load_returns(self):
        """
        تحميل بيانات المرتجعات من قاعدة البيانات وعرضها في الجدول
        """
        try:
            # إعادة تحميل البيانات من قاعدة البيانات
            self.returns = db.get_all_purchase_returns()
            
            # تنظيف الجدول أولاً
            self.table.setRowCount(0)
            
            # إعادة تعبئة الجدول
            self.table.setRowCount(len(self.returns))
            
            for row, ret in enumerate(self.returns):
                self.table.setRowHeight(row, 42)
                
                # 0. رقم السند
                number_item = QTableWidgetItem(f"RET-{ret.get('id', 0):04d}")
                number_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, number_item)
                
                # 1. التاريخ
                date_item = QTableWidgetItem(ret.get('return_date', ret.get('date', '')))
                date_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, date_item)
                
                # 2. اسم المورد
                supplier_item = QTableWidgetItem(ret.get('supplier_name', ''))
                supplier_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, supplier_item)
                
                # 3. اسم المنتج
                product_item = QTableWidgetItem(ret.get('product_name', ''))
                product_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, product_item)
                
                # 4. الكمية المرتجعة
                qty = ret.get('quantity', 0)
                qty_item = QTableWidgetItem(str(qty))
                qty_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 4, qty_item)
                
                # 5. سعر الوحدة
                price = ret.get('return_price', 0)
                price_item = QTableWidgetItem(f"{price:,.2f}")
                price_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 5, price_item)
                
                # 6. الإجمالي
                total_amount = ret.get('total_return_amount', ret.get('total_amount', ret.get('amount', 0)))
                try:
                    amount = float(total_amount)
                except (TypeError, ValueError):
                    amount = 0.0
                amount_item = QTableWidgetItem(f"{amount:,.2f} ج.م")
                amount_item.setTextAlignment(Qt.AlignCenter)
                if amount > 0:
                    amount_item.setForeground(QBrush(QColor(COLORS['warning'])))
                    amount_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                else:
                    amount_item.setForeground(QBrush(QColor(COLORS['text_muted'])))
                self.table.setItem(row, 6, amount_item)
                
                # 7. سبب المرتجع
                reason_item = QTableWidgetItem(ret.get('return_reason', ret.get('reason', '')))
                reason_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 7, reason_item)
                
                # 8. الإجراءات (زر حذف)
                delete_btn = QPushButton("🗑️")
                delete_btn.setFixedSize(32, 28)
                delete_btn.setCursor(Qt.PointingHandCursor)
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
                delete_btn.setToolTip("حذف المرتجع")
                delete_btn.clicked.connect(lambda checked, rid=ret.get('id', 0): self.delete_return(rid))
                
                container = QWidget()
                container.setStyleSheet("background: transparent; border: none;")
                container_layout = QHBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setAlignment(Qt.AlignCenter)
                container_layout.addWidget(delete_btn)
                self.table.setCellWidget(row, 8, container)
            
            # ===== تحديث الجدول وإعادة الرسم الفورية =====
            self.table.viewport().update()
            self.table.resizeRowsToContents()
            QApplication.processEvents()
            if self.parent_window:
                self.parent_window.updateGeometry()
            
            # تحديث واجهة المستخدم
            self.table.update()
            self.table.repaint()
            
            if self.parent_window and hasattr(self.parent_window, 'show_toast'):
                self.parent_window.show_toast(f"✅ تم تحديث جدول المرتجعات - {len(self.returns)} سجل")
                
        except Exception as e:
            logger.error(f"خطأ في تحميل المرتجعات: {e}")
            self.returns = []
            self.table.setRowCount(0)
            if self.parent_window:
                self.parent_window.show_toast(f"⚠️ خطأ في تحميل المرتجعات: {str(e)}")
    
    def delete_return(self, return_id):
        try:
            success, msg = db.delete_purchase_return(return_id)
            if success:
                if self.parent_window:
                    self.parent_window.show_toast(f"✅ {msg}")
                self.load_returns()
            else:
                if self.parent_window:
                    self.parent_window.show_toast(f"❌ {msg}")
        except Exception as e:
            logger.error(f"خطأ في حذف المرتجع: {e}")
            if self.parent_window:
                self.parent_window.show_toast(f"❌ خطأ في حذف المرتجع: {str(e)}")
    
    def add_return(self):
        """
        فتح نافذة إضافة مرتجع جديد
        """
        try:
            products = db.get_all_products()
            if not products:
                if self.parent_window:
                    self.parent_window.show_toast("⚠️ لا توجد منتجات في النظام لإرجاعها")
                return
        except Exception as e:
            logger.error(f"خطأ في جلب المنتجات: {e}")
            if self.parent_window:
                self.parent_window.show_toast("⚠️ لا توجد منتجات في النظام لإرجاعها")
            return
        
        # فتح نافذة إضافة المرتجع
        dlg = PurchaseReturnDialog(self.parent_window)
        
        if dlg.exec():
            # تم تأكيد المرتجع في الديالوج، والجدول سيتم تحديثه تلقائياً
            # من خلال استدعاء load_returns في on_confirm
            pass


class PurchaseReturnWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setMinimumSize(int(screen_geometry.width() * 0.6), int(screen_geometry.height() * 0.5))
        
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        title = QLabel("📦 المشتريات ومرتجع المشتريات")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['text']}; padding: 8px;")
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
                padding: 10px 25px;
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
        
        self.purchase_tab = PurchaseInvoiceTab(self)
        self.tab_widget.addTab(self.purchase_tab, "📦 فاتورة شراء جديدة")
        
        self.returns_tab = PurchaseReturnsTab(self)
        self.tab_widget.addTab(self.returns_tab, "🔄 إدارة مرتجع المشتريات")
        
        layout.addWidget(self.tab_widget)
    
    def show_toast(self, message, duration=2500):
        ToastMessage(self, message, duration)
    
    def load_returns(self):
        """تحديث بيانات مرتجعات المشتريات"""
        try:
            if hasattr(self, 'returns_tab') and hasattr(self.returns_tab, 'load_returns'):
                self.returns_tab.load_returns()
                # تحديث واجهة المستخدم
                QApplication.processEvents()
                self.show_toast("✅ تم تحديث بيانات مرتجعات المشتريات")
            else:
                logger.warning("returns_tab غير موجود أو لا يحتوي على load_returns")
        except Exception as e:
            logger.error(f"خطأ أثناء تحديث بيانات مرتجعات المشتريات: {e}")
            self.show_toast(f"⚠️ خطأ أثناء تحديث بيانات مرتجعات المشتريات: {e}")
    
    def load_purchases(self):
        try:
            if hasattr(self, 'purchase_tab') and hasattr(self.purchase_tab, 'load_products'):
                self.purchase_tab.load_products()
                self.show_toast("✅ تم تحديث بيانات المشتريات")
        except Exception as e:
            logger.error(f"خطأ أثناء تحديث بيانات المشتريات: {e}")
            self.show_toast(f"⚠️ خطأ أثناء تحديث بيانات المشتريات: {e}")
    
    def refresh_all(self):
        self.load_returns()
        self.load_purchases()
        self.show_toast("🔄 تم تحديث جميع البيانات")


if __name__ == "__main__":
    app = QApplication([])
    window = PurchaseReturnWindow()
    window.showMaximized()
    app.exec_()