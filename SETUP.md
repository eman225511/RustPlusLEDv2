# Setup Guide

Follow these steps to set up the Rust+ WLED Trigger App. The process takes about 10-15 minutes.

---

## Prerequisites

- **Python 3.7 or higher** installed on your computer
- **WLED controller** connected to your local network (note its IP address)
- **Rust+ app** installed on your phone with smart alarms configured in-game
- **Google account**
- **IFTTT account** (free tier is sufficient)

---

## Step 1: Install Python Dependencies

Open a terminal/command prompt in the project folder and run:

```bash
pip install -r requirements.txt
```

This installs the required packages:
- `python-telegram-bot` - Telegram Bot API
- `requests` - HTTP requests to WLED
- `pillow` - Color picker support

---

## Step 2: Telegram Bot Setup

### 2.1 Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow the prompts:
   - Choose a name for your bot (e.g., "Rust WLED Trigger")
   - Choose a username (must end in 'bot', e.g., "rust_wled_bot")
4. BotFather will give you a **Bot Token** - save this! (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
5. Copy the bot token

### 2.2 Get Your Chat ID

1. Search for **@userinfobot** on Telegram
2. Start a chat with it
3. It will reply with your **Chat ID** (a number like `123456789`)
4. Save this Chat ID

### 2.3 Start Your Bot

1. Search for your bot username in Telegram (the one you created)
2. Click **Start** or send `/start` to begin a conversation
3. This authorizes the bot to send you messages

---

## Step 3: IFTTT Applet Setup

### 3.1 Create the Applet

1. Go to [IFTTT](https://ifttt.com) and sign in
2. Click **Create** (top right)
3. Click **If This**
4. Search for and select **Rust+**
5. Choose a trigger (e.g., "Smart Alarm triggered")
6. Connect your Rust+ account if prompted
7. Select your server and smart alarm device
8. Click **Create Trigger**

### 3.2 Configure the Action

1. Click **Then That**
2. Search for and select **Telegram**
3. Choose **Send message**
4. Configure:
   - **Message text**: `Rust+ Alert: {{Title}} - {{Body}}`
   - **Target chat**: Use the chat with your bot
5. Click **Create Action**
6. Click **Continue** → **Finish**

**Note**: You may need to connect IFTTT to your Telegram account and authorize it to send messages to your bot.

### 3.3 Test the Applet

1. Trigger your Rust+ smart alarm in-game (or use the test button in IFTTT)
2. Check your Telegram bot chat - you should see a new message appear
3. If it works, you're ready to go!

---

## Step 4: WLED Configuration

1. Make sure your WLED device is powered on and connected to your network
2. Find its IP address (check your router, or use the WLED app)
3. Open a web browser and go to `http://[WLED_IP]` to verify it's accessible
4. (Optional) Configure presets and effects in WLED that you want to use

---

## Step 5: Run the Application

1. In the project folder, run:
   ```bash
   python main.py
   ```

2. The GUI window will open

3. Configure your settings:
   - **WLED IP**: Enter your WLED controller's IP address
   - **Telegram Bot Token**: Paste the bot token from BotFather
   - **Telegram Chat ID**: Paste your chat ID from @userinfobot
   - **Action on Trigger**: Choose what happens when an alarm triggers
     - **Turn ON**: Turns lights on
     - **Turn OFF**: Turns lights off
     - **Set Color**: Changes to a specific color (click "Pick Color" to choose)
     - **Set Effect**: Runs a WLED effect (enter effect number)
     - **Run Preset**: Activates a saved WLED preset (enter preset number)

4. Click **Save Settings**

5. The status will show "Waiting for Rust+ trigger..."

6. Trigger a Rust+ smart alarm - you should receive a Telegram message and your lights should respond!

---

## Step 6: Running in the Background

### Option A: Keep the Window Open
Simply minimize the window and let it run while you play Rust.

### Option B: Run as a Background Process (Advanced)
For Windows, create a `.vbs` script to run it silently:

Create `run_hidden.vbs`:
```vbscript
Set objShell = CreateObject("WScript.Shell")
objShell.Run "python main.py", 0, False
```

Double-click the `.vbs` file to run the app without a visible window.

---

## Troubleshooting

### "ERROR: Telegram bot token or chat ID not set!"
- Make sure you've entered both the bot token and chat ID in the app
- Verify you copied them correctly (no extra spaces)

### "Telegram error" messages
- Verify your bot token is correct
- Make sure you started a conversation with your bot in Telegram
- Check that your chat ID is correct

### IFTTT applet not triggering
- Check that your Rust+ alarm is properly configured in-game
- Verify the IFTTT applet is enabled (toggle it off and on)
- Make sure IFTTT is connected to your Telegram account
- Check IFTTT activity log to see if the applet is running

### Lights not responding
- Test your WLED manually by visiting `http://[WLED_IP]` in a browser
- Check effect/preset numbers are valid in WLED
- Look for error messages in the app's status label

---

## Tips for Best Experience

- **Create multiple LED presets** in WLED for different scenarios (raid alert, door breach, etc.)
- **Test your setup** before a raid by manually triggering alarms
- **Keep the app running** whenever you're playing Rust for real-time notifications
- **Adjust polling interval** in `main.py` (line `time.sleep(2)`) if needed - lower = faster but more API calls

---

## Next Steps

Once everything is working:
1. Set up multiple smart alarms in Rust (doors, turrets, vending machines, etc.)
2. Create multiple IFTTT applets for different alarm types
3. Experiment with different WLED effects and colors
4. Enjoy your immersive lighting setup!

Happy raiding! 🎮💡

