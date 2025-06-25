import sys
import time
import threading
import platform
from datetime import datetime, timedelta
import os
import json
import re
import subprocess

# PyQt5 imports
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QMessageBox, QFrame,
    QGridLayout, QScrollArea, QSizePolicy, QFileDialog,
    QInputDialog, QMenu, QAction, QMenuBar, QSystemTrayIcon,
    QDialog, QFormLayout, QComboBox, QSpinBox, QListWidgetItem,
    QCheckBox, QTimeEdit
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QThread, QTime
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QCursor

# Conditional import for winsound (Windows only)
try:
    import winsound
except ImportError:
    winsound = None
    


# Third-party imports
try:
    import ping3
except ImportError:
    ping3 = None
    print("Warning: 'ping3' library not found. Falling back to subprocess ping. For better performance, consider installing it: pip install ping3")

# --- Global Settings ---
# These will be loaded from config.json or use defaults
DNS_SERVER = "8.8.8.8"
PING_TIMEOUT = 1
PING_INTERVAL = 1
ERROR_SOUND_FILE = "error.wav"
ALARM_SOUND_FILE = "alarm.wav"
dark_mode = True  # Default to dark mode
english_language = False # Default to Turkish
CONFIG_FILE = "config.json"

# Store active alarms (timestamps) that AlarmThread monitors
active_alarm_timestamps = [] # This list will hold UNIX timestamps for active alarms
# Flag to indicate if an alarm is currently ringing
active_alarm_ringing = False


# --- Alarm Class ---
class Alarm:
    """Represents a single, reusable alarm."""
    def __init__(self, hour, minute, enabled=True, name="Alarm"):
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid hour or minute for alarm.")
        self.hour = hour
        self.minute = minute
        self.enabled = enabled
        self.name = name

    def to_dict(self):
        """Serializes the alarm object to a dictionary."""
        return {
            "hour": self.hour,
            "minute": self.minute,
            "enabled": self.enabled,
            "name": self.name
        }

    @staticmethod
    def from_dict(data):
        """Creates an Alarm object from a dictionary."""
        return Alarm(data.get("hour", 0), data.get("minute", 0), data.get("enabled", True), data.get("name", "Alarm"))

    def __eq__(self, other):
        """Two alarms are equal if their time and name are the same."""
        if not isinstance(other, Alarm):
            return NotImplemented
        return self.hour == other.hour and self.minute == other.minute and self.name == other.name

    def __hash__(self):
        """Generate a hash for the alarm, useful for set operations."""
        return hash((self.hour, self.minute, self.name))

    def __str__(self):
        """String representation for display."""
        status = " (Enabled)" if self.enabled else " (Disabled)"
        return f"{self.hour:02d}:{self.minute:02d} - {self.name}{status}"


# --- Helper Functions ---
def ping_host(host, timeout=1):
    """
    Pings a host using ping3 if available, otherwise falls back to system ping.
    Returns the response time in milliseconds or None if failed.
    """
    if ping3:
        try:
            # ping3.ping can return False or None for failures
            response = ping3.ping(host, timeout=timeout, unit='ms')
            if isinstance(response, (int, float)) and response > 0:
                return response
        except Exception:
            pass # Fallback to subprocess 

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
            else: # Linux/macOS
                match = re.search(r'time=(\d+\.?\d*)\s*ms', result.stdout)

            if match:
                return float(match.group(1))
            return 1.0  # Default successful response if time isn't parsed
        else:
            return None
    except Exception:
        return None

# --- Sound Management ---
class SoundManager(QObject):
    """Manages playing system sounds in a separate thread."""
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
        """Plays a sound asynchronously."""
        if sound_type == "error":
            threading.Thread(target=self._play_sound, args=(self.error_sound, False), daemon=True).start()
        elif sound_type == "alarm":
            if not self._alarm_thread or not self._alarm_thread.is_alive():
                self._stop_requested.clear()
                self._alarm_thread = threading.Thread(target=self._play_sound, args=(self.alarm_sound, True), daemon=True)
                self._alarm_thread.start()

    def _play_sound(self, sound_file, loop=False):
        """Internal sound playing logic."""
        if platform.system().lower() == "windows" and winsound:
            try:
                if not os.path.exists(sound_file):
                    print(f"Sound file not found: {sound_file}. Playing default.")
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    return

                if loop:
                    while not self._stop_requested.is_set():
                        winsound.PlaySound(sound_file, winsound.SND_FILENAME)
                        time.sleep(0.1) # Small pause
                else:
                    winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)

            except Exception as e:
                print(f"Error playing sound: {e}")
        else:
            print(f"Non-Windows system or winsound not available. Sound: {sound_file}, Loop: {loop}")


    def stop_alarm(self):
        """Stops the looping alarm sound."""
        self._stop_requested.set()
        if platform.system().lower() == "windows" and winsound:
            winsound.PlaySound(None, winsound.SND_PURGE) # Stop all sounds


# --- Worker Threads ---
class PingThread(QThread):
    """Thread for continuously pinging the DNS server."""
    update_signal = pyqtSignal(str, bool) # Message, is_success
    status_signal = pyqtSignal(str, str)  # Status message, CSS class

    def __init__(self, sound_manager):
        super().__init__()
        self.running = True
        self.last_success_time = time.time()
        self.sound_manager = sound_manager
        self.consecutive_errors = 0
        self.max_errors_before_sound = 3

    def run(self):
        while self.running:
            response = ping_host(DNS_SERVER, timeout=PING_TIMEOUT)
            now_str = datetime.now().strftime('%H:%M:%S')

            if response is not None:
                self.consecutive_errors = 0
                self.last_success_time = time.time()
                msg = f"[{now_str}] ✅ {('Successful' if english_language else 'Uğurlu')} → {response:.1f} ms"
                status_msg = f"🟢 {('Internet: Good' if english_language else 'İnternet: Yaxşı')}"
                self.status_signal.emit(status_msg, "status-good")
                self.update_signal.emit(msg, True)
            else:
                self.consecutive_errors += 1
                elapsed = time.time() - self.last_success_time
                msg = f"[{now_str}] ❌ {('Failed' if english_language else 'Uğursuz')} → Timeout ({elapsed:.1f}s)"
                self.update_signal.emit(msg, False)
                if self.consecutive_errors >= self.max_errors_before_sound:
                    status_msg = f"🔴 {('Internet: Poor' if english_language else 'İnternet: Zəif')}"
                    self.status_signal.emit(status_msg, "status-error")
                    self.sound_manager.play("error")

            time.sleep(PING_INTERVAL)

    def stop(self):
        self.running = False
        self.wait()


class AlarmThread(QThread):
    """Thread for monitoring and triggering alarms."""
    alarm_signal = pyqtSignal(str) # Alarm message

    def __init__(self, sound_manager):
        super().__init__()
        self.running = True
        self.sound_manager = sound_manager
        self.triggered_today = set() # Stores (hour, minute) of alarms already triggered today

    def run(self):
        global active_alarm_ringing
        while self.running:
            now = datetime.now()
            # Reset daily triggers at midnight
            if now.hour == 0 and now.minute == 0 and self.triggered_today:
                self.triggered_today.clear()

            # Iterate over a copy to allow modification
            for alarm_timestamp in active_alarm_timestamps[:]:
                alarm_time = datetime.fromtimestamp(alarm_timestamp)
                
                # Check if it's time and if it hasn't been triggered for this minute yet
                # We also check if the alarm_time is in the past, accounting for possible small delays.
                # It should trigger only once per minute for a given alarm.
                if now.hour == alarm_time.hour and \
                   now.minute == alarm_time.minute and \
                   (alarm_time.hour, alarm_time.minute) not in self.triggered_today:
                    
                    active_alarm_ringing = True
                    self.triggered_today.add((alarm_time.hour, alarm_time.minute))
                    
                    alarm_msg = f"🚨 {('Alarm is ringing!' if english_language else 'Zəngli Saat İşləyir!')}"
                    self.alarm_signal.emit(alarm_msg)
                    self.sound_manager.play("alarm")
                    # We don't remove the timestamp, allowing reschedule logic to handle it
            time.sleep(1)

    def stop(self):
        self.running = False
        self.wait()

# --- Settings Dialog ---
class SettingsDialog(QDialog):
    """A dialog for managing application settings."""
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings" if english_language else "Ayarlar")
        self.setWindowIcon(QIcon('icon.png'))
        self.setGeometry(500, 400, 650, 550)
        self.init_ui()
        self.apply_theme_to_dialog()

    def init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(10)

        # DNS Server
        self.dns_input = QLineEdit(DNS_SERVER)
        layout.addRow(QLabel("DNS/IP Server:"), self.dns_input)

        # Ping Interval
        self.ping_interval_spin = QSpinBox()
        self.ping_interval_spin.setMinimum(1); self.ping_interval_spin.setMaximum(60); self.ping_interval_spin.setValue(PING_INTERVAL)
        layout.addRow(QLabel(f"{('Ping Interval (s):' if english_language else 'Ping Aralığı (s):')}"), self.ping_interval_spin)

        # Ping Timeout
        self.ping_timeout_spin = QSpinBox()
        self.ping_timeout_spin.setMinimum(1); self.ping_timeout_spin.setMaximum(10); self.ping_timeout_spin.setValue(PING_TIMEOUT)
        layout.addRow(QLabel(f"{('Ping Timeout (s):' if english_language else 'Ping Zaman Aşımı (s):')}"), self.ping_timeout_spin)
        
        # Language
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", True)
        self.language_combo.addItem("Azərbaycanca", False)
        self.language_combo.setCurrentIndex(0 if english_language else 1)
        layout.addRow(QLabel("Language:" if english_language else "Dil:"), self.language_combo)

        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light", False)
        self.theme_combo.addItem("Dark", True)
        self.theme_combo.setCurrentIndex(1 if dark_mode else 0)
        layout.addRow(QLabel("Theme:" if english_language else "Mövzu:"), self.theme_combo)

        # Sound file buttons
        self.error_sound_label = QLabel(os.path.basename(ERROR_SOUND_FILE))
        change_error_sound_btn = QPushButton("Browse..." if english_language else "Gözat...")
        change_error_sound_btn.clicked.connect(self._select_error_sound)
        error_sound_layout = QHBoxLayout(); error_sound_layout.addWidget(self.error_sound_label); error_sound_layout.addWidget(change_error_sound_btn)
        layout.addRow(QLabel("Error Sound:" if english_language else "Xəta Səsi:"), error_sound_layout)

        self.alarm_sound_label = QLabel(os.path.basename(ALARM_SOUND_FILE))
        change_alarm_sound_btn = QPushButton("Browse..." if english_language else "Gözat...")
        change_alarm_sound_btn.clicked.connect(self._select_alarm_sound)
        alarm_sound_layout = QHBoxLayout(); alarm_sound_layout.addWidget(self.alarm_sound_label); alarm_sound_layout.addWidget(change_alarm_sound_btn)
        layout.addRow(QLabel("Alarm Sound:" if english_language else "Alarm Səsi:"), alarm_sound_layout)
        
        # Save button
        save_button = QPushButton("Save" if english_language else "Yadda Saxla")
        save_button.clicked.connect(self.save_settings)
        layout.addRow(save_button)

        self.setLayout(layout)

    def apply_theme_to_dialog(self):
        style = ""
        if dark_mode:
            style = """
                QDialog { background-color: #353535; }
                QLabel, QCheckBox { color: white; }
                QLineEdit, QSpinBox, QComboBox, QTimeEdit {
                    background-color: #252525; border: 1px solid #444; color: white; padding: 5px;
                }
                QPushButton {
                    background-color: #555; color: white; border: 1px solid #666;
                    padding: 5px; border-radius: 4px;
                }
                QPushButton:hover { background-color: #666; }
                QPushButton:pressed { background-color: #444; }
            """
        else: # Light mode
            style = """
                QDialog { background-color: #f0f0f0; }
                QLabel, QCheckBox { color: black; }
                QLineEdit, QSpinBox, QComboBox, QTimeEdit {
                    background-color: white; border: 1px solid #ccc; color: black; padding: 5px;
                }
                QPushButton {
                    background-color: #f0f0f0; border: 1px solid #ccc;
                    padding: 5px; border-radius: 4px;
                }
                QPushButton:hover { background-color: #e0e0e0; }
                QPushButton:pressed { background-color: #d0d0d0; }
            """
        self.setStyleSheet(style)


    def _select_sound(self, label_widget, sound_type):
        title = f"Select {sound_type.capitalize()} Sound" if english_language else f"{sound_type.capitalize()} Səsi Seçin"
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
        global DNS_SERVER, PING_INTERVAL, PING_TIMEOUT, dark_mode, english_language, ERROR_SOUND_FILE, ALARM_SOUND_FILE

        DNS_SERVER = self.dns_input.text() or "8.8.8.8"
        PING_INTERVAL = self.ping_interval_spin.value()
        PING_TIMEOUT = self.ping_timeout_spin.value()
        english_language = self.language_combo.currentData()
        dark_mode = self.theme_combo.currentData()
        ERROR_SOUND_FILE = self.parent().sound_manager.error_sound
        ALARM_SOUND_FILE = self.parent().sound_manager.alarm_sound
        
        self.settings_changed.emit()
        self.accept()


# --- Main Application Window ---
class PingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.sound_manager = SoundManager()
        self.managed_alarms = [] # This holds Alarm objects
        self.load_config() # Load before UI 

        self.ping_thread = PingThread(self.sound_manager)
        self.alarm_thread = AlarmThread(self.sound_manager)

        self.init_ui()
        self.init_threads_and_timers()

        self.load_alarms_data()
        self.update_alarm_list_ui()
        self.reschedule_all_alarms()
        
        self.create_menu_bar()
        self.create_tray_icon()
        self.retranslate_ui() # Set initial text based on loaded language
        self.apply_theme() # Apply theme based on loaded config

    def init_ui(self):
        """Initializes the main UI layout and widgets."""
        self.setWindowTitle("🚀 DNS Ping & Alarm Monitor")
        # Increase dimensions by 2.5 times
        self.original_width = 600
        self.original_height = 400
        self.setGeometry(1000, 200, int(self.original_width * 2.5), int(self.original_height * 2.5))
        self.setWindowIcon(QIcon('icon.png'))

        main_layout = QVBoxLayout(self)
        self.main_frame = QFrame()
        grid = QGridLayout(self.main_frame)

        # --- Ping Panel ---
        ping_panel = self.create_ping_panel()
        grid.addWidget(ping_panel, 0, 0)

        # --- Alarm Panel ---
        alarm_panel = self.create_alarm_panel()
        grid.addWidget(alarm_panel, 0, 1)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        main_layout.addWidget(self.main_frame)
        self.setLayout(main_layout)

    def create_ping_panel(self):
        """Creates the left panel for ping monitoring."""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)

        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)

        self.connection_status = QLabel()
        self.connection_status.setObjectName("ConnectionStatus")
        self.connection_status.setFont(QFont("Arial", 12))
        
        self.target_label = QLabel()
        self.target_label.setFont(QFont("Arial", 10))
        
        # Ping results list
        self.ping_result_list = QListWidget()
        self.ping_result_list.setObjectName("PingResultList")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.connection_status)
        layout.addWidget(self.target_label)
        layout.addWidget(self.ping_result_list)
        return panel

    def create_alarm_panel(self):
        """Creates the right panel for clock and alarms."""
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)

        # Clock
        self.clock_title = QLabel()
        self.clock_title.setFont(QFont("Arial", 20, QFont.Bold))
        self.clock_title.setAlignment(Qt.AlignCenter)
        self.current_time_label = QLabel()
        self.current_time_label.setObjectName("CurrentTimeLabel")
        # Increase clock font size for larger window
        self.current_time_label.setFont(QFont("Segoe UI", 36 * 2, QFont.Bold)) 
        self.current_time_label.setAlignment(Qt.AlignCenter)

        # Alarm Status
        self.alarm_status = QLabel()
        self.alarm_status.setObjectName("AlarmStatus")
        self.alarm_status.setFont(QFont("Arial", 14, QFont.Bold))
        self.alarm_status.setAlignment(Qt.AlignCenter)
        self.stop_alarm_btn = QPushButton()
        self.stop_alarm_btn.clicked.connect(self.stop_alarm_sound)
        self.stop_alarm_btn.setVisible(False)

        # Alarm Management
        self.daily_alarms_title = QLabel()
        self.daily_alarms_title.setFont(QFont("Arial", 16, QFont.Bold))
        self.managed_alarms_list = QListWidget()
        self.managed_alarms_list.setSelectionMode(QListWidget.ExtendedSelection) # Allow multi-select 
        # Connect item click to toggle alarm enabled status
        self.managed_alarms_list.itemClicked.connect(self.toggle_alarm_enabled)


        # Management Buttons
        alarm_btn_layout = QHBoxLayout()
        self.add_new_alarm_btn = QPushButton()
        self.add_new_alarm_btn.clicked.connect(self.add_new_alarm)
        self.delete_selected_alarm_btn = QPushButton()
        self.delete_selected_alarm_btn.clicked.connect(self.delete_selected_alarm)
        self.save_managed_alarms_btn = QPushButton()
        self.save_managed_alarms_btn.clicked.connect(self.save_alarms_data)
        alarm_btn_layout.addWidget(self.add_new_alarm_btn)
        alarm_btn_layout.addWidget(self.delete_selected_alarm_btn)
        alarm_btn_layout.addWidget(self.save_managed_alarms_btn)
        
        layout.addWidget(self.clock_title)
        layout.addWidget(self.current_time_label)
        layout.addWidget(self.alarm_status)
        layout.addWidget(self.stop_alarm_btn)
        layout.addSpacing(20)
        layout.addWidget(self.daily_alarms_title)
        layout.addWidget(self.managed_alarms_list)
        layout.addLayout(alarm_btn_layout)

        return panel

    def init_threads_and_timers(self):
        """Connects signals and starts all background processes."""
        # Timer for the main clock
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

        # Ping thread signals
        self.ping_thread.update_signal.connect(self.update_ping_display)
        self.ping_thread.status_signal.connect(self.update_connection_status)
        self.ping_thread.start()

        # Alarm thread signals
        self.alarm_thread.alarm_signal.connect(self.on_alarm_ring)
        self.alarm_thread.start()
        
    def create_tray_icon(self):
        """Sets up the system tray icon and its menu."""
        self.tray_icon = QSystemTrayIcon(QIcon('icon.png'), self)
        self.tray_icon.setVisible(True)
        self.tray_icon.activated.connect(self.restore_from_tray)
        self.set_tray_menu()

    def set_tray_menu(self):
        """Creates or updates the tray icon's context menu."""
        tray_menu = QMenu()
        restore_action = QAction("Show" if english_language else "Göstər", self, triggered=self.showNormal)
        quit_action = QAction("Quit" if english_language else "Çıxış", self, triggered=self.close)
        tray_menu.addAction(restore_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)

    def restore_from_tray(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event):
        """Handles the window close event."""
        reply = QMessageBox.question(self, 
                                     "Quit?" if english_language else "Çıxmaq?",
                                     "Quit the application?" if english_language else "Proqramdan çıxılsın?",
                                     QMessageBox.Yes | QMessageBox.Cancel, 
                                     QMessageBox.Yes)
        
        if reply == QMessageBox.Yes: # Minimize 
            self.shutdown()
            event.accept()
        else: # Cancel
            event.ignore()

    def shutdown(self):
        """Properly saves data and stops threads before quitting."""
        self.save_config()
        self.save_alarms_data()
        self.ping_thread.stop()
        self.alarm_thread.stop()
        self.tray_icon.hide()

    def load_config(self):
        """Loads settings from config.json."""
        global DNS_SERVER, PING_TIMEOUT, PING_INTERVAL, dark_mode, english_language, ERROR_SOUND_FILE, ALARM_SOUND_FILE
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                DNS_SERVER = config.get('dns_server', DNS_SERVER)
                PING_TIMEOUT = config.get('ping_timeout', PING_TIMEOUT)
                PING_INTERVAL = config.get('ping_interval', PING_INTERVAL)
                dark_mode = config.get('dark_mode', dark_mode)
                english_language = config.get('english_language', english_language)
                ERROR_SOUND_FILE = config.get('error_sound_file', ERROR_SOUND_FILE)
                ALARM_SOUND_FILE = config.get('alarm_sound_file', ALARM_SOUND_FILE)
                self.sound_manager.error_sound = ERROR_SOUND_FILE
                self.sound_manager.alarm_sound = ALARM_SOUND_FILE
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        """Saves current settings to config.json."""
        config = {
            'dns_server': DNS_SERVER, 'ping_timeout': PING_TIMEOUT,
            'ping_interval': PING_INTERVAL, 'dark_mode': dark_mode,
            'english_language': english_language, 'error_sound_file': ERROR_SOUND_FILE,
            'alarm_sound_file': ALARM_SOUND_FILE,
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def load_alarms_data(self):
        """Loads managed alarms from config.json."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                alarms_data = config.get('managed_alarms', [])
                self.managed_alarms = [Alarm.from_dict(d) for d in alarms_data]
            
            # If no alarms loaded, set default automatic alarms
            if not self.managed_alarms:
                self.managed_alarms.append(Alarm(9, 0, True, "Morning Alarm"))
                self.managed_alarms.append(Alarm(11, 0, True, "Lunch Reminder"))
                self.managed_alarms.append(Alarm(14, 0, True, "Afternoon Break"))
                self.managed_alarms.append(Alarm(17, 0, True, "End of Day"))
                self.save_alarms_data() # Save these new default alarms
        except Exception as e:
            QMessageBox.warning(self, "Alarm Load Error", f"Failed to load alarms: {e}")

    def save_alarms_data(self):
        """Saves the list of managed alarms to config.json."""
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f: config = json.load(f)
            
            config['managed_alarms'] = [alarm.to_dict() for alarm in self.managed_alarms]

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print("Alarms saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Alarm Save Error", f"Could not save alarms: {e}")

    def create_menu_bar(self):
        menubar = QMenuBar(self)
        self.layout().setMenuBar(menubar)
        settings_menu = menubar.addMenu("&Settings" if english_language else "&Ayarlar")
        
        open_settings_action = QAction("Open Settings", self, triggered=self.show_settings_dialog)
        settings_menu.addAction(open_settings_action)
        settings_menu.addSeparator()
        exit_action = QAction("Exit", self, triggered=self.close)
        settings_menu.addAction(exit_action)

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.handle_settings_changed)
        dialog.exec_()

    def handle_settings_changed(self):
        self.apply_theme()
        self.retranslate_ui()
        # Restart ping thread to apply new settings
        self.ping_thread.stop()
        self.ping_thread = PingThread(self.sound_manager)
        self.ping_thread.update_signal.connect(self.update_ping_display)
        self.ping_thread.status_signal.connect(self.update_connection_status)
        self.ping_thread.start()
        self.save_config()

    def retranslate_ui(self):
        """Updates all UI text based on the current language."""
        self.setWindowTitle("🚀 DNS Ping & Alarm Monitor")
        # Menubar
        self.layout().menuBar().actions()[0].setText("&Settings" if english_language else "&Ayarlar")
        self.layout().menuBar().actions()[0].menu().actions()[0].setText("Open Settings" if english_language else "Ayarları Aç")
        self.layout().menuBar().actions()[0].menu().actions()[2].setText("Exit" if english_language else "Çıxış")

        # Ping panel
        self.title_label.setText("📡 DNS Ping Monitor" if english_language else "📡 DNS Ping Monitoru")
        self.connection_status.setText("Searching..." if english_language else "Axtarılır...")
        self.target_label.setText(f"🎯 Target: {DNS_SERVER}" if english_language else f"🎯 Hədəf: {DNS_SERVER}")

        # Alarm panel
        self.clock_title.setText("🕐 CLOCK" if english_language else "🕐 SAAT")
        self.alarm_status.setText("💤 No active alarms" if english_language else "💤 Aktiv alarm yoxdur")
        self.stop_alarm_btn.setText("🚨 STOP ALARM" if english_language else "🚨 ZƏNGİ DAYANDIR")
        self.daily_alarms_title.setText("⏰ ALARM MANAGEMENT" if english_language else "⏰ ALARM İDARƏETMƏSİ")
        self.add_new_alarm_btn.setText("Add New" if english_language else "Yeni Əlavə Et")
        self.delete_selected_alarm_btn.setText("Delete Selected" if english_language else "Seçilmişləri Sil")
        self.save_managed_alarms_btn.setText("Save Alarms" if english_language else "Alarmları Saxla")
        
        self.set_tray_menu()
        self.update_alarm_list_ui()

    def apply_theme(self):
        """Applies the selected light or dark theme."""
        light_style = """
            QWidget { background-color: #f0f0f0; color: black; }
            QFrame { background-color: #ffffff; border-radius: 8px; }
            QLabel { color: black; background-color: transparent; }
            QLabel#ConnectionStatus[class="status-good"] { color: #008800; }
            QLabel#ConnectionStatus[class="status-error"] { color: #D32F2F; }
            QLabel#AlarmStatus[ringing="true"] { color: #D32F2F; }
            QListWidget { background-color: #f8f8f8; border: 1px solid #ccc; }
            QListWidget::item:selected { background-color: #a8d8ff; color: black; }
            QPushButton { background-color: #e0e0e0; border: 1px solid #ccc; border-radius: 4px; padding: 5px; }
            QPushButton:hover { background-color: #d0d0d0; }
            QMenuBar { background-color: #e0e0e0; }
            QMenuBar::item:selected { background-color: #c0c0c0; }
            QMenu { background-color: #f0f0f0; border: 1px solid #ccc; }
            QMenu::item:selected { background-color: #a8d8ff; }
        """
        dark_style = """
            QWidget { background-color: #2b2b2b; color: #e0e0e0; }
            QFrame { background-color: #3c3c3c; border-radius: 8px; }
            QLabel { color: #e0e0e0; background-color: transparent; }
            QLabel#ConnectionStatus[class="status-good"] { color: #4CAF50; }
            QLabel#ConnectionStatus[class="status-error"] { color: #FF6347; }
            QLabel#AlarmStatus[ringing="true"] { color: #FF6347; }
            QListWidget { background-color: #3a3a3a; border: 1px solid #555; color: #e0e0e0; }
            QListWidget::item { color: #e0e0e0; }
            QListWidget::item:selected { background-color: #5e5e5e; color: #ffffff; }
            QListWidget::item:selected:!active { background-color: #5e5e5e; }
            QListWidget::item:selected:active { background-color: #5e5e5e; }
            QPushButton { background-color: #505050; border: 1px solid #666; border-radius: 4px; padding: 5px; color: #e0e0e0; }
            QPushButton:hover { background-color: #606060; }
            QMenuBar { background-color: #3c3c3c; color: #e0e0e0; }
            QMenuBar::item:selected { background-color: #505050; }
            QMenu { background-color: #3c3c3c; border: 1px solid #555; }
            QMenu::item { color: #e0e0e0; }
            QMenu::item:selected { background-color: #505050; }
        """
        self.setStyleSheet(dark_style if dark_mode else light_style)
        # Apply style to menubar explicitly, as it might not inherit from QWidget
        if self.layout() and self.layout().menuBar():
            self.layout().menuBar().setStyleSheet("QMenuBar { background-color: #3c3c3c; color: #e0e0e0; }" if dark_mode else "QMenuBar { background-color: #e0e0e0; color: black; }")

    def update_clock(self):
        """Updates the current time display."""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.current_time_label.setText(current_time)

    def update_ping_display(self, message, is_success):
        """Adds a new ping result to the list."""
        item = QListWidgetItem(message)
        if not is_success:
            item.setForeground(QColor("red") if dark_mode else QColor("darkred"))
        else:
            item.setForeground(QColor("green") if dark_mode else QColor("darkgreen"))
        self.ping_result_list.addItem(item)
        self.ping_result_list.scrollToBottom()

    def update_connection_status(self, message, css_class):
        """Updates the connection status label."""
        self.connection_status.setText(message)
        self.connection_status.setProperty("class", css_class)
        self.style().polish(self.connection_status) # Reapply stylesheet to update class

    def on_alarm_ring(self, message):
        """Handles an alarm ringing event."""
        global active_alarm_ringing
        self.alarm_status.setText(message)
        self.alarm_status.setProperty("ringing", "true")
        self.style().polish(self.alarm_status)
        self.stop_alarm_btn.setVisible(True)
        # Bring app to front if minimized when alarm rings
        if self.isMinimized():
            self.showNormal()
        self.activateWindow()
        self.raise_()

    def stop_alarm_sound(self):
        """Stops the alarm sound and resets UI status."""
        global active_alarm_ringing
        self.sound_manager.stop_alarm()
        active_alarm_ringing = False
        self.alarm_status.setText("💤 No active alarms" if english_language else "💤 Aktiv alarm yoxdur")
        self.alarm_status.setProperty("ringing", "false")
        self.style().polish(self.alarm_status)
        self.stop_alarm_btn.setVisible(False)

    def update_alarm_list_ui(self):
        """Refreshes the displayed list of managed alarms."""
        self.managed_alarms_list.clear()
        for alarm in self.managed_alarms:
            item = QListWidgetItem(str(alarm))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable) # Make it checkable
            item.setCheckState(Qt.Checked if alarm.enabled else Qt.Unchecked)
            # Store the actual Alarm object in the QListWidgetItem for easy retrieval
            item.setData(Qt.UserRole, alarm) 
            self.managed_alarms_list.addItem(item)
        self.reschedule_all_alarms()

    def add_new_alarm(self):
        """Opens a dialog to add a new alarm."""
        text, ok = QInputDialog.getText(self, "New Alarm Name" if english_language else "Yeni Alarm Adı", 
                                       "Enter alarm name:" if english_language else "Alarm adını daxil edin:")
        if not ok or not text:
            return

        time_dialog = QDialog(self)
        time_dialog.setWindowTitle("Set Alarm Time" if english_language else "Alarm Vaxtını Ayarla")
        time_layout = QVBoxLayout(time_dialog)
        time_edit = QTimeEdit(QTime.currentTime())
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setFont(QFont("Arial", 24))
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(time_dialog.accept)
        time_layout.addWidget(QLabel("Select time:" if english_language else "Vaxtı seçin:"))
        time_layout.addWidget(time_edit)
        time_layout.addWidget(ok_button)

        if time_dialog.exec_() == QDialog.Accepted:
            selected_time = time_edit.time()
            new_alarm = Alarm(selected_time.hour(), selected_time.minute(), True, text)
            
            # Avoid adding duplicate alarms (by time and name)
            if new_alarm not in self.managed_alarms:
                self.managed_alarms.append(new_alarm)
                self.update_alarm_list_ui()
                self.save_alarms_data()
            else:
                QMessageBox.warning(self, "Duplicate Alarm", "An alarm with this time and name already exists." if english_language else "Bu vaxt və adla bir alarm artıq mövcuddur.")

    def delete_selected_alarm(self):
        """Deletes selected alarms from the list."""
        selected_items = self.managed_alarms_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select at least one alarm to delete." if english_language else "Zəhmət olmasa silmək üçün ən azı bir alarm seçin.")
            return

        reply = QMessageBox.question(self, 
                                     "Confirm Deletion" if english_language else "Silməyi Təsdiqlə",
                                     f"Are you sure you want to delete {len(selected_items)} selected alarm(s)?" if english_language else f"Seçilmiş {len(selected_items)} alarmı silmək istədiyinizə əminsiniz?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # Create a list of alarms to remove from managed_alarms
            alarms_to_remove = [item.data(Qt.UserRole) for item in selected_items]
            
            # Remove from managed_alarms list
            self.managed_alarms = [alarm for alarm in self.managed_alarms if alarm not in alarms_to_remove]
            
            self.update_alarm_list_ui() # Refresh the UI
            self.save_alarms_data()
            self.reschedule_all_alarms() # Reschedule remaining alarms

    def toggle_alarm_enabled(self, item):
        """Toggles the enabled status of an alarm when its checkbox is clicked."""
        alarm = item.data(Qt.UserRole)
        if alarm:
            alarm.enabled = item.checkState() == Qt.Checked
            # Update the display text to reflect the enabled/disabled state
            item.setText(str(alarm)) 
            self.save_alarms_data()
            self.reschedule_all_alarms()

    def reschedule_all_alarms(self):
        """Recalculates and updates the global active_alarm_timestamps list."""
        global active_alarm_timestamps
        active_alarm_timestamps.clear()
        now = datetime.now()
        for alarm in self.managed_alarms:
            if alarm.enabled:
                # Set alarm for today
                alarm_dt_today = now.replace(hour=alarm.hour, minute=alarm.minute, second=0, microsecond=0)
                
                # If the alarm time has already passed for today, schedule it for tomorrow
                if alarm_dt_today <= now:
                    alarm_dt_today += timedelta(days=1)
                
                active_alarm_timestamps.append(alarm_dt_today.timestamp())
        
        # Sort timestamps to process them in order
        active_alarm_timestamps.sort()
        print(f"Rescheduled alarms. Next alarms: {[datetime.fromtimestamp(ts).strftime('%H:%M') for ts in active_alarm_timestamps]}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check if 'icon.png' exists, if not, create a dummy one
    if not os.path.exists('icon.png'):
        try:
            from PIL import Image
            img = Image.new('RGB', (16, 16), color = 'red')
            img.save('icon.png')
            print("Created a dummy 'icon.png'.")
        except ImportError:
            print("Pillow not found. Please install Pillow (pip install Pillow) or provide 'icon.png' for the icon to display correctly.")

    # Check for default sound files and create dummy ones if missing
    for sound_file in [ERROR_SOUND_FILE, ALARM_SOUND_FILE]:
        if not os.path.exists(sound_file):
            print(f"Warning: {sound_file} not found. Sound alerts might not work as expected.")
            # Optional: create a silent dummy file or inform the user
            # You might want to create a simple silent .wav or just rely on the 'winsound.SND_ALIAS' fallback
            # For simplicity, we'll just print a warning for now.

    ex = PingApp()
    ex.show()
    sys.exit(app.exec_())