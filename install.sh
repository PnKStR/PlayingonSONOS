#!/bin/bash

echo "🔧 Installing PlayingonSONOS..."

# System aktualisieren
sudo apt update
sudo apt install -y python3 python3-pip git

# Python-Abhängigkeiten global installieren
echo "📦 Installing Python dependencies..."
sudo pip3 install flask requests

echo "🚀 Installation complete."
echo "You can now start the app with:"
echo "python3 app.py"