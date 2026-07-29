# ================= manage_categories_ui.py - إدارة التصنيفات =================
"""
مدير التصنيفات - واجهة لإدارة تصنيفات المنتجات
"""

import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLineEdit, QInputDialog, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from back.database import get_all_categories, add_category, update_category, delete_category

logger = logging.getLogger(__name__)

# الألوان
COLORS = {
    'bg_dark': '#0f172a',
    'bg_sidebar': '#1e293b',
    'bg_card': '#1e293b',
    'text': '#f8fafc',
    'text_muted': '#94a3b8',
    'accent': '#38bdf8',
    'accent_hover': '#0ea5e9',
    'success': '#22c55e',
    'success_hover': '#16a34a',
    'danger': '#ef4444',
    'danger_hover': '#dc2626',
    'warning': '#f59e0b',
    'warning_hover': '#d97706',
    'border': '#334155',
    'info': '#38bdf8',
}


class CategoryManagerDialog(QDialog):
    """نافذة إدارة التصنيفات"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📂 إدارة التصنيفات")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
                border: 2px solid {COLORS['accent']};
                border-radius: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("📂 إدارة التصنيفات")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # نموذج إضافة تصنيف
        form_layout = QHBoxLayout()
        form_layout.setSpacing(10)
        
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("اسم التصنيف الجديد")
        self.category_input.setStyleSheet(self._get_input_style())
        form_layout.addWidget(self.category_input, 1)
        
        add_btn = QPushButton("➕ إضافة")
        add_btn.setMinimumHeight(36)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background-color: {COLORS['success_hover']}; }}
        """)
        add_btn.clicked.connect(self.add_category)
        form_layout.addWidget(add_btn)
        
        layout.addLayout(form_layout)
        
        # جدول التصنيفات
        self.categories_table = QTableWidget(0, 2)
        self.categories_table.setHorizontalHeaderLabels(["ID", "اسم التصنيف"])
        self.categories_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_sidebar']};
                color: {COLORS['accent']};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
        """)
        self.categories_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.categories_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.categories_table.setColumnHidden(0, True)
        layout.addWidget(self.categories_table)
        
        # أزرار التحكم
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        edit_btn = QPushButton("✏️ تعديل")
        edit_btn.setMinimumHeight(36)
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['warning']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background-color: {COLORS['warning_hover']}; }}
        """)
        edit_btn.clicked.connect(self.edit_category)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ حذف")
        delete_btn.setMinimumHeight(36)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                padding: 0 20px;
            }}
            QPushButton:hover {{ background-color: {COLORS['danger_hover']}; }}
        """)
        delete_btn.clicked.connect(self.delete_category)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("✓ إغلاق")
        close_btn.setMinimumHeight(36)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                border: none;
                padding: 0 30px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.load_categories()
    
    def _get_input_style(self):
        return f"""
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
        """
    
    def load_categories(self):
        """تحميل قائمة التصنيفات"""
        try:
            categories = get_all_categories()
            self.categories_table.setRowCount(len(categories))
            for row, cat in enumerate(categories):
                self.categories_table.setItem(row, 0, QTableWidgetItem(str(cat['id'])))
                self.categories_table.setItem(row, 1, QTableWidgetItem(cat['name']))
        except Exception as e:
            logger.error(f"خطأ في تحميل التصنيفات: {e}")
            self.show_toast(f"❌ خطأ في تحميل التصنيفات: {str(e)}")
    
    def add_category(self):
        """إضافة تصنيف جديد"""
        name = self.category_input.text().strip()
        if not name:
            self.show_toast("⚠️ الرجاء إدخال اسم التصنيف")
            return
        
        try:
            success, message = add_category(name)
            if success:
                self.show_toast(f"✅ تم إضافة التصنيف: {name}")
                self.category_input.clear()
                self.load_categories()
            else:
                self.show_toast(f"❌ {message}")
        except Exception as e:
            logger.error(f"خطأ في add_category: {e}")
            self.show_toast(f"❌ خطأ: {str(e)}")
    
    def edit_category(self):
        """تعديل تصنيف محدد"""
        row = self.categories_table.currentRow()
        if row < 0:
            self.show_toast("⚠️ الرجاء اختيار تصنيف للتعديل")
            return
        
        cat_id = int(self.categories_table.item(row, 0).text())
        old_name = self.categories_table.item(row, 1).text()
        
        new_name, ok = QInputDialog.getText(
            self, "تعديل التصنيف",
            "اسم التصنيف الجديد:",
            QLineEdit.Normal, old_name
        )
        
        if ok and new_name.strip():
            try:
                success, message = update_category(cat_id, new_name.strip())
                if success:
                    self.show_toast(f"✅ تم تحديث التصنيف")
                    self.load_categories()
                else:
                    self.show_toast(f"❌ {message}")
            except Exception as e:
                logger.error(f"خطأ في edit_category: {e}")
                self.show_toast(f"❌ خطأ: {str(e)}")
    
    def delete_category(self):
        """حذف تصنيف محدد"""
        row = self.categories_table.currentRow()
        if row < 0:
            self.show_toast("⚠️ الرجاء اختيار تصنيف للحذف")
            return
        
        cat_id = int(self.categories_table.item(row, 0).text())
        cat_name = self.categories_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل أنت متأكد من حذف التصنيف: {cat_name}؟",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success, message = delete_category(cat_id)
                if success:
                    self.show_toast(f"✅ تم حذف التصنيف: {cat_name}")
                    self.load_categories()
                else:
                    self.show_toast(f"❌ {message}")
            except Exception as e:
                logger.error(f"خطأ في delete_category: {e}")
                self.show_toast(f"❌ خطأ: {str(e)}")
    
    def show_toast(self, message):
        """عرض رسالة Toast"""
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import QTimer, QPropertyAnimation
        
        toast = QLabel(message, self)
        toast.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['accent']};
                border-radius: 12px;
                padding: 12px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        toast.setAlignment(Qt.AlignCenter)
        toast.setWordWrap(True)
        toast.setMinimumHeight(45)
        toast.setMaximumWidth(350)
        
        screen = self.screen().availableGeometry()
        x = (screen.width() - toast.width()) // 2
        y = screen.height() - 100
        toast.move(x, y)
        toast.setWindowOpacity(0)
        toast.show()
        
        anim = QPropertyAnimation(toast, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(0.95)
        anim.start()
        
        QTimer.singleShot(2500, lambda: self._fade_toast(toast))
    
    def _fade_toast(self, toast):
        from PyQt5.QtCore import QPropertyAnimation
        anim = QPropertyAnimation(toast, b"windowOpacity")
        anim.setDuration(400)
        anim.setStartValue(0.95)
        anim.setEndValue(0)
        anim.finished.connect(toast.deleteLater)
        anim.start()