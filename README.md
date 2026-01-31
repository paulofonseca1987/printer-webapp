# Send Me a Message

A tiny web app that lets anyone on the internet send messages directly to my thermal receipt printer at home. Because why not?

![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
[![CC0](https://img.shields.io/badge/license-CC0-blue.svg)](https://creativecommons.org/publicdomain/zero/1.0/)

## What is this?

Type a message -> Click send -> It prints on my desk.

This is a simple Flask app with a minimal dark UI that connects to a thermal printer via TCP. Messages appear on little receipt paper strips, complete with timestamp and sender IP.

## Features

- Clean, modern web interface
- PWA-ready (installable on phones)
- ESC/POS thermal printer support
- Timestamps each message
- Tracks visitor IP (from Cloudflare headers)
- Rate limiting (60 seconds between messages)
- Message persistence (saved as markdown files)
- Print queue (prevents printer overload)
- Honeypot bot protection
- CSRF protection
- Production-ready with Gunicorn

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Run (development)
python app.py

# Run (production)
gunicorn -c gunicorn.conf.py app:app
```

Then open http://localhost:5000

## Configuration

Create a `.env` file (copy from `.env.example`):

```bash
# Generate a secure secret key
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Printer settings
PRINTER_HOST=172.29.208.1
PRINTER_PORT=9100

# Rate limiting (seconds)
RATE_LIMIT_SECONDS=60

# Delay between prints (seconds)
PRINT_DELAY_SECONDS=5
```

## How it works

```
[Browser] -> [Flask/Gunicorn] -> [Print Queue] -> [TCP Socket] -> [Printer Bridge] -> [Thermal Printer]
```

1. User submits a message
2. Honeypot + CSRF + rate limit checks
3. Message queued (queue position shown to user)
4. Background worker sends to printer with delays between jobs
5. Message saved to `messages/` directory

## Production Deployment

For public deployment, ensure:

1. **Set a strong SECRET_KEY** in `.env`
2. **Use Gunicorn** (not Flask's dev server): `gunicorn -c gunicorn.conf.py app:app`
3. **Put behind a reverse proxy** (nginx/Caddy) with HTTPS
4. **Consider Cloudflare** for DDoS protection (the app reads `CF-Connecting-IP` header)

## License

[CC0 1.0 Universal](LICENSE) - Public domain. Do whatever you want with it!

---

Made with love by [Paulo Fonseca](https://paulofonseca.com)
