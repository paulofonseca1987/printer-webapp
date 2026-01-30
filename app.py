#!/usr/bin/env python3
"""
Thermal Printer Web App
A simple web interface to send messages to a thermal printer via TCP bridge.
"""

import socket
import textwrap
from flask import Flask, render_template_string, request, flash, redirect, url_for
from datetime import datetime

app = Flask(__name__, static_folder='static')
app.secret_key = 'change-this-to-something-random-in-production'

# Configuration - update this to your Windows bridge IP
PRINTER_HOST = "172.29.208.1"
PRINTER_PORT = 9100

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Send me a message</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Favicon and PWA -->
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1a1a2e">
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
            font-family: 'Space Grotesk', sans-serif;
            min-height: 100vh;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            width: 100%;
            max-width: 480px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        
        .icon {
            width: 64px;
            height: 64px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 24px;
            font-size: 28px;
        }
        
        h1 {
            color: #fff;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .subtitle {
            color: rgba(255, 255, 255, 0.5);
            font-size: 15px;
            margin-bottom: 32px;
            line-height: 1.5;
        }
        
        .form-group {
            margin-bottom: 24px;
        }
        
        textarea {
            width: 100%;
            height: 160px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            font-size: 16px;
            font-family: 'Space Grotesk', sans-serif;
            color: #fff;
            resize: none;
            transition: all 0.3s ease;
        }
        
        textarea::placeholder {
            color: rgba(255, 255, 255, 0.3);
        }
        
        textarea:focus {
            outline: none;
            border-color: #667eea;
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.15);
        }
        
        .char-count {
            text-align: right;
            color: rgba(255, 255, 255, 0.4);
            font-size: 13px;
            margin-top: 8px;
        }
        
        button {
            width: 100%;
            padding: 18px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            font-family: 'Space Grotesk', sans-serif;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px -10px rgba(102, 126, 234, 0.5);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        .flash {
            padding: 16px 20px;
            border-radius: 12px;
            margin-bottom: 24px;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .flash.success {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #6ee7b7;
        }
        
        .flash.error {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fca5a5;
        }
        
        .footer {
            text-align: center;
            margin-top: 24px;
            color: rgba(255, 255, 255, 0.3);
            font-size: 13px;
        }
        
        .footer a {
            color: rgba(255, 255, 255, 0.5);
            text-decoration: none;
            transition: color 0.2s;
        }
        
        .footer a:hover {
            color: #667eea;
        }
        
        .receipt-preview {
            background: #fff;
            color: #000;
            padding: 16px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            margin-top: 16px;
            display: none;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        
        .receipt-preview.show {
            display: block;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .sending button {
            animation: pulse 1.5s infinite;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="icon">🖨️</div>
            <h1>Send me a message</h1>
            <p class="subtitle">Type something nice and it will get automagically printed on my small receipt printer at home!</p>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">
                        {% if category == 'success' %}✓{% else %}⚠{% endif %}
                        {{ message }}
                    </div>
                {% endfor %}
            {% endwith %}
            
            <form method="POST" id="printForm">
                <div class="form-group">
                    <textarea 
                        name="message" 
                        placeholder="Write your message here..."
                        maxlength="240"
                        id="message"
                    >{{ request.form.get('message', '') }}</textarea>
                    <div class="char-count"><span id="count">0</span> / 240</div>
                </div>
                <button type="submit">
                    <span>Print Message</span>
                    <span>→</span>
                </button>
            </form>
        </div>
        
        <p class="footer">
            Made with ♥ by <a href="https://paulofonseca.com" target="_blank">Paulo Fonseca</a>
        </p>
    </div>
    
    <script>
        const textarea = document.getElementById('message');
        const count = document.getElementById('count');
        const form = document.getElementById('printForm');
        
        textarea.addEventListener('input', function() {
            count.textContent = this.value.length;
        });
        
        count.textContent = textarea.value.length;
        
        form.addEventListener('submit', function() {
            this.classList.add('sending');
        });
    </script>
</body>
</html>
'''

def send_to_printer(message, visitor_ip):
    """Send a message to the thermal printer via TCP bridge."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((PRINTER_HOST, PRINTER_PORT))
        
        # ESC/POS commands for formatting
        INIT = b'\x1b\x40'  # Initialize printer
        CENTER = b'\x1b\x61\x01'  # Center align
        LEFT = b'\x1b\x61\x00'  # Left align
        BOLD_ON = b'\x1b\x45\x01'  # Bold on
        BOLD_OFF = b'\x1b\x45\x00'  # Bold off
        DOUBLE_SIZE = b'\x1d\x21\x11'  # Double width and height
        NORMAL_SIZE = b'\x1d\x21\x00'  # Normal size
        FEED = b'\r\n\r\n\r\n\r\n\r\n\r\n'  # Feed paper
        
        # Build the print job
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%B %d").replace(" 0", " ")  # Remove leading zero from day
        
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


@app.route('/manifest.json')
def manifest():
    return {
        "name": "Send me a message",
        "short_name": "Message",
        "description": "Send a message to Paulo's thermal printer",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1a1a2e",
        "theme_color": "#1a1a2e",
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
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        
        if not message:
            flash('Please enter a message!', 'error')
        elif len(message) > 240:
            flash('Message too long (max 240 characters / 5 lines)', 'error')
        else:
            visitor_ip = request.headers.get('CF-Connecting-IP', request.headers.get('X-Forwarded-For', request.remote_addr))
            success, result = send_to_printer(message, visitor_ip)
            if success:
                flash(result, 'success')
                return redirect(url_for('index'))
            else:
                flash(result, 'error')
    
    return render_template_string(HTML_TEMPLATE)


if __name__ == '__main__':
    print(f"Starting Thermal Printer Web App")
    print(f"Printer bridge: {PRINTER_HOST}:{PRINTER_PORT}")
    print(f"Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=True)
