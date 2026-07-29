# ================= ai_predictions.py - توقعات الذكاء الاصطناعي =================
"""
ai_predictions.py - وحدة توقعات الذكاء الاصطناعي
تدعم توقع أسعار المنتجات والأرباح المستقبلية باستخدام Linear Regression مع حماية للأجهزة القديمة
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QHBoxLayout, QMessageBox, QFrame, 
    QGroupBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
import sqlite3
import numpy as np
import pandas as pd
import logging

# محاولة استيراد مكتبة الذكاء الاصطناعي بأمان للأجهزة الضعيفة
AI_ENABLED = True
try:
    from sklearn.linear_model import LinearRegression
except Exception as e:
    AI_ENABLED = False

# إعداد نظام التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== الألوان ==========
COLORS = {
    'bg_dark': '#F3F7F7',
    'bg_sidebar': '#FFFFFF',
    'bg_card': '#FFFFFF',
    'bg_card_dark': '#e2e8f0',
    'bg_input': '#FFFFFF',
    'text': '#1e293b',
    'text_muted': '#64748b',
    'accent': '#0284c7',
    'success': '#16a34a',
    'success_hover': '#15803d',
    'danger': '#dc2626',
    'danger_dark': '#b91c1c',
    'warning': '#d97706',
    'warning_hover': '#b45309',
    'border': '#cbd5e1',
    'border_light': '#e2e8f0',
    'info': '#0284c7',
    'purple': '#9333ea',
    
    'accent_hover': '#0369a1',
    'accent_light': '#e0f2fe',
    'text_on_accent': '#ffffff',
    'bg_hover': '#f1f5f9',
    'warning_bg': 'rgba(217, 119, 6, 0.12)',
    'danger_bg': 'rgba(220, 38, 38, 0.12)',
    'success_bg': 'rgba(22, 163, 74, 0.12)',
    'scrollbar': '#cbd5e1',
}

class MarketAIPredictor:
    """كلاس التنبؤ بالذكاء الاصطناعي مع حماية الأجهزة القديمة"""
    
    def __init__(self, db_path="database/supermarket.db"):
        self.db_path = db_path
        self.ai_available = AI_ENABLED
        if self.ai_available:
            try:
                self.model = LinearRegression()
            except:
                self.ai_available = False
        
        if not self.ai_available:
            logger.warning("مكتبات الذكاء الاصطناعي غير مدعومة أو معطلة على هذا الجهاز، سيتم تخطي التنبؤات.")
        else:
            logger.info(f"تم تهيئة MarketAIPredictor مع قاعدة البيانات: {db_path}")

    def get_connection(self):
        """الحصول على اتصال بقاعدة البيانات"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
            return None

    def predict_product_price(self, product_id):
        """توقع سعر منتج معين بناءً على تاريخ أسعاره"""
        if not self.ai_available:
            return None
            
        conn = self.get_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_history'")
            if not cursor.fetchone():
                logger.warning("جدول price_history غير موجود")
                conn.close()
                return None
            
            query = "SELECT price FROM price_history WHERE product_id = ? ORDER BY date ASC"
            df = pd.read_sql_query(query, conn, params=(product_id,))
            conn.close()
            
            if df.empty or len(df) < 2:
                return None
                
            prices = df['price'].values
            X = np.array(range(len(prices))).reshape(-1, 1)
            y = np.array(prices)
            self.model.fit(X, y)
            predicted = self.model.predict(np.array([[len(prices)]]))
            return round(float(predicted[0]), 2)
            
        except Exception as e:
            logger.error(f"خطأ في predict_product_price للمنتج {product_id}: {e}")
            try:
                conn.close()
            except:
                pass
            return None

    def predict_future_profits(self):
        """توقع الأرباح المستقبلية بناءً على تاريخ المبيعات"""
        if not self.ai_available:
            return 0.0
            
        conn = self.get_connection()
        if not conn:
            return 0.0
            
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales'")
            if not cursor.fetchone():
                logger.warning("جدول sales غير موجود")
                conn.close()
                return 0.0
            
            query = """
                SELECT date(sale_date) as date, 
                       SUM(total_amount) as total_sales
                FROM sales 
                WHERE sale_date IS NOT NULL
                GROUP BY date(sale_date) 
                ORDER BY date(sale_date) ASC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty or len(df) < 2:
                logger.info("لا توجد بيانات كافية للتنبؤ بالأرباح")
                return 0.0
                
            profits = df['total_sales'].values
            X = np.array(range(len(profits))).reshape(-1, 1)
            y = np.array(profits)
            self.model.fit(X, y)
            predicted_profit = self.model.predict(np.array([[len(profits)]]))
            
            result = max(0, round(float(predicted_profit[0]), 2))
            logger.info(f"الأرباح المتوقعة: {result}")
            return result
            
        except Exception as e:
            logger.error(f"خطأ في predict_future_profits: {e}")
            try:
                conn.close()
            except:
                pass
            return 0.0
    
    def get_all_products(self):
        """جلب جميع المنتجات مع أسمائها"""
        conn = self.get_connection()
        if not conn:
            return []
            
        try:
            query = "SELECT id, name FROM products ORDER BY name"
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"خطأ في get_all_products: {e}")
            try:
                conn.close()
            except:
                pass
            return []


class AIPredictionsWidget(QWidget):
    """واجهة توقعات الذكاء الاصطناعي"""
    
    def __init__(self, db_path="database/supermarket.db", parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.predictor = MarketAIPredictor(db_path)
        self.is_loading = False
        self.init_ui()
        self.load_predictions()
    
    def init_ui(self):
        """تهيئة واجهة المستخدم"""
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # عنوان الصفحة
        title_text = "🤖 لوحة تحليلات وتوقعات الذكاء الاصطناعي" if AI_ENABLED else "🤖 لوحة تحليلات وتوقعات المبيعات"
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title_label.setStyleSheet(f"color: {COLORS['accent']}; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # ===== بطاقات الإحصائيات =====
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)
        
        # بطاقة الأرباح المتوقعة
        self.profit_card = QFrame()
        self.profit_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {COLORS['accent']};
                border-radius: 12px;
                padding: 15px;
                min-height: 80px;
            }}
        """)
        profit_card_layout = QVBoxLayout(self.profit_card)
        
        profit_title = QLabel("📈 الأرباح المتوقعة للفترة القادمة")
        profit_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; font-weight: bold;")
        profit_card_layout.addWidget(profit_title)
        
        self.profit_value = QLabel("جاري التحميل...")
        self.profit_value.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.profit_value.setStyleSheet(f"color: {COLORS['success']};")
        self.profit_value.setAlignment(Qt.AlignCenter)
        profit_card_layout.addWidget(self.profit_value)
        
        cards_layout.addWidget(self.profit_card, 1)
        
        # بطاقة عدد المنتجات المتوقعة
        self.products_card = QFrame()
        self.products_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {COLORS['purple']};
                border-radius: 12px;
                padding: 15px;
                min-height: 80px;
            }}
        """)
        products_card_layout = QVBoxLayout(self.products_card)
        
        products_title = QLabel("📦 عدد المنتجات المتوقعة")
        products_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; font-weight: bold;")
        products_card_layout.addWidget(products_title)
        
        self.products_count = QLabel("0")
        self.products_count.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.products_count.setStyleSheet(f"color: {COLORS['purple']};")
        self.products_count.setAlignment(Qt.AlignCenter)
        products_card_layout.addWidget(self.products_count)
        
        cards_layout.addWidget(self.products_card, 1)
        
        main_layout.addLayout(cards_layout)
        
        # ===== أزرار التحكم =====
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.refresh_btn = QPushButton("🔄 تحديث التوقعات")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                border: none;
                padding: 8px 25px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['info']};
            }}
        """)
        self.refresh_btn.clicked.connect(self.load_predictions)
        btn_layout.addWidget(self.refresh_btn)
        
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)
        
        # ===== شريط التقدم =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['bg_input']};
                border-radius: 8px;
                text-align: center;
                color: {COLORS['text']};
                font-weight: bold;
                min-height: 25px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 8px;
            }}
        """)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # ===== جدول توقعات أسعار المنتجات =====
        table_group = QGroupBox("📊 توقعات أسعار المنتجات")
        table_group.setStyleSheet(f"""
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
                padding: 0 10px 0 10px;
            }}
        """)
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["رقم المنتج", "اسم المنتج", "السعر المتوقع (ج.م)", "حالة التوقع"])
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text']};
                gridline-color: {COLORS['border']};
                border: none;
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_card']};
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
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        table_layout.addWidget(self.table)
        main_layout.addWidget(table_group)
        
        # رسالة الحالة
        self.status_label = QLabel("✅ جاهز")
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; margin-top: 5px;")
        main_layout.addWidget(self.status_label)

    def load_predictions(self):
        """تحميل وتحديث التوقعات"""
        if self.is_loading:
            return
        
        self.is_loading = True
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("⏳ جاري تحديث التوقعات...")
        self.status_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px;")
        
        self.load_step = 0
        self.total_steps = 4
        
        def update_progress():
            self.load_step += 1
            progress = int((self.load_step / self.total_steps) * 100)
            self.progress_bar.setValue(min(progress, 100))
            
            if self.load_step < self.total_steps:
                QTimer.singleShot(100, update_progress)
            else:
                self.finish_loading()
        
        QTimer.singleShot(100, update_progress)
    
    def finish_loading(self):
        """إنهاء التحميل وعرض النتائج"""
        try:
            # 1. عرض الأرباح المتوقعة
            profit = self.predictor.predict_future_profits()
            if profit > 0:
                self.profit_value.setText(f"{profit:,.2f} ج.م")
                self.profit_value.setStyleSheet(f"color: {COLORS['success']};")
            else:
                self.profit_value.setText("لا توجد بيانات كافية")
                self.profit_value.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 16px;")
            
            # 2. جلب المنتجات وتوقعات أسعارها
            products = self.predictor.get_all_products()
            self.products_count.setText(str(len(products)))
            
            self.table.setRowCount(0)
            predicted_count = 0
            
            for product in products:
                p_id = product['id']
                p_name = product['name']
                predicted_price = self.predictor.predict_product_price(p_id)
                
                row_position = self.table.rowCount()
                self.table.insertRow(row_position)
                
                # رقم المنتج
                self.table.setItem(row_position, 0, QTableWidgetItem(str(p_id)))
                
                # اسم المنتج
                self.table.setItem(row_position, 1, QTableWidgetItem(str(p_name)))
                
                # السعر المتوقع والحالة
                if predicted_price is not None and predicted_price > 0:
                    price_item = QTableWidgetItem(f"{predicted_price:,.2f}")
                    price_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_position, 2, price_item)
                    
                    status_item = QTableWidgetItem("✅ متوقع")
                    status_item.setTextAlignment(Qt.AlignCenter)
                    status_item.setForeground(QColor(22, 163, 74))
                    self.table.setItem(row_position, 3, status_item)
                    predicted_count += 1
                else:
                    self.table.setItem(row_position, 2, QTableWidgetItem("—"))
                    status_item = QTableWidgetItem("⚠️ بيانات غير كافية")
                    status_item.setTextAlignment(Qt.AlignCenter)
                    status_item.setForeground(QColor(100, 116, 139))
                    self.table.setItem(row_position, 3, status_item)
            
            # تحديث الحالة النهائية
            self.status_label.setText(f"✅ تم التحديث - {predicted_count} منتج متوقع من {len(products)}")
            self.status_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
            
        except Exception as e:
            logger.error(f"خطأ في finish_loading: {e}")
            self.status_label.setText(f"❌ خطأ: {str(e)}")
            self.status_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 12px;")
            QMessageBox.warning(self, "خطأ", f"حدث خطأ أثناء تحميل التوقعات:\n{str(e)}")
            
        finally:
            self.is_loading = False
            self.refresh_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)