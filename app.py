#!/usr/bin/env python3
"""
Thermal Printer Web App
A simple web interface to send messages to a thermal printer via TCP bridge.
Production-ready with rate limiting, print queue, and bot protection.
"""

import socket
import textwrap
import os
import json
import threading
import time
import queue
import atexit
from flask import Flask, render_template_string, request, flash, redirect, url_for
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import TextAreaField, StringField, HiddenField
from wtforms.validators import DataRequired, Length
from datetime import datetime

# =============================================================================
# Configuration
# =============================================================================

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# CSRF Protection
csrf = CSRFProtect(app)

# Printer settings
PRINTER_HOST = os.environ.get('PRINTER_HOST', '172.29.208.1')
PRINTER_PORT = int(os.environ.get('PRINTER_PORT', '9100'))

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_DIR = os.path.join(BASE_DIR, 'messages')
DATA_DIR = os.path.join(BASE_DIR, 'data')
RATE_LIMIT_FILE = os.path.join(DATA_DIR, 'rate_limits.json')
QUEUE_FILE = os.path.join(DATA_DIR, 'print_queue.json')

# Rate limiting
RATE_LIMIT_SECONDS = int(os.environ.get('RATE_LIMIT_SECONDS', '60'))

# Print queue settings
PRINT_DELAY_SECONDS = int(os.environ.get('PRINT_DELAY_SECONDS', '5'))

# Ensure directories exist
os.makedirs(MESSAGES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# =============================================================================
# Rate Limiting (File-based, persists across restarts)
# =============================================================================

rate_limit_lock = threading.Lock()


def load_rate_limits():
    """Load rate limits from file."""
    if os.path.exists(RATE_LIMIT_FILE):
        try:
            with open(RATE_LIMIT_FILE, 'r') as f:
                data = json.load(f)
                # Convert string timestamps back to datetime
                return {ip: datetime.fromisoformat(ts) for ip, ts in data.items()}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def save_rate_limits(limits):
    """Save rate limits to file."""
    # Convert datetime to ISO format strings
    data = {ip: ts.isoformat() for ip, ts in limits.items()}
    with open(RATE_LIMIT_FILE, 'w') as f:
        json.dump(data, f)


def check_rate_limit(visitor_ip):
    """Check if IP is rate limited. Returns (allowed, seconds_remaining)."""
    with rate_limit_lock:
        limits = load_rate_limits()
        now = datetime.now()

        # Clean old entries (older than rate limit)
        limits = {ip: ts for ip, ts in limits.items()
                  if (now - ts).total_seconds() < RATE_LIMIT_SECONDS}

        if visitor_ip in limits:
            time_since_last = (now - limits[visitor_ip]).total_seconds()
            if time_since_last < RATE_LIMIT_SECONDS:
                remaining = int(RATE_LIMIT_SECONDS - time_since_last)
                return False, remaining

        return True, 0


def record_submission(visitor_ip):
    """Record a successful submission for rate limiting."""
    with rate_limit_lock:
        limits = load_rate_limits()
        limits[visitor_ip] = datetime.now()
        save_rate_limits(limits)


# =============================================================================
# Print Queue (Background worker thread)
# =============================================================================

print_queue = queue.Queue()
queue_lock = threading.Lock()


def load_pending_queue():
    """Load any pending jobs from file (survives restarts)."""
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, 'r') as f:
                jobs = json.load(f)
                for job in jobs:
                    print_queue.put(job)
                # Clear the file after loading
                os.remove(QUEUE_FILE)
        except (json.JSONDecodeError, ValueError):
            pass


def save_pending_queue():
    """Save pending jobs to file (for graceful shutdown)."""
    jobs = []
    while not print_queue.empty():
        try:
            jobs.append(print_queue.get_nowait())
        except queue.Empty:
            break
    if jobs:
        with open(QUEUE_FILE, 'w') as f:
            json.dump(jobs, f)


def print_worker():
    """Background worker that processes the print queue."""
    while True:
        try:
            job = print_queue.get(timeout=1)
            if job is None:  # Shutdown signal
                break

            message = job['message']
            visitor_ip = job['visitor_ip']

            success, result = send_to_printer_internal(message, visitor_ip)
            if not success:
                print(f"[PrintQueue] Failed to print: {result}")
            else:
                print(f"[PrintQueue] Printed message from {visitor_ip}")

            print_queue.task_done()

            # Delay between prints to prevent printer overload
            time.sleep(PRINT_DELAY_SECONDS)

        except queue.Empty:
            continue
        except Exception as e:
            print(f"[PrintQueue] Worker error: {e}")


# Start worker thread
worker_thread = threading.Thread(target=print_worker, daemon=True)
worker_thread.start()

# Load any pending jobs from previous run
load_pending_queue()

# Save queue on shutdown
atexit.register(save_pending_queue)


def queue_print_job(message, visitor_ip):
    """Add a print job to the queue."""
    job = {
        'message': message,
        'visitor_ip': visitor_ip,
        'queued_at': datetime.now().isoformat()
    }
    print_queue.put(job)
    return print_queue.qsize()


# =============================================================================
# Form with Honeypot
# =============================================================================

class MessageForm(FlaskForm):
    """Form with honeypot field for bot detection."""
    message = TextAreaField('Message', validators=[
        DataRequired(message='Please enter a message!'),
        Length(max=240, message='Message too long (max 240 characters)')
    ])
    # Honeypot field - bots will fill this, humans won't see it
    website = StringField('Website')  # Named innocuously to trick bots


# =============================================================================
# HTML Template
# =============================================================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Send me a message</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

    <!-- Favicon and PWA -->
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#0a0a0a">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Send Message">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'JetBrains Mono', monospace;
            min-height: 100vh;
            background: #0a0a0a;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #fff;
        }

        .container {
            width: 100%;
            max-width: 500px;
        }

        .card {
            background: #0a0a0a;
            border: 1px solid #222;
            border-radius: 8px;
            padding: 32px;
        }

        .header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }

        .icon {
            font-size: 24px;
            filter: grayscale(100%);
        }

        h1 {
            color: #fff;
            font-size: 18px;
            font-weight: 500;
        }

        .subtitle {
            color: #666;
            font-size: 13px;
            margin-bottom: 32px;
            line-height: 1.6;
        }

        textarea {
            width: 100%;
            height: 140px;
            padding: 16px;
            background: #111;
            border: 1px solid #222;
            border-radius: 6px;
            font-size: 14px;
            font-family: 'JetBrains Mono', monospace;
            color: #fff;
            resize: none;
            transition: border-color 0.2s;
        }

        textarea::placeholder {
            color: #444;
        }

        textarea:focus {
            outline: none;
            border-color: #444;
        }

        .char-count {
            text-align: right;
            color: #444;
            font-size: 12px;
            margin-top: 8px;
            margin-bottom: 20px;
        }

        button {
            width: 100%;
            padding: 14px 20px;
            background: #fff;
            color: #000;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            font-family: 'JetBrains Mono', monospace;
            cursor: pointer;
            transition: all 0.2s;
        }

        button:hover {
            background: #ddd;
        }

        button:active {
            transform: scale(0.98);
        }

        .flash {
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-size: 13px;
        }

        .flash.success {
            background: #0a1a0a;
            border: 1px solid #1a3a1a;
            color: #4a4;
        }

        .flash.error {
            background: #1a0a0a;
            border: 1px solid #3a1a1a;
            color: #a44;
        }

        .footer {
            text-align: center;
            margin-top: 20px;
            color: #333;
            font-size: 12px;
        }

        .footer a {
            color: #444;
            text-decoration: none;
        }

        .footer a:hover {
            color: #666;
        }

        /* Honeypot field - hidden from humans */
        .hp-field {
            opacity: 0;
            position: absolute;
            top: 0;
            left: 0;
            height: 0;
            width: 0;
            z-index: -1;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <span class="icon">🖨️</span>
                <h1>send me a message</h1>
            </div>
            <p class="subtitle">and it will print on my thermal printer at home</p>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endwith %}

            <form method="POST" id="printForm">
                {{ form.hidden_tag() }}
                <textarea
                    name="message"
                    placeholder="type something..."
                    maxlength="240"
                    id="message"
                >{{ form.message.data or '' }}</textarea>
                <div class="char-count"><span id="count">0</span>/240</div>

                <!-- Honeypot field - invisible to humans, bots will fill it -->
                <div class="hp-field" aria-hidden="true">
                    <label for="website">Leave this empty</label>
                    <input type="text" name="website" id="website" tabindex="-1" autocomplete="off">
                </div>

                <button type="submit">print</button>
            </form>
        </div>

        <p class="footer">
            <a href="https://paulofonseca.com" target="_blank">paulofonseca.com</a>
        </p>
    </div>

    <script>
        const textarea = document.getElementById('message');
        const count = document.getElementById('count');

        textarea.addEventListener('input', function() {
            count.textContent = this.value.length;
        });

        count.textContent = textarea.value.length;
    </script>
</body>
</html>
'''


# =============================================================================
# Printer Functions
# =============================================================================

def save_message(message, visitor_ip):
    """Save a message to a markdown file with YAML frontmatter."""
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}.md"
    filepath = os.path.join(MESSAGES_DIR, filename)

    content = f"""---
from: {visitor_ip}
date: {now.strftime("%Y-%m-%d")}
time: {now.strftime("%H:%M:%S")}
---

{message}
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def send_to_printer_internal(message, visitor_ip):
    """Send a message to the thermal printer via TCP bridge."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((PRINTER_HOST, PRINTER_PORT))

        # ESC/POS commands for formatting
        INIT = b'\x1b\x40'  # Initialize printer
        LEFT = b'\x1b\x61\x00'  # Left align
        FEED = b'\r\n\r\n\r\n\r\n\r\n\r\n'  # Feed paper

        # Build the print job
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%B %d, %Y").replace(" 0", " ")

        # Wrap text to 48 characters (typical for 80mm thermal paper)
        wrapped_message = textwrap.fill(message, width=48)

        data = INIT
        data += b"\r\n"
        data += LEFT
        data += wrapped_message.encode('cp1252', errors='replace')
        data += b"\r\n\r\n"
        data += f"-- from {visitor_ip}\r\n".encode('cp1252')
        data += f"   at {time_str} of {date_str}\r\n".encode('cp1252')
        data += FEED

        sock.send(data)
        sock.close()
        return True, "Message sent to printer!"
    except socket.timeout:
        return False, "Connection timed out - is the printer bridge running?"
    except ConnectionRefusedError:
        return False, "Connection refused - is the printer bridge running?"
    except Exception as e:
        return False, f"Error: {str(e)}"


# =============================================================================
# Routes
# =============================================================================

@app.route('/manifest.json')
def manifest():
    return {
        "name": "Send me a message",
        "short_name": "Message",
        "description": "Send a message to Paulo's thermal printer",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0a0a",
        "theme_color": "#0a0a0a",
        "icons": [
            {
                "src": "/static/apple-touch-icon.png",
                "sizes": "180x180",
                "type": "image/png"
            },
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }


@app.route('/', methods=['GET', 'POST'])
def index():
    form = MessageForm()

    if request.method == 'POST':
        # Check honeypot field first
        honeypot = request.form.get('website', '')
        if honeypot:
            # Bot detected! Pretend success but do nothing
            flash('Message queued for printing!', 'success')
            return redirect(url_for('index'))

        if form.validate_on_submit():
            message = form.message.data.strip()
            visitor_ip = request.headers.get(
                'CF-Connecting-IP',
                request.headers.get('X-Forwarded-For', request.remote_addr)
            )

            # Check rate limit
            allowed, remaining = check_rate_limit(visitor_ip)
            if not allowed:
                flash(f'Please wait {remaining} seconds before sending another message', 'error')
                return render_template_string(HTML_TEMPLATE, form=form)

            # Queue the print job
            queue_position = queue_print_job(message, visitor_ip)
            record_submission(visitor_ip)
            save_message(message, visitor_ip)

            if queue_position == 1:
                flash('Message queued for printing!', 'success')
            else:
                flash(f'Message queued! Position in queue: {queue_position}', 'success')

            return redirect(url_for('index'))
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    flash(error, 'error')

    return render_template_string(HTML_TEMPLATE, form=form)


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    print(f"Starting Thermal Printer Web App")
    print(f"Printer bridge: {PRINTER_HOST}:{PRINTER_PORT}")
    print(f"Rate limit: {RATE_LIMIT_SECONDS} seconds")
    print(f"Print delay: {PRINT_DELAY_SECONDS} seconds between jobs")
    print(f"Open http://localhost:5000 in your browser")

    # Only use debug mode if explicitly set
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
