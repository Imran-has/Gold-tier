#!/usr/bin/env python3
"""
Test all API connections for Gold Tier
"""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent / "config" / ".env"
load_dotenv(env_path, override=True)

import aiohttp

async def test_facebook():
    """Test Facebook API connection"""
    print("\n[FACEBOOK] Testing...")

    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")

    if not access_token or access_token == "your_facebook_page_access_token":
        print("  ❌ Not configured")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://graph.facebook.com/v18.0/{page_id}?access_token={access_token}"
            async with session.get(url) as response:
                data = await response.json()
                if "error" in data:
                    print(f"  ❌ Error: {data['error'].get('message', 'Unknown')}")
                    return False
                print(f"  ✅ Connected! Page: {data.get('name', 'Unknown')}")
                return True
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return False

async def test_linkedin():
    """Test LinkedIn API connection"""
    print("\n[LINKEDIN] Testing...")

    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")

    if not access_token or access_token == "your_linkedin_access_token":
        print("  ❌ Not configured")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.linkedin.com/v2/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    name = f"{data.get('localizedFirstName', '')} {data.get('localizedLastName', '')}"
                    print(f"  ✅ Connected! Profile: {name}")
                    return True
                else:
                    data = await response.json()
                    print(f"  ❌ Error: {response.status} - {data}")
                    return False
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return False

async def test_twitter():
    """Test Twitter API connection"""
    print("\n[TWITTER] Testing...")

    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

    if not bearer_token or bearer_token == "your_twitter_bearer_token":
        print("  ❌ Not configured")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.twitter.com/2/users/me"
            headers = {"Authorization": f"Bearer {bearer_token}"}
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    username = data.get("data", {}).get("username", "Unknown")
                    print(f"  ✅ Connected! User: @{username}")
                    return True
                else:
                    print(f"  ❌ Error: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return False

async def test_instagram():
    """Test Instagram API connection"""
    print("\n[INSTAGRAM] Testing...")

    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")

    if not access_token or access_token == "your_instagram_access_token":
        print("  ❌ Not configured")
        return False

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://graph.facebook.com/v18.0/{account_id}?fields=username&access_token={access_token}"
            async with session.get(url) as response:
                data = await response.json()
                if "error" in data:
                    print(f"  ❌ Error: {data['error'].get('message', 'Unknown')}")
                    return False
                print(f"  ✅ Connected! Account: @{data.get('username', 'Unknown')}")
                return True
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return False

async def test_odoo():
    """Test Odoo connection"""
    print("\n[ODOO] Testing...")

    url = os.getenv("ODOO_URL", "http://localhost:8069")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/web/database/list", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    print(f"  ✅ Odoo server reachable at {url}")
                    return True
                else:
                    print(f"  ❌ Error: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        print(f"     (Odoo server not running at {url})")
        return False

async def main():
    print("=" * 50)
    print("GOLD TIER - CONNECTION TEST")
    print("=" * 50)

    results = {}

    results["Facebook"] = await test_facebook()
    results["LinkedIn"] = await test_linkedin()
    results["Twitter"] = await test_twitter()
    results["Instagram"] = await test_instagram()
    results["Odoo"] = await test_odoo()

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    for service, status in results.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {service}")

    connected = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n  {connected}/{total} services connected")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
