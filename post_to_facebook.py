#!/usr/bin/env python3
"""
Post to Facebook Page - Karachi Ka King
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

# Load environment variables
env_path = Path(__file__).parent / "config" / ".env"
load_dotenv(env_path, override=True)

async def post_to_facebook(message: str):
    """Post a message to Facebook page"""

    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")

    print(f"Posting to Page ID: {page_id}")
    print(f"Message: {message}")
    print("-" * 40)

    url = f"https://graph.facebook.com/v18.0/{page_id}/feed"

    params = {
        "message": message,
        "access_token": access_token
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=params) as response:
            result = await response.json()

            if "error" in result:
                print(f"❌ Error: {result['error'].get('message', 'Unknown error')}")
                return False
            else:
                post_id = result.get("id")
                print(f"✅ Post successful!")
                print(f"Post ID: {post_id}")
                print(f"View at: https://www.facebook.com/{post_id}")
                return True

async def main():
    message = """🤖 Gold Tier AI Employee - First Post!

This post was automatically created by the Gold Tier Autonomous AI Employee system.

Karachi Ka King is now powered by AI! 🚀

#AI #Automation #KarachiKaKing #GoldTier"""

    await post_to_facebook(message)

if __name__ == "__main__":
    asyncio.run(main())
