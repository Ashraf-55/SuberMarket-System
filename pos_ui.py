# ================= pos_ui.py بعد التعديل =================

import sys, os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, QLabel, 
                             QHeaderView, QListWidget, QFrame, QSpinBox, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QTimer, QEvent
from PyQt6.QtGui import QFont, QShortcut, QKeySequence, QKeyEvent
from back.database import search_products, make_sale
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from datetime import datetime

# ========== الألوان (نفس الألوان الموجودة) ==========
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

# ========== نافذة إدخال اسم العميل (بدون تغيير) ==========
class CustomerNameDialog(QDialog):
    # ... (نفس الكود الموجود) ...
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("💰 بيع آجل")
        self.setModal(True)
        self.setFixedSize(450, 250)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border: 2px solid {COLORS['accent']};
                border-radius: 15px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        title_label = QLabel("📋 تسجيل فاتورة آجلة")
        title_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {COLORS['accent']};
            text-align: center;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        hint_label = QLabel("الرجاء إدخال اسم العميل")
        hint_label.setStyleSheet(f"""
            font-size: 14px;
            color: {COLORS['text_muted']};
            text-align: center;
        """)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم العميل...")
        self.name_input.setMinimumHeight(50)
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
                padding: 12px 15px;
                font-size: 16px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        layout.addWidget(self.name_input)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                min-width: 100px;
                min-height: 40px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_hover']};
            }}
            QPushButton[text="إلغاء"] {{
                background-color: {COLORS['danger']};
            }}
            QPushButton[text="إلغاء"]:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("تأكيد")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("إلغاء")
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        self.name_input.setFocus()
    
    def get_customer_name(self):
        return self.name_input.text().strip()


# ========== رسالة Toast (بدون تغيير) ==========
class ToastMessage(QLabel):
    # ... (نفس الكود الموجود) ...
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


# ========== نافذة POS الرئيسية (معدلة) ==========
class POSWindow(QWidget):
    """نافذة نقطة البيع الرئيسية"""
    
    def __init__(self):
        super().__init__()
        self.cart_items = {} 
        self.init_ui()
        self.setup_shortcuts()
        self.setup_keyboard_navigation()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # شريط البحث (سيتم إضافة eventFilter له)
        search_container = QFrame()
        search_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']}; 
                border-radius: 12px; 
                border: 1px solid {COLORS['border']};
            }}
        """)
        search_layout = QHBoxLayout(search_container)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 ابحث عن منتج بالاسم أو الباركود...")
        self.search_input.setFixedHeight(50)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: none;
                font-size: 15px;
                padding: 0 15px;
                border-radius: 10px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        self.search_input.returnPressed.connect(self.add_from_search)
        self.search_input.textChanged.connect(self.live_search)
        # إضافة eventFilter لالتقاط أحداث الأسهم
        self.search_input.installEventFilter(self)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_container)

        # قائمة نتائج البحث
        self.results_list = QListWidget()
        self.results_list.setFixedHeight(150)
        self.results_list.setStyleSheet(f"""
            QListWidget {{ 
                background-color: {COLORS['bg_dark']}; 
                color: {COLORS['text']};
                border: 2px solid {COLORS['accent']}; 
                border-radius: 10px; 
            }}
            QListWidget::item {{ 
                padding: 12px; 
                border-bottom: 1px solid {COLORS['border']};
            }}
            QListWidget::item:selected {{ 
                background-color: {COLORS['accent']}; 
                color: white;
            }}
        """)
        self.results_list.hide()
        self.results_list.itemClicked.connect(self.add_from_list)
        # السماح بالتنقل في قائمة النتائج بالأسهم
        self.results_list.installEventFilter(self)
        layout.addWidget(self.results_list)

        # جدول السلة (بدون تغيير)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["المنتج", "السعر", "الكمية", "الإجمالي", "التحكم", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{ 
                border-radius: 12px; 
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: 1px solid {COLORS['border']};
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_dark']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 12px;
                border: none;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.table)

        # الفوتر (بدون تغيير)
        footer_frame = QFrame()
        footer_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_sidebar']};
                border-radius: 15px;
                padding: 15px;
            }}
        """)
        footer_layout = QHBoxLayout(footer_frame)

        disc_box = QVBoxLayout()
        disc_label = QLabel("💰 الخصم (ج.م)")
        disc_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        self.discount_input = QLineEdit("0")
        self.discount_input.setFixedWidth(130)
        self.discount_input.setFixedHeight(45)
        self.discount_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_dark']}; 
                color: {COLORS['warning']}; 
                border: 2px solid {COLORS['warning']}; 
                border-radius: 8px; 
                padding: 8px;
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        self.discount_input.textChanged.connect(self.update_total)
        disc_box.addWidget(disc_label)
        disc_box.addWidget(self.discount_input)
        footer_layout.addLayout(disc_box)

        footer_layout.addStretch()

        total_box = QVBoxLayout()
        self.total_label = QLabel("الإجمالي: 0.00 ج.م")
        self.total_label.setStyleSheet(f"font-size: 32px; color: {COLORS['success']}; font-weight: 900;")
        total_box.addWidget(self.total_label)
        footer_layout.addLayout(total_box)

        footer_layout.addSpacing(40)

        self.btn_cash = QPushButton("💰 كاش (F5)")
        self.btn_cash.setFixedSize(180, 70)
        self.btn_cash.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
        """)
        self.btn_cash.clicked.connect(self.process_cash_sale)

        self.btn_credit = QPushButton("📋 آجل (F2)")
        self.btn_credit.setFixedSize(180, 70)
        self.btn_credit.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['info']};
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {COLORS['info_hover']}; }}
        """)
        self.btn_credit.clicked.connect(self.process_deferred_sale)

        footer_layout.addWidget(self.btn_cash)
        footer_layout.addWidget(self.btn_credit)
        layout.addWidget(footer_frame)

    def setup_shortcuts(self):
        # اختصارات لوحة المفاتيح
        self.shortcut_f5 = QShortcut(QKeySequence("F5"), self)
        self.shortcut_f5.activated.connect(self.process_cash_sale)
        self.shortcut_f2 = QShortcut(QKeySequence("F2"), self)
        self.shortcut_f2.activated.connect(self.process_deferred_sale)
        self.shortcut_enter = QShortcut(QKeySequence("Return"), self)
        self.shortcut_enter.activated.connect(self.add_from_search)
        self.shortcut_enter2 = QShortcut(QKeySequence("Enter"), self)
        self.shortcut_enter2.activated.connect(self.add_from_search)

    def setup_keyboard_navigation(self):
        """إعداد التنقل بالأسهم بين البحث والجدول"""
        # تعيين التركيز الأولي على حقل البحث
        self.search_input.setFocus()

    def eventFilter(self, obj, event):
        """فلترة الأحداث لالتقاط أزرار الأسهم و Enter"""
        if event.type() == QEvent.Type.KeyPress:
            key_event = event
            
            # حالة التركيز على حقل البحث
            if obj == self.search_input:
                if key_event.key() == Qt.Key.Key_Down:
                    # سهم تحت: نقل التركيز إلى قائمة النتائج إذا كانت ظاهرة
                    if self.results_list.isVisible() and self.results_list.count() > 0:
                        self.results_list.setFocus()
                        self.results_list.setCurrentRow(0)
                        return True
                    # إذا لم تكن القائمة ظاهرة، نقل التركيز إلى الجدول
                    elif self.table.rowCount() > 0:
                        self.table.setFocus()
                        self.table.selectRow(0)
                        return True
            
            # حالة التركيز على قائمة النتائج
            elif obj == self.results_list:
                if key_event.key() == Qt.Key.Key_Return or key_event.key() == Qt.Key.Key_Enter:
                    # إضافة المنتج المحدد إلى السلة
                    current_item = self.results_list.currentItem()
                    if current_item:
                        self.add_from_list(current_item)
                        self.search_input.setFocus()
                        return True
                elif key_event.key() == Qt.Key.Key_Up and self.results_list.currentRow() == 0:
                    # سهم أعلى في أول عنصر: نقل التركيز إلى حقل البحث
                    self.search_input.setFocus()
                    return True
            
            # حالة التركيز على الجدول
            elif obj == self.table:
                if key_event.key() == Qt.Key.Key_Return or key_event.key() == Qt.Key.Key_Enter:
                    # إضافة المنتج المحدد من الصف النشط في الجدول
                    current_row = self.table.currentRow()
                    if current_row >= 0:
                        # البحث عن product_id من الصف المحدد
                        for p_id, info in self.cart_items.items():
                            if info['row'] == current_row:
                                # زيادة كمية المنتج
                                current_qty = int(self.table.item(current_row, 2).text())
                                new_qty = current_qty + 1
                                if new_qty <= info['stock']:
                                    self.update_row_qty(current_row, p_id, new_qty, info['price'])
                                    self.update_total()
                                    self.show_success_toast(f"✅ تم زيادة كمية {info['name']}")
                                else:
                                    self.show_warning_toast(f"⚠️ الكمية المطلوبة أكبر من المتاحة ({info['stock']})")
                                break
                        return True
                elif key_event.key() == Qt.Key.Key_Up and self.table.currentRow() == 0:
                    # سهم أعلى في أول صف: نقل التركيز إلى حقل البحث
                    self.search_input.setFocus()
                    return True
        
        return super().eventFilter(obj, event)

    def show_toast(self, message, is_success=True):
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_info_toast(self, message):
        ToastMessage(self, message, COLORS['info'])

    def show_warning_toast(self, message):
        self.show_toast(message, is_success=False)

    def show_success_toast(self, message):
        self.show_toast(message, is_success=True)

    def live_search(self):
        text = self.search_input.text()
        if len(text) < 2:
            self.results_list.hide()
            return
        try:
            results = search_products(text)
            self.results_list.clear()
            for p in results:
                item_text = f"📦 {p[1]} | سعر: {p[4]:.2f} ج.م | المخزن: {p[5]}"
                self.results_list.addItem(item_text)
                self.results_list.item(self.results_list.count()-1).setData(Qt.ItemDataRole.UserRole, p)
            self.results_list.show() if results else self.results_list.hide()
        except Exception as e:
            print(f"خطأ في البحث: {e}")

    def add_from_search(self):
        text = self.search_input.text()
        if text:
            try:
                results = search_products(text)
                if results:
                    self.add_to_cart_logic(results[0])
                    self.search_input.clear()
                    self.results_list.hide()
                    self.show_success_toast("✅ تم إضافة المنتج بنجاح")
            except Exception as e:
                self.show_warning_toast(f"❌ خطأ: {str(e)}")

    def add_from_list(self, item):
        product = item.data(Qt.ItemDataRole.UserRole)
        self.add_to_cart_logic(product)
        self.results_list.hide()
        self.search_input.clear()
        self.show_success_toast("✅ تم إضافة المنتج بنجاح")

    def add_to_cart_logic(self, p):
        try:
            p_id = p[0]
            name = p[1]
            price = p[4]
            stock = p[5]
            
            if p_id in self.cart_items:
                row = self.cart_items[p_id]['row']
                current_qty = int(self.table.item(row, 2).text())
                if current_qty + 1 > stock:
                    self.show_warning_toast(f"⚠️ الكمية المطلوبة أكبر من المتاحة ({stock})")
                    return
                self.update_row_qty(row, p_id, current_qty + 1, price)
                self.show_success_toast(f"✅ تم تحديث كمية {name}")
            else:
                if stock < 1:
                    self.show_warning_toast(f"⚠️ المنتج {name} غير متوفر في المخزون")
                    return
                    
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setRowHeight(row, 55)
                self.table.setItem(row, 0, QTableWidgetItem(name))
                self.table.setItem(row, 1, QTableWidgetItem(f"{price:.2f}"))
                self.table.setItem(row, 2, QTableWidgetItem("1"))
                self.table.setItem(row, 3, QTableWidgetItem(f"{price:.2f}"))

                spin_qty = QSpinBox()
                spin_qty.setMinimum(1)
                spin_qty.setMaximum(stock)
                spin_qty.setValue(1)
                spin_qty.setStyleSheet(f"""
                    QSpinBox {{
                        background-color: {COLORS['bg_dark']};
                        color: {COLORS['text']};
                        border: 1px solid {COLORS['accent']};
                        border-radius: 6px;
                        padding: 5px;
                    }}
                """)
                spin_qty.valueChanged.connect(lambda val, pid=p_id, pr=price: self.update_qty_from_spin(pid, val, pr))
                self.table.setCellWidget(row, 4, spin_qty)

                btn_del = QPushButton("🗑️ حذف")
                btn_del.setFixedSize(70, 35)
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
                btn_del.clicked.connect(lambda ch, pid=p_id: self.remove_item(pid))
                self.table.setCellWidget(row, 5, btn_del)

                self.cart_items[p_id] = {'row': row, 'price': price, 'name': name, 'stock': stock}
                self.show_success_toast(f"✅ تم إضافة {name} إلى السلة")
            self.update_total()
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ: {str(e)}")

    def update_qty_from_spin(self, p_id, new_qty, price):
        if p_id in self.cart_items:
            row = self.cart_items[p_id]['row']
            self.update_row_qty(row, p_id, new_qty, price)

    def update_row_qty(self, row, p_id, qty, price):
        self.table.setItem(row, 2, QTableWidgetItem(str(qty)))
        self.table.setItem(row, 3, QTableWidgetItem(f"{qty * price:.2f}"))

    def remove_item(self, p_id):
        if p_id in self.cart_items:
            name = self.cart_items[p_id]['name']
            row = self.cart_items[p_id]['row']
            self.table.removeRow(row)
            del self.cart_items[p_id]
            for idx, (pid, info) in enumerate(self.cart_items.items()):
                info['row'] = idx
            self.update_total()
            self.show_success_toast(f"🗑️ تم حذف {name} من السلة")

    def update_total(self):
        try:
            subtotal = 0
            for i in range(self.table.rowCount()):
                subtotal += float(self.table.item(i, 3).text())
            try:
                discount = float(self.discount_input.text()) if self.discount_input.text() else 0
            except:
                discount = 0
            total = subtotal - discount
            self.total_label.setText(f"الإجمالي: {max(0, total):.2f} ج.م")
        except Exception as e:
            print(f"خطأ في تحديث الإجمالي: {e}")

    def reset_ui(self):
        self.table.setRowCount(0)
        self.cart_items.clear()
        self.discount_input.setText("0")
        self.search_input.clear()
        self.update_total()

    def get_sale_data(self):
        if self.table.rowCount() == 0:
            return None, None, None, None, "لا توجد منتجات في السلة"
        
        for p_id, info in self.cart_items.items():
            qty = int(self.table.item(info['row'], 2).text())
            if qty > info['stock']:
                return None, None, None, None, f"المنتج {info['name']} غير متوفر بالكمية المطلوبة"
        
        items_for_db = []
        items_for_pdf = []
        subtotal = 0
        
        for p_id, info in self.cart_items.items():
            qty = int(self.table.item(info['row'], 2).text())
            items_for_db.append((p_id, qty, info['price']))
            items_for_pdf.append((info['name'], qty, info['price']))
            subtotal += (qty * info['price'])

        try:
            discount = float(self.discount_input.text()) if self.discount_input.text() else 0
        except:
            discount = 0
        
        total = subtotal - discount
        
        return items_for_db, items_for_pdf, total, discount, None

    def process_cash_sale(self):
        """معالجة البيع النقدي - تم تعديلها لاستقبال القيم بشكل صحيح"""
        try:
            items_for_db, items_for_pdf, total, discount, error = self.get_sale_data()
            
            if error:
                self.show_warning_toast(f"⚠️ {error}")
                return
            
            # استقبال جميع القيم المرتجعة من make_sale
            result = make_sale(items_for_db, total, discount, payment_method='نقدي', customer_name=None)
            
            # التحقق من عدد القيم المرتجعة
            if isinstance(result, tuple):
                if len(result) == 2:
                    success, sale_id = result
                elif len(result) == 3:
                    # إذا كانت الدالة ترجع 3 قيم
                    success, sale_id, _ = result
                else:
                    # إذا كانت ترجع أكثر من قيمتين
                    success = result[0] if len(result) > 0 else False
                    sale_id = result[1] if len(result) > 1 else None
            else:
                success = result
                sale_id = None
            
            if success:
                self.generate_invoice(sale_id, items_for_pdf, total, discount,
                                     sum(qty * price for _, qty, price in items_for_db))
                self.reset_ui()
                self.show_success_toast(f"✅ تمت عملية البيع النقدي بنجاح - الفاتورة رقم {sale_id}")
            else:
                self.show_warning_toast(f"❌ فشل حفظ البيع: {sale_id}")
                
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ: {str(e)}")
            print(f"تفاصيل الخطأ في process_cash_sale: {e}")

    def process_deferred_sale(self):
        """معالجة البيع الآجل - تم تعديلها لاستقبال القيم بشكل صحيح"""
        try:
            items_for_db, items_for_pdf, total, discount, error = self.get_sale_data()
            
            if error:
                self.show_warning_toast(f"⚠️ {error}")
                return
            
            dialog = CustomerNameDialog(self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                customer_name = dialog.get_customer_name()
                
                if not customer_name:
                    self.show_warning_toast("❌ اسم العميل مطلوب لإتمام البيع الآجل")
                    return
                
                # استقبال جميع القيم المرتجعة من make_sale
                result = make_sale(items_for_db, total, discount, payment_method='آجل', customer_name=customer_name)
                
                # التحقق من عدد القيم المرتجعة
                if isinstance(result, tuple):
                    if len(result) == 2:
                        success, sale_id = result
                    elif len(result) == 3:
                        # إذا كانت الدالة ترجع 3 قيم
                        success, sale_id, _ = result
                    else:
                        # إذا كانت ترجع أكثر من قيمتين
                        success = result[0] if len(result) > 0 else False
                        sale_id = result[1] if len(result) > 1 else None
                else:
                    success = result
                    sale_id = None
                
                if success:
                    self.generate_invoice(sale_id, items_for_pdf, total, discount,
                                         sum(qty * price for _, qty, price in items_for_db))
                    self.reset_ui()
                    self.show_info_toast(f"✅ تم خصم البضاعة من المخزن وتسجيل دَين على العميل {customer_name} - فاتورة رقم {sale_id}")
                else:
                    self.show_warning_toast(f"❌ فشل حفظ البيع: {sale_id}")
            else:
                self.show_warning_toast("❌ تم إلغاء عملية البيع الآجل")
                
        except Exception as e:
            self.show_warning_toast(f"❌ خطأ في البيع الآجل: {str(e)}")
            print(f"تفاصيل الخطأ في process_deferred_sale: {e}")

    def generate_invoice(self, sale_id, items, total, discount, subtotal):
        # ... (نفس الكود الموجود بدون تغيير) ...
        if not os.path.exists('invoices'):
            os.makedirs('invoices')
        
        filename = f"invoices/invoice_{sale_id}.pdf"
        c = canvas.Canvas(filename, pagesize=(80*mm, 200*mm))
        
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(40*mm, 185*mm, "SMART MARKET")
        c.setFont("Helvetica", 9)
        c.drawCentredString(40*mm, 175*mm, "سوبر ماركت")
        c.drawCentredString(40*mm, 168*mm, f"فاتورة رقم: {sale_id}")
        
        c.drawCentredString(40*mm, 161*mm, f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        c.line(5*mm, 155*mm, 75*mm, 155*mm)
        
        c.setFont("Helvetica-Bold", 8)
        c.drawString(5*mm, 148*mm, "المنتج")
        c.drawString(50*mm, 148*mm, "الكمية")
        c.drawRightString(75*mm, 148*mm, "السعر")
        
        c.line(5*mm, 145*mm, 75*mm, 145*mm)
        
        y = 138*mm
        c.setFont("Helvetica", 8)
        for name, qty, price in items:
            if y < 20*mm:
                c.showPage()
                y = 185*mm
            c.drawString(5*mm, y, name[:20])
            c.drawString(50*mm, y, str(qty))
            c.drawRightString(75*mm, y, f"{qty*price:.2f}")
            y -= 5*mm
        
        c.line(5*mm, y+2*mm, 75*mm, y+2*mm)
        y -= 5*mm
        
        c.setFont("Helvetica", 9)
        c.drawString(5*mm, y, f"المجموع: {subtotal:.2f} ج.م")
        y -= 5*mm
        c.drawString(5*mm, y, f"الخصم: {discount:.2f} ج.م")
        y -= 7*mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(5*mm, y, f"الإجمالي: {total:.2f} ج.م")
        
        c.line(5*mm, y-3*mm, 75*mm, y-3*mm)
        y -= 10*mm
        c.setFont("Helvetica", 8)
        c.drawCentredString(40*mm, y, "شكراً لتسوقكم معنا")
        
        c.save()
        try:
            os.startfile(filename)
        except:
            pass