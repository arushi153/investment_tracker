#!/bin/bash
# =============================================
# AI Powered SaT Tool - One-click setup script
# =============================================

echo ""
echo "🚀 Setting up AI Powered SaT Tool..."
echo ""

# Step 1: Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Step 2: Activate and install dependencies
echo "📥 Installing dependencies..."
source venv/bin/activate && pip install -r requirements.txt --quiet

echo ""
echo "✅ Setup complete!"
echo ""
echo "▶️  To start the app, run:"
echo "    source venv/bin/activate && python app.py"
echo ""
echo "🌐 Then open: http://127.0.0.1:5000/"
echo ""
