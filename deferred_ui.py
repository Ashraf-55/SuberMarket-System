"""
نافذة الحسابات الآجلة - تدعم إضافة وتسوية وحذف الديون
مع توحيد الهوية البصرية ونظام الـ Toast
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel,
                             QPushButton, QFrame, QDialog, QFormLayout, QLineEdit,
                             QDateEdit, QDoubleSpinBox, QComboBox, QTextEdit)
from PyQt6.QtCore import Qt, QDate, QPropertyAnimation, QTimer
from back import database as db
from PyQt6.QtGui import QFont

# ========== الألوان الثابتة الموحدة ==========
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
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()


# ========== نافذة إضافة دين جديد ==========
class AddDebtDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة حساب آجل جديد")
        self.setModal(True)
        self.resize(500, 400)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
            }}
            QLineEdit, QDateEdit, QComboBox, QDoubleSpinBox, QTextEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }}
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
            QTextEdit {{
                min-height: 80px;
            }}
        """)
        
        layout = QFormLayout(self)
        layout.setSpacing(15)
        
        self.customer_name = QLineEdit()
        self.customer_name.setPlaceholderText("مثال: أحمد محمد")
        self.customer_phone = QLineEdit()
        self.customer_phone.setPlaceholderText("مثال: 01234567890")
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 1000000)
        self.amount.setPrefix("ج.م ")
        self.due_date = QDateEdit()
        self.due_date.setCalendarPopup(True)
        self.due_date.setDate(QDate.currentDate().addDays(30))
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("ملاحظات إضافية...")
        
        layout.addRow("اسم العميل:", self.customer_name)
        layout.addRow("رقم الهاتف:", self.customer_phone)
        layout.addRow("المبلغ:", self.amount)
        layout.addRow("تاريخ الاستحقاق:", self.due_date)
        layout.addRow("ملاحظات:", self.notes)
        
        buttons = QHBoxLayout()
        buttons.setSpacing(15)
        
        save_btn = QPushButton("💾 حفظ")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)
    
    def get_data(self):
        return {
            'customer_name': self.customer_name.text(),
            'customer_phone': self.customer_phone.text(),
            'amount': float(self.amount.value()),
            'due_date': self.due_date.date().toString("yyyy-MM-dd"),
            'notes': self.notes.toPlainText()
        }


# ========== نافذة تسوية دفعة ==========
class PaymentDialog(QDialog):
    def __init__(self, debt_id, remaining_amount, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تسوية دفعة")
        self.debt_id = debt_id
        self.setModal(True)
        self.resize(450, 350)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
            }}
            QLineEdit, QComboBox, QDoubleSpinBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """)
        
        layout = QFormLayout(self)
        layout.setSpacing(15)
        
        self.remaining_label = QLabel(f"{remaining_amount:,.2f} ج.م")
        self.remaining_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {COLORS['warning']}; padding: 5px;")
        self.remaining_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.payment_amount = QDoubleSpinBox()
        self.payment_amount.setRange(0, remaining_amount)
        self.payment_amount.setPrefix("ج.م ")
        
        self.payment_method = QComboBox()
        self.payment_method.addItems(["نقدي", "تحويل بنكي", "شيك", "بطاقة ائتمان"])
        
        self.notes = QLineEdit()
        self.notes.setPlaceholderText("ملاحظات عن الدفعة...")
        
        layout.addRow("المبلغ المتبقي:", self.remaining_label)
        layout.addRow("مبلغ الدفعة:", self.payment_amount)
        layout.addRow("طريقة الدفع:", self.payment_method)
        layout.addRow("ملاحظات:", self.notes)
        
        buttons = QHBoxLayout()
        buttons.setSpacing(15)
        
        save_btn = QPushButton("💰 تسجيل الدفعة")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("❌ إلغاء")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 12px 25px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)
    
    def get_data(self):
        return {
            'amount': float(self.payment_amount.value()),
            'method': self.payment_method.currentText(),
            'notes': self.notes.text()
        }


# ========== شاشة الحسابات الآجلة ==========
class DeferredAccountsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("💳 الحسابات الآجلة")
        title.setFont(FONTS['title'])
        title.setStyleSheet(f"color: {COLORS['text']}; padding: 10px;")
        layout.addWidget(title)
        
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
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
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
        """)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "اسم العميل", "المبلغ الكلي", "المدفوع", "المتبقي", "تاريخ الاستحقاق", "الحالة"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        buttons = QHBoxLayout()
        buttons.setSpacing(15)
        
        add_btn = QPushButton("➕ إضافة حساب")
        add_btn.setFont(FONTS['button'])
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                padding: 12px 25px;
                border-radius: 10px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info_hover']};
            }}
        """)
        add_btn.clicked.connect(self.add_debt)
        
        pay_btn = QPushButton("💰 تسوية دفعة")
        pay_btn.setFont(FONTS['button'])
        pay_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                padding: 12px 25px;
                border-radius: 10px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
        """)
        pay_btn.clicked.connect(self.make_payment)
        
        delete_btn = QPushButton("🗑️ حذف")
        delete_btn.setFont(FONTS['button'])
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 12px 25px;
                border-radius: 10px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
        """)
        delete_btn.clicked.connect(self.delete_debt)
        
        buttons.addWidget(add_btn)
        buttons.addWidget(pay_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        layout.addLayout(buttons)
        
        self.load_debts()
    
    def show_toast(self, message, is_success=True):
        color = COLORS['success'] if is_success else COLORS['danger']
        ToastMessage(self, message, color)
    
    def show_info_toast(self, message):
        ToastMessage(self, message, COLORS['info'])
    
    def show_warning_toast(self, message):
        ToastMessage(self, message, COLORS['warning'])
    
    def show_success_toast(self, message):
        ToastMessage(self, message, COLORS['success'])
    
    def load_debts(self):
        debts = db.get_all_debts()
        self.table.setRowCount(len(debts))
        
        for row, debt in enumerate(debts):
            self.table.setRowHeight(row, 55)
            
            debt_id = debt['id']
            customer_name = debt['customer_name']
            amount = float(debt['amount']) if debt['amount'] else 0.0
            paid_amount = float(debt['paid_amount']) if debt['paid_amount'] else 0.0
            remaining_amount = float(debt['remaining_amount']) if debt['remaining_amount'] else 0.0
            due_date = debt['due_date'] if debt['due_date'] else "غير محدد"
            status = debt['status'] if debt['status'] else "مستحق"
            
            self.table.setItem(row, 0, QTableWidgetItem(str(debt_id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(customer_name)))
            self.table.setItem(row, 2, QTableWidgetItem(f"{amount:,.2f} ج.م"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{paid_amount:,.2f} ج.م"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{remaining_amount:,.2f} ج.م"))
            self.table.setItem(row, 5, QTableWidgetItem(str(due_date)))
            
            status_item = QTableWidgetItem(status)
            if status == "متأخر":
                status_item.setForeground(Qt.GlobalColor.red)
            elif status == "مدفوع":
                status_item.setForeground(Qt.GlobalColor.green)
            elif status == "مستحق":
                status_item.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(row, 6, status_item)
            
            # ✅ أزرار الإجراءات في عمود منفصل (سنضيفها في تحديث لاحق)
            # إضافة أزرار حذف وتسوية داخل الجدول
    
    def add_debt(self):
        dlg = AddDebtDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            success, msg = db.add_debt(
                customer_name=data['customer_name'],
                amount=data['amount'],
                due_date=data['due_date'],
                sale_id=None,
                customer_phone=data['customer_phone'],
                notes=data['notes']
            )
            
            if success:
                self.show_success_toast("✅ تم إضافة الحساب بنجاح")
                self.load_debts()
            else:
                self.show_warning_toast(f"❌ فشل إضافة الحساب: {msg}")
    
    def make_payment(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_warning_toast("⚠️ الرجاء اختيار حساب أولاً")
            return
        
        debt_id = int(self.table.item(row, 0).text())
        remaining_text = self.table.item(row, 4).text().replace(" ج.م", "").replace(",", "")
        remaining = float(remaining_text) if remaining_text else 0.0
        
        if remaining <= 0:
            self.show_warning_toast("⚠️ هذا الحساب مدفوع بالكامل")
            return
        
        dlg = PaymentDialog(debt_id, remaining, self)
        if dlg.exec():
            data = dlg.get_data()
            if data['amount'] > 0:
                success, msg = db.add_debt_payment(
                    debt_id=debt_id,
                    payment_amount=data['amount'],
                    payment_method=data['method'],
                    notes=data['notes']
                )
                
                if success:
                    self.show_success_toast(f"✅ تم تسجيل دفعة بقيمة {data['amount']:,.2f} ج.م")
                    self.load_debts()
                else:
                    self.show_warning_toast(f"❌ فشل تسجيل الدفعة: {msg}")
    
    def delete_debt(self):
        row = self.table.currentRow()
        if row < 0:
            self.show_warning_toast("⚠️ الرجاء اختيار حساب أولاً")
            return
        
        debt_id = int(self.table.item(row, 0).text())
        customer_name = self.table.item(row, 1).text()
        
        success, msg = db.delete_debt(debt_id)
        if success:
            self.show_success_toast(f"✅ تم حذف حساب {customer_name}")
            self.load_debts()
        else:
            self.show_warning_toast(f"❌ فشل حذف الحساب: {msg}")