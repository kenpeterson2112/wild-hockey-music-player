#!/bin/sh
# Run before every push:  sh scripts/check.sh
# Fails (non-zero exit) if the song list or the app is broken. Do not push if it fails.
cd "$(dirname "$0")" || exit 1
python3 check_app.py || exit 1
if command -v node >/dev/null 2>&1; then
    node ../tests/app.test.mjs > /tmp/wild-app-tests.log 2>&1 || {
        grep -E "FAIL|Error" /tmp/wild-app-tests.log
        echo "FAILED: app tests (full log: /tmp/wild-app-tests.log). Do not push."
        exit 1
    }
    tail -1 /tmp/wild-app-tests.log
else
    echo "WARNING: node not installed: skipped tests/app.test.mjs"
fi
