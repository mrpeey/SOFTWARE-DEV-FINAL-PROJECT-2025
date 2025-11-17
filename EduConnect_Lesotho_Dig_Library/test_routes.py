#!/usr/bin/env python3
"""Test script to list all available routes"""

import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

print("Available auth routes:")
print("=" * 50)

for rule in app.url_map.iter_rules():
    if 'auth' in rule.endpoint:
        print(f"{rule.endpoint}: {rule.rule} [{', '.join(rule.methods)}]")