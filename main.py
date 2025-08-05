import sys
import time
import threading
import platform
from datetime import datetime, timedelta
import os
import json
import re
import subprocess
import socket
import pytz
import numpy as np
from geopy.geocoders import Nominatim
import requests
from classic_speedometer import ClassicSpeedometer

# PyQt5 imports
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QMessageBox, QFrame,
    QGridLayout, QScrollArea, QSizePolicy, QFileDialog,
    QInputDialog, QMenu, QAction, QMenuBar, QSystemTrayIcon,
    QDialog, QFormLayout, QComboBox, QSpinBox, QListWidgetItem,
    QCheckBox, QTimeEdit, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QThread, QTime, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QCursor, QLinearGradient, QGradient, QPainter, QBrush
import pyqtgraph as pg  # For graphing

# Conditional imports for platform-specific features
try:
    import winsound
except ImportError:
    winsound = None

try:
    import ping3
except ImportError:
    ping3 = None
    print("Warning: 'ping3' library not found. Falling back to subprocess ping.")

try:
    import speedtest
except ImportError:
    speedtest = None
    print("Warning: 'speedtest-cli' library not found. Speed test feature will be disabled.")


# --- Global Settings ---
DNS_SERVER = "8.8.8.8"
PING_TIMEOUT = 1
PING_INTERVAL = 1
ERROR_SOUND_FILE = "error.wav"
ALARM_SOUND_FILE = "alarm.wav"
dark_mode = True
english_language = True  # Default to English
CONFIG_FILE = "config.json"

# --- Text Resources ---
TEXTS = {
    "en": {
        "main_title": "🚀 DNS Ping & Alarm Monitor",
        "settings_title": "Settings",
        "dns_server": "DNS/IP Server:",
        "ping_interval": "Ping Interval (s):",
        "ping_timeout": "Ping Timeout (s):",
        "language": "Language:",
        "theme": "Theme:",
        "error_sound": "Error Sound:",
        "alarm_sound": "Alarm Sound:",
        "save": "Save",
        "browse": "Browse...",
        "ping_graph_title": "Ping Response Time (ms)",
        "ping_monitor_title": "DNS Ping Monitor",
        "searching": "Searching...",
        "internet_good": "✓ Internet: Good",
        "internet_poor": "✗ Internet: Poor",
        "alarm_management": "ALARM MANAGEMENT",
        "alarm_ringing": "🚨 Alarm is ringing!",
        "stop_alarm": "🚨 STOP ALARM",
        "add_new": "Add New",
        "delete_selected": "Delete Selected",
        "save_alarms": "Save Alarms",
        "no_selection": "Please select at least one alarm to delete.",
        "confirm_delete": "Are you sure you want to delete {} selected alarm(s)?",
        "duplicate_alarm": "An alarm with this time and name already exists.",
        "quit_title": "Quit?",
        "quit_message": "Quit the application?",
        "alarm_load_error": "Alarm Load Error",
        "alarm_save_error": "Alarm Save Error",
        "new_alarm_title": "New Alarm Name",
        "new_alarm_prompt": "Enter alarm name:",
        "set_time_title": "Set Alarm Time",
        "select_time": "Select time:",
        "ok": "OK",
        "local_ip": "Local IP:",
        "public_ip": "Public IP:",
        "ip_not_available": "Not available",
        "menu_settings": "&Settings",
        "menu_open_settings": "Open Settings",
        "menu_exit": "Exit",
        "tray_show": "Show",
        "tray_quit": "Quit",
        "default_alarms": ["Morning Alarm", "Lunch Reminder", "Afternoon Break", "End of Day"],
        "speed_test": "Speed Test",
        "speed_test_results": "Speed Test Results",
        "download_speed": "Download",
        "upload_speed": "Upload",
        "testing_download": "Testing Download Speed...",
        "testing_upload": "Testing Upload Speed...",
        "test_completed": "Test Completed",
        "mbps": "Mbps",
        "close": "Close",
        "speed_test_error_title": "Speed Test Error",
        "speed_test_failed": "Speed test failed: {}",
        "ping_success": "✅ Ping successful → Response time: {:.1f} ms (Connection stable)",
        "ping_failure": "❌ Failure detected: Didn't reply within {:.1f} seconds. Server unavailable."
    },
    "az": {
        "main_title": "🚀 DNS Ping & Siqnal Monitoru",
        "settings_title": "Parametrlər",
        "dns_server": "DNS/IP Server:",
        "ping_interval": "Ping intervalı (s):",
        "ping_timeout": "Ping zaman aşımı (s):",
        "language": "Dil:",
        "theme": "Mövzu:",
        "error_sound": "Xəta səsi:",
        "alarm_sound": "Siqnal səsi:",
        "save": "Yadda saxla",
        "browse": "Göz at...",
        "ping_graph_title": "Ping cavab müddəti (ms)",
        "ping_monitor_title": "DNS Ping Monitoru",
        "searching": "Axtarılır...",
        "internet_good": "✓ İnternet: Yaxşı",
        "internet_poor": "✗ İnternet: Zəif",
        "alarm_management": "SİQNAL İDARƏETMƏSİ",
        "alarm_ringing": "🚨 Siqnal çalır!",
        "stop_alarm": "🚨 SİQNALI DAYANDIR",
        "add_new": "Yeni əlavə et",
        "delete_selected": "Seçilənləri sil",
        "save_alarms": "Siqnalları yadda saxla",
        "no_selection": "Silmək üçün ən azı bir siqnal seçin.",
        "confirm_delete": "Seçilmiş {} siqnalı silməyə əminsiniz?",
        "duplicate_alarm": "Bu vaxt və adla siqnal artıq mövcuddur.",
        "quit_title": "Çıxış?",
        "quit_message": "Proqramdan çıxmaq istəyirsiniz?",
        "alarm_load_error": "Siqnal Yükləmə Xətası",
        "alarm_save_error": "Siqnal Saxlama Xətası",
        "new_alarm_title": "Yeni Siqnal Adı",
        "new_alarm_prompt": "Siqnal adını daxil edin:",
        "set_time_title": "Siqnal Vaxtını Təyin Et",
        "select_time": "Vaxtı seçin:",
        "ok": "TAMAM",
        "local_ip": "Lokal IP:",
        "public_ip": "Xarici IP:",
        "ip_not_available": "Mövcud deyil",
        "menu_settings": "&Parametrlər",
        "menu_open_settings": "Parametrləri aç",
        "menu_exit": "Çıxış",
        "tray_show": "Göstər",
        "tray_quit": "Çıx",
        "default_alarms": ["Səhər siqnalı", "Nahar xatırlatması", "Günortadan sonra fasilə", "Günün sonu"],
        "speed_test": "Sürət Testi",
        "speed_test_results": "Sürət Testi Nəticələri",
        "download_speed": "Yükləmə",
        "upload_speed": "Qarşıya Yükləmə",
        "testing_download": "Yükləmə sürəti yoxlanılır...",
        "testing_upload": "Qarşıya yükləmə sürəti yoxlanılır...",
        "test_completed": "Test Tamamlandı",
        "mbps": "Mbit/s",
        "close": "Bağla",
        "speed_test_error_title": "Sürət Testi Xətası",
        "speed_test_failed": "Sürət testi uğursuz oldu: {}",
        "ping_success": "✅ Ping uğurlu → Cavab müddəti: {:.1f} ms (Bağlantı sabit)",
        "ping_failure": "❌ Uğursuzluq aşkarlandı: {:.1f} saniyə ərzində cavab vermədi. Server əlçatan deyil."
    }
}

# Store active alarms (timestamps)
active_alarm_timestamps = []
active_alarm_ringing = False

# --- Modern Color Palette ---
COLORS = {
    'dark': {
        'primary': '#000000',
        'secondary': '#000000',
        'tertiary': '#02040f',
        'accent_blue': '#4A9AFF',
        'accent_green': "#3DDC97",
        'accent_red': "#FF5E5B",
        'accent_orange': '#FF9F1C',
        'text_primary': '#FFFFFF',
        'text_secondary': '#E0E0E0',
        'text_muted': '#A0A0A0',
        'border': '#383838',
        'success_bg': "#3DDC9730",
        'error_bg': "#FF5E5B20",
        'warning_bg': '#FF9F1C20',
        'hover': 'rgba(255, 255, 255, 0.08)',
        'active': 'rgba(255, 255, 255, 0.16)'
    },
    'light': {
        'primary': '#F5F7FA',
        'secondary': '#F5F7FA',
        'tertiary': '#E1E5EB',
        'accent_blue': '#1A73E8',
        'accent_green': '#0B8043',
        'accent_red': '#D32F2F',
        'accent_orange': '#F57C00',
        'text_primary': '#202124',
        'text_secondary': '#5F6368',
        'text_muted': '#80868B',
        'border': '#DADCE0',
        'success_bg': '#0B804320',
        'error_bg': '#D32F2F20',
        'warning_bg': '#F57C0020',
        'hover': 'rgba(0, 0, 0, 0.04)',
        'active': 'rgba(0, 0, 0, 0.08)'
    }
}

class Alarm:
    """Represents a single alarm with time, status and name"""
    def __init__(self, hour, minute, enabled=True, name="Alarm"):
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid hour or minute for alarm.")
        self.hour = hour
        self.minute = minute
        self.enabled = enabled
        self.name = name

    def to_dict(self):
        """Serialize alarm to dictionary for saving"""
        return {
            "hour": self.hour,
            "minute": self.minute,
            "enabled": self.enabled,
            "name": self.name
        }

    @staticmethod
    def from_dict(data):
        """Create Alarm object from dictionary"""
        return Alarm(data.get("hour", 0), data.get("minute", 0),
                   data.get("enabled", True), data.get("name", "Alarm"))

    def __eq__(self, other):
        """Compare alarms by time and name"""
        if not isinstance(other, Alarm):
            return NotImplemented
        return self.hour == other.hour and self.minute == other.minute and self.name == other.name

    def __hash__(self):
        """Hash for set operations"""
        return hash((self.hour, self.minute, self.name))

    def __str__(self):
        """String representation for display"""
        status = " (Enabled)" if self.enabled else " (Disabled)"
        return f"{self.hour:02d}:{self.minute:02d} - {self.name}{status}"

def ping_host(host, timeout=1):
    """Ping a host and return response time in ms or None if failed"""
    if ping3:
        try:
            response = ping3.ping(host, timeout=timeout, unit='ms')
            if isinstance(response, (int, float)) and response > 0:
                return response
        except Exception:
            pass

    # Fallback to subprocess ping
    try:
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
        timeout_val = int(timeout * 1000) if platform.system().lower() == 'windows' else int(timeout)
        command = ['ping', param, '1', timeout_param, str(timeout_val), host]

        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            if platform.system().lower() == "windows":
                match = re.search(r'time[=<](\d+\.?\d*)ms', result.stdout)
            else:
                match = re.search(r'time=(\d+\.?\d*)\s*ms', result.stdout)

            if match:
                return float(match.group(1))
            return 1.0
        else:
            return None
    except Exception:
        return None

class SoundManager(QObject):
    """Handles playing sound effects in background threads"""
    def __init__(self):
        super().__init__()
        self._error_sound = ERROR_SOUND_FILE
        self._alarm_sound = ALARM_SOUND_FILE
        self._stop_requested = threading.Event()
        self._alarm_thread = None

    @property
    def error_sound(self): return self._error_sound
    @error_sound.setter
    def error_sound(self, value): self._error_sound = value

    @property
    def alarm_sound(self): return self._alarm_sound
    @alarm_sound.setter
    def alarm_sound(self, value): self._alarm_sound = value

    def play(self, sound_type):
        """Play sound asynchronously based on type"""
        if sound_type == "error":
            threading.Thread(target=self._play_sound, args=(self.error_sound, False), daemon=True).start()
        elif sound_type == "alarm":
            if not self._alarm_thread or not self._alarm_thread.is_alive():
                self._stop_requested.clear()
                self._alarm_thread = threading.Thread(target=self._play_sound, args=(self.alarm_sound, True), daemon=True)
                self._alarm_thread.start()

    def _play_sound(self, sound_file, loop=False):
        """Internal sound playing logic"""
        if platform.system().lower() == "windows" and winsound:
            try:
                if not os.path.exists(sound_file):
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    return

                if loop:
                    while not self._stop_requested.is_set():
                        winsound.PlaySound(sound_file, winsound.SND_FILENAME)
                        time.sleep(0.1)
                else:
                    winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"Error playing sound: {e}")

    def stop_alarm(self):
        """Stop the looping alarm sound"""
        self._stop_requested.set()
        if platform.system().lower() == "windows" and winsound:
            winsound.PlaySound(None, winsound.SND_PURGE)

class SpeedTestThread(QThread):
    """Thread for running an internet speed test with real-time progress."""
    download_progress = pyqtSignal(float)
    upload_progress = pyqtSignal(float)
    test_finished = pyqtSignal(float, float)
    error_signal = pyqtSignal(str)
    upload_started = pyqtSignal()

    def run(self):
        """Executes the speed test, reporting progress along the way."""
        if not speedtest or not requests:
            self.error_signal.emit("Speedtest or Requests library not installed.")
            return

        try:
            st = speedtest.Speedtest(secure=True)
            st.get_best_server()

            # --- Real-time Download Test ---
            download_url = os.path.dirname(st.results.server['url'])
            test_file_url = f"{download_url}/random3500x3500.jpg"

            start_time = time.time()
            bytes_downloaded = 0
            with requests.get(test_file_url, stream=True, timeout=10) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192):
                    if self.isInterruptionRequested():
                        return
                    bytes_downloaded += len(chunk)
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0.1:
                        speed_bps = (bytes_downloaded * 8) / elapsed_time
                        self.download_progress.emit(speed_bps / 1_000_000)
                    if elapsed_time > 10:  # Prevent test from running too long
                        break

            final_download_time = time.time() - start_time
            final_download_speed = (bytes_downloaded * 8 / final_download_time) / 1_000_000
            self.download_progress.emit(final_download_speed)

            self.upload_started.emit()

            # --- Animated Upload Test ---
            st.upload(threads=None)
            final_upload_speed = st.results.upload / 1_000_000

            # Animate the result for a better user experience
            animation_steps = 20
            for i in range(1, animation_steps + 1):
                if self.isInterruptionRequested():
                    return
                animated_speed = (final_upload_speed / animation_steps) * i
                self.upload_progress.emit(animated_speed)
                time.sleep(0.05)

            self.upload_progress.emit(final_upload_speed)
            self.test_finished.emit(final_download_speed, final_upload_speed)

        except Exception as e:
            self.error_signal.emit(str(e))


class SpeedTestDialog(QDialog):
    """Dialog to display speed test results with a speedometer-style interface."""
    def __init__(self, parent=None):
        super().__init__(parent)
        lang = "en" if english_language else "az"
        self.setWindowTitle(TEXTS[lang]["speed_test_results"])
        self.setFixedSize(975, 900)
        
        self.max_speed = 100
        self.current_speed = 0
        self.download_speed = 0
        self.upload_speed = 0
        self.test_phase = "download"
        
        self.init_ui()
        self.apply_theme()
        
        self.test_thread = SpeedTestThread()
        self.test_thread.download_progress.connect(self.update_download_progress)
        self.test_thread.upload_progress.connect(self.update_upload_progress)
        self.test_thread.upload_started.connect(self.on_upload_started)
        self.test_thread.test_finished.connect(self.on_test_finished)
        self.test_thread.error_signal.connect(self.on_test_error)
        self.test_thread.start()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(40)
        self.layout.setContentsMargins(30, 30, 30, 30)

        # Speedometer Container (top part)
        speedometer_container = QVBoxLayout()
        speedometer_container.setAlignment(Qt.AlignCenter)

        self.speedometer = ClassicSpeedometer(max_speed=100)
        self.speedometer.setMinimumSize(480, 480)
        self.speedometer.setMaximumSize(600, 600)
        speedometer_container.addWidget(self.speedometer, 0, Qt.AlignCenter)

        # Current speed display
        speed_display_container = QVBoxLayout()
        speed_display_container.setSpacing(8)
        speed_display_container.setAlignment(Qt.AlignCenter)

        self.speed_label = QLabel("0.00")
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed_label.setFont(QFont("Arial", 48, QFont.Bold))

        self.unit_label = QLabel("Mbps")
        self.unit_label.setAlignment(Qt.AlignCenter)
        self.unit_label.setFont(QFont("Arial", 18))

        speed_display_container.addWidget(self.speed_label)
        speed_display_container.addWidget(self.unit_label)

        speedometer_container.addLayout(speed_display_container)
        self.layout.addLayout(speedometer_container)

        # -------------------------
        # Results Container (bottom part)
        # Bütün sonuçlar ve butonlar buraya toplanacak
        self.results_container = QVBoxLayout()
        self.results_container.setSpacing(20)
        self.results_container.setContentsMargins(0, 0, 0, 0)
        self.results_container.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        lang = "en" if english_language else "az"

        # Test mode label (Download/Upload/Completed)
        self.mode_label = QLabel(TEXTS[lang]["testing_download"])
        self.mode_label.setAlignment(Qt.AlignCenter)
        self.mode_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.mode_label.setStyleSheet("margin: 20px 0px;")
        self.results_container.addWidget(self.mode_label)

        # Results frame
        self.results_frame = QFrame()
        self.results_frame.setVisible(False)
        self.results_frame.setFixedHeight(240)
        self.results_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255,255,255,0.05);
                border-radius: 12px;
                padding: 10px;
                margin: 5px 10px;
            }
        """)

        results_layout = QHBoxLayout(self.results_frame)
        results_layout.setSpacing(30)

        # Download container
        download_container = QVBoxLayout()
        download_container.setSpacing(5)
        download_container.setAlignment(Qt.AlignCenter)

        self.download_title = QLabel(TEXTS[lang]["download_speed"])
        self.download_title.setAlignment(Qt.AlignCenter)
        self.download_title.setFont(QFont("Arial", 12, QFont.Bold))
        self.download_title.setStyleSheet("color: #AAAAAA;")

        self.download_result = QLabel("0.00 Mbps")
        self.download_result.setAlignment(Qt.AlignCenter)
        self.download_result.setFont(QFont("Arial", 16, QFont.Bold))
        self.download_result.setStyleSheet("color: #3DDC97; margin-top: 5px;")

        download_container.addWidget(self.download_title)
        download_container.addWidget(self.download_result)

        # Upload container
        upload_container = QVBoxLayout()
        upload_container.setSpacing(5)
        upload_container.setAlignment(Qt.AlignCenter)

        self.upload_title = QLabel(TEXTS[lang]["upload_speed"])
        self.upload_title.setAlignment(Qt.AlignCenter)
        self.upload_title.setFont(QFont("Arial", 12, QFont.Bold))
        self.upload_title.setStyleSheet("color: #AAAAAA;")

        self.upload_result = QLabel("0.00 Mbps")
        self.upload_result.setAlignment(Qt.AlignCenter)
        self.upload_result.setFont(QFont("Arial", 16, QFont.Bold))
        self.upload_result.setStyleSheet("color: #FF9F1C; margin-top: 5px;")

        upload_container.addWidget(self.upload_title)
        upload_container.addWidget(self.upload_result)

        results_layout.addLayout(download_container)
        results_layout.addLayout(upload_container)

        self.results_container.addWidget(self.results_frame)

        # Close button
        self.close_button = QPushButton(TEXTS[lang]["close"])
        self.close_button.setVisible(False)
        self.close_button.setFixedHeight(90)
        self.close_button.clicked.connect(self.accept)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #4A9AFF;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px 25px;
                font-size: 18px;
                font-weight: bold;
                margin: 15px 50px;
            }
            QPushButton:hover {
                background-color: #3A8AEF;
            }
        """)
        self.results_container.addWidget(self.close_button)

        self.layout.addLayout(self.results_container)

    # The rest of the methods remain unchanged

    def update_download_progress(self, speed):
        if self.test_phase == "download":
            self.speedometer.set_speed(min(speed, 100))
            self.speed_label.setText(f"{speed:.1f}")
            self.download_speed = speed

    def update_upload_progress(self, speed):
        if self.test_phase == "upload":
            self.speedometer.set_speed(min(speed, 100))
            self.speed_label.setText(f"{speed:.1f}")
            self.upload_speed = speed

    def on_upload_started(self):
        self.test_phase = "upload"
        lang = "en" if english_language else "az"
        self.mode_label.setText(TEXTS[lang]["testing_upload"])
        self.download_result.setText(f"{self.download_speed:.1f} Mbps")

    def on_test_finished(self, final_download, final_upload):
        self.test_phase = "completed"
        lang = "en" if english_language else "az"
        self.download_speed = final_download
        self.upload_speed = final_upload
        self.download_result.setText(f"{final_download:.1f} Mbps")
        self.upload_result.setText(f"{final_upload:.1f} Mbps")
        self.mode_label.setText(TEXTS[lang]["test_completed"])
        self.results_frame.setVisible(True)
        self.close_button.setVisible(True)
        self.speed_label.setVisible(False)
        self.unit_label.setVisible(False)
        max_speed = max(final_download, final_upload)
        self.speedometer.set_speed(min(max_speed, 100))

    def apply_theme(self):
        colors = COLORS['dark'] if dark_mode else COLORS['light']
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['primary']};
                color: {colors['text_primary']};
            }}
            QLabel {{
                color: {colors['text_primary']};
            }}
            QFrame {{
                background-color: rgba(255,255,255,0.05);
                border-radius: 10px;
            }}
        """)

    def on_test_error(self, error_message):
        lang = "en" if english_language else "az"
        QMessageBox.critical(self, TEXTS[lang]["speed_test_error_title"], 
                             TEXTS[lang]["speed_test_failed"].format(error_message))
        self.accept()

    def closeEvent(self, event):
        if self.test_thread.isRunning():
            self.test_thread.requestInterruption()
            self.test_thread.quit()
            self.test_thread.wait(2000)
        event.accept()



class PingThread(QThread):
    """Thread for continuous ping monitoring"""
    update_signal = pyqtSignal(str, bool)  # Message, is_success
    status_signal = pyqtSignal(str, str)   # Status message, CSS class
    ping_result_signal = pyqtSignal(float) # Ping response time

    def __init__(self, sound_manager):
        super().__init__()
        self.running = True
        self.last_success_time = time.time()
        self.sound_manager = sound_manager
        self.consecutive_errors = 0
        self.max_errors_before_sound = 3

    def run(self):
        """Main ping loop"""
        while self.running:
            response = ping_host(DNS_SERVER, timeout=PING_TIMEOUT)
            now_str = datetime.now().strftime('%H:%M:%S')
            lang = "en" if english_language else "az"

            if response is not None:
                self.consecutive_errors = 0
                self.last_success_time = time.time()
                msg = TEXTS[lang]["ping_success"].format(response)
                status_msg = TEXTS[lang]["internet_good"]
                self.status_signal.emit(status_msg, "status-good")
                self.update_signal.emit(msg, True)
                self.ping_result_signal.emit(response)
            else:
                self.consecutive_errors += 1
                elapsed = time.time() - self.last_success_time
                msg = TEXTS[lang]["ping_failure"].format(elapsed)
                self.update_signal.emit(msg, False)
                if self.consecutive_errors >= self.max_errors_before_sound:
                    status_msg = TEXTS[lang]["internet_poor"]
                    self.status_signal.emit(status_msg, "status-error")
                    self.sound_manager.play("error")

            time.sleep(PING_INTERVAL)

    def stop(self):
        """Stop the ping thread"""
        self.running = False
        self.wait()

class AlarmThread(QThread):
    """Thread for monitoring and triggering alarms"""
    alarm_signal = pyqtSignal(str)  # Alarm message

    def __init__(self, sound_manager):
        super().__init__()
        self.running = True
        self.sound_manager = sound_manager
        self.triggered_today = set()  # Stores (hour, minute) of triggered alarms

    def run(self):
        """Main alarm monitoring loop"""
        global active_alarm_ringing
        while self.running:
            now = datetime.now()
            # Reset daily triggers at midnight
            if now.hour == 0 and now.minute == 0 and self.triggered_today:
                self.triggered_today.clear()

            for alarm_timestamp in active_alarm_timestamps[:]:
                alarm_time = datetime.fromtimestamp(alarm_timestamp)

                if now.hour == alarm_time.hour and \
                   now.minute == alarm_time.minute and \
                   (alarm_time.hour, alarm_time.minute) not in self.triggered_today:

                    active_alarm_ringing = True
                    self.triggered_today.add((alarm_time.hour, alarm_time.minute))
                    alarm_msg = TEXTS["en" if english_language else "az"]["alarm_ringing"]
                    self.alarm_signal.emit(alarm_msg)
                    self.sound_manager.play("alarm")
            time.sleep(1)

    def stop(self):
        """Stop the alarm thread"""
        self.running = False
        self.wait()

class SettingsDialog(QDialog):
    """Dialog for application settings"""
    settings_changed = pyqtSignal()
    language_changed = pyqtSignal(str)  # New signal for language change

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(TEXTS["en" if english_language else "az"]["settings_title"])
        self.setWindowIcon(QIcon('icon.png'))
        self.setGeometry(500, 400, 650, 550)
        self.init_ui()
        self.apply_theme_to_dialog()

    def init_ui(self):
        """Initialize settings UI"""
        layout = QFormLayout()
        layout.setSpacing(10)

        # DNS Server
        self.dns_input = QLineEdit(DNS_SERVER)
        self.dns_input.setProperty("class", "input-field")
        layout.addRow(QLabel(TEXTS["en" if english_language else "az"]["dns_server"]), self.dns_input)

        # Ping Interval
        self.ping_interval_spin = QSpinBox()
        self.ping_interval_spin.setRange(1, 60)
        self.ping_interval_spin.setValue(PING_INTERVAL)
        self.ping_interval_spin.setProperty("class", "input-field")
        layout.addRow(QLabel(TEXTS["en" if english_language else "az"]["ping_interval"]), self.ping_interval_spin)

        # Ping Timeout
        self.ping_timeout_spin = QSpinBox()
        self.ping_timeout_spin.setRange(1, 10)
        self.ping_timeout_spin.setValue(PING_TIMEOUT)
        self.ping_timeout_spin.setProperty("class", "input-field")
        layout.addRow(QLabel(TEXTS["en" if english_language else "az"]["ping_timeout"]), self.ping_timeout_spin)

        # Language
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", True)
        self.language_combo.addItem("Azərbaycanca", False)
        self.language_combo.setCurrentIndex(0 if english_language else 1)
        self.language_combo.setProperty("class", "input-field")
        layout.addRow(QLabel(TEXTS["en" if english_language else "az"]["language"]), self.language_combo)

        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light", False)
        self.theme_combo.addItem("Dark", True)
        self.theme_combo.setCurrentIndex(1 if dark_mode else 0)
        self.theme_combo.setProperty("class", "input-field")
        layout.addRow(QLabel(TEXTS["en" if english_language else "az"]["theme"]), self.theme_combo)

        # Sound files
        self.error_sound_label = QLabel(os.path.basename(ERROR_SOUND_FILE))
        change_error_sound_btn = QPushButton(TEXTS["en" if english_language else "az"]["browse"])
        change_error_sound_btn.setProperty("class", "browse-btn")
        change_error_sound_btn.clicked.connect(self._select_error_sound)
        error_sound_layout = QHBoxLayout()
        error_sound_layout.addWidget(self.error_sound_label)
        error_sound_layout.addWidget(change_error_sound_btn)
        layout.addRow(QLabel(TEXTS["en" if english_language else "az"]["error_sound"]), error_sound_layout)

        self.alarm_sound_label = QLabel(os.path.basename(ALARM_SOUND_FILE))
        change_alarm_sound_btn = QPushButton(TEXTS["en" if english_language else "az"]["browse"])
        change_alarm_sound_btn.setProperty("class", "browse-btn")
        change_alarm_sound_btn.clicked.connect(self._select_alarm_sound)
        alarm_sound_layout = QHBoxLayout()
        alarm_sound_layout.addWidget(self.alarm_sound_label)
        alarm_sound_layout.addWidget(change_alarm_sound_btn)
        layout.addRow(QLabel(TEXTS["en" if english_language else "az"]["alarm_sound"]), alarm_sound_layout)

        # Save button
        save_button = QPushButton(TEXTS["en" if english_language else "az"]["save"])
        save_button.setProperty("class", "save-btn")
        save_button.clicked.connect(self.save_settings)
        layout.addRow(save_button)

        self.setLayout(layout)

    def apply_theme_to_dialog(self):
        """Apply current theme to settings dialog"""
        colors = COLORS['dark'] if dark_mode else COLORS['light']
        style = f"""
            QDialog {{
                background-color: {colors['primary']};
                color: {colors['text_primary']};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QLabel {{
                color: {colors['text_primary']};
                font-size: 14px;
            }}
            .input-field {{
                background-color: {colors['secondary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 8px;
                color: {colors['text_primary']};
                font-size: 14px;
                min-height: 36px;
            }}
            QLineEdit.input-field {{
                padding: 8px 12px;
            }}
            .browse-btn, .save-btn {{
                background-color: {colors['tertiary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 8px 16px;
                color: {colors['text_primary']};
                font-size: 14px;
                min-width: 100px;
            }}
            .browse-btn:hover, .save-btn:hover {{
                background-color: {colors['hover']};
            }}
            .browse-btn:pressed, .save-btn:pressed {{
                background-color: {colors['active']};
            }}
            .save-btn {{
                background-color: {colors['accent_blue']};
                color: white;
                font-weight: bold;
                margin-top: 20px;
            }}
            .save-btn:hover {{
                background-color: {colors['accent_blue']};
                opacity: 0.9;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: {colors['border']};
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {colors['secondary']};
                border: 1px solid {colors['border']};
                selection-background-color: {colors['accent_blue']};
                selection-color: white;
            }}
        """
        self.setStyleSheet(style)

    def _select_sound(self, label_widget, sound_type):
        """Open file dialog to select sound file"""
        title = f"Select {sound_type.capitalize()} Sound"
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", "WAV Files (*.wav)")
        if file_path:
            label_widget.setText(os.path.basename(file_path))
            if sound_type == "error":
                self.parent().sound_manager.error_sound = file_path
            elif sound_type == "alarm":
                self.parent().sound_manager.alarm_sound = file_path

    def _select_error_sound(self):
        self._select_sound(self.error_sound_label, "error")

    def _select_alarm_sound(self):
        self._select_sound(self.alarm_sound_label, "alarm")

    def save_settings(self):
        """Save settings and emit changed signal"""
        global DNS_SERVER, PING_INTERVAL, PING_TIMEOUT, dark_mode, english_language
        DNS_SERVER = self.dns_input.text() or "8.8.8.8"
        PING_INTERVAL = self.ping_interval_spin.value()
        PING_TIMEOUT = self.ping_timeout_spin.value()

        # Check if language changed
        lang_changed = english_language != self.language_combo.currentData()
        english_language = self.language_combo.currentData()
        dark_mode = self.theme_combo.currentData()

        self.settings_changed.emit()
        if lang_changed:
            self.language_changed.emit("en" if english_language else "az")
        self.accept()

class PingApp(QWidget):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.sound_manager = SoundManager()
        self.managed_alarms = []
        self.load_config()

        self.ping_thread = PingThread(self.sound_manager)
        self.alarm_thread = AlarmThread(self.sound_manager)

        # Data for graphing
        self.ping_data = []
        self.time_data = []
        self.max_data_points = 60

        self.init_ui()
        self.init_threads_and_timers()
        self.load_alarms_data()
        self.reschedule_all_alarms()
        self.create_menu_bar()
        self.create_tray_icon()
        self.apply_theme()
        self.update_texts()

    def init_ui(self):
        """Initialize main UI components"""
        self.setWindowTitle(TEXTS["en" if english_language else "az"]["main_title"])
        self.original_width = 1100
        self.original_height = 750
        self.setGeometry(500, 250, int(self.original_width * 1.5), int(self.original_height * 1.5))
        self.setWindowIcon(QIcon('icon.png'))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        self.main_frame = QFrame()
        grid = QGridLayout(self.main_frame)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(15)

        # Top panel with ping monitor and graph
        top_panel = QFrame()
        top_panel.setFrameShape(QFrame.StyledPanel)
        top_panel.setProperty("class", "panel")
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(15, 15, 15, 15)
        top_layout.setSpacing(15)

        ping_panel = self.create_ping_panel()
        top_layout.addWidget(ping_panel, 2)

        graph_panel = self.create_graph_panel()
        top_layout.addWidget(graph_panel, 2)

        grid.addWidget(top_panel, 0, 0, 1, 2)

        # Bottom panel with alarms, clock and ip
        bottom_panel = QFrame()
        bottom_panel.setFrameShape(QFrame.StyledPanel)
        bottom_panel.setProperty("class", "panel")
        bottom_layout = QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(15, 15, 15, 15)
        bottom_layout.setSpacing(15)

        alarm_panel = self.create_alarm_panel()
        bottom_layout.addWidget(alarm_panel, 1)

        clock_panel = self.create_clock_panel()
        bottom_layout.addWidget(clock_panel, 1)

        grid.addWidget(bottom_panel, 1, 0, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        main_layout.addWidget(self.main_frame)
        self.setLayout(main_layout)

    def create_clock_panel(self):
        """Create clock panel with time, date and location info"""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setProperty("class", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Digital clock
        self.current_time_label = QLabel()
        self.current_time_label.setObjectName("CurrentTimeLabel")
        self.current_time_label.setFont(QFont("Segoe UI", 48, QFont.Bold))
        self.current_time_label.setAlignment(Qt.AlignCenter)

        # Date display
        self.current_date_label = QLabel()
        self.current_date_label.setObjectName("CurrentDateLabel")
        self.current_date_label.setFont(QFont("Segoe UI", 24))
        self.current_date_label.setAlignment(Qt.AlignCenter)

        # IP addresses
        ip_layout = QVBoxLayout()
        ip_layout.setSpacing(5)

        # Local IP
        self.local_ip_label = QLabel()
        self.local_ip_label.setObjectName("LocalIpLabel")
        self.local_ip_label.setFont(QFont("Segoe UI", 14))
        self.local_ip_label.setAlignment(Qt.AlignCenter)
        self.local_ip_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.local_ip_label.mousePressEvent = lambda e: QApplication.clipboard().setText(self.local_ip_label.text().split(": ")[1])

        # Public IP
        self.public_ip_label = QLabel()
        self.public_ip_label.setObjectName("PublicIpLabel")
        self.public_ip_label.setFont(QFont("Segoe UI", 14))
        self.public_ip_label.setAlignment(Qt.AlignCenter)
        self.public_ip_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.public_ip_label.mousePressEvent = lambda e: QApplication.clipboard().setText(self.public_ip_label.text().split(": ")[1])

        ip_layout.addWidget(self.local_ip_label)
        ip_layout.addWidget(self.public_ip_label)

        # Glow effect for clock
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(20)
        glow.setColor(QColor(COLORS['dark']['accent_blue'] if dark_mode else COLORS['light']['accent_blue']))
        glow.setOffset(0, 0)
        self.current_time_label.setGraphicsEffect(glow)

        layout.addWidget(self.current_time_label)
        layout.addWidget(self.current_date_label)
        layout.addLayout(ip_layout)

        # Initialize IP info
        self.update_ip_info()

        return panel

    def update_ip_info(self):
        """Update IP address information"""
        try:
            # Get local IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            self.local_ip_label.setText(f"{TEXTS['en' if english_language else 'az']['local_ip']} {local_ip}")

            # Get public IP (with timeout to prevent blocking)
            try:
                public_ip = requests.get('https://api.ipify.org', timeout=3).text
                self.public_ip_label.setText(f"{TEXTS['en' if english_language else 'az']['public_ip']} {public_ip}")
            except:
                self.public_ip_label.setText(f"{TEXTS['en' if english_language else 'az']['public_ip']} {TEXTS['en' if english_language else 'az']['ip_not_available']}")

        except Exception as e:
            print(f"IP info error: {e}")
            self.local_ip_label.setText(f"{TEXTS['en' if english_language else 'az']['local_ip']} {TEXTS['en' if english_language else 'az']['ip_not_available']}")
            self.public_ip_label.setText(f"{TEXTS['en' if english_language else 'az']['public_ip']} {TEXTS['en' if english_language else 'az']['ip_not_available']}")

    def create_graph_panel(self):
        """Create ping response time graph panel"""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setProperty("class", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        self.graph_title = QLabel(TEXTS["en" if english_language else "az"]["ping_graph_title"])
        self.graph_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.graph_title.setAlignment(Qt.AlignCenter)
        self.graph_title.setProperty("class", "panel-title")
        layout.addWidget(self.graph_title)

        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground(COLORS['dark']['tertiary'] if dark_mode else COLORS['light']['tertiary'])
        self.plot = self.graphWidget.plot(pen=pg.mkPen(color=COLORS['dark']['accent_blue'] if dark_mode else COLORS['light']['accent_blue'], width=2))
        self.graphWidget.setLabel('left', "Response Time (ms)")
        self.graphWidget.setLabel('bottom', "Time")
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.setYRange(0, 100)

        layout.addWidget(self.graphWidget)
        return panel

    def create_ping_panel(self):
        """Create ping monitoring panel"""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setProperty("class", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        self.title_label = QLabel(TEXTS["en" if english_language else "az"]["ping_monitor_title"])
        self.title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setProperty("class", "panel-title")

        self.connection_status = QLabel(TEXTS["en" if english_language else "az"]["searching"])
        self.connection_status.setObjectName("ConnectionStatus")
        self.connection_status.setFont(QFont("Segoe UI", 12))
        self.connection_status.setAlignment(Qt.AlignCenter)

        self.ping_result_list = QListWidget()
        self.ping_result_list.setObjectName("PingResultList")
        self.ping_result_list.setFont(QFont("Segoe UI", 10))  # Reduced font size for ping results
        self.ping_result_list.setSpacing(4)

        layout.addWidget(self.title_label)
        layout.addWidget(self.connection_status)
        layout.addWidget(self.ping_result_list)
        return panel

    def create_alarm_panel(self):
        """Create alarm management panel"""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setProperty("class", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        self.alarm_status = QLabel()
        self.alarm_status.setObjectName("AlarmStatus")
        self.alarm_status.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.alarm_status.setAlignment(Qt.AlignCenter)

        self.stop_alarm_btn = QPushButton(TEXTS["en" if english_language else "az"]["stop_alarm"])
        self.stop_alarm_btn.clicked.connect(self.stop_alarm_sound)
        self.stop_alarm_btn.setVisible(False)
        self.stop_alarm_btn.setProperty("class", "stop-alarm-btn")

        self.daily_alarms_title = QLabel(TEXTS["en" if english_language else "az"]["alarm_management"])
        self.daily_alarms_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.daily_alarms_title.setAlignment(Qt.AlignCenter)
        self.daily_alarms_title.setProperty("class", "panel-title")

        self.managed_alarms_list = QListWidget()
        self.managed_alarms_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.managed_alarms_list.setFont(QFont("Segoe UI", 12))
        self.managed_alarms_list.setSpacing(4)
        self.managed_alarms_list.itemClicked.connect(self.toggle_alarm_enabled)

        alarm_btn_layout = QHBoxLayout()
        alarm_btn_layout.setSpacing(10)

        self.add_new_alarm_btn = QPushButton(TEXTS["en" if english_language else "az"]["add_new"])
        self.add_new_alarm_btn.clicked.connect(self.add_new_alarm)
        self.add_new_alarm_btn.setProperty("class", "action-btn")

        self.delete_selected_alarm_btn = QPushButton(TEXTS["en" if english_language else "az"]["delete_selected"])
        self.delete_selected_alarm_btn.clicked.connect(self.delete_selected_alarm)
        self.delete_selected_alarm_btn.setProperty("class", "action-btn danger")

        self.save_managed_alarms_btn = QPushButton(TEXTS["en" if english_language else "az"]["save_alarms"])
        self.save_managed_alarms_btn.clicked.connect(self.save_alarms_data)
        self.save_managed_alarms_btn.setProperty("class", "action-btn success")

        self.speed_test_btn = QPushButton(TEXTS["en" if english_language else "az"]["speed_test"])
        self.speed_test_btn.clicked.connect(self.run_speed_test)
        self.speed_test_btn.setProperty("class", "action-btn")
        if not speedtest:
            self.speed_test_btn.setEnabled(False)
            self.speed_test_btn.setToolTip("Install 'speedtest-cli' library to enable.")


        alarm_btn_layout.addWidget(self.add_new_alarm_btn)
        alarm_btn_layout.addWidget(self.delete_selected_alarm_btn)
        alarm_btn_layout.addWidget(self.save_managed_alarms_btn)
        alarm_btn_layout.addWidget(self.speed_test_btn)

        layout.addWidget(self.daily_alarms_title)
        layout.addWidget(self.managed_alarms_list)
        layout.addLayout(alarm_btn_layout)
        layout.addWidget(self.alarm_status)
        layout.addWidget(self.stop_alarm_btn)

        return panel

    def run_speed_test(self):
        """Show the speed test dialog."""
        if not speedtest:
            QMessageBox.warning(self, "Feature Unavailable",
                                "The 'speedtest-cli' library is not installed.\nPlease install it via: pip install speedtest-cli")
            return
        dialog = SpeedTestDialog(self)
        dialog.exec_()


    def init_threads_and_timers(self):
        """Initialize and start background threads and timers"""
        # Clock update timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

        # Ping thread signals
        self.ping_thread.update_signal.connect(self.update_ping_display)
        self.ping_thread.status_signal.connect(self.update_connection_status)
        self.ping_thread.ping_result_signal.connect(self.update_ping_graph)
        self.ping_thread.start()

        # Alarm thread signals
        self.alarm_thread.alarm_signal.connect(self.on_alarm_ring)
        self.alarm_thread.start()

    def update_ping_graph(self, response_time):
        """Update ping response time graph with new data"""
        now = time.time()

        # Add new data point
        self.ping_data.append(response_time)
        self.time_data.append(now)

        # Keep only recent data points
        if len(self.ping_data) > self.max_data_points:
            self.ping_data = self.ping_data[-self.max_data_points:]
            self.time_data = self.time_data[-self.max_data_points:]

        # Convert timestamps to relative seconds
        if len(self.time_data) > 0:
            relative_times = [t - self.time_data[0] for t in self.time_data]

            # Update plot
            self.plot.setData(relative_times, self.ping_data)

            # Auto-scale Y axis
            min_y = max(0, min(self.ping_data) - 5)
            max_y = max(100, max(self.ping_data) + 5)
            self.graphWidget.setYRange(min_y, max_y)

            # Set X axis range
            self.graphWidget.setXRange(0, max(60, relative_times[-1] + 5))

    def create_tray_icon(self):
        """Create system tray icon"""
        self.tray_icon = QSystemTrayIcon(QIcon('icon.png'), self)
        self.tray_icon.setVisible(True)
        self.tray_icon.activated.connect(self.restore_from_tray)
        self.set_tray_menu()

    def set_tray_menu(self):
        """Create tray icon context menu"""
        tray_menu = QMenu()
        restore_action = QAction(TEXTS["en" if english_language else "az"]["tray_show"], self, triggered=self.showNormal)
        quit_action = QAction(TEXTS["en" if english_language else "az"]["tray_quit"], self, triggered=self.close)
        tray_menu.addAction(restore_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)

    def restore_from_tray(self, reason):
        """Restore window from tray icon"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.activateWindow()
            self.raise_()

    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(self,
                                   TEXTS["en" if english_language else "az"]["quit_title"],
                                   TEXTS["en" if english_language else "az"]["quit_message"],
                                   QMessageBox.Yes | QMessageBox.Cancel,
                                   QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            self.shutdown()
            event.accept()
        else:
            event.ignore()

    def shutdown(self):
        """Cleanup before quitting"""
        self.save_config()
        self.save_alarms_data()
        self.ping_thread.stop()
        self.alarm_thread.stop()
        self.tray_icon.hide()

    def load_config(self):
        """Load settings from config file"""
        global DNS_SERVER, PING_TIMEOUT, PING_INTERVAL, dark_mode, english_language
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                DNS_SERVER = config.get('dns_server', DNS_SERVER)
                PING_TIMEOUT = config.get('ping_timeout', PING_TIMEOUT)
                PING_INTERVAL = config.get('ping_interval', PING_INTERVAL)
                dark_mode = config.get('dark_mode', dark_mode)
                english_language = config.get('english_language', english_language)
                self.sound_manager.error_sound = config.get('error_sound_file', ERROR_SOUND_FILE)
                self.sound_manager.alarm_sound = config.get('alarm_sound_file', ALARM_SOUND_FILE)
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        """Save settings to config file"""
        config = {
            'dns_server': DNS_SERVER,
            'ping_timeout': PING_TIMEOUT,
            'ping_interval': PING_INTERVAL,
            'dark_mode': dark_mode,
            'english_language': english_language,
            'error_sound_file': self.sound_manager.error_sound,
            'alarm_sound_file': self.sound_manager.alarm_sound,
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def load_alarms_data(self):
        """Load alarms from config file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                alarms_data = config.get('managed_alarms', [])
                self.managed_alarms = [Alarm.from_dict(d) for d in alarms_data]

            # Add default alarms if none loaded
            if not self.managed_alarms:
                lang = "en" if english_language else "az"
                self.managed_alarms.append(Alarm(9, 0, True, TEXTS[lang]["default_alarms"][0]))
                self.managed_alarms.append(Alarm(11, 0, True, TEXTS[lang]["default_alarms"][1]))
                self.managed_alarms.append(Alarm(14, 0, True, TEXTS[lang]["default_alarms"][2]))
                self.managed_alarms.append(Alarm(17, 0, True, TEXTS[lang]["default_alarms"][3]))
                self.save_alarms_data()

            # Update UI with loaded alarms
            self.update_alarm_list_ui()
        except Exception as e:
            QMessageBox.warning(self,
                              TEXTS["en" if english_language else "az"]["alarm_load_error"],
                              f"{TEXTS['en' if english_language else 'az']['alarm_load_error']}: {e}")

    def save_alarms_data(self):
        """Save alarms to config file"""
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)

            config['managed_alarms'] = [alarm.to_dict() for alarm in self.managed_alarms]

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self,
                               TEXTS["en" if english_language else "az"]["alarm_save_error"],
                               f"{TEXTS['en' if english_language else 'az']['alarm_save_error']}: {e}")

    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = QMenuBar(self)
        self.layout().setMenuBar(menubar)
        settings_menu = menubar.addMenu(TEXTS["en" if english_language else "az"]["menu_settings"])

        open_settings_action = QAction(TEXTS["en" if english_language else "az"]["menu_open_settings"], self, triggered=self.show_settings_dialog)
        settings_menu.addAction(open_settings_action)
        settings_menu.addSeparator()
        exit_action = QAction(TEXTS["en" if english_language else "az"]["menu_exit"], self, triggered=self.close)
        settings_menu.addAction(exit_action)

    def show_settings_dialog(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.handle_settings_changed)
        dialog.language_changed.connect(self.update_texts)
        dialog.exec_()

    def handle_settings_changed(self):
        """Handle settings changes"""
        self.apply_theme()
        # Restart ping thread with new settings
        self.ping_thread.stop()
        self.ping_thread = PingThread(self.sound_manager)
        self.ping_thread.update_signal.connect(self.update_ping_display)
        self.ping_thread.status_signal.connect(self.update_connection_status)
        self.ping_thread.ping_result_signal.connect(self.update_ping_graph)
        self.ping_thread.start()
        self.save_config()

    def update_texts(self, lang=None):
        """Update all UI texts based on current language"""
        lang = "en" if english_language else "az" if lang is None else lang

        # Main window
        self.setWindowTitle(TEXTS[lang]["main_title"])

        # Ping panel
        self.title_label.setText(TEXTS[lang]["ping_monitor_title"])
        self.connection_status.setText(TEXTS[lang]["searching"])

        # Alarm panel
        self.daily_alarms_title.setText(TEXTS[lang]["alarm_management"])
        self.stop_alarm_btn.setText(TEXTS[lang]["stop_alarm"])
        self.add_new_alarm_btn.setText(TEXTS[lang]["add_new"])
        self.delete_selected_alarm_btn.setText(TEXTS[lang]["delete_selected"])
        self.save_managed_alarms_btn.setText(TEXTS[lang]["save_alarms"])
        if hasattr(self, 'speed_test_btn'):
            self.speed_test_btn.setText(TEXTS[lang]["speed_test"])

        # Graph panel title
        if hasattr(self, 'graph_title'):
            self.graph_title.setText(TEXTS[lang]["ping_graph_title"])

        # Menu bar
        if self.layout() and self.layout().menuBar():
            menu_bar = self.layout().menuBar()
            actions = menu_bar.actions()
            if actions:
                settings_menu = actions[0].menu()
                if settings_menu:
                    menu_actions = settings_menu.actions()
                    actions[0].setText(TEXTS[lang]["menu_settings"])
                    menu_actions[0].setText(TEXTS[lang]["menu_open_settings"])
                    menu_actions[2].setText(TEXTS[lang]["menu_exit"])

        # Tray menu
        self.set_tray_menu()

        # IP info
        self.update_ip_info()

    def apply_theme(self):
        """Apply current theme to UI"""
        colors = COLORS['dark'] if dark_mode else COLORS['light']

        style = f"""
            /* Main window styling */
            QWidget {{
                background-color: {colors['primary']};
                color: {colors['text_primary']};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}

            /* Panel styling */
            .panel {{
                background-color: {colors['secondary']};
                border-radius: 12px;
                border: 1px solid {colors['border']};
            }}

            .panel-title {{
                color: {colors['accent_blue']};
                margin-bottom: 10px;
            }}

            /* List widgets */
            QListWidget {{
                background-color: {colors['tertiary']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 5px;
                outline: 0;
            }}

            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}

            QListWidget::item:hover {{
                background-color: {colors['hover']};
            }}

            QListWidget::item:selected {{
                background-color: {colors['accent_blue']};
                color: white;
            }}

            /* Ping result list specific */
            #PingResultList::item[success="true"] {{
                background-color: {colors['success_bg']};
                color: {colors['accent_green']};
            }}

            #PingResultList::item[success="false"] {{
                background-color: {colors['error_bg']};
                color: {colors['accent_red']};
            }}

            /* Connection status labels */
            #ConnectionStatus.status-good {{
                color: {colors['accent_green']};
            }}

            #ConnectionStatus.status-error {{
                color: {colors['accent_red']};
                font-weight: bold;
            }}

            /* Alarm status */
            #AlarmStatus[ringing="true"] {{
                color: {colors['accent_red']};
                font-weight: bold;
            }}

            /* Clock panel specific */
            #CurrentDateLabel {{
                color: {colors['text_secondary']};
                margin-top: 10px;
            }}

            /* IP labels */
            #LocalIpLabel, #PublicIpLabel {{
                color: {colors['text_secondary']};
            }}
            #LocalIpLabel:hover, #PublicIpLabel:hover {{
                color: {colors['accent_blue']};
                text-decoration: underline;
            }}

            /* Buttons */
            .action-btn {{
                background-color: {colors['tertiary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 8px 16px;
                color: {colors['text_primary']};
                min-height: 36px;
                font-weight: bold;
            }}

            .action-btn:hover {{
                background-color: {colors['hover']};
            }}

            .action-btn:pressed {{
                background-color: {colors['active']};
            }}
            
            .action-btn:disabled {{
                background-color: {colors['tertiary']};
                color: {colors['text_muted']};
            }}

            .action-btn.success {{
                background-color: {colors['accent_green']};
                color: white;
            }}
            .action-btn.success:hover {{
                background-color: #38D08F;
            }}

            .action-btn.danger {{
                background-color: {colors['accent_red']};
                color: white;
            }}
            .action-btn.danger:hover {{
                background-color: #F84D49;
            }}

            .stop-alarm-btn {{
                background-color: {colors['accent_red']};
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px;
                border: none;
            }}

            .stop-alarm-btn:hover {{
                background-color: #F84D49;
            }}

            /* Menu bar */
            QMenuBar {{
                background-color: {colors['secondary']};
                padding: 5px;
                border-bottom: 1px solid {colors['border']};
            }}

            QMenuBar::item {{
                padding: 5px 10px;
                background-color: transparent;
                border-radius: 4px;
            }}

            QMenuBar::item:selected {{
                background-color: {colors['hover']};
            }}

            QMenuBar::item:pressed {{
                background-color: {colors['active']};
            }}
        """
        self.setStyleSheet(style)

        # Apply style to menubar
        if self.layout() and self.layout().menuBar():
            self.layout().menuBar().setStyleSheet(f"""
                QMenuBar {{
                    background-color: {colors['secondary']};
                    color: {colors['text_primary']};
                }}
                QMenu {{
                    background-color: {colors['secondary']};
                    color: {colors['text_primary']};
                    border: 1px solid {colors['border']};
                }}
                QMenu::item:selected {{
                    background-color: {colors['hover']};
                }}
            """)

        # Update graph colors
        if hasattr(self, 'graphWidget'):
            self.graphWidget.setBackground(colors['tertiary'])
            self.plot.setPen(pg.mkPen(color=colors['accent_blue'], width=2))
            self.graphWidget.getAxis('bottom').setPen(pg.mkPen(color=colors['text_muted']))
            self.graphWidget.getAxis('left').setPen(pg.mkPen(color=colors['text_muted']))

    def update_clock(self):
        """Update clock display with current time"""
        try:
            # Azerbaijan timezone (UTC+4)
            timezone = pytz.timezone('Asia/Baku')
            current_time = datetime.now(timezone)

            # Update time
            time_str = current_time.strftime("%H:%M:%S")
            self.current_time_label.setText(time_str)

            # Update date if day changed
            if not hasattr(self, 'last_date') or self.last_date != current_time.date():
                self.last_date = current_time.date()
                date_str = current_time.strftime('%d %B %Y, %A')
                self.current_date_label.setText(date_str)
                self.update_ip_info()

        except Exception as e:
            print(f"Clock update error: {e}")
            self.current_time_label.setText(datetime.now().strftime("%H:%M:%S"))
            self.current_date_label.setText(datetime.now().strftime('%d %B %Y, %A'))

    def update_ping_display(self, message, is_success):
        """Add new ping result to display"""
        item = QListWidgetItem(message)
        item.setData(Qt.UserRole + 1, "true" if is_success else "false")

        if is_success:
            item.setForeground(QColor(COLORS['dark']['accent_green'] if dark_mode else COLORS['light']['accent_green']))
        else:
            item.setForeground(QColor(COLORS['dark']['accent_red'] if dark_mode else COLORS['light']['accent_red']))

        self.ping_result_list.addItem(item)
        self.ping_result_list.scrollToBottom()

    def update_connection_status(self, message, css_class):
        """Update connection status label"""
        self.connection_status.setText(message)
        self.connection_status.setProperty("class", css_class)
        self.style().polish(self.connection_status)

    def on_alarm_ring(self, message):
        """Handle alarm ringing event"""
        global active_alarm_ringing
        self.alarm_status.setText(message)
        self.alarm_status.setProperty("ringing", "true")
        self.style().polish(self.alarm_status)
        self.stop_alarm_btn.setVisible(True)

        # Bring app to front
        if self.isMinimized():
            self.showNormal()
        self.activateWindow()
        self.raise_()

    def stop_alarm_sound(self):
        """Stop alarm sound and reset UI"""
        global active_alarm_ringing
        self.sound_manager.stop_alarm()
        active_alarm_ringing = False
        self.alarm_status.setText("")
        self.alarm_status.setProperty("ringing", "false")
        self.style().polish(self.alarm_status)
        self.stop_alarm_btn.setVisible(False)

    def update_alarm_list_ui(self):
        """Refresh displayed alarm list"""
        self.managed_alarms_list.clear()
        for alarm in self.managed_alarms:
            item = QListWidgetItem(str(alarm))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if alarm.enabled else Qt.Unchecked)
            item.setData(Qt.UserRole, alarm)

            # Set background based on status
            if alarm.enabled:
                item.setBackground(QColor(COLORS['dark']['success_bg'] if dark_mode else COLORS['light']['success_bg']))
            else:
                item.setBackground(QColor(COLORS['dark']['tertiary'] if dark_mode else COLORS['light']['tertiary']))

            self.managed_alarms_list.addItem(item)
        self.reschedule_all_alarms()

    def add_new_alarm(self):
        """Add new alarm through dialog"""
        text, ok = QInputDialog.getText(self,
                                      TEXTS["en" if english_language else "az"]["new_alarm_title"],
                                      TEXTS["en" if english_language else "az"]["new_alarm_prompt"])
        if not ok or not text:
            return

        time_dialog = QDialog(self)
        time_dialog.setWindowTitle(TEXTS["en" if english_language else "az"]["set_time_title"])
        time_layout = QVBoxLayout(time_dialog)
        time_edit = QTimeEdit(QTime.currentTime())
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setFont(QFont("Segoe UI", 24))
        ok_button = QPushButton(TEXTS["en" if english_language else "az"]["ok"])
        ok_button.clicked.connect(time_dialog.accept)
        time_layout.addWidget(QLabel(TEXTS["en" if english_language else "az"]["select_time"]))
        time_layout.addWidget(time_edit)
        time_layout.addWidget(ok_button)

        if time_dialog.exec_() == QDialog.Accepted:
            selected_time = time_edit.time()
            new_alarm = Alarm(selected_time.hour(), selected_time.minute(), True, text)

            if new_alarm not in self.managed_alarms:
                self.managed_alarms.append(new_alarm)
                self.update_alarm_list_ui()
                self.save_alarms_data()
            else:
                QMessageBox.warning(self,
                                   TEXTS["en" if english_language else "az"]["new_alarm_title"],
                                   TEXTS["en" if english_language else "az"]["duplicate_alarm"])

    def delete_selected_alarm(self):
        """Delete selected alarms"""
        selected_items = self.managed_alarms_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self,
                                   TEXTS["en" if english_language else "az"]["new_alarm_title"],
                                   TEXTS["en" if english_language else "az"]["no_selection"])
            return

        reply = QMessageBox.question(self,
                                   TEXTS["en" if english_language else "az"]["new_alarm_title"],
                                   TEXTS["en" if english_language else "az"]["confirm_delete"].format(len(selected_items)),
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            alarms_to_remove = [item.data(Qt.UserRole) for item in selected_items]
            self.managed_alarms = [alarm for alarm in self.managed_alarms if alarm not in alarms_to_remove]
            self.update_alarm_list_ui()
            self.save_alarms_data()

    def toggle_alarm_enabled(self, item):
        """Toggle alarm enabled status"""
        alarm = item.data(Qt.UserRole)
        if alarm:
            alarm.enabled = item.checkState() == Qt.Checked
            item.setText(str(alarm))

            # Update background color
            if alarm.enabled:
                item.setBackground(QColor(COLORS['dark']['success_bg'] if dark_mode else COLORS['light']['success_bg']))
            else:
                item.setBackground(QColor(COLORS['dark']['tertiary'] if dark_mode else COLORS['light']['tertiary']))

            self.save_alarms_data()
            self.reschedule_all_alarms()

    def reschedule_all_alarms(self):
        """Recalculate alarm timestamps"""
        global active_alarm_timestamps
        active_alarm_timestamps.clear()
        now = datetime.now()
        for alarm in self.managed_alarms:
            if alarm.enabled:
                alarm_dt_today = now.replace(hour=alarm.hour, minute=alarm.minute, second=0, microsecond=0)
                if alarm_dt_today <= now:
                    alarm_dt_today += timedelta(days=1)
                active_alarm_timestamps.append(alarm_dt_today.timestamp())

        active_alarm_timestamps.sort()
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Create dummy icon if missing
    if not os.path.exists('icon.png'):
        try:
            from PIL import Image
            img = Image.new('RGB', (16, 16), color = 'red')
            img.save('icon.png')
            print("Created dummy 'icon.png'")
        except ImportError:
            print("Pillow not found. Please install Pillow or provide 'icon.png'")

    # Check for sound files
    for sound_file in [ERROR_SOUND_FILE, ALARM_SOUND_FILE]:
        if not os.path.exists(sound_file):
            print(f"Warning: {sound_file} not found. Sound alerts might not work.")

    ex = PingApp()
    ex.show()
    sys.exit(app.exec_())