# 🚀 DNS Ping & Alarm Monitor

A modern cross-platform desktop application that monitors your internet connection by pinging a DNS server **and** manages customizable daily alarms — built with Python and PyQt5.

## ✨ Features

✅ **DNS Ping Monitor**  
- Real-time ping to your chosen DNS or IP server  
- Displays response times with color-coded success/failure  
- Plays an error sound if the connection becomes unstable

⏰ **Alarm Manager**  
- Create, delete, and enable/disable daily alarms  
- Each alarm can have its own name and time  
- Alarm sound plays in a loop until stopped

⚙ **Settings & Customization**  
- Choose target DNS/IP, ping interval & timeout  
- Light or dark theme support  
- Switch between English and Azerbaijani languages  
- Change alarm and error sound files

🖥 **System Tray & Auto Minimize**  
- Runs quietly in the system tray  
- Double-click to restore the window  
- Confirmation on exit

📦 **Configurable & Persistent**  
- Automatically saves and loads settings & alarms from `config.json`  
- Default alarms are created on first run if none exist

## 🛠 Installation

> **Requires Python 3.8+**

```bash
pip install PyQt5 ping3 Pillow
python main.py
```

## ⚙ Configuration
All settings (DNS server, theme, language, alarm list, etc.) are saved to config.json automatically.

If icon.png, error.wav or alarm.wav are missing, the app will warn and may create dummy files.

## 📋 File Structure

| File          | Purpose                         |
| ------------- | ------------------------------- |
| `main.py`     | Main application code           |
| `config.json` | Stores user settings and alarms |
| `icon.png`    | App icon                        |
| `error.wav`   | Sound played on ping error      |
| `alarm.wav`   | Sound played when alarm rings   |

## 📸 Screenshots

## 💡 Notes
On Windows, sound playback uses the built-in winsound module.

On other systems, sound alerts print a message to the console (you can extend support using other libraries).