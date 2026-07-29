"""
login_ui.py - نافذة تسجيل الدخول للنظام مع واجهة حديثة
يدعم وضعين: إنشاء حساب المدير (أول مرة) وتسجيل الدخول العادي
📡 [تم الربط] مع قاعدة البيانات عبر دالة login_user و register_admin
🔄 [تم الإصلاح] للانتقال إلى لوحة التحكم الرئيسية بعد تسجيل الدخول
"""

import sys
import logging
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel, QFrame, QShortcut,
                             QSizePolicy, QDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent
from PyQt5.QtGui import QFont, QKeySequence
import os

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from back.database import login_user, change_password, is_users_table_empty, register_admin, initialize_system

# الألوان - Modern Dark Mode
COLORS = {
    'bg_dark': '#0f172a',
    'bg_sidebar': '#1e293b',
    'bg_card': '#1e293b',
    'bg_hover': '#334155',
    'text': '#f8fafc',
    'text_muted': '#94a3b8',
    'accent': '#38bdf8',
    'accent_hover': '#0ea5e9',
    'success': '#22c55e',
    'success_dark': '#16a34a',
    'danger': '#ef4444',
    'danger_dark': '#dc2626',
    'warning': '#f59e0b',
    'border': '#334155'
}


class ToastNotification(QFrame):
    """نظام Toast موحد - لون واحد ثابت لجميع أنواع الرسائل"""
    def __init__(self, message, parent=None, duration=2500):
        super().__init__(parent)
        self.setObjectName("Toast")
        
        # لون موحد للجميع
        toast_color = COLORS['bg_card']
        border_color = COLORS['accent']
        
        self.setStyleSheet(f"""
            #Toast {{
                background-color: {toast_color};
                border: 2px solid {border_color};
                border-radius: 15px;
                padding: 10px 18px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        icon_label = QLabel("ℹ️")
        icon_label.setStyleSheet(f"font-size: 16px; color: {COLORS['accent']};")
        layout.addWidget(icon_label)
        
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # حساب الموقع بناءً على حجم الشاشة
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setFixedWidth(min(350, screen_geometry.width() - 40))
        x = (screen_geometry.width() - self.width()) // 2
        y = screen_geometry.height() - 100
        self.move(x, y)
        
        self.show()
        self.raise_()
        QTimer.singleShot(duration, self.fade_out)
    
    def fade_out(self):
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.close)
        self.animation.start()


class ChangePasswordDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.result = False
        self.parent_window = parent
        self.setWindowTitle("تغيير كلمة المرور")
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        # حساب حجم النافذة بناءً على حجم الشاشة
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.35)
        height = int(screen_geometry.height() * 0.4)
        self.setMinimumSize(int(screen_geometry.width() * 0.3), int(screen_geometry.height() * 0.3))
        self.resize(max(380, width), max(340, height))
        width = max(380, min(width, 500))
        height = max(340, min(height, 450))
        self.setMinimumSize(380, 340)
        self.resize(width, height)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: transparent;
            }}
        """)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setup_ui()
        self.setup_shortcuts()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        bg_frame = QFrame()
        bg_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border: 2px solid {COLORS['accent']};
                border-radius: 20px;
            }}
        """)
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setContentsMargins(20, 20, 20, 20)
        bg_layout.setSpacing(12)
        
        title = QLabel("🔐 تغيير كلمة المرور")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']};")
        bg_layout.addWidget(title)
        
        user_info = QLabel(f"المستخدم: {self.username}")
        user_info.setAlignment(Qt.AlignCenter)
        user_info.setStyleSheet(f"color: {COLORS['text_muted']};")
        bg_layout.addWidget(user_info)
        
        bg_layout.addSpacing(10)
        
        # ====== تعديل الريسبونسيف: تغليف المحتوى بـ ScrollArea ======
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)
        

        self.old_pwd = QLineEdit()
        self.old_pwd.setPlaceholderText("كلمة المرور الحالية")
        self.old_pwd.setEchoMode(QLineEdit.Password)
        self.old_pwd.setMinimumHeight(40)
        self.old_pwd.setStyleSheet(self.get_input_style())
        scroll_layout.addWidget(self.old_pwd)
        bg_layout.addWidget(self.old_pwd)
        
        self.new_pwd = QLineEdit()
        self.new_pwd.setPlaceholderText("كلمة المرور الجديدة")
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.setMinimumHeight(40)
        self.new_pwd.setStyleSheet(self.get_input_style())
        scroll_layout.addWidget(self.new_pwd)
        bg_layout.addWidget(self.new_pwd)
        
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setPlaceholderText("تأكيد كلمة المرور الجديدة")
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd.setMinimumHeight(40)
        self.confirm_pwd.setStyleSheet(self.get_input_style())
        scroll_layout.addWidget(self.confirm_pwd)
        
        scroll.setWidget(scroll_widget)
        bg_layout.addWidget(scroll)
        bg_layout.addWidget(self.confirm_pwd)
        
        bg_layout.addSpacing(10)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border-radius: 10px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: {COLORS['danger_dark']}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        change_btn = QPushButton("تغيير")
        change_btn.setMinimumHeight(38)
        change_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border-radius: 10px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: {COLORS['success_dark']}; }}
        """)
        change_btn.clicked.connect(self.change_password)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(change_btn)
        bg_layout.addLayout(btn_layout)
        
        layout.addWidget(bg_frame)
    
    def get_input_style(self):
        return f"""
            QLineEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
            }}
        """
    
    def setup_shortcuts(self):
        enter_shortcut = QShortcut(QKeySequence("Return"), self)
        enter_shortcut.activated.connect(self.change_password)
        enter_shortcut2 = QShortcut(QKeySequence("Enter"), self)
        enter_shortcut2.activated.connect(self.change_password)
        
        esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        esc_shortcut.activated.connect(self.reject)
        
        self.old_pwd.installEventFilter(self)
        self.new_pwd.installEventFilter(self)
        self.confirm_pwd.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Down:
                if obj == self.old_pwd:
                    self.new_pwd.setFocus()
                elif obj == self.new_pwd:
                    self.confirm_pwd.setFocus()
            elif key == Qt.Key_Up:
                if obj == self.confirm_pwd:
                    self.new_pwd.setFocus()
                elif obj == self.new_pwd:
                    self.old_pwd.setFocus()
        return super().eventFilter(obj, event)
    
    def change_password(self):
        old = self.old_pwd.text().strip()
        new = self.new_pwd.text().strip()
        confirm = self.confirm_pwd.text().strip()
        
        if not old:
            self.show_toast("الرجاء إدخال كلمة المرور الحالية")
            self.old_pwd.setFocus()
            return
        
        if not new:
            self.show_toast("الرجاء إدخال كلمة المرور الجديدة")
            self.new_pwd.setFocus()
            return
        
        if len(new) < 4:
            self.show_toast("كلمة المرور الجديدة يجب أن تكون 4 أحرف على الأقل")
            self.new_pwd.setFocus()
            return
        
        if new != confirm:
            self.show_toast("كلمة المرور غير متطابقة مع التأكيد")
            self.confirm_pwd.clear()
            self.confirm_pwd.setFocus()
            return
        
        # استدعاء change_password - تستخدم الهاش الجديد تلقائياً
        success, message, was_upgraded = change_password(self.username, old, new)
        
        if success:
            self.show_toast(message)
            self.result = True
            
            # إذا تمت ترقية كلمة المرور من نص صريح إلى هاش، نعرض رسالة توضيحية
            if was_upgraded:
                QTimer.singleShot(500, lambda: self.show_upgrade_notification())
            else:
                QTimer.singleShot(1000, self.accept)
        else:
            self.show_toast(message)
    
    def show_upgrade_notification(self):
        """عرض رسالة تنبيه بأن كلمة المرور تمت ترقيتها تلقائياً"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🔒 ترقية كلمة المرور")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("تم ترقية كلمة المرور الخاصة بك تلقائياً إلى نظام تشفير أكثر أماناً.")
        msg_box.setInformativeText("لا داعي للقلق، هذا إجراء أمني تلقائي. يمكنك الاستمرار في استخدام كلمة المرور نفسها.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
            }}
            QMessageBox QLabel {{
                color: {COLORS['text']};
            }}
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        msg_box.exec_()
        self.accept()
    
    def show_toast(self, message):
        ToastNotification(message, self.parent())


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.dashboard = None
        self.is_setup_mode = False
        self.login_success = False
        self.result = False
        self.user_info = None
        self.password_upgraded = False
        
        try:
            initialize_system()
        except Exception as e:
            logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")
        
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_keyboard_navigation()
        
        self.check_and_switch_mode()
    
    def setup_ui(self):
        self.setWindowTitle("الماركت الذكي - نظام إدارة المبيعات")
        
        # ====== تعديل الريسبونسيف: حساب حجم النافذة بناءً على حجم الشاشة ======
        # حساب حجم النافذة بناءً على حجم الشاشة
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.35)
        height = int(screen_geometry.height() * 0.6)
        self.setMinimumSize(int(screen_geometry.width() * 0.3), int(screen_geometry.height() * 0.5))
        self.resize(max(450, width), max(550, height))
        width = max(450, min(width, 600))
        height = max(550, min(height, 700))
        self.setMinimumSize(450, 550)
        self.resize(width, height)
        
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS['bg_dark']}, stop:1 {COLORS['bg_sidebar']});
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 40, 30, 40)
        main_layout.setSpacing(20)
        
        logo_frame = QFrame()
        logo_frame.setMinimumHeight(120)
        logo_layout = QVBoxLayout(logo_frame)
        
        self.logo_label = QLabel("🛒")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("font-size: 60px;")
        logo_layout.addWidget(self.logo_label)
        
        self.title_label = QLabel("الماركت الذكي")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: bold;
            color: {COLORS['accent']};
            letter-spacing: 1px;
        """)
        logo_layout.addWidget(self.title_label)
        
        self.subtitle_label = QLabel("نظام إدارة المبيعات المتكامل")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet(f"""
            font-size: 11px;
            color: {COLORS['text_muted']};
        """)
        logo_layout.addWidget(self.subtitle_label)
        
        main_layout.addWidget(logo_frame)
        main_layout.addSpacing(10)
        
        username_frame = QFrame()
        username_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        username_layout = QVBoxLayout(username_frame)
        username_layout.setContentsMargins(18, 10, 18, 10)
        
        username_icon = QLabel("👤 اسم المستخدم")
        username_icon.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        username_layout.addWidget(username_icon)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("أدخل اسم المستخدم...")
        self.username_input.setMinimumHeight(42)
        self.username_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {COLORS['text']};
                border: none;
                padding: 6px 0;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: none;
            }}
        """)
        username_layout.addWidget(self.username_input)
        
        main_layout.addWidget(username_frame)
        
        password_frame = QFrame()
        password_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        password_layout = QVBoxLayout(password_frame)
        password_layout.setContentsMargins(18, 10, 18, 10)
        
        password_icon = QLabel("🔒 كلمة المرور")
        password_icon.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        password_layout.addWidget(password_icon)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(42)
        self.password_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {COLORS['text']};
                border: none;
                padding: 6px 0;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: none;
            }}
        """)
        password_layout.addWidget(self.password_input)
        
        main_layout.addWidget(password_frame)
        
        main_layout.addSpacing(10)
        
        self.action_btn = QPushButton("🔓 دخول")
        self.action_btn.setMinimumHeight(52)
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['accent']}, stop:1 {COLORS['accent_hover']});
                color: white;
                border-radius: 12px;
                font-size: 15px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['accent_hover']}, stop:1 {COLORS['accent']});
            }}
            QPushButton:pressed {{
                padding-top: 2px;
            }}
        """)
        self.action_btn.clicked.connect(self.handle_action)
        main_layout.addWidget(self.action_btn)
        
        self.change_btn = QPushButton("🔐 تغيير كلمة المرور")
        self.change_btn.setMinimumHeight(38)
        self.change_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
                color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
        """)
        self.change_btn.clicked.connect(self.show_change_password_dialog)
        main_layout.addWidget(self.change_btn)
        
        main_layout.addStretch()
        
        copyright_label = QLabel("© 2024 الماركت الذكي - جميع الحقوق محفوظة")
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; padding: 8px;")
        main_layout.addWidget(copyright_label)
    
    def update_ui_for_setup_mode(self):
        self.is_setup_mode = True
        self.setWindowTitle("الماركت الذكي - تهيئة النظام لأول مرة")
        self.title_label.setText("🏗️ إنشاء حساب المدير")
        self.subtitle_label.setText("الرجاء إدخال بيانات المدير الرئيسي")
        self.action_btn.setText("✅ إنشاء حساب المدير")
        self.change_btn.hide()
        self.username_input.setPlaceholderText("اسم المستخدم (مثال: admin)")
        self.password_input.setPlaceholderText("كلمة المرور (4 أحرف على الأقل)")
        self.username_input.clear()
        self.password_input.clear()
        self.username_input.setFocus()
    
    def update_ui_for_login_mode(self):
        self.is_setup_mode = False
        self.setWindowTitle("الماركت الذكي - تسجيل الدخول")
        self.title_label.setText("الماركت الذكي")
        self.subtitle_label.setText("نظام إدارة المبيعات المتكامل")
        self.action_btn.setText("🔓 دخول")
        self.change_btn.show()
        self.username_input.setPlaceholderText("أدخل اسم المستخدم...")
        self.password_input.setPlaceholderText("••••••••")
        self.username_input.clear()
        self.password_input.clear()
        self.username_input.setFocus()
    
    def setup_shortcuts(self):
        self.enter_shortcut = QShortcut(QKeySequence("Return"), self)
        self.enter_shortcut.activated.connect(self.handle_action)
        self.enter_shortcut2 = QShortcut(QKeySequence("Enter"), self)
        self.enter_shortcut2.activated.connect(self.handle_action)
    
    def setup_keyboard_navigation(self):
        self.username_input.installEventFilter(self)
        self.password_input.installEventFilter(self)
        self.username_input.setFocus()
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Down:
                if obj == self.username_input:
                    self.password_input.setFocus()
                    return True
            elif key == Qt.Key_Up:
                if obj == self.password_input:
                    self.username_input.setFocus()
                    return True
        return super().eventFilter(obj, event)
    
    def check_and_switch_mode(self):
        try:
            is_empty = is_users_table_empty()
            
            if is_empty:
                self.update_ui_for_setup_mode()
            else:
                self.update_ui_for_login_mode()
        except Exception as e:
            logger.error(f"خطأ في فحص المستخدمين: {e}")
            self.update_ui_for_login_mode()
    
    def handle_action(self):
        if self.is_setup_mode:
            self.handle_register()
        else:
            self.handle_login()
    
    def handle_register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username:
            self.show_toast("الرجاء إدخال اسم المستخدم")
            self.username_input.setFocus()
            return
        
        if len(username) < 3:
            self.show_toast("اسم المستخدم يجب أن يكون 3 أحرف على الأقل")
            self.username_input.setFocus()
            return
        
        if not password:
            self.show_toast("الرجاء إدخال كلمة المرور")
            self.password_input.setFocus()
            return
        
        if len(password) < 4:
            self.show_toast("كلمة المرور يجب أن تكون 4 أحرف على الأقل")
            self.password_input.setFocus()
            return
        
        success, message, user = register_admin(username, password)
        
        if success:
            self.show_toast("تم إنشاء حساب المدير بنجاح، جاري فتح لوحة التحكم...")
            self.action_btn.setEnabled(False)
            self.login_success = True
            self.result = True
            self.user_info = user
            QTimer.singleShot(500, self.close)
        else:
            self.show_toast(message)
            self.password_input.clear()
            self.password_input.setFocus()
    
    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username:
            self.show_toast("الرجاء إدخال اسم المستخدم")
            self.username_input.setFocus()
            return
        
        if not password:
            self.show_toast("الرجاء إدخال كلمة المرور")
            self.password_input.setFocus()
            return
        
        # login_user الآن ترجع user مع last_login و password_upgraded
        user = login_user(username, password)
        
        if user:
            self.user_info = {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
            
            # التحقق مما إذا كانت كلمة المرور تمت ترقيتها
            if user.get('password_upgraded', False):
                self.password_upgraded = True
                self.show_toast(f"مرحباً {username}، تم تسجيل الدخول بنجاح")
                self.show_password_upgrade_notification()
            else:
                self.show_toast(f"مرحباً {username}، تم تسجيل الدخول بنجاح")
            
            self.action_btn.setEnabled(False)
            self.login_success = True
            self.result = True
            QTimer.singleShot(500, self.close)
        else:
            self.show_toast("اسم المستخدم أو كلمة المرور غير صحيحة")
            self.password_input.clear()
            self.password_input.setFocus()
    
    def show_password_upgrade_notification(self):
        """عرض رسالة تنبيه بأن كلمة المرور تمت ترقيتها تلقائياً"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("🔒 ترقية أمنية")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("تم ترقية كلمة المرور الخاصة بك إلى نظام تشفير أكثر أماناً.")
        msg_box.setInformativeText(
            "هذا إجراء أمني تلقائي تم تطبيقه عند تسجيل الدخول.\n\n"
            "لا داعي لتغيير كلمة المرور، يمكنك الاستمرار في استخدامها كالمعتاد.\n"
            "تم تحديث نظام التشفير لحماية بياناتك بشكل أفضل."
        )
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
            }}
            QMessageBox QLabel {{
                color: {COLORS['text']};
            }}
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        msg_box.exec_()
    
    def show_toast(self, message):
        ToastNotification(message, self)
    
    def show_change_password_dialog(self):
        username = self.username_input.text().strip()
        
        if not username:
            self.show_toast("الرجاء إدخال اسم المستخدم أولاً")
            self.username_input.setFocus()
            return
        
        dialog = ChangePasswordDialog(username, self)
        if dialog.exec() == QDialog.Accepted and dialog.result:
            self.result = True
            self.show_toast("تم تغيير كلمة المرور بنجاح")
            self.password_input.clear()
            self.password_input.setFocus()


def run_dashboard(user_info):
    """تشغيل لوحة التحكم الرئيسية"""
    try:
        from main_dashboard import MainDashboard
        dashboard = MainDashboard(user_info=user_info)
        dashboard.showMaximized()
        return dashboard
    except Exception as e:
        logger.error(f"خطأ في فتح لوحة التحكم: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """الدالة الرئيسية لتشغيل التطبيق"""
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    try:
        initialize_system()
        logger.info("تم تهيئة قاعدة البيانات بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")
    
    login_window = LoginWindow()
    login_window.show()
    
    app.exec_()
    
    is_logged_in = getattr(login_window, 'login_success', False) or getattr(login_window, 'result', False)
    
    if is_logged_in:
        user_info = getattr(login_window, 'user_info', None)
        if not user_info:
            user_info = {'username': 'admin', 'role': 'مدير'}
            
        logger.info(f"تسجيل الدخول ناجح للمستخدم: {user_info['username']}")
        logger.info("جاري فتح لوحة التحكم الرئيسية...")
        
        dashboard = run_dashboard(user_info)
        if dashboard:
            sys.exit(app.exec_())
        else:
            logger.error("فشل في فتح لوحة التحكم")
            sys.exit(1)
    else:
        logger.info("تم إغلاق النافذة دون تسجيل دخول ناجح.")
        sys.exit(0)


if __name__ == "__main__":
    main()