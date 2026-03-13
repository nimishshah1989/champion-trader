#!/bin/bash
# ============================================================
# Champion Trader System — macOS Auto-Start Setup
# ============================================================
# This script installs the backend as a macOS LaunchAgent.
# After running this, the backend starts automatically when
# you log in and restarts itself if it ever crashes.
#
# Usage:
#   bash scripts/setup_autostart.sh          # Install
#   bash scripts/setup_autostart.sh uninstall  # Remove
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_UVICORN="$PROJECT_DIR/venv/bin/uvicorn"
PLIST_LABEL="com.championtrader.backend"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
LOG_DIR="$HOME/Library/Logs/champion-trader"

# ── Uninstall ────────────────────────────────────────────────
if [ "${1:-}" = "uninstall" ]; then
    echo "Stopping and removing Champion Trader backend service..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm -f "$PLIST_PATH"
    echo "✅  Service removed. You can delete $LOG_DIR manually if desired."
    exit 0
fi

# ── Preflight ────────────────────────────────────────────────
echo ""
echo "Champion Trader System — Auto-Start Setup"
echo "Project: $PROJECT_DIR"
echo ""

if [ ! -f "$VENV_UVICORN" ]; then
    echo "❌  venv not found at $VENV_UVICORN"
    echo "    Create it first: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check .env exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️   .env file not found. The backend may not start correctly."
    echo "    Copy .env.example to .env and fill in your values."
fi

# ── Log directory ────────────────────────────────────────────
mkdir -p "$LOG_DIR"
echo "📁  Log directory: $LOG_DIR"

# ── Write plist ──────────────────────────────────────────────
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$VENV_UVICORN</string>
        <string>backend.main:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8000</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <!-- Start at login -->
    <key>RunAtLoad</key>
    <true/>

    <!-- Auto-restart if it crashes -->
    <key>KeepAlive</key>
    <true/>

    <!-- Wait 5 s before restarting after a crash -->
    <key>ThrottleInterval</key>
    <integer>5</integer>

    <!-- Logs -->
    <key>StandardOutPath</key>
    <string>$LOG_DIR/backend.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/backend-error.log</string>

    <!-- Environment — load .env values -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$PROJECT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>PYTHONPATH</key>
        <string>$PROJECT_DIR</string>
    </dict>
</dict>
</plist>
EOF

echo "📄  Plist written: $PLIST_PATH"

# ── Load (start now + on future logins) ─────────────────────
# Unload first in case an old version was running
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load -w "$PLIST_PATH"

echo ""
echo "✅  Champion Trader backend is now running as a background service."
echo ""
echo "   Status:  launchctl list | grep championtrader"
echo "   Logs:    tail -f $LOG_DIR/backend.log"
echo "   Errors:  tail -f $LOG_DIR/backend-error.log"
echo "   Stop:    launchctl unload $PLIST_PATH"
echo "   Remove:  bash scripts/setup_autostart.sh uninstall"
echo ""
echo "   The backend will auto-start every time you log in."
echo "   Scheduled jobs (scanner, price monitor, intelligence) run automatically."
echo ""

# Quick health check
sleep 3
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "🟢  Backend responding at http://127.0.0.1:8000"
else
    echo "⏳  Backend starting up... check logs in a moment:"
    echo "    tail -f $LOG_DIR/backend.log"
fi
