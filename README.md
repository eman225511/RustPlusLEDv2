# Rust+ → WLED Trigger App

**Bring your gaming experience to life!** This app connects your Rust+ smart alarms to your WLED RGB lights, creating real-time visual notifications when in-game events occur (raids, door opens, vending machine purchases, etc.).

## ✨ Features

- **Easy-to-Use GUI**: Configure WLED actions with a simple interface
- **Multiple Trigger Actions**:
  - Turn lights ON/OFF
  - Set custom colors
  - Activate WLED effects
  - Run saved presets
- **Real-Time Response**: Monitors Google Sheets for instant triggering (2-second polling)
- **Free Tier Friendly**: Uses IFTTT's free Google Sheets integration (no webhook quota limits)
- **Persistent Settings**: Automatically saves your configuration
- **Background Monitoring**: Runs continuously while you play

## 🎮 How It Works

1. Rust+ smart alarms trigger IFTTT applets
2. IFTTT logs events to a Google Sheet
3. This app monitors the sheet for new rows
4. When detected, triggers your configured WLED action
5. Your lights flash, change color, or run effects in real-time!

## 📋 Requirements

- Python 3.7+
- WLED-compatible LED controller on your local network
- Google account (for Google Sheets)
- IFTTT account (free tier works)
- Rust+ app with smart alarms configured

## 🚀 Quick Start

See [SETUP.md](SETUP.md) for detailed installation and configuration instructions.

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## 💡 Usage Tips

- **Effect Numbers**: Find WLED effect IDs in your WLED controller's web interface (typically 0-100+)
- **Presets**: Create and save presets in WLED, then use their preset number here
- **Color Picker**: Click "Pick Color" to choose any RGB color visually
- **Multiple Alarms**: Set up different IFTTT applets for different alarm types - they'll all trigger the same action

## 🔧 Troubleshooting

- **"Error reading sheet"**: Check your `service_account.json` file and sheet sharing permissions
- **"Error: Connection refused"**: Verify your WLED IP address is correct and accessible
- **No trigger happening**: Ensure your Google Sheet is named `RustTrigger` exactly
- **Delayed response**: Normal - sheet polls every 2 seconds; IFTTT may add 1-5 second delay

## 📝 License

Open source - feel free to modify and share!

## 🤝 Contributing

Suggestions and improvements welcome! This is a hobby project to enhance the Rust gaming experience.
