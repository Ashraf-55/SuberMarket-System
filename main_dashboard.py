import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

# استيراد الشاشات الأساسية
from add_product_ui import AddProductWindow 
from pos_ui import POSWindow
from reports_ui import ReportsWindow
from sales_history_ui import SalesHistoryWindow

# استيراد الشاشات المنفصلة (الملفات الجديدة)
from deferred_ui import DeferredAccountsWindow
from damaged_ui import DamagedGoodsWindow
from sales_return_ui import SalesReturnWindow
from purchase_return_ui import PurchaseReturnWindow
from transfer_ui import StockTransferWindow

# الألوان الثابتة
COLORS = {
    'bg_dark': '#121212',
    'bg_sidebar': '#1a1a2e',
    'bg_card': '#1e1e2e',
    'text': '#e0e0e0',
    'text_muted': '#a0a0a0',
    'accent': '#00d4ff',
    'danger': '#e74c3c',
    'danger_dark': '#c0392b',
    'border': '#2d2d5c',
}

FONTS = {
    'subtitle': QFont("Segoe UI", 18, QFont.Weight.Medium),
    'button': QFont("Segoe UI", 13, QFont.Weight.Medium),
}

class MainDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("نظام الماركت الذكي - الإصدار الاحترافي")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLORS['bg_dark']}; }}")
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setStyleSheet(f"""
            #Sidebar {{
                background-color: {COLORS['bg_sidebar']};
                min-width: 280px;
                max-width: 280px;
                border-right: 1px solid {COLORS['border']};
            }}
            #Sidebar QPushButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                border: none;
                padding: 15px 25px;
                text-align: left;
                font-size: 15px;
                font-weight: 500;
                min-height: 50px;
            }}
            #Sidebar QPushButton:hover {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
            }}
            #Sidebar QPushButton:checked {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['accent']};
                border-left: 4px solid {COLORS['accent']};
                font-weight: bold;
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        
        user_frame = QFrame()
        user_layout = QVBoxLayout(user_frame)
        user_icon = QLabel("👤")
        user_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_icon.setStyleSheet(f"font-size: 55px; color: {COLORS['text_muted']};")
        user_name = QLabel("المستخدم: Admin\nالصلاحية: مدير النظام")
        user_name.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 14px;")
        user_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        user_layout.addWidget(user_icon)
        user_layout.addWidget(user_name)
        sidebar_layout.addWidget(user_frame)
        sidebar_layout.addSpacing(30)
        
        # الأزرار
        self.btn_pos = QPushButton("🛒 المبيعات")
        self.btn_pos.setCheckable(True)
        self.btn_history = QPushButton("📜 سجل الفواتير")
        self.btn_history.setCheckable(True)
        self.btn_inventory = QPushButton("📦 المخزن")
        self.btn_inventory.setCheckable(True)
        self.btn_reports = QPushButton("📊 التقارير")
        self.btn_reports.setCheckable(True)
        self.btn_deferred = QPushButton("💳 الحسابات الآجلة")
        self.btn_deferred.setCheckable(True)
        self.btn_sales_return = QPushButton("↩️ مرتجع مبيعات")
        self.btn_sales_return.setCheckable(True)
        self.btn_purchase_return = QPushButton("🔃 مرتجع مشتريات")
        self.btn_purchase_return.setCheckable(True)
        self.btn_transfer = QPushButton("🚚 نقل مخزني")
        self.btn_transfer.setCheckable(True)
        self.btn_damaged = QPushButton("⚠️ تالف / هالك")
        self.btn_damaged.setCheckable(True)
        
        for btn in [self.btn_pos, self.btn_history, self.btn_inventory, self.btn_reports]:
            sidebar_layout.addWidget(btn)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; margin: 10px 20px; max-height: 2px;")
        sidebar_layout.addWidget(sep)
        
        for btn in [self.btn_deferred, self.btn_sales_return, self.btn_purchase_return, self.btn_transfer, self.btn_damaged]:
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        
        logout = QPushButton("🚪 تسجيل الخروج")
        logout.setFont(FONTS['button'])
        logout.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                padding: 14px;
                border-radius: 10px;
                margin: 10px;
                font-weight: bold;
                min-height: 50px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_dark']};
            }}
        """)
        logout.clicked.connect(self.close)
        sidebar_layout.addWidget(logout)
        
        main_layout.addWidget(sidebar)
        
        # منطقة المحتوى
        content = QVBoxLayout()
        content.setSpacing(0)
        
        header = QFrame()
        header.setObjectName("Header")
        header.setStyleSheet(f"""
            #Header {{
                background-color: {COLORS['bg_sidebar']};
                min-height: 80px;
                border-bottom: 2px solid {COLORS['border']};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 0, 25, 0)
        self.header_title = QLabel("المبيعات")
        self.header_title.setFont(FONTS['subtitle'])
        self.header_title.setStyleSheet(f"color: {COLORS['accent']}; font-weight: bold;")
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()
        content.addWidget(header)
        
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        # إنشاء الشاشات
        self.pos_screen = POSWindow()
        self.history_screen = SalesHistoryWindow()
        self.inventory_screen = AddProductWindow()
        self.report_screen = ReportsWindow()
        self.deferred_screen = DeferredAccountsWindow()
        self.sales_return_screen = SalesReturnWindow()
        self.purchase_return_screen = PurchaseReturnWindow()
        self.transfer_screen = StockTransferWindow()
        self.damaged_screen = DamagedGoodsWindow()
        
        # إضافة الشاشات إلى StackedWidget
        self.stack.addWidget(self.pos_screen)          # 0
        self.stack.addWidget(self.history_screen)      # 1
        self.stack.addWidget(self.inventory_screen)    # 2
        self.stack.addWidget(self.report_screen)       # 3
        self.stack.addWidget(self.deferred_screen)     # 4
        self.stack.addWidget(self.sales_return_screen) # 5
        self.stack.addWidget(self.purchase_return_screen) # 6
        self.stack.addWidget(self.transfer_screen)     # 7
        self.stack.addWidget(self.damaged_screen)      # 8
        
        content.addWidget(self.stack)
        main_layout.addLayout(content)
        
        # ربط الأزرار
        self.btn_pos.clicked.connect(lambda: self.switch(0, "🛒 المبيعات", self.btn_pos))
        self.btn_history.clicked.connect(lambda: self.switch(1, "📜 سجل الفواتير", self.btn_history))
        self.btn_inventory.clicked.connect(lambda: self.switch(2, "📦 المخزن", self.btn_inventory))
        self.btn_reports.clicked.connect(lambda: self.switch(3, "📊 التقارير", self.btn_reports))
        self.btn_deferred.clicked.connect(lambda: self.switch(4, "💳 الحسابات الآجلة", self.btn_deferred))
        self.btn_sales_return.clicked.connect(lambda: self.switch(5, "↩️ مرتجع مبيعات", self.btn_sales_return))
        self.btn_purchase_return.clicked.connect(lambda: self.switch(6, "🔃 مرتجع مشتريات", self.btn_purchase_return))
        self.btn_transfer.clicked.connect(lambda: self.switch(7, "🚚 نقل مخزني", self.btn_transfer))
        self.btn_damaged.clicked.connect(lambda: self.switch(8, "⚠️ تالف / هالك", self.btn_damaged))
        
        self.btn_pos.setChecked(True)
    
    def switch(self, index, title, btn):
        for b in [self.btn_pos, self.btn_history, self.btn_inventory, self.btn_reports,
                  self.btn_deferred, self.btn_sales_return, self.btn_purchase_return,
                  self.btn_transfer, self.btn_damaged]:
            b.setChecked(False)
        btn.setChecked(True)
        self.stack.setCurrentIndex(index)
        self.header_title.setText(title)
        
        # تحديث البيانات عند التبديل
        if index == 4:
            self.deferred_screen.load_debts()
        elif index == 5:
            self.sales_return_screen.load_sales()
        elif index == 6:
            self.purchase_return_screen.load_returns()
        elif index == 7:
            self.transfer_screen.load_transfers()
        elif index == 8:
            self.damaged_screen.load_damaged()
        elif index == 1 and hasattr(self.history_screen, 'load_sales'):
            self.history_screen.load_sales()
        elif index == 3 and hasattr(self.report_screen, 'load_data'):
            self.report_screen.load_data()
        elif index == 2 and hasattr(self.inventory_screen, 'load_data'):
            self.inventory_screen.load_data()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    window = MainDashboard()
    window.show()
    sys.exit(app.exec())