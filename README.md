# 🖨️ Send Me a Message

A tiny web app that lets anyone on the internet send messages directly to my thermal receipt printer at home. Because why not?

![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)

## What is this?

Type a message → Click send → It prints on my desk. Magic! ✨

This is a simple Flask app with a beautiful dark UI that connects to a thermal printer via TCP. Messages appear on little receipt paper strips, complete with timestamp and sender IP.

## Features

- 📝 Clean, modern web interface
- 📱 PWA-ready (installable on phones)
- 🎨 Pretty gradient UI with glassmorphism
- 🧾 ESC/POS thermal printer support
- ⏰ Timestamps each message
- 🌐 Tracks visitor IP (from Cloudflare headers)

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Then open http://localhost:5000

## Configuration

Edit these lines in `app.py` to match your printer setup:

```python
PRINTER_HOST = "172.29.208.1"  # Your printer bridge IP
PRINTER_PORT = 9100            # Standard raw printing port
```

## How it works

```
[Web Browser] → [Flask App] → [TCP Socket] → [Printer Bridge] → [Thermal Printer]
                                                    ↑
                                          (Windows/Linux host)
```

The app sends ESC/POS commands over TCP to a print server or bridge that forwards to the thermal printer.

## License

Do whatever you want with it. Send me a message if you build something cool! 💌

---

Made with ♥ by [Paulo Fonseca](https://paulofonseca.com)
