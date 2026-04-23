from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGraphicsDropShadowEffect, QPushButton, QComboBox)
from PyQt6.QtCore import Qt
from back.database import get_connection
from datetime import datetime, timedelta

# ========== الألوان الثابتة ==========
COLORS = {
    'bg_dark': '#121212',
    'bg_sidebar': '#1a1a2e',
    'bg_card': '#1b1b28',
    'bg_card_dark': '#2d2d44',
    'bg_input': '#12121c',
    'text': '#e0e0e0',
    'text_muted': '#a0a0a0',
    'accent': '#00d4ff',
    'success': '#2ecc71',
    'success_dark': '#27ae60',
    'info': '#3498db',
    'warning': '#e67e22',
    'purple': '#9b59b6',
    'border': '#2b2b3d',
    'border_light': '#3d3d5c',
    'header': '#2b2b3d'
}

class ReportsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # خلفية النافذة
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")

        # فلترة الفترة
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                padding: 15px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_frame)
        
        period_label = QLabel("📅 فترة التقرير:")
        period_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: bold;")
        filter_layout.addWidget(period_label)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["اليوم", "آخر 7 أيام", "هذا الشهر", "هذا العام", "كل الفترة"])
        self.period_combo.setFixedWidth(150)
        self.period_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
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
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
            }}
        """)
        self.period_combo.currentTextChanged.connect(self.load_data)  # ✅ تحديث تلقائي عند تغيير الفترة
        filter_layout.addWidget(self.period_combo)
        filter_layout.addStretch()
        
        self.main_layout.addWidget(filter_frame)

        # صف الكروت العلوي
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.card_sales = self.create_stat_card("💰 إجمالي المبيعات", "0.00 ج.م", COLORS['success'])
        self.card_count = self.create_stat_card("📄 عدد الفواتير", "0", COLORS['info'])
        self.card_profit = self.create_stat_card("📈 صافي الربح", "0.00 ج.م", COLORS['warning'])
        self.card_avg = self.create_stat_card("⭐ متوسط الفاتورة", "0.00 ج.م", COLORS['purple'])

        stats_layout.addWidget(self.card_sales)
        stats_layout.addWidget(self.card_count)
        stats_layout.addWidget(self.card_profit)
        stats_layout.addWidget(self.card_avg)
        self.main_layout.addLayout(stats_layout)

        # الأكثر مبيعاً
        top_container = QFrame()
        top_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        top_layout = QVBoxLayout(top_container)
        
        top_title = QLabel("🔥 المنتجات الأكثر مبيعاً")
        top_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']}; padding: 15px; background-color: {COLORS['header']}; border-top-left-radius: 15px; border-top-right-radius: 15px;")
        top_layout.addWidget(top_title)

        self.top_products_table = QTableWidget(0, 3)
        self.top_products_table.setHorizontalHeaderLabels(["اسم المنتج", "الكمية المباعة", "إجمالي الإيرادات"])
        self.top_products_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.top_products_table.setAlternatingRowColors(True)
        self.top_products_table.setShowGrid(False)
        self.top_products_table.verticalHeader().setVisible(False)
        
        self.top_products_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: none;
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['border_light']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['accent']};
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        
        top_layout.addWidget(self.top_products_table)
        self.main_layout.addWidget(top_container)

        # الأقل مبيعاً
        low_container = QFrame()
        low_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 15px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        low_layout = QVBoxLayout(low_container)
        
        low_title = QLabel("❄️ المنتجات الأقل مبيعاً")
        low_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['accent']}; padding: 15px; background-color: {COLORS['header']}; border-top-left-radius: 15px; border-top-right-radius: 15px;")
        low_layout.addWidget(low_title)

        self.low_products_table = QTableWidget(0, 3)
        self.low_products_table.setHorizontalHeaderLabels(["اسم المنتج", "الكمية المباعة", "إجمالي الإيرادات"])
        self.low_products_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.low_products_table.setAlternatingRowColors(True)
        self.low_products_table.setShowGrid(False)
        self.low_products_table.verticalHeader().setVisible(False)
        
        self.low_products_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                border: none;
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['border_light']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['accent']};
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        
        low_layout.addWidget(self.low_products_table)
        self.main_layout.addWidget(low_container)

        self.load_data()

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setMinimumHeight(140)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card_dark']};
                border-left: 6px solid {color};
                border-radius: 12px;
                border-right: 1px solid {COLORS['border_light']};
                border-top: 1px solid {COLORS['border_light']};
                border-bottom: 1px solid {COLORS['border_light']};
            }}
        """)
        
        # ظل خفيف
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(Qt.GlobalColor.black)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 14px; font-weight: bold;")
        
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: 900;")
        lbl_value.setObjectName("value_label")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        layout.addStretch()
        return card

    def get_date_filter(self):
        today = datetime.now().date()
        period = self.period_combo.currentText()
        
        if period == "اليوم":
            return f"DATE(sale_date) = '{today}'"
        elif period == "آخر 7 أيام":
            start_date = today - timedelta(days=7)
            return f"DATE(sale_date) BETWEEN '{start_date}' AND '{today}'"
        elif period == "هذا الشهر":
            return f"strftime('%Y-%m', sale_date) = '{today.strftime('%Y-%m')}'"
        elif period == "هذا العام":
            return f"strftime('%Y', sale_date) = '{today.year}'"
        else:
            return "1=1"

    def load_data(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            date_filter = self.get_date_filter()
            
            # إجمالي المبيعات وعدد الفواتير
            cursor.execute(f"""
                SELECT COALESCE(SUM(total_amount), 0), COUNT(id) 
                FROM sales 
                WHERE {date_filter}
            """)
            total_sales, sales_count = cursor.fetchone()

            # صافي الربح
            cursor.execute(f'''
                SELECT COALESCE(SUM((si.price_at_sale - p.purchase_price) * si.quantity), 0)
                FROM sale_items si
                JOIN products p ON si.product_id = p.id
                JOIN sales s ON si.sale_id = s.id
                WHERE {date_filter}
            ''')
            profit = cursor.fetchone()[0]

            # متوسط الفاتورة
            avg_bill = total_sales / sales_count if sales_count > 0 else 0

            # المنتجات الأكثر مبيعاً
            cursor.execute(f'''
                SELECT p.name, COALESCE(SUM(si.quantity), 0), COALESCE(SUM(si.quantity * si.price_at_sale), 0)
                FROM sale_items si
                JOIN products p ON si.product_id = p.id
                JOIN sales s ON si.sale_id = s.id
                WHERE {date_filter}
                GROUP BY p.id 
                ORDER BY SUM(si.quantity) DESC 
                LIMIT 10
            ''')
            top_products = cursor.fetchall()

            # المنتجات الأقل مبيعاً
            cursor.execute(f'''
                SELECT p.name, COALESCE(SUM(si.quantity), 0), COALESCE(SUM(si.quantity * si.price_at_sale), 0)
                FROM sale_items si
                JOIN products p ON si.product_id = p.id
                JOIN sales s ON si.sale_id = s.id
                WHERE {date_filter}
                GROUP BY p.id 
                ORDER BY SUM(si.quantity) ASC
                LIMIT 5
            ''')
            low_products = cursor.fetchall()
            
            conn.close()

            # تحديث الكروت
            self.card_sales.findChild(QLabel, "value_label").setText(f"{total_sales:,.2f} ج.م")
            self.card_count.findChild(QLabel, "value_label").setText(str(sales_count))
            self.card_profit.findChild(QLabel, "value_label").setText(f"{profit:,.2f} ج.م")
            self.card_avg.findChild(QLabel, "value_label").setText(f"{avg_bill:,.2f} ج.م")

            # تحديث جدول الأكثر مبيعاً
            self.top_products_table.setRowCount(0)
            for row_data in top_products:
                row = self.top_products_table.rowCount()
                self.top_products_table.insertRow(row)
                self.top_products_table.setRowHeight(row, 45)
                
                name_item = QTableWidgetItem(row_data[0])
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.top_products_table.setItem(row, 0, name_item)
                
                qty_item = QTableWidgetItem(str(row_data[1]))
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.top_products_table.setItem(row, 1, qty_item)
                
                revenue_item = QTableWidgetItem(f"{row_data[2]:,.2f}")
                revenue_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.top_products_table.setItem(row, 2, revenue_item)

            # تحديث جدول الأقل مبيعاً
            self.low_products_table.setRowCount(0)
            for row_data in low_products:
                row = self.low_products_table.rowCount()
                self.low_products_table.insertRow(row)
                self.low_products_table.setRowHeight(row, 45)
                
                name_item = QTableWidgetItem(row_data[0])
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.low_products_table.setItem(row, 0, name_item)
                
                qty_item = QTableWidgetItem(str(row_data[1]))
                qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.low_products_table.setItem(row, 1, qty_item)
                
                revenue_item = QTableWidgetItem(f"{row_data[2]:,.2f}")
                revenue_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.low_products_table.setItem(row, 2, revenue_item)

        except Exception as e:
            print(f"Error in reports: {e}")