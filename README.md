# 🚀 DNS Ping & Alarm Monitor

A modern and user-friendly network connection monitoring and alarm application. Built with PyQt5, this application combines DNS ping monitoring and time-based alarm features in a single interface.

## ✨ Features

### 📡 DNS Ping Monitor
- **Real-time ping monitoring**: Continuously pings specified DNS server
- **Visual status indication**: Track connection status with color-coded indicators
- **History tracking**: View last 100 ping results
- **Customizable target**: Set any DNS server or IP address as target
- **Audio alerts**: Sound notifications for connection interruptions

### ⏰ Alarm Clock System
- **Digital clock**: Real-time date and time display
- **Custom alarms**: Set alarms for any desired time
- **Template alarms**: Daily routine alarms (09:00, 11:00, 14:00, 17:00, 19:00)
- **Customizable sounds**: Upload your own alarm sounds
- **Alarm control**: Stop active alarms feature

## 🛠️ Requirements

### Python Packages
```bash
pip install PyQt5 ping3
```

### System Requirements
- **Python 3.6+**
- **Windows**: winsound module (built-in)
- **Linux/macOS**: ping command-line tool

## 🚀 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/nicatbayram/gping.git
cd gping
```

2. **Install dependencies:**
```bash
pip install PyQt5 ping3
```

3. **Run the application:**
```bash
python main.py
```

## 📖 Usage

### DNS Ping Monitor
1. The application starts monitoring the default DNS server (8.8.8.8) automatically
2. **Change target server**: Click "Change DNS or IP" button to set a custom target
3. **Monitor results**: View real-time ping results and connection status
4. **Audio settings**: Click "Set Error Sound" to customize error notification sounds

### Alarm Clock
1. **Set custom alarm**: 
   - Enter hour and minute in the input fields
   - Click "SET ALARM" button
   - Alarm will be set for the next occurrence of that time
2. **Template alarms**: Pre-configured daily alarms activate automatically
3. **Stop alarm**: Click "STOP ALARM" button when alarm is ringing
4. **Custom alarm sound**: Click "SET ALARM SOUND" to upload your own sound file

## 🔧 Configuration

### Default Settings
- **Default DNS Server**: 8.8.8.8 (Google DNS)
- **Ping Timeout**: 1 second
- **Ping Interval**: 1 second
- **Template Alarms**: 09:00, 11:00, 14:00, 17:00, 19:00

### Sound Files
- Place `error.wav` and `alarm.wav` files in the application directory
- Supported formats: WAV, MP3 (Windows only for audio playback)

## 🖥️ Interface

The application features a dual-panel interface:

### Left Panel - Ping Monitor
- Real-time connection status indicator
- Current ping target display
- Live ping results with color coding
- Ping history list (last 100 results)
- Server change and sound configuration buttons

### Right Panel - Clock & Alarms
- Digital clock with date display
- Alarm setup controls
- Active alarm status
- Template alarms list
- Alarm control buttons

## 🎨 Features in Detail

### Status Indicators
- 🟢 **Good Connection**: Green indicator, successful pings
- 🔴 **Poor Connection**: Red indicator, failed pings
- 🟡 **Error**: Yellow indicator, system errors

### Alarm States
- 💤 **No Active Alarms**: Default state
- ✅ **Alarm Set**: Shows next alarm time
- 🚨 **Alarm Ringing**: Active alarm notification

## 🔊 Audio System

The application uses different audio systems based on the platform:
- **Windows**: Uses `winsound` module for audio playback
- **Linux/macOS**: Basic audio support (extensible)

## 🚨 Troubleshooting

### Common Issues

**Ping not working:**
- Check internet connection
- Verify target server accessibility
- Run as administrator (Windows) if needed

**Audio not playing:**
- Ensure sound files exist in application directory
- Check system audio settings
- Verify file format compatibility

**Application crashes:**
- Install all required dependencies
- Check Python version compatibility (3.6+)
- Verify PyQt5 installation


## 🙏 Acknowledgments

- PyQt5 framework for the GUI
- ping3 library for cross-platform ping functionality
- Google DNS (8.8.8.8) as default monitoring target

