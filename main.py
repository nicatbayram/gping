import sys
import time
import threading
import platform
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QMessageBox, QFrame,
    QGridLayout, QScrollArea, QSpacerItem, QSizePolicy, QFileDialog, QInputDialog
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
import ping3
import subprocess
import re
import os

try:
    import winsound
except ImportError:
    winsound = None

# Global ayarlar
DNS_SERVER = "8.8.8.8"
PING_TIMEOUT = 1
PING_INTERVAL = 1
alarms = []
active_alarm = False  # Aktif alarm durumunu takip etmek için

class SoundManager:
    def __init__(self):
        self.error_sound = "error.wav"
        self.alarm_sound = "alarm.wav"
        self.alarm_playing = False
        self.stop_requested = False
        
    def play(self, sound_type):
        if sound_type == "error":
            self._play_error()
        elif sound_type == "alarm":
            self._play_alarm()
            
    def _play_error(self):
        if platform.system().lower() == "windows" and winsound:
            winsound.PlaySound(self.error_sound, winsound.SND_ALIAS)
    
    def _play_alarm(self):
        if platform.system().lower() == "windows" and winsound:
            self.alarm_playing = True
            self.stop_requested = False
            while self.alarm_playing and not self.stop_requested:
                winsound.PlaySound(self.alarm_sound, winsound.SND_ALIAS)
                time.sleep(10)  # Her 10 saniyede bir kontrol
    
    def stop_alarm(self):
        self.stop_requested = True
        self.alarm_playing = False
        if platform.system().lower() == "windows" and winsound:
            winsound.PlaySound(None, winsound.SND_PURGE)

class PingThread(QThread):
    update_signal = pyqtSignal(str, bool)
    status_signal = pyqtSignal(str, str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, sound_manager):
        super().__init__()
        self.running = True
        self.last_success = time.time()
        self.sound_manager = sound_manager
        self.error_count = 0
        
    def run(self):
        while self.running:
            try:
                response = ping_host(DNS_SERVER, timeout=PING_TIMEOUT)
                now = datetime.now().strftime('%H:%M:%S')
                
                if response is not None and response > 0:
                    self.error_count = 0
                    msg = f"[{now}] ✅ Uğurlu → {response:.1f} ms"
                    self.status_signal.emit("🟢 İnternet əlaqəsi: Yaxşı", "status-good")
                    self.last_success = time.time()
                    self.update_signal.emit(msg, True)
                else:
                    self.error_count += 1
                    elapsed = time.time() - self.last_success
                    msg = f"[{now}] ❌ Uğursuz → Timeout ({elapsed:.1f}s)"
                    
                    self.error_signal.emit(msg)
                    
                    if elapsed > PING_TIMEOUT:
                        self.status_signal.emit("🔴 İnternet əlaqəsi: Zəif", "status-error")
                        self.sound_manager.play("error")
                    
                    self.update_signal.emit(msg, False)
                
            except Exception as e:
                self.error_count += 1
                msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ HATA → {str(e)}"
                self.update_signal.emit(msg, False)
                self.status_signal.emit("🟡 İnternet əlaqəsi: Xəta", "status-error")
                self.error_signal.emit(msg)
                self.sound_manager.play("error")
                
            time.sleep(PING_INTERVAL)
    
    def stop(self):
        self.running = False
        self.wait()

class AlarmThread(QThread):
    alarm_signal = pyqtSignal(str, bool)  # bool parametresi eklendi (alarm durumu)
    
    def __init__(self, sound_manager):
        super().__init__()
        self.running = True
        self.sound_manager = sound_manager
        
    def run(self):
        global active_alarm
        while self.running:
            now = time.time()
            for alarm_time in alarms[:]:
                if now >= alarm_time:
                    active_alarm = True
                    alarms.remove(alarm_time)
                    self.alarm_signal.emit("🚨 Zəngli Saat İşləyir !", True)  # True = alarm aktif
                    self.sound_manager.play("alarm")
                    active_alarm = False
                    self.alarm_signal.emit("💤 Aktiv alarm yox", False)  # False = alarm pasif
                    
            time.sleep(1)
    
    def stop(self):
        self.running = False
        self.wait()

def ping_host(host, timeout=5):
    """Cross-platform ping function"""
    try:
        response = ping3.ping(host, timeout=timeout, unit='ms')
        if response is not None and response > 0:
            return response
    except Exception:
        pass
    
    try:
        if platform.system().lower() == "windows":
            cmd = f"ping -n 1 -w {timeout*100} {host}"
        else:
            cmd = f"ping -c 1 -W {timeout} {host}"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout+2)
        
        if result.returncode == 0:
            if platform.system().lower() == "windows":
                match = re.search(r'time[<=](\d+)ms', result.stdout)
                if match:
                    return float(match.group(1))
                match = re.search(r'time[<=](\d+\.\d+)ms', result.stdout)
                if match:
                    return float(match.group(1))
            else:
                match = re.search(r'time=(\d+\.?\d*).*ms', result.stdout)
                if match:
                    return float(match.group(1))
            return 1.0
        else:
            return None
    except Exception:
        return None

class PingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 DNS Ping & Alarm Monitor")
        self.setGeometry(200, 100, 1440, 960)
        
        self.sound_manager = SoundManager()
        self.ping_thread = PingThread(self.sound_manager)
        self.alarm_thread = AlarmThread(self.sound_manager)
        
        self.init_ui()
        self.start_threads()
        self.setup_daily_alarms()

    def init_ui(self):
        # Ana layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(24)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Sol Panel - Ping Monitörü
        left_panel = self.create_ping_panel()
        
        # Sağ Panel - Saat ve Alarm (Ölçüler %15 küçültüldü)
        right_panel = self.create_alarm_panel()
        
        main_layout.addWidget(left_panel, 3)
        main_layout.addWidget(right_panel, 1)
        
        self.setLayout(main_layout)

    def create_ping_panel(self):
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setSpacing(18)
        
        # Başlık
        title = QLabel("📡 DNS ping Monitoru")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 18px;")
        
        # Bağlantı durumu
        self.connection_status = QLabel("🔴 İnternet əlaqəsi: Axtarılır...")
        self.connection_status.setFont(QFont("Arial", 16, QFont.Bold))
        self.connection_status.setStyleSheet("margin-bottom: 24px;")
        
        # Hedef sunucu
        self.target_label = QLabel(f"🎯 Hədəf DNS və ya İP: {DNS_SERVER}")
        self.target_label.setFont(QFont("Arial", 14))
        self.target_label.setStyleSheet("color: #4a5568; margin-bottom: 18px;")
        
        # Sunucu değiştirme butonu
        self.change_server_btn = QPushButton("DNS və ya İP Dəyişdir")
        self.change_server_btn.setFont(QFont("Arial", 12))
        self.change_server_btn.clicked.connect(self.change_server)
        self.change_server_btn.setStyleSheet("""
            QPushButton {
                background-color: #4299e1;
                color: white;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 18px;
                border: 2px solid #2b6cb0;
            }
            QPushButton:pressed {
                background-color: #2b6cb0;
                padding: 14px 12px 10px 12px;
                border: 2px solid #1a4d8c;
            }
        """)
        
        # Anlık ping sonucu
        self.ping_result = QLabel("Ping nəticələri burada görünəcək...")
        self.ping_result.setFont(QFont("Consolas", 28, QFont.Bold))
        self.ping_result.setStyleSheet("""
            background-color: #f8f9fa;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            padding: 24px;
            margin: 12px 0;
            min-height: 96px;
        """)
        
        # Hata sesi ayarı butonu
        sound_layout = QHBoxLayout()
        sound_layout.setSpacing(12)
        
        self.error_sound_btn = QPushButton("Xəta Səsini Dəyişdir")
        self.error_sound_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.error_sound_btn.clicked.connect(lambda: self.set_sound("error"))
        self.error_sound_btn.setStyleSheet("""
            QPushButton {
                background-color: #f56565;
                color: white;
                padding: 12px;
                border-radius: 6px;
                border: 2px solid #c53030;
            }
            QPushButton:pressed {
                background-color: #c53030;
                padding: 14px 12px 10px 12px;
                border: 2px solid #9b2c2c;
            }
        """)
        
        sound_layout.addWidget(self.error_sound_btn)
        
        # Ping geçmişi
        self.ping_history = QListWidget()
        self.ping_history.setFont(QFont("Consolas", 14))
        self.ping_history.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                padding: 12px;
            }
            QListWidget::item {
                padding: 6px;
            }
        """)
        
        layout.addWidget(title)
        layout.addWidget(self.connection_status)
        layout.addWidget(self.target_label)
        layout.addWidget(self.change_server_btn)
        layout.addWidget(self.ping_result)
        layout.addLayout(sound_layout)
        layout.addWidget(self.ping_history)
        
        frame.setLayout(layout)
        return frame

    def create_alarm_panel(self):
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Dijital Saat
        clock_title = QLabel("🕐 SAAT")
        clock_title.setFont(QFont("Arial", 17, QFont.Bold))
        clock_title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        
        self.current_time_label = QLabel()
        self.current_time_label.setFont(QFont("Consolas", 24, QFont.Bold))
        self.current_time_label.setStyleSheet("""
            background-color: #f0f4f8;
            border: 2px solid #cbd5e0;
            border-radius: 13px;
            padding: 20px;
            color: #2d3748;
        """)
        self.current_time_label.setAlignment(Qt.AlignCenter)
        
        # Alarm Kurma Bölümü
        alarm_title = QLabel("⏰ ZƏNGLİ SAAT")
        alarm_title.setFont(QFont("Arial", 17, QFont.Bold))
        alarm_title.setStyleSheet("color: #2c3e50; margin: 20px 0 10px 0;")
        
        # Zaman girişleri
        time_layout = QGridLayout()
        time_layout.setSpacing(10)
        
        time_layout.addWidget(QLabel("SAAT:"), 0, 0)
        self.hour_input = QLineEdit("00")
        self.hour_input.setFont(QFont("Arial", 12))
        self.hour_input.setMaxLength(2)
        self.hour_input.setStyleSheet("padding: 8px;")
        time_layout.addWidget(self.hour_input, 0, 1)
        
        time_layout.addWidget(QLabel("DƏQİQƏ:"), 1, 0)
        self.minute_input = QLineEdit("00")
        self.minute_input.setFont(QFont("Arial", 12))
        self.minute_input.setMaxLength(2)
        self.minute_input.setStyleSheet("padding: 8px;")
        time_layout.addWidget(self.minute_input, 1, 1)
        
        # Alarm kur butonu
        self.set_alarm_btn = QPushButton("🔔 ZƏNGLİ SAATİ QUR")
        self.set_alarm_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.set_alarm_btn.clicked.connect(self.set_alarm)
        self.set_alarm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4299e1;
                color: white;
                padding: 12px;
                border-radius: 6px;
                border: 2px solid #2b6cb0;
            }
            QPushButton:pressed {
                background-color: #2b6cb0;
                padding: 14px 12px 10px 12px;
                border: 2px solid #1a4d8c;
            }
        """)
        
        # Alarm durumu
        self.alarm_status = QLabel("💤 AKTİV ALARMLAR")
        self.alarm_status.setFont(QFont("Arial", 12))
        self.alarm_status.setStyleSheet("color: #718096; margin-top: 15px;")
        self.alarm_status.setWordWrap(True)
        
        # Alarm kapatma butonu
        self.stop_alarm_btn = QPushButton("🚨 ALARMİ DAYANDIR")
        self.stop_alarm_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.stop_alarm_btn.clicked.connect(self.stop_alarm)
        self.stop_alarm_btn.setStyleSheet("""
            QPushButton {
                background-color: #e53e3e;
                color: white;
                padding: 12px;
                border-radius: 6px;
                margin-top: 10px;
                border: 2px solid #c53030;
            }
            QPushButton:pressed {
                background-color: #c53030;
                padding: 14px 12px 10px 12px;
                border: 2px solid #9b2c2c;
            }
        """)
        self.stop_alarm_btn.setVisible(False)
        
        # Alarm sesi ayarı butonu
        self.alarm_sound_btn = QPushButton("ZƏNG  SƏSİNİ AYARLA")
        self.alarm_sound_btn.setFont(QFont("Arial", 10, QFont.Bold))
        self.alarm_sound_btn.clicked.connect(lambda: self.set_sound("alarm"))
        self.alarm_sound_btn.setStyleSheet("""
            QPushButton {
                background-color: #ed8936;
                color: white;
                padding: 10px;
                border-radius: 6px;
                margin-top: 15px;
                border: 2px solid #dd6b20;
            }
            QPushButton:pressed {
                background-color: #dd6b20;
                padding: 12px 10px 8px 10px;
                border: 2px solid #c05621;
            }
        """)
        
        # Günlük alarmlar başlığı
        daily_alarms_title = QLabel("⏰ ŞABLON ZƏNGLİ SAAT")
        daily_alarms_title.setFont(QFont("Arial", 14, QFont.Bold))
        daily_alarms_title.setStyleSheet("color: #2c3e50; margin: 20px 0 10px 0;")
        
        # Günlük alarmlar listesi
        self.daily_alarms_list = QListWidget()
        self.daily_alarms_list.setFont(QFont("Arial", 10))
        self.daily_alarms_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 6px;
            }
        """)
        
        layout.addWidget(clock_title)
        layout.addWidget(self.current_time_label)
        layout.addWidget(alarm_title)
        layout.addLayout(time_layout)
        layout.addWidget(self.set_alarm_btn)
        layout.addWidget(self.alarm_status)
        layout.addWidget(self.stop_alarm_btn)
        layout.addWidget(self.alarm_sound_btn)
        layout.addWidget(daily_alarms_title)
        layout.addWidget(self.daily_alarms_list)
        layout.addStretch()
        
        frame.setLayout(layout)
        return frame

# ... (diğer metodlar ve son kısım aynı)

    def create_alarm_panel(self):
        frame = QFrame()
        layout = QVBoxLayout()
        layout.setSpacing(15)  # %15 daha küçük aralıklar
        
        # Dijital Saat (Ölçüler %15 küçültüldü)
        clock_title = QLabel("🕐 SAAT")
        clock_title.setFont(QFont("Arial", 17, QFont.Bold))  # %15 küçük font
        clock_title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        
        self.current_time_label = QLabel()
        self.current_time_label.setFont(QFont("Consolas", 24, QFont.Bold))  # %15 küçük font
        self.current_time_label.setStyleSheet("""
            background-color: #f0f4f8;
            border: 2px solid #cbd5e0;
            border-radius: 13px;
            padding: 20px;
            color: #2d3748;
        """)
        self.current_time_label.setAlignment(Qt.AlignCenter)
        
        # Alarm Kurma Bölümü
        alarm_title = QLabel("⏰ ZƏNGLİ SAAT")
        alarm_title.setFont(QFont("Arial", 17, QFont.Bold))  # %15 küçük font
        alarm_title.setStyleSheet("color: #2c3e50; margin: 20px 0 10px 0;")
        
        # Zaman girişleri
        time_layout = QGridLayout()
        time_layout.setSpacing(10)  # %15 daha küçük aralıklar
        
        time_layout.addWidget(QLabel("SAAT:"), 0, 0)
        self.hour_input = QLineEdit("00")
        self.hour_input.setFont(QFont("Arial", 12))  # %15 küçük font
        self.hour_input.setMaxLength(2)
        self.hour_input.setStyleSheet("padding: 8px;")
        time_layout.addWidget(self.hour_input, 0, 1)
        
        time_layout.addWidget(QLabel("DƏQİQƏ:"), 1, 0)
        self.minute_input = QLineEdit("00")
        self.minute_input.setFont(QFont("Arial", 12))  # %15 küçük font
        self.minute_input.setMaxLength(2)
        self.minute_input.setStyleSheet("padding: 8px;")
        time_layout.addWidget(self.minute_input, 1, 1)
        
        # Alarm kur butonu
        self.set_alarm_btn = QPushButton("🔔 ZƏNGLİ SAATİ QUR")
        self.set_alarm_btn.setFont(QFont("Arial", 12, QFont.Bold))  # %15 küçük font
        self.set_alarm_btn.clicked.connect(self.set_alarm)
        self.set_alarm_btn.setStyleSheet("""
            background-color: #4299e1;
            color: white;
            padding: 12px;
            border-radius: 6px;
        """)
        
        # Alarm durumu
        self.alarm_status = QLabel("💤 AKTİV ALARMLAR")
        self.alarm_status.setFont(QFont("Arial", 12))  # %15 küçük font
        self.alarm_status.setStyleSheet("color: #718096; margin-top: 15px;")
        self.alarm_status.setWordWrap(True)
        
        # Alarm kapatma butonu (Yeni eklendi)
        self.stop_alarm_btn = QPushButton("🚨 ALARMİ DAYANDIR")
        self.stop_alarm_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.stop_alarm_btn.clicked.connect(self.stop_alarm)
        self.stop_alarm_btn.setStyleSheet("""
            background-color: #e53e3e;
            color: white;
            padding: 12px;
            border-radius: 6px;
            margin-top: 10px;
        """)
        self.stop_alarm_btn.setVisible(False)  # Başlangıçta gizli
        
        # Alarm sesi ayarı butonu
        self.alarm_sound_btn = QPushButton("ZƏNG  SƏSİNİ AYARLA")
        self.alarm_sound_btn.setFont(QFont("Arial", 10, QFont.Bold))  # %15 küçük font
        self.alarm_sound_btn.clicked.connect(lambda: self.set_sound("alarm"))
        self.alarm_sound_btn.setStyleSheet("""
            background-color: #ed8936;
            color: white;
            padding: 10px;
            border-radius: 6px;
            margin-top: 15px;
        """)
        
        # Günlük alarmlar başlığı
        daily_alarms_title = QLabel("⏰ ŞABLON ZƏNGLİ SAAT")
        daily_alarms_title.setFont(QFont("Arial", 14, QFont.Bold))  # %15 küçük font
        daily_alarms_title.setStyleSheet("color: #2c3e50; margin: 20px 0 10px 0;")
        
        # Günlük alarmlar listesi
        self.daily_alarms_list = QListWidget()
        self.daily_alarms_list.setFont(QFont("Arial", 10))  # %15 küçük font
        self.daily_alarms_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 6px;
            }
        """)
        
        layout.addWidget(clock_title)
        layout.addWidget(self.current_time_label)
        layout.addWidget(alarm_title)
        layout.addLayout(time_layout)
        layout.addWidget(self.set_alarm_btn)
        layout.addWidget(self.alarm_status)
        layout.addWidget(self.stop_alarm_btn)  # Yeni eklendi
        layout.addWidget(self.alarm_sound_btn)
        layout.addWidget(daily_alarms_title)
        layout.addWidget(self.daily_alarms_list)
        layout.addStretch()
        
        frame.setLayout(layout)
        return frame

    def stop_alarm(self):
        """Alarmı durdurmak için yeni eklendi"""
        global active_alarm
        self.sound_manager.stop_alarm()
        active_alarm = False
        self.alarm_status.setText("💤 Alarm dayandırıldı")
        self.alarm_status.setStyleSheet("color: #718096;")
        self.stop_alarm_btn.setVisible(False)

    def setup_daily_alarms(self):
        # Günlük alarmları ekle (09:00, 11:00, 14:00, 17:00)
        daily_times = ["09:00", "11:00", "14:00", "17:00", "19:00"]
        
        for alarm_time in daily_times:
            self.daily_alarms_list.addItem(f"⏰ {alarm_time} - ŞABLON ALARM")
            
        # Alarmları aktif hale getir
        self.set_daily_alarms()
        
    def set_daily_alarms(self):
        now = datetime.now()
        daily_times = ["09:00", "11:00", "14:00", "17:00", "19:00"]
        
        for time_str in daily_times:
            h, m = map(int, time_str.split(":"))
            alarm_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
            
            # Eğer bu zaman bugün için geçtiyse, yarına ayarla
            if alarm_time < now:
                alarm_time += timedelta(days=1)
                
            delay = (alarm_time - now).total_seconds()
            alarms.append(time.time() + delay)

    def change_server(self):
        global DNS_SERVER
        new_server, ok = QInputDialog.getText(
            self, 
            "Sunucu Değiştir", 
            "Yeni ping hedefini girin:", 
            text=DNS_SERVER
        )
        
        if ok and new_server:
            DNS_SERVER = new_server
            self.target_label.setText(f"🎯 HEDEF SUNUCU: {DNS_SERVER}")
            QMessageBox.information(self, "Uğurlu", f"Ping hədəfi {DNS_SERVER} olaraq dəyişdirildi!")

    def start_threads(self):
        self.ping_thread.update_signal.connect(self.update_ping_display)
        self.ping_thread.status_signal.connect(self.update_connection_status)
        self.ping_thread.error_signal.connect(self.handle_error)
        self.ping_thread.start()
        
        self.alarm_thread.alarm_signal.connect(self.update_alarm_status)
        self.alarm_thread.start()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)

    def update_clock(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%d.%m.%Y")
        self.current_time_label.setText(f"{current_time}\n{current_date}")

    def update_ping_display(self, message, is_success):
        self.ping_result.setText(message)
        
        if is_success:
            self.ping_result.setStyleSheet("""
                font-family: Consolas;
                font-size: 28px;
                font-weight: bold;
                background-color: #c6f6d5;
                color: #22543d;
                border: 2px solid #9ae6b4;
                border-radius: 10px;
                padding: 24px;
                margin: 12px 0;
                min-height: 96px;
            """)
        else:
            self.ping_result.setStyleSheet("""
                font-family: Consolas;
                font-size: 28px;
                font-weight: bold;
                background-color: #fed7d7;
                color: #742a2a;
                border: 2px solid #feb2b2;
                border-radius: 10px;
                padding: 24px;
                margin: 12px 0;
                min-height: 96px;
            """)
        
        self.ping_history.addItem(message)
        item = self.ping_history.item(self.ping_history.count() - 1)
        
        if is_success:
            item.setBackground(QColor(198, 246, 213))
            item.setForeground(QColor(34, 84, 61))
        else:
            item.setBackground(QColor(254, 215, 215))
            item.setForeground(QColor(116, 42, 42))
            
        self.ping_history.scrollToBottom()
        
        if self.ping_history.count() > 100:
            self.ping_history.takeItem(0)

    def handle_error(self, error_msg):
        self.ping_result.setStyleSheet("""
            font-family: Consolas;
            font-size: 28px;
            font-weight: bold;
            background-color: #ff0000;
            color: #ffffff;
            border: 3px solid #ff0000;
            border-radius: 15px;
            padding: 25px;
            margin: 15px 0;
            min-height: 96px;
        """)

    def update_connection_status(self, text, style):
        self.connection_status.setText(text)
        if "İyi" in text:
            self.connection_status.setStyleSheet("color: #38a169; font-weight: bold;")
        elif "Kötü" in text:
            self.connection_status.setStyleSheet("color: #e53e3e; font-weight: bold;")
        else:
            self.connection_status.setStyleSheet("color: #d69e2e; font-weight: bold;")

    def update_alarm_status(self, text, is_active):
        global active_alarm
        self.alarm_status.setText(text)
        if is_active:
            self.alarm_status.setStyleSheet("color: #e53e3e; font-weight: bold;")
            self.stop_alarm_btn.setVisible(True)  # Alarm çalarken butonu göster
        else:
            self.alarm_status.setStyleSheet("color: #718096;")
            self.stop_alarm_btn.setVisible(False)  # Alarm durunca butonu gizle

    def set_sound(self, sound_type):
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            f"{sound_type.capitalize()} Səs faylını Seç", 
            "", 
            "Ses Dosyaları (*.wav *.mp3);;Tüm Dosyalar (*)"
        )
        
        if file_name:
            setattr(self.sound_manager, f"{sound_type}_sound", file_name)
            QMessageBox.information(self, "Uğurlu", f"{sound_type.capitalize()} səsi ayarlandı!")

    def set_alarm(self):
        try:
            hour_text = self.hour_input.text()
            minute_text = self.minute_input.text()
            
            if ":" in hour_text:
                time_parts = hour_text.split(":")
                h = int(time_parts[0])
                m = int(time_parts[1]) if len(time_parts) > 1 else 0
            else:
                h = int(hour_text) if hour_text else 0
                m = int(minute_text) if minute_text else 0
            
            if h > 23 or m > 59:
                QMessageBox.warning(self, "Xəta", "Uyğunsuz zaman! (Saat: 0-23, Dəqiqə: 0-59)")
                return
                
            now = datetime.now()
            alarm_time = now.replace(hour=h, minute=m, second=0)
            
            if alarm_time < now:
                alarm_time += timedelta(days=1)
                
            delay = (alarm_time - now).total_seconds()
            
            if delay > 0:
                alarms.append(time.time() + delay)
                
                self.alarm_status.setText(
                    f"✅ ALARM KURULDU!\n"
                    f"🕐 {h:02d}:{m:02d}\n"
                    f"📅 {alarm_time.strftime('%d.%m.%Y %H:%M')}"
                )
                self.alarm_status.setStyleSheet("color: #38a169; font-weight: bold;")
            else:
                QMessageBox.warning(self, "Xəta", "Zəhmət olmasa uyğun bir zaman seçin.")
                
        except ValueError:
            QMessageBox.warning(self, "Xəta", "Zəhmət olmasa düzgün bir zaman formatı daxil edin (HH:MM)")

    def closeEvent(self, event):
        self.ping_thread.stop()
        self.alarm_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PingApp()
    window.show()
    sys.exit(app.exec_())