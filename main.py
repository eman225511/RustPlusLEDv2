import sys
import time
import threading
import requests
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QRadioButton, QButtonGroup, QSpinBox, QFrame,
                               QDialog, QTextEdit, QColorDialog, QMessageBox,
                               QTabWidget, QProgressBar, QToolTip)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QIcon
from telegram import Bot
from telegram.error import TelegramError
import asyncio

CONFIG_FILE = "config.json"

class TelegramWorker(QThread):
    """Worker thread for polling Telegram"""
    status_update = Signal(str, str)  # message, color
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True
        self.trigger_callback = None
        
    def run(self):
        print("[TELEGRAM] Starting Telegram bot connection...")
        self.status_update.emit("Connecting to Telegram...", "orange")
        
        bot_token = self.config.get("telegram_bot_token", "")
        chat_id = self.config.get("telegram_chat_id", "")
        
        if not bot_token or not chat_id:
            error_msg = "ERROR: Telegram bot token or chat ID not set!"
            print(f"[TELEGRAM] {error_msg}")
            self.status_update.emit(error_msg, "red")
            return
        
        # Validate bot token format
        if ":" not in bot_token or len(bot_token.split(":")) != 2:
            error_msg = "ERROR: Invalid bot token format! Should be like: 123456789:ABCdefGHI..."
            print(f"[TELEGRAM] {error_msg}")
            self.status_update.emit(error_msg, "red")
            return
        
        # Create one event loop for this thread and keep it alive
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            print(f"[TELEGRAM] Connecting to bot...")
            print(f"[TELEGRAM] Bot token: {bot_token[:10]}...{bot_token[-10:]}")
            print(f"[TELEGRAM] Chat ID: {chat_id}")
            
            # Create bot with custom timeout
            from telegram.request import HTTPXRequest
            request = HTTPXRequest(connection_pool_size=1, connect_timeout=30, read_timeout=30)
            bot = Bot(token=bot_token, request=request)
            
            # Test connection with timeout
            print("[TELEGRAM] Testing bot connection (30s timeout)...")
            bot_info = asyncio.wait_for(bot.get_me(), timeout=30.0)
            bot_info = loop.run_until_complete(bot_info)
            print(f"[TELEGRAM] ✓ Connected as @{bot_info.username} ({bot_info.first_name})")
            self.status_update.emit(f"✓ Connected as @{bot_info.username}! Waiting for messages...", "green")
                
        except asyncio.TimeoutError:
            error_msg = "ERROR: Connection timed out! Check your internet connection."
            print(f"[TELEGRAM] {error_msg}")
            self.status_update.emit(error_msg, "red")
            return
        except TelegramError as e:
            if "Unauthorized" in str(e):
                error_msg = "ERROR: Invalid bot token! Check your bot token."
            elif "Not Found" in str(e):
                error_msg = "ERROR: Bot not found! Check your bot token."
            elif "Forbidden" in str(e):
                error_msg = "ERROR: Bot access forbidden! Make sure bot is active."
            else:
                error_msg = f"Telegram error: {str(e)}"
            print(f"[TELEGRAM] {error_msg}")
            self.status_update.emit(error_msg, "red")
            return
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            print(f"[TELEGRAM] {error_msg}")
            self.status_update.emit(error_msg, "red")
            return

        print(f"[TELEGRAM] Starting polling loop (every {self.config.get('polling_rate', 2)} seconds...)")
        last_update_id = 0
        
        while self.running:
            try:
                # Use the same event loop throughout with timeout and offset
                get_updates_params = {"timeout": 5, "offset": last_update_id + 1 if last_update_id > 0 else None}
                get_updates_task = asyncio.wait_for(bot.get_updates(**get_updates_params), timeout=10.0)
                updates = loop.run_until_complete(get_updates_task)
                
                print(f"[TELEGRAM] Received {len(updates)} updates")
                
                # Process all updates
                for update in updates:
                    last_update_id = update.update_id
                    print(f"[TELEGRAM] Processing update ID: {update.update_id}")
                    
                    # Check for regular messages
                    if update.message:
                        message_chat_id = str(update.message.chat_id)
                        message_id = update.message.message_id
                        message_text = update.message.text or ""
                        
                        print(f"[TELEGRAM] Message from chat {message_chat_id}, expected {chat_id}")
                        print(f"[TELEGRAM] Message text: '{message_text}'")
                        
                        if message_chat_id == str(chat_id):
                            if message_id > self.config.get("last_message_id", 0):
                                print(f"[TELEGRAM] ✓ New message detected! ID: {message_id}")
                                
                                if self.trigger_callback:
                                    self.trigger_callback()
                                
                                self.config["last_message_id"] = message_id
                                with open(CONFIG_FILE, "w") as f:
                                    json.dump(self.config, f, indent=4)
                                print(f"[TELEGRAM] Updated last_message_id to {message_id}")
                            else:
                                print(f"[TELEGRAM] Message ID {message_id} already processed (last: {self.config.get('last_message_id', 0)})")
                        else:
                            print(f"[TELEGRAM] Ignoring message from different chat: {message_chat_id}")
                    
                    # Check for channel posts
                    elif update.channel_post:
                        post_chat_id = str(update.channel_post.chat_id)
                        post_id = update.channel_post.message_id
                        post_text = update.channel_post.text or ""
                        
                        print(f"[TELEGRAM] Channel post from chat {post_chat_id}, expected {chat_id}")
                        print(f"[TELEGRAM] Post text: '{post_text}'")
                        
                        if post_chat_id == str(chat_id):
                            if post_id > self.config.get("last_message_id", 0):
                                print(f"[TELEGRAM] ✓ New channel post detected! ID: {post_id}")
                                
                                if self.trigger_callback:
                                    self.trigger_callback()
                                
                                self.config["last_message_id"] = post_id
                                with open(CONFIG_FILE, "w") as f:
                                    json.dump(self.config, f, indent=4)
                                print(f"[TELEGRAM] Updated last_message_id to {post_id}")
                            else:
                                print(f"[TELEGRAM] Post ID {post_id} already processed (last: {self.config.get('last_message_id', 0)})")
                        else:
                            print(f"[TELEGRAM] Ignoring post from different channel: {post_chat_id}")
                    
                    else:
                        print(f"[TELEGRAM] Update type not handled: {type(update)}")

            except asyncio.TimeoutError:
                print("[TELEGRAM] Polling timeout (normal, continuing...)")
            except Exception as e:
                print(f"[ERROR] Failed to poll Telegram: {str(e)}")
                self.status_update.emit(f"Error polling: {str(e)[:50]}", "red")

            # Use configurable polling rate
            time.sleep(self.config.get("polling_rate", 2))
        
        # Clean up the event loop when done
        loop.close()
    
    def stop(self):
        self.running = False


class SetupDialog(QDialog):
    """Dialog showing Telegram setup instructions"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rust+ WLED Setup Guide")
        self.setFixedSize(750, 700)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 10))
        
        setup_text = """🚀 RUST+ WLED TRIGGER SETUP GUIDE

🎯 OVERVIEW:
This app monitors your Telegram channel for Rust+ messages and triggers WLED actions.
When IFTTT sends Rust+ notifications to your channel, this app will detect them and 
control your WLED lights automatically!

1️⃣ CREATE YOUR TELEGRAM CHANNEL:
   • Open Telegram and create a new channel
   • Make it private (recommended for security)
   • Give it a name like "Rust+ Notifications"

2️⃣ CREATE A BOT:
   • Search for @BotFather on Telegram
   • Send /newbot command
   • Follow instructions to name your bot (e.g., "MyRustWLEDBot")
   • Copy the Bot Token (looks like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
   • Paste it in the 'Bot Token' field above

3️⃣ ADD BOTS TO YOUR CHANNEL:
   • Go to your channel settings → Administrators → Add Administrator
   • Search and add your newly created bot (give it "Post Messages" permission)
   • Search and add @IFTTT bot (this sends Rust+ notifications)
   • Both bots must be channel admins!

4️⃣ GET YOUR CHANNEL ID:
   Method A - Using @userinfobot:
   • Forward any message from your channel to @userinfobot
   • It will show the channel ID (starts with -100, like: -1001234567890)
   
   Method B - Using @RawDataBot:
   • Forward any message from your channel to @RawDataBot
   • Look for "forward_from_chat":{"id":-100xxxxxxxxx}
   
   Method C - Using bot API:
   • Post a test message in your channel
   • Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   • Look for "chat":{"id":-100xxxxxxxxx}

5️⃣ CONFIGURE IFTTT (IMPORTANT!):
   • Go to IFTTT.com and set up Rust+ integration
   • In the "Then" action, choose "Telegram" → "Send message to channel"
   • Set the channel to your newly created channel
   • Make sure IFTTT sends messages when Rust+ events occur

6️⃣ TEST THE SETUP:
   • Paste your channel ID (starts with -100) in the 'Chat ID' field above
   • Click 'Save Settings' in the main window
   • Send a test message to your channel (or trigger a Rust+ event)
   • Your WLED should trigger!

🔧 TROUBLESHOOTING:
   • Channel IDs always start with -100 (e.g., -1001234567890)
   • Both your bot AND @IFTTT must be channel admins
   • Your bot needs "Post Messages" permission in the channel
   • Test by sending any message to the channel first
   • Check the console output for detailed error messages

⚠️ SECURITY TIPS:
   • Keep your channel private
   • Don't share your bot token publicly
   • Only add trusted bots as administrators
   
🎮 RUST+ INTEGRATION:
   • This app works with IFTTT's Rust+ integration
   • Set up IFTTT to send notifications to your Telegram channel
   • Events like "Player Online", "Smart Alarm", "Cargo Ship" will trigger WLED
   • Customize your WLED action above (colors, effects, presets)
"""
        text_edit.setPlainText(setup_text)
        layout.addWidget(text_edit)
        
        # Close button
        close_btn = QPushButton("❌ Close")
        close_btn.setFont(QFont("Arial", 13, QFont.Bold))
        close_btn.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 #2196f3, stop: 1 #1976d2);
            color: white;
            padding: 12px 35px;
            border-radius: 8px;
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
        
        self.setLayout(layout)


class RustWLEDApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_config()
        self.telegram_worker = None
        self.current_color = QColor(self.config["color"])
        
        self.setWindowTitle("Rust+ WLED Trigger")
        self.setFixedSize(850, 950)
        
        # Set window icon if available
        try:
            self.setWindowIcon(QIcon("logo.ico"))
        except:
            pass  # Icon not found, continue without it
        
        # Apply modern dark theme stylesheet with animations
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #2b2b2b, stop: 1 #1e1e1e);
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            QLineEdit {
                padding: 12px;
                border: 2px solid #404040;
                border-radius: 8px;
                background-color: #3c3c3c;
                color: #ffffff;
                font-size: 14px;
                selection-background-color: #0078d4;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
                background-color: #424242;
            }
            QLineEdit:hover {
                border: 2px solid #555555;
                background-color: #404040;
            }
            QPushButton {
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.2);
            }
            QRadioButton {
                font-size: 14px;
                font-weight: bold;
                spacing: 12px;
                color: #ffffff;
                padding: 8px 15px;
                margin: 2px;
                background-color: rgba(255, 255, 255, 0.08);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                min-height: 20px;
            }
            QRadioButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            QRadioButton::indicator {
                width: 22px;
                height: 22px;
                border-radius: 11px;
            }
            QRadioButton::indicator:unchecked {
                border: 3px solid #666666;
                background-color: #3c3c3c;
            }
            QRadioButton::indicator:checked {
                border: 3px solid #0078d4;
                background-color: #0078d4;
                background: qradialgradient(cx: 0.5, cy: 0.5, radius: 0.5,
                                           fx: 0.5, fy: 0.5, stop: 0 #ffffff, stop: 0.3 #0078d4);
            }
            QRadioButton::indicator:unchecked:hover {
                border: 3px solid #888888;
                background-color: #484848;
            }
            QRadioButton::indicator:checked:hover {
                border: 3px solid #1e88e5;
                background-color: #1e88e5;
            }
            QSpinBox {
                padding: 12px;
                border: 2px solid #404040;
                border-radius: 8px;
                background-color: #3c3c3c;
                color: #ffffff;
                font-size: 14px;
            }
            QSpinBox:focus {
                border: 2px solid #0078d4;
                background-color: #424242;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                border: none;
                background-color: #505050;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #606060;
            }
            QFrame {
                color: #666666;
            }
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 2px solid #404040;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', monospace;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #606060;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #707070;
            }
        """)
        
        self.init_ui()
        self.start_telegram_worker()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("🎮 Rust+ WLED Trigger")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: #ffffff;
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                       stop: 0 #0078d4, stop: 1 #00bcf2);
            padding: 20px;
            border-radius: 12px;
            margin: 10px;
        """)
        main_layout.addWidget(title)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #404040;
                border-radius: 12px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 rgba(255, 255, 255, 0.08),
                                           stop: 1 rgba(255, 255, 255, 0.03));
                margin-top: 10px;
            }
            QTabBar::tab {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #3c3c3c, stop: 1 #2a2a2a);
                color: #ffffff;
                padding: 15px 30px;
                margin: 2px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #0078d4, stop: 1 #005a9e);
                color: #ffffff;
                border: 2px solid #00bcf2;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #505050, stop: 1 #3a3a3a);
                border: 2px solid #666666;
            }
        """)
        
        # Create tabs
        self.create_main_tab()
        self.create_settings_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # Status label (outside tabs)
        self.status_label = QLabel("Configure Telegram settings and save!")
        self.status_label.setFont(QFont("Arial", 13))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(80)
        self.status_label.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 rgba(33, 150, 243, 0.2),
                                       stop: 1 rgba(33, 150, 243, 0.1));
            color: #ffffff;
            padding: 20px;
            border-radius: 12px;
            border: 2px solid rgba(33, 150, 243, 0.3);
        """)
        main_layout.addWidget(self.status_label)
        
        # Main action buttons (outside tabs)
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setFont(QFont("Arial", 14, QFont.Bold))
        save_btn.setToolTip("Save all configuration settings to file")
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #2196f3, stop: 1 #1976d2);
                color: white;
                padding: 18px 35px;
                border-radius: 12px;
                font-weight: bold;
                border: 2px solid transparent;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #42a5f5, stop: 1 #1e88e5);
                border: 2px solid #64b5f6;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #1976d2, stop: 1 #1565c0);
            }
        """)
        save_btn.clicked.connect(self.save_config)
        
        test_btn = QPushButton("🧪 Test WLED")
        test_btn.setFont(QFont("Arial", 14, QFont.Bold))
        test_btn.setToolTip("Test the current WLED configuration")
        test_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #4caf50, stop: 1 #388e3c);
                color: white;
                padding: 18px 35px;
                border-radius: 12px;
                font-weight: bold;
                border: 2px solid transparent;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #66bb6a, stop: 1 #43a047);
                border: 2px solid #81c784;
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #388e3c, stop: 1 #2e7d32);
            }
        """)
        test_btn.clicked.connect(self.test_wled)
        
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(test_btn)
        main_layout.addLayout(buttons_layout)
        
        main_layout.addStretch()
        central_widget.setLayout(main_layout)
    
    def create_main_tab(self):
        """Create the main control tab"""
        main_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Action on Trigger
        action_title = QLabel("⚡ Action on Trigger")
        action_title.setFont(QFont("Arial", 16, QFont.Bold))
        action_title.setStyleSheet("""
            color: #ffffff;
            background-color: rgba(255, 255, 255, 0.1);
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0px;
        """)
        layout.addWidget(action_title)
        
        # Radio buttons for actions
        self.action_group = QButtonGroup()
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(5)
        
        self.radio_on = QRadioButton("💡 Turn ON")
        self.radio_off = QRadioButton("🌙 Turn OFF")
        self.radio_color = QRadioButton("🎨 Set Color")
        self.radio_effect = QRadioButton("✨ Set Effect")
        self.radio_preset = QRadioButton("🎭 Run Preset")
        
        for i, radio in enumerate([self.radio_on, self.radio_off, self.radio_color, self.radio_effect, self.radio_preset]):
            radio.setFont(QFont("Arial", 14, QFont.Bold))
            radio.setStyleSheet("color: #ffffff; font-weight: bold;")
            self.action_group.addButton(radio, i)
            actions_layout.addWidget(radio)
        
        # Set current action
        action_map = {"on": 0, "off": 1, "color": 2, "effect": 3, "preset": 4}
        self.action_group.button(action_map.get(self.config["action"], 0)).setChecked(True)
        
        layout.addLayout(actions_layout)
        
        # Add spacing
        layout.addSpacing(20)
        
        # Color picker
        color_layout = QHBoxLayout()
        color_label = QLabel("🎨 Color:")
        color_label.setFont(QFont("Arial", 14, QFont.Bold))
        color_label.setStyleSheet("color: #ffffff; padding: 5px;")
        self.color_button = QPushButton("🎨 Pick Color")
        self.color_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 #9c27b0, stop: 1 #7b1fa2);
            color: white;
            border-radius: 8px;
            font-weight: bold;
            padding: 10px 20px;
        """)
        self.color_button.clicked.connect(self.pick_color)
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(120, 50)
        self.color_preview.setStyleSheet(f"""
            background-color: {self.current_color.name()};
            border: 3px solid #666666;
            border-radius: 8px;
        """)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Effect and Preset
        params_layout = QHBoxLayout()
        
        effect_label = QLabel("✨ Effect #:")
        effect_label.setFont(QFont("Arial", 14, QFont.Bold))
        effect_label.setStyleSheet("color: #ffffff; padding: 5px;")
        self.effect_spin = QSpinBox()
        self.effect_spin.setRange(0, 255)
        self.effect_spin.setValue(int(self.config.get("effect", 0)))
        self.effect_spin.setFont(QFont("Arial", 14))
        
        preset_label = QLabel("🎭 Preset #:")
        preset_label.setFont(QFont("Arial", 14, QFont.Bold))
        preset_label.setStyleSheet("color: #ffffff; padding: 5px;")
        self.preset_spin = QSpinBox()
        self.preset_spin.setRange(0, 255)
        self.preset_spin.setValue(int(self.config.get("preset", 0)))
        self.preset_spin.setFont(QFont("Arial", 14))
        
        params_layout.addWidget(effect_label)
        params_layout.addWidget(self.effect_spin)
        params_layout.addSpacing(30)
        params_layout.addWidget(preset_label)
        params_layout.addWidget(self.preset_spin)
        params_layout.addStretch()
        layout.addLayout(params_layout)
        
        layout.addStretch()
        main_tab.setLayout(layout)
        self.tab_widget.addTab(main_tab, "🎮 Control")
    
    def create_settings_tab(self):
        """Create the settings tab"""
        settings_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # WLED Settings
        wled_title = QLabel("💻 WLED Settings")
        wled_title.setFont(QFont("Arial", 16, QFont.Bold))
        wled_title.setStyleSheet("""
            color: #ffffff;
            background-color: rgba(255, 255, 255, 0.1);
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0px;
        """)
        layout.addWidget(wled_title)
        
        # WLED IP
        wled_layout = QHBoxLayout()
        wled_label = QLabel("💻 WLED IP:")
        wled_label.setFont(QFont("Arial", 14, QFont.Bold))
        wled_label.setMinimumWidth(130)
        wled_label.setStyleSheet("color: #ffffff; padding: 5px;")
        self.ip_entry = QLineEdit(self.config["wled_ip"])
        self.ip_entry.setFont(QFont("Arial", 13))
        self.ip_entry.setPlaceholderText("192.168.1.100")
        self.ip_entry.setToolTip("Enter the IP address of your WLED device")
        wled_layout.addWidget(wled_label)
        wled_layout.addWidget(self.ip_entry)
        layout.addLayout(wled_layout)
        
        # Add spacing
        layout.addSpacing(20)
        
        # Telegram Settings
        telegram_title = QLabel("💬 Telegram Settings")
        telegram_title.setFont(QFont("Arial", 16, QFont.Bold))
        telegram_title.setStyleSheet("""
            color: #ffffff;
            background-color: rgba(255, 255, 255, 0.1);
            padding: 12px;
            border-radius: 8px;
            margin: 8px 0px;
        """)
        layout.addWidget(telegram_title)
        
        # Bot Token
        token_layout = QHBoxLayout()
        token_label = QLabel("🤖 Bot Token:")
        token_label.setFont(QFont("Arial", 14, QFont.Bold))
        token_label.setMinimumWidth(130)
        token_label.setStyleSheet("color: #ffffff; padding: 5px;")
        self.bot_token_entry = QLineEdit(self.config.get("telegram_bot_token", ""))
        self.bot_token_entry.setFont(QFont("Arial", 13))
        self.bot_token_entry.setEchoMode(QLineEdit.Password)
        self.bot_token_entry.setPlaceholderText("123456789:ABCdefGHIjklMNOpqr")
        self.bot_token_entry.setToolTip("Bot token from @BotFather (123456789:ABC...)")
        setup_btn = QPushButton("📋 Setup Help")
        setup_btn.setToolTip("Show detailed setup instructions")
        setup_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #ff9800, stop: 1 #f57c00);
                color: white;
                border-radius: 8px;
                font-weight: bold;
                padding: 8px 16px;
                border: 2px solid transparent;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #ffb74d, stop: 1 #ff9800);
                border: 2px solid #ffcc02;
            }
        """)
        setup_btn.clicked.connect(self.show_setup_dialog)
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.bot_token_entry)
        token_layout.addWidget(setup_btn)
        layout.addLayout(token_layout)
        
        # Chat ID
        chat_layout = QHBoxLayout()
        chat_label = QLabel("💬 Chat ID:")
        chat_label.setFont(QFont("Arial", 14, QFont.Bold))
        chat_label.setMinimumWidth(130)
        chat_label.setStyleSheet("color: #ffffff; padding: 5px;")
        self.chat_id_entry = QLineEdit(self.config.get("telegram_chat_id", ""))
        self.chat_id_entry.setFont(QFont("Arial", 13))
        self.chat_id_entry.setPlaceholderText("-1001234567890")
        self.chat_id_entry.setToolTip("Channel ID (starts with -100) or personal chat ID")
        chat_layout.addWidget(chat_label)
        chat_layout.addWidget(self.chat_id_entry)
        layout.addLayout(chat_layout)
        
        # Polling Rate
        polling_layout = QHBoxLayout()
        polling_label = QLabel("🔄 Polling Rate:")
        polling_label.setFont(QFont("Arial", 14, QFont.Bold))
        polling_label.setMinimumWidth(130)
        polling_label.setStyleSheet("color: #ffffff; padding: 5px;")
        self.polling_spin = QSpinBox()
        self.polling_spin.setRange(1, 30)
        self.polling_spin.setValue(int(self.config.get("polling_rate", 2)))
        self.polling_spin.setFont(QFont("Arial", 14))
        self.polling_spin.setSuffix(" sec")
        self.polling_spin.setToolTip("How often to check for new messages (1-30 seconds)")
        polling_layout.addWidget(polling_label)
        polling_layout.addWidget(self.polling_spin)
        polling_layout.addStretch()
        layout.addLayout(polling_layout)
        
        layout.addStretch()
        settings_tab.setLayout(layout)
        self.tab_widget.addTab(settings_tab, "⚙️ Settings")
    
    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                self.config = json.load(f)
            print(f"[INFO] Loaded config from {CONFIG_FILE}")
        except:
            print(f"[INFO] Config file not found. Creating default config...")
            self.config = {
                "wled_ip": "192.168.1.50",
                "action": "on",
                "color": "#ffffff",
                "effect": "0",
                "preset": "0",
                "telegram_bot_token": "",
                "telegram_chat_id": "",
                "last_message_id": 0,
                "polling_rate": 2
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            print(f"[INFO] Created default config file: {CONFIG_FILE}")
    
    def save_config(self):
        # Store old telegram settings to check if they changed
        old_bot_token = self.config.get("telegram_bot_token", "")
        old_chat_id = self.config.get("telegram_chat_id", "")
        
        self.config["wled_ip"] = self.ip_entry.text()
        self.config["telegram_bot_token"] = self.bot_token_entry.text()
        self.config["telegram_chat_id"] = self.chat_id_entry.text()
        self.config["polling_rate"] = self.polling_spin.value()
        
        # Get selected action
        action_map = {0: "on", 1: "off", 2: "color", 3: "effect", 4: "preset"}
        self.config["action"] = action_map.get(self.action_group.checkedId(), "on")
        
        self.config["color"] = self.current_color.name()
        self.config["effect"] = str(self.effect_spin.value())
        self.config["preset"] = str(self.preset_spin.value())
        self.config["polling_rate"] = self.polling_spin.value()
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)
        
        print(f"[INFO] Settings saved: IP={self.config['wled_ip']}, Action={self.config['action']}")
        self.update_status("✓ Settings Saved Successfully!", "green")
        
        # Visual feedback - briefly highlight save button
        self.sender().setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #4caf50, stop: 1 #388e3c);
                color: white;
                padding: 18px 35px;
                border-radius: 12px;
                font-weight: bold;
                border: 2px solid #81c784;
            }
        """)
        
        # Reset button style after 1 second
        QTimer.singleShot(1000, lambda: self.sender().setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #2196f3, stop: 1 #1976d2);
                color: white;
                padding: 18px 35px;
                border-radius: 12px;
                font-weight: bold;
                border: 2px solid transparent;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 #42a5f5, stop: 1 #1e88e5);
                border: 2px solid #64b5f6;
            }
        """))
        
        # Only restart telegram worker if telegram settings changed
        new_bot_token = self.config.get("telegram_bot_token", "")
        new_chat_id = self.config.get("telegram_chat_id", "")
        
        if old_bot_token != new_bot_token or old_chat_id != new_chat_id:
            print("[INFO] Telegram settings changed, restarting worker...")
            self.restart_telegram_worker()
    
    def pick_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Pick a Color")
        if color.isValid():
            self.current_color = color
            self.color_preview.setStyleSheet(f"""
                background-color: {color.name()};
                border: 3px solid #666666;
                border-radius: 8px;
            """)
    
    def show_setup_dialog(self):
        dialog = SetupDialog(self)
        dialog.exec()
    
    def test_wled(self):
        print("[INFO] Testing WLED connection...")
        
        # Visual feedback - show testing state
        sender = self.sender()
        original_text = sender.text()
        sender.setText("🔄 Testing...")
        sender.setEnabled(False)
        
        # Update config from UI without saving to file or restarting telegram
        self.config["wled_ip"] = self.ip_entry.text()
        self.config["polling_rate"] = self.polling_spin.value()
        action_map = {0: "on", 1: "off", 2: "color", 3: "effect", 4: "preset"}
        self.config["action"] = action_map.get(self.action_group.checkedId(), "on")
        self.config["color"] = self.current_color.name()
        self.config["effect"] = str(self.effect_spin.value())
        self.config["preset"] = str(self.preset_spin.value())
        
        self.trigger_wled()
        
        # Reset button after 2 seconds
        QTimer.singleShot(2000, lambda: [
            sender.setText(original_text),
            sender.setEnabled(True)
        ])
    
    def trigger_wled(self):
        ip = self.config["wled_ip"]
        action = self.config["action"]
        url = f"http://{ip}/json/state"
        
        try:
            if action == "on":
                payload = {"on": True}
                print(f"[WLED] Turning ON -> {url}")
                requests.post(url, json=payload, timeout=5)
            elif action == "off":
                payload = {"on": False}
                print(f"[WLED] Turning OFF -> {url}")
                requests.post(url, json=payload, timeout=5)
            elif action == "color":
                hex_color = self.config["color"].lstrip("#")
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                payload = {"on": True, "seg": [{"col": [[r, g, b]]}]}
                print(f"[WLED] Setting color RGB({r},{g},{b}) -> {url}")
                requests.post(url, json=payload, timeout=5)
            elif action == "effect":
                fx = int(self.config["effect"])
                payload = {"on": True, "seg": [{"fx": fx}]}
                print(f"[WLED] Setting effect #{fx} -> {url}")
                requests.post(url, json=payload, timeout=5)
            elif action == "preset":
                p = int(self.config["preset"])
                payload = {"ps": p}
                print(f"[WLED] Running preset #{p} -> {url}")
                requests.post(url, json=payload, timeout=5)
            
            print(f"[WLED] ✓ Success!")
            self.update_status("✓ WLED Triggered Successfully!", "green")
        
        except Exception as e:
            print(f"[ERROR] WLED request failed: {str(e)}")
            self.update_status(f"❌ Error: {str(e)[:50]}", "red")
    
    def update_status(self, message, color):
        color_map = {
            "green": ("""
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 rgba(76, 175, 80, 0.3),
                                           stop: 1 rgba(76, 175, 80, 0.1));
                color: #a5d6a7;
                border: 2px solid rgba(76, 175, 80, 0.5);
            """),
            "red": ("""
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 rgba(244, 67, 54, 0.3),
                                           stop: 1 rgba(244, 67, 54, 0.1));
                color: #ef9a9a;
                border: 2px solid rgba(244, 67, 54, 0.5);
            """),
            "orange": ("""
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 rgba(255, 152, 0, 0.3),
                                           stop: 1 rgba(255, 152, 0, 0.1));
                color: #ffcc02;
                border: 2px solid rgba(255, 152, 0, 0.5);
            """),
            "blue": ("""
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                           stop: 0 rgba(33, 150, 243, 0.3),
                                           stop: 1 rgba(33, 150, 243, 0.1));
                color: #90caf9;
                border: 2px solid rgba(33, 150, 243, 0.5);
            """)
        }
        style = color_map.get(color, color_map["blue"])
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"{style} padding: 20px; border-radius: 12px;")
    
    def start_telegram_worker(self):
        self.telegram_worker = TelegramWorker(self.config)
        self.telegram_worker.status_update.connect(self.update_status)
        self.telegram_worker.trigger_callback = self.trigger_wled
        self.telegram_worker.start()
    
    def restart_telegram_worker(self):
        if self.telegram_worker and self.telegram_worker.isRunning():
            self.telegram_worker.stop()
            self.telegram_worker.wait()
        self.start_telegram_worker()
    
    def closeEvent(self, event):
        if self.telegram_worker and self.telegram_worker.isRunning():
            self.telegram_worker.stop()
            self.telegram_worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RustWLEDApp()
    window.show()
    sys.exit(app.exec())
