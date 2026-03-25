#!/usr/bin/env python3
"""
Post to LinkedIn - AI Startups
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

# Load environment variables
env_path = Path(__file__).parent / "config" / ".env"
load_dotenv(env_path, override=True)

async def post_to_linkedin(text: str):
    """Post a message to LinkedIn"""

    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    async with aiohttp.ClientSession() as session:

        # Step 1: Get user URN
        async with session.get("https://api.linkedin.com/v2/me", headers=headers) as me_resp:
            me = await me_resp.json()
            if me_resp.status != 200:
                print(f"❌ Auth failed: {me_resp.status} - {me}")
                return False

            person_urn = f"urn:li:person:{me['id']}"
            print(f"Logged in as: {me.get('localizedFirstName')} {me.get('localizedLastName')}")

        # Step 2: Post content
        payload = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        async with session.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=payload,
        ) as response:
            result = await response.json()

            if response.status == 201:
                post_id = response.headers.get("x-restli-id")
                print(f"✅ Post successful!")
                print(f"Post ID: {post_id}")
                return True
            else:
                print(f"❌ Error: {result}")
                return False


async def main():
    message = """🚀 Top AI Startup Companies to Watch in 2026

The AI revolution is accelerating! Here are the most exciting AI startups making waves:

1. Anthropic - Safety-focused AI, creators of Claude
2. OpenAI - GPT-4, ChatGPT, leading LLM research
3. Mistral AI - Open-source European AI powerhouse
4. Cohere - Enterprise AI for business automation
5. Perplexity AI - AI-powered search engine
6. xAI (Grok) - Elon Musk's AI venture
7. Stability AI - Generative image & media AI
8. Hugging Face - Open-source AI model hub
9. Scale AI - AI data infrastructure & labeling
10. ElevenLabs - AI voice & audio generation

💡 Which AI startup are you most excited about?

#AI #ArtificialIntelligence #Startups #Tech #Innovation #MachineLearning"""

    await post_to_linkedin(message)


if __name__ == "__main__":
    asyncio.run(main())
