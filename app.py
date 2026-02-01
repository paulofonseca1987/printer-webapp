#!/usr/bin/env python3
"""
Thermal Printer Web App
A simple web interface to send messages to a thermal printer via TCP bridge.
"""

import socket
import textwrap
import os
import threading
import queue
import time
import secrets
import re
from flask import Flask, render_template_string, request, flash, redirect, url_for
from datetime import datetime

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configuration
PRINTER_HOST = "172.29.208.1"
PRINTER_PORT = 9100
MESSAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages")
RATE_LIMIT_SECONDS = 60  # 1 minute between messages per IP
PRINT_INTERVAL = 5  # Seconds between prints

# Emoji to text replacements
EMOJI_MAP = {
    # Smileys
    '😀': ':D', '😃': ':D', '😄': ':D', '😁': ':D', '😆': 'xD',
    '😅': "':D", '🤣': 'xD', '😂': ":'D", '🙂': ':)', '🙃': '(:', 
    '😉': ';)', '😊': ':)', '😇': '0:)', '🥰': ':)', '😍': '<3',
    '🤩': '*_*', '😘': ':*', '😗': ':*', '😚': ':*', '😙': ':*',
    '🥲': ":')", '😋': ':P', '😛': ':P', '😜': ';P', '🤪': ';P',
    '😝': 'xP', '🤑': '$)', '🤗': ':)', '🤭': ':x', '🤫': 'shh',
    '🤔': ':?', '🤐': ':X', '🤨': 'o_O', '😐': ':|', '😑': '-_-',
    '😶': ':|', '😏': ';)', '😒': '-_-', '🙄': '-_-', '😬': ':S',
    '🤥': ';)', '😌': ':)', '😔': ':(', '😪': ':/', '🤤': ':P~',
    '😴': 'zzz', '😷': ':mask:', '🤒': ':sick:', '🤕': ':hurt:',
    '🤢': ':S', '🤮': ':P~~', '🤧': ':achoo:', '🥵': ':hot:',
    '🥶': ':cold:', '🥴': ':/', '😵': 'x_x', '🤯': ':boom:',
    '🤠': ':cowboy:', '🥳': ':party:', '🥸': ':disguise:',
    '😎': 'B)', '🤓': '8)', '🧐': ':monocle:',
    '😕': ':/', '😟': ':(', '🙁': ':(', '☹️': ':(', '😮': ':o',
    '😯': ':o', '😲': ':O', '😳': ':$', '🥺': ':(', '😦': ':(',
    '😧': 'D:', '😨': 'D:', '😰': ":'(", '😥': ":'(", '😢': ":'(",
    '😭': ":'(", '😱': ':O', '😖': ':S', '😣': '>.<', '😞': ':(',
    '😓': "':)", '😩': 'D:', '😫': 'D:', '🥱': ':yawn:',
    '😤': '>:(', '😡': '>:(', '😠': '>:(', '🤬': ':@#$!',
    '😈': '>:)', '👿': '>:)', '💀': ':skull:', '☠️': ':skull:',
    '💩': ':poop:', '🤡': ':clown:', '👹': ':ogre:', '👺': ':goblin:',
    '👻': ':ghost:', '👽': ':alien:', '👾': ':alien:', '🤖': ':robot:',
    '😺': ':)', '😸': ':D', '😹': ":'D", '😻': '<3', '😼': ';)',
    '😽': ':*', '🙀': ':O', '😿': ":'(", '😾': '>:(',
    
    # Gestures
    '👋': ':wave:', '🤚': ':hand:', '🖐️': ':hand:', '✋': ':hand:',
    '🖖': ':vulcan:', '👌': ':ok:', '🤌': ':pinch:', '🤏': ':tiny:',
    '✌️': ':v:', '🤞': ':fingers-crossed:', '🤟': ':ily:',
    '🤘': ':rock:', '🤙': ':call-me:', '👈': '<-', '👉': '->',
    '👆': '^', '👇': 'v', '☝️': '^', '👍': ':+1:', '👎': ':-1:',
    '✊': ':fist:', '👊': ':punch:', '🤛': ':left-fist:',
    '🤜': ':right-fist:', '👏': ':clap:', '🙌': ':raise:',
    '👐': ':open-hands:', '🤲': ':palms:', '🤝': ':handshake:',
    '🙏': ':pray:', '✍️': ':writing:', '💅': ':nails:',
    '🤳': ':selfie:', '💪': ':muscle:',
    
    # Hearts
    '❤️': '<3', '🧡': '<3', '💛': '<3', '💚': '<3', '💙': '<3',
    '💜': '<3', '🖤': '<3', '🤍': '<3', '🤎': '<3', '💔': '</3',
    '❣️': '<3', '💕': '<3 <3', '💞': '<3', '💓': '<3', '💗': '<3',
    '💖': '<3', '💘': '<3', '💝': '<3', '💟': '<3',
    
    # Misc
    '✨': '*', '⭐': '*', '🌟': '*', '💫': '*', '✴️': '*',
    '🔥': ':fire:', '💯': '100', '💢': ':angry:', '💥': ':boom:',
    '💤': 'zzz', '💨': ':wind:', '💦': ':sweat:', '🎉': ':party:',
    '🎊': ':party:', '✅': '[x]', '❌': '[X]', '❓': '?', '❗': '!',
    '💬': ':speech:', '👁️': ':eye:', '👀': ':eyes:',
    '🚀': ':rocket:', '⚡': ':zap:', '☀️': ':sun:', '🌙': ':moon:',
    '⬆️': '^', '⬇️': 'v', '➡️': '->', '⬅️': '<-',
}

def replace_emojis(text):
    """Replace emojis with text equivalents."""
    # First, replace known emojis
    for emoji, replacement in EMOJI_MAP.items():
        text = text.replace(emoji, replacement)
    
    # Then, replace any remaining emojis/special chars with ;)
    # This regex matches most emoji and special unicode characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"  # Enclosed characters
        "]+", 
        flags=re.UNICODE
    )
    text = emoji_pattern.sub(';)', text)
    
    return text

# Ensure messages directory exists
os.makedirs(MESSAGES_DIR, exist_ok=True)

# Rate limiting: track last submission time per IP
rate_limit = {}

# Print queue
print_queue = queue.Queue()
queue_lock = threading.Lock()

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
        
        .hp-field {
            position: absolute;
            left: -9999px;
            opacity: 0;
            height: 0;
            width: 0;
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
                <input type="text" name="website" class="hp-field" tabindex="-1" autocomplete="off">
                <textarea 
                    name="message" 
                    placeholder="type something..."
                    maxlength="240"
                    id="message"
                >{{ request.form.get('message', '') }}</textarea>
                <div class="char-count"><span id="count">0</span>/240</div>
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


def print_worker():
    """Background worker that processes the print queue."""
    print("Print worker started!")
    while True:
        try:
            job = print_queue.get(timeout=1)
            if job is None:
                continue
            
            message, visitor_ip = job
            print(f"Processing print job from {visitor_ip}")
            actual_send_to_printer(message, visitor_ip)
            time.sleep(PRINT_INTERVAL)  # Wait between prints
            print_queue.task_done()
            print(f"Print job completed")
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Print worker error: {e}")


def actual_send_to_printer(message, visitor_ip):
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
        date_str = now.strftime("%B %d, %Y").replace(" 0", " ")  # Remove leading zero from day
        
        # Replace emojis with text equivalents
        printable_message = replace_emojis(message)
        
        # Wrap text to 48 characters (typical for 80mm thermal paper)
        wrapped_message = textwrap.fill(printable_message, width=48)
        
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


def send_to_printer(message, visitor_ip):
    """Add a message to the print queue."""
    try:
        print_queue.put((message, visitor_ip))
        queue_size = print_queue.qsize()
        if queue_size > 1:
            return True, f"Message queued! ({queue_size} in queue)"
        return True, "Message sent to printer!"
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
    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        
        if not message:
            flash('Please enter a message!', 'error')
        elif len(message) > 240:
            flash('Message too long (max 240 characters / 5 lines)', 'error')
        else:
            visitor_ip = request.headers.get('CF-Connecting-IP', request.headers.get('X-Forwarded-For', request.remote_addr))
            
            # Check rate limit
            now = datetime.now()
            if visitor_ip in rate_limit:
                time_since_last = (now - rate_limit[visitor_ip]).total_seconds()
                if time_since_last < RATE_LIMIT_SECONDS:
                    remaining = int(RATE_LIMIT_SECONDS - time_since_last)
                    flash(f'Please wait {remaining} seconds before sending another message', 'error')
                    return render_template_string(HTML_TEMPLATE)
            
            success, result = send_to_printer(message, visitor_ip)
            if success:
                rate_limit[visitor_ip] = now
                save_message(message, visitor_ip)
                flash(result, 'success')
                return redirect(url_for('index'))
            else:
                flash(result, 'error')
    
    return render_template_string(HTML_TEMPLATE)


# Start the print worker thread
worker_thread = threading.Thread(target=print_worker, daemon=True)
worker_thread.start()


if __name__ == '__main__':
    print(f"Starting Thermal Printer Web App")
    print(f"Printer bridge: {PRINTER_HOST}:{PRINTER_PORT}")
    print(f"Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=False)
