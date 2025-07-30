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

<img width="400"  alt="Untitled" src="https://github.com/user-attachments/assets/6c52fdc6-bcf1-4706-a780-bf2b06493378" />
<img width="400"  alt="Untitled11" src="https://github.com/user-attachments/assets/deb0e5ee-e005-4934-bd55-a0cbc178e8e5" />
<img width="400" alt="Untitled2" src="https://github.com/user-attachments/assets/d2b9dc3d-f787-48ab-8abc-316db4c3ea64" />
<img width="400" alt="Untitled222png" src="https://github.com/user-attachments/assets/95c72116-efac-4b65-b1dd-634dd86d11b0" />


## 💡 Notes
On Windows, sound playback uses the built-in winsound module.

On other systems, sound alerts print a message to the console (you can extend support using other libraries).
