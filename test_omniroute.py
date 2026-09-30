#!/usr/bin/env python3
"""
Simple test to verify OmniRoute connection
"""

import os
import sys
from anthropic import Anthropic
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
load_dotenv()

def test_omniroute_connection():
    """Test connection to OmniRoute"""
    print("=" * 60)
    print("OMNIROUTE CONNECTION TEST")
    print("=" * 60)

    # Get configuration
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    model = os.getenv("ANTHROPIC_MODEL", "deepak-ai")

    print(f"\n✓ Base URL: {base_url}")
    print(f"✓ Model: {model}")
    print(f"✓ Auth token: {'*' * 20 if auth_token else 'NOT SET'}")

    if not base_url or not auth_token:
        print("\n❌ Configuration incomplete!")
        print("Please set ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN in .env file")
        return False

    # Test connection
    print("\n🔄 Testing connection to OmniRoute...")

    try:
        client = Anthropic(
            base_url=base_url,
            api_key=auth_token
        )

        response = client.messages.create(
            model=model,
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": "Reply with exactly: OmniRoute connection successful!"
            }]
        )

        # Extract response text
        response_text = ""
        for content_block in response.content:
            if hasattr(content_block, "text"):
                response_text += content_block.text
