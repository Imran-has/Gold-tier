"""
Social Media MCP Server
Provides Model Context Protocol interface for Facebook, Instagram, Twitter/X, and LinkedIn.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import aiohttp

from config.settings import config, RiskLevel, requires_approval


class SocialMCPServer:
    """
    MCP Server for social media operations.
    Supports Facebook, Instagram, Twitter/X, and LinkedIn platforms.
    """

    def __init__(self):
        self.name = "social_mcp"
        self.logger = logging.getLogger(f"gold.mcp.{self.name}")
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
        self._tools = self._define_tools()

    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Define available MCP tools for social media operations."""
        return {
            # Facebook tools
            "facebook_post": {
                "name": "facebook_post",
                "description": "Create a post on Facebook page",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Post content"},
                        "link": {"type": "string", "description": "Optional URL to share"},
                        "scheduled_time": {"type": "string", "description": "ISO datetime for scheduling"},
                    },
                    "required": ["message"],
                },
                "risk_level": RiskLevel.MEDIUM,
            },
            "facebook_get_insights": {
                "name": "facebook_get_insights",
                "description": "Get Facebook page insights and analytics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Metrics to retrieve",
                        },
                        "period": {"type": "string", "enum": ["day", "week", "month"]},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "facebook_list_posts": {
                "name": "facebook_list_posts",
                "description": "List recent Facebook posts",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 25},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "facebook_delete_post": {
                "name": "facebook_delete_post",
                "description": "Delete a Facebook post",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string", "description": "Post ID to delete"},
                    },
                    "required": ["post_id"],
                },
                "risk_level": RiskLevel.HIGH,
            },

            # Instagram tools
            "instagram_post": {
                "name": "instagram_post",
                "description": "Create an Instagram post (requires image)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "image_url": {"type": "string", "description": "Public URL of image"},
                        "caption": {"type": "string", "description": "Post caption"},
                        "hashtags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Hashtags to include",
                        },
                    },
                    "required": ["image_url"],
                },
                "risk_level": RiskLevel.MEDIUM,
            },
            "instagram_get_insights": {
                "name": "instagram_get_insights",
                "description": "Get Instagram account insights",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "instagram_list_media": {
                "name": "instagram_list_media",
                "description": "List recent Instagram media",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 25},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },

            # Twitter/X tools
            "twitter_post": {
                "name": "twitter_post",
                "description": "Create a tweet on Twitter/X",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Tweet content (max 280 chars)"},
                        "reply_to": {"type": "string", "description": "Tweet ID to reply to"},
                    },
                    "required": ["text"],
                },
                "risk_level": RiskLevel.MEDIUM,
            },
            "twitter_get_timeline": {
                "name": "twitter_get_timeline",
                "description": "Get user's Twitter timeline",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "twitter_get_mentions": {
                "name": "twitter_get_mentions",
                "description": "Get mentions of the account",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "twitter_delete_tweet": {
                "name": "twitter_delete_tweet",
                "description": "Delete a tweet",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tweet_id": {"type": "string", "description": "Tweet ID to delete"},
                    },
                    "required": ["tweet_id"],
                },
                "risk_level": RiskLevel.HIGH,
            },

            # LinkedIn tools
            "linkedin_post": {
                "name": "linkedin_post",
                "description": "Create a post on LinkedIn (personal or company page)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Post content"},
                        "visibility": {"type": "string", "enum": ["PUBLIC", "CONNECTIONS"], "default": "PUBLIC"},
                        "as_organization": {"type": "boolean", "description": "Post as organization/company", "default": False},
                    },
                    "required": ["text"],
                },
                "risk_level": RiskLevel.MEDIUM,
            },
            "linkedin_get_profile": {
                "name": "linkedin_get_profile",
                "description": "Get LinkedIn profile information",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "risk_level": RiskLevel.LOW,
            },
            "linkedin_list_posts": {
                "name": "linkedin_list_posts",
                "description": "List recent LinkedIn posts",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "linkedin_get_analytics": {
                "name": "linkedin_get_analytics",
                "description": "Get LinkedIn post and profile analytics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string", "description": "Specific post ID (optional)"},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "linkedin_delete_post": {
                "name": "linkedin_delete_post",
                "description": "Delete a LinkedIn post",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string", "description": "Post ID to delete"},
                    },
                    "required": ["post_id"],
                },
                "risk_level": RiskLevel.HIGH,
            },

            # Cross-platform tools
            "generate_content_summary": {
                "name": "generate_content_summary",
                "description": "Generate a summary of social media performance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "platforms": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["facebook", "instagram", "twitter", "linkedin"]},
                        },
                        "period": {"type": "string", "enum": ["day", "week", "month"]},
                    },
                },
                "risk_level": RiskLevel.LOW,
            },
            "cross_post": {
                "name": "cross_post",
                "description": "Post content to multiple platforms",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Content to post"},
                        "platforms": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["facebook", "instagram", "twitter", "linkedin"]},
                        },
                        "image_url": {"type": "string", "description": "Optional image URL"},
                    },
                    "required": ["content", "platforms"],
                },
                "risk_level": RiskLevel.MEDIUM,
            },
        }

    async def start(self) -> bool:
        """Start the Social Media MCP server."""
        self.session = aiohttp.ClientSession()
        self.is_running = True
        self.logger.info("Social Media MCP server started")
        return True

    async def stop(self) -> None:
        """Stop the Social Media MCP server."""
        if self.session:
            await self.session.close()
            self.session = None
        self.is_running = False
        self.logger.info("Social Media MCP server stopped")

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for MCP discovery."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["input_schema"],
            }
            for tool in self._tools.values()
        ]

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        approval_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Execute a tool by name with given arguments."""
        if tool_name not in self._tools:
            return {"error": f"Unknown tool: {tool_name}"}

        tool = self._tools[tool_name]

        # Check if approval is required
        if requires_approval(f"social.{tool_name}"):
            if approval_callback:
                approved = await approval_callback(tool_name, arguments)
                if not approved:
                    return {"error": "Action not approved", "requires_approval": True}
            else:
                return {
                    "error": "Action requires approval",
                    "requires_approval": True,
                    "risk_level": tool["risk_level"].value,
                }

        # Execute the tool
        method_name = f"_execute_{tool_name}"
        if hasattr(self, method_name):
            try:
                result = await getattr(self, method_name)(arguments)
                return {"success": True, "result": result}
            except Exception as e:
                self.logger.error(f"Tool execution error: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {"error": f"Tool not implemented: {tool_name}"}

    # Facebook implementations

    async def _execute_facebook_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Facebook post."""
        if not config.facebook.is_configured():
            return {"error": "Facebook not configured"}

        url = f"https://graph.facebook.com/v18.0/{config.facebook.page_id}/feed"
        params = {
            "message": args["message"],
            "access_token": config.facebook.access_token,
        }

        if args.get("link"):
            params["link"] = args["link"]

        if args.get("scheduled_time"):
            params["published"] = False
            params["scheduled_publish_time"] = int(
                datetime.fromisoformat(args["scheduled_time"]).timestamp()
            )

        async with self.session.post(url, data=params) as response:
            result = await response.json()
            if "error" in result:
                return {"error": result["error"].get("message", "Unknown error")}
            return {"post_id": result.get("id"), "scheduled": bool(args.get("scheduled_time"))}

    async def _execute_facebook_get_insights(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get Facebook page insights."""
        if not config.facebook.is_configured():
            return {"error": "Facebook not configured"}

        metrics = args.get("metrics", ["page_impressions", "page_engaged_users"])
        period = args.get("period", "day")

        url = f"https://graph.facebook.com/v18.0/{config.facebook.page_id}/insights"
        params = {
            "metric": ",".join(metrics),
            "period": period,
            "access_token": config.facebook.access_token,
        }

        async with self.session.get(url, params=params) as response:
            result = await response.json()
            if "error" in result:
                return {"error": result["error"].get("message", "Unknown error")}
            return {"insights": result.get("data", [])}

    async def _execute_facebook_list_posts(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List Facebook posts."""
        if not config.facebook.is_configured():
            return {"error": "Facebook not configured"}

        url = f"https://graph.facebook.com/v18.0/{config.facebook.page_id}/posts"
        params = {
            "limit": args.get("limit", 25),
            "access_token": config.facebook.access_token,
            "fields": "id,message,created_time,shares,likes.summary(true),comments.summary(true)",
        }

        async with self.session.get(url, params=params) as response:
            result = await response.json()
            if "error" in result:
                return {"error": result["error"].get("message", "Unknown error")}
            return result.get("data", [])

    async def _execute_facebook_delete_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a Facebook post."""
        if not config.facebook.is_configured():
            return {"error": "Facebook not configured"}

        url = f"https://graph.facebook.com/v18.0/{args['post_id']}"
        params = {"access_token": config.facebook.access_token}

        async with self.session.delete(url, params=params) as response:
            result = await response.json()
            if "error" in result:
                return {"error": result["error"].get("message", "Unknown error")}
            return {"deleted": True, "post_id": args["post_id"]}

    # Instagram implementations

    async def _execute_instagram_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create an Instagram post."""
        if not config.instagram.is_configured():
            return {"error": "Instagram not configured"}

        # Instagram requires a two-step process: create container, then publish
        caption = args.get("caption", "")
        if args.get("hashtags"):
            caption += " " + " ".join(f"#{tag}" for tag in args["hashtags"])

        # Step 1: Create media container
        container_url = f"https://graph.facebook.com/v18.0/{config.instagram.business_account_id}/media"
        container_params = {
            "image_url": args["image_url"],
            "caption": caption,
            "access_token": config.instagram.access_token,
        }

        async with self.session.post(container_url, data=container_params) as response:
            container_result = await response.json()
            if "error" in container_result:
                return {"error": container_result["error"].get("message", "Unknown error")}

            container_id = container_result.get("id")

        # Step 2: Publish the container
        publish_url = f"https://graph.facebook.com/v18.0/{config.instagram.business_account_id}/media_publish"
        publish_params = {
            "creation_id": container_id,
            "access_token": config.instagram.access_token,
        }

        async with self.session.post(publish_url, data=publish_params) as response:
            result = await response.json()
            if "error" in result:
                return {"error": result["error"].get("message", "Unknown error")}
            return {"post_id": result.get("id")}

    async def _execute_instagram_get_insights(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get Instagram account insights."""
        if not config.instagram.is_configured():
            return {"error": "Instagram not configured"}

        metrics = args.get("metrics", ["impressions", "reach", "profile_views"])

        url = f"https://graph.facebook.com/v18.0/{config.instagram.business_account_id}/insights"
        params = {
            "metric": ",".join(metrics),
            "period": "day",
            "access_token": config.instagram.access_token,
        }

        async with self.session.get(url, params=params) as response:
            result = await response.json()
            if "error" in result:
                return {"error": result["error"].get("message", "Unknown error")}
            return {"insights": result.get("data", [])}

    async def _execute_instagram_list_media(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List Instagram media."""
        if not config.instagram.is_configured():
            return {"error": "Instagram not configured"}

        url = f"https://graph.facebook.com/v18.0/{config.instagram.business_account_id}/media"
        params = {
            "limit": args.get("limit", 25),
            "access_token": config.instagram.access_token,
            "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count",
        }

        async with self.session.get(url, params=params) as response:
            result = await response.json()
            if "error" in result:
                return {"error": result["error"].get("message", "Unknown error")}
            return result.get("data", [])

    # Twitter implementations

    async def _execute_twitter_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a tweet."""
        if not config.twitter.is_configured():
            return {"error": "Twitter not configured"}

        # Twitter API v2 requires OAuth 1.0a or OAuth 2.0
        # This is a simplified implementation - full implementation needs proper auth
        url = "https://api.twitter.com/2/tweets"
        headers = {
            "Authorization": f"Bearer {config.twitter.bearer_token}",
            "Content-Type": "application/json",
        }

        payload = {"text": args["text"][:280]}  # Enforce character limit

        if args.get("reply_to"):
            payload["reply"] = {"in_reply_to_tweet_id": args["reply_to"]}

        async with self.session.post(url, json=payload, headers=headers) as response:
            result = await response.json()
            if "errors" in result:
                return {"error": result["errors"][0].get("message", "Unknown error")}
            return {"tweet_id": result.get("data", {}).get("id")}

    async def _execute_twitter_get_timeline(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get Twitter timeline."""
        if not config.twitter.is_configured():
            return {"error": "Twitter not configured"}

        url = "https://api.twitter.com/2/users/me/tweets"
        headers = {"Authorization": f"Bearer {config.twitter.bearer_token}"}
        params = {
            "max_results": min(args.get("limit", 20), 100),
            "tweet.fields": "created_at,public_metrics",
        }

        async with self.session.get(url, headers=headers, params=params) as response:
            result = await response.json()
            if "errors" in result:
                return {"error": result["errors"][0].get("message", "Unknown error")}
            return result.get("data", [])

    async def _execute_twitter_get_mentions(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get Twitter mentions."""
        if not config.twitter.is_configured():
            return {"error": "Twitter not configured"}

        url = "https://api.twitter.com/2/users/me/mentions"
        headers = {"Authorization": f"Bearer {config.twitter.bearer_token}"}
        params = {
            "max_results": min(args.get("limit", 20), 100),
            "tweet.fields": "created_at,author_id,public_metrics",
        }

        async with self.session.get(url, headers=headers, params=params) as response:
            result = await response.json()
            if "errors" in result:
                return {"error": result["errors"][0].get("message", "Unknown error")}
            return result.get("data", [])

    async def _execute_twitter_delete_tweet(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a tweet."""
        if not config.twitter.is_configured():
            return {"error": "Twitter not configured"}

        url = f"https://api.twitter.com/2/tweets/{args['tweet_id']}"
        headers = {"Authorization": f"Bearer {config.twitter.bearer_token}"}

        async with self.session.delete(url, headers=headers) as response:
            result = await response.json()
            if "errors" in result:
                return {"error": result["errors"][0].get("message", "Unknown error")}
            return {"deleted": True, "tweet_id": args["tweet_id"]}

    # LinkedIn implementations

    async def _execute_linkedin_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a LinkedIn post."""
        if not config.linkedin.is_configured():
            return {"error": "LinkedIn not configured"}

        headers = {
            "Authorization": f"Bearer {config.linkedin.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        # Determine author (person or organization)
        if args.get("as_organization") and config.linkedin.organization_id:
            author = f"urn:li:organization:{config.linkedin.organization_id}"
        else:
            # Get user profile first to get the person URN
            profile = await self._execute_linkedin_get_profile({})
            if "error" in profile:
                return profile
            author = f"urn:li:person:{profile.get('id', '')}"

        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": args["text"]
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": args.get("visibility", "PUBLIC")
            }
        }

        url = "https://api.linkedin.com/v2/ugcPosts"

        async with self.session.post(url, json=payload, headers=headers) as response:
            if response.status == 201:
                result = await response.json()
                return {"post_id": result.get("id"), "status": "published"}
            else:
                result = await response.json()
                return {"error": result.get("message", f"HTTP {response.status}")}

    async def _execute_linkedin_get_profile(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get LinkedIn profile information."""
        if not config.linkedin.is_configured():
            return {"error": "LinkedIn not configured"}

        headers = {
            "Authorization": f"Bearer {config.linkedin.access_token}",
        }

        url = "https://api.linkedin.com/v2/me"

        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                return {
                    "id": result.get("id"),
                    "firstName": result.get("localizedFirstName"),
                    "lastName": result.get("localizedLastName"),
                }
            else:
                result = await response.json()
                return {"error": result.get("message", f"HTTP {response.status}")}

    async def _execute_linkedin_list_posts(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List LinkedIn posts."""
        if not config.linkedin.is_configured():
            return {"error": "LinkedIn not configured"}

        headers = {
            "Authorization": f"Bearer {config.linkedin.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        # Get user profile first
        profile = await self._execute_linkedin_get_profile({})
        if "error" in profile:
            return profile

        author = f"urn:li:person:{profile.get('id', '')}"
        limit = args.get("limit", 20)

        url = f"https://api.linkedin.com/v2/ugcPosts?q=authors&authors=List({author})&count={limit}"

        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                return result.get("elements", [])
            else:
                result = await response.json()
                return {"error": result.get("message", f"HTTP {response.status}")}

    async def _execute_linkedin_get_analytics(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get LinkedIn analytics."""
        if not config.linkedin.is_configured():
            return {"error": "LinkedIn not configured"}

        headers = {
            "Authorization": f"Bearer {config.linkedin.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        post_id = args.get("post_id")

        if post_id:
            # Get specific post analytics
            url = f"https://api.linkedin.com/v2/socialActions/{post_id}"
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return {"post_analytics": result}
                else:
                    return {"error": f"HTTP {response.status}"}
        else:
            # Get general profile statistics
            return {
                "note": "Profile analytics requires LinkedIn Marketing API access",
                "status": "limited_access"
            }

    async def _execute_linkedin_delete_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a LinkedIn post."""
        if not config.linkedin.is_configured():
            return {"error": "LinkedIn not configured"}

        headers = {
            "Authorization": f"Bearer {config.linkedin.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        post_id = args["post_id"]
        url = f"https://api.linkedin.com/v2/ugcPosts/{post_id}"

        async with self.session.delete(url, headers=headers) as response:
            if response.status == 204:
                return {"deleted": True, "post_id": post_id}
            else:
                result = await response.json()
                return {"error": result.get("message", f"HTTP {response.status}")}

    # Cross-platform tools

    async def _execute_generate_content_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cross-platform content summary."""
        platforms = args.get("platforms", ["facebook", "instagram", "twitter"])
        period = args.get("period", "week")

        summary = {
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "platforms": {},
        }

        for platform in platforms:
            if platform == "facebook" and config.facebook.is_configured():
                insights = await self._execute_facebook_get_insights({"period": period})
                posts = await self._execute_facebook_list_posts({"limit": 10})
                summary["platforms"]["facebook"] = {
                    "insights": insights.get("insights", []),
                    "recent_posts": len(posts) if isinstance(posts, list) else 0,
                }
            elif platform == "instagram" and config.instagram.is_configured():
                insights = await self._execute_instagram_get_insights({})
                media = await self._execute_instagram_list_media({"limit": 10})
                summary["platforms"]["instagram"] = {
                    "insights": insights.get("insights", []),
                    "recent_media": len(media) if isinstance(media, list) else 0,
                }
            elif platform == "twitter" and config.twitter.is_configured():
                timeline = await self._execute_twitter_get_timeline({"limit": 10})
                mentions = await self._execute_twitter_get_mentions({"limit": 10})
                summary["platforms"]["twitter"] = {
                    "recent_tweets": len(timeline) if isinstance(timeline, list) else 0,
                    "recent_mentions": len(mentions) if isinstance(mentions, list) else 0,
                }
            elif platform == "linkedin" and config.linkedin.is_configured():
                posts = await self._execute_linkedin_list_posts({"limit": 10})
                profile = await self._execute_linkedin_get_profile({})
                summary["platforms"]["linkedin"] = {
                    "profile": profile if "error" not in profile else None,
                    "recent_posts": len(posts) if isinstance(posts, list) else 0,
                }
            else:
                summary["platforms"][platform] = {"status": "not_configured"}

        return summary

    async def _execute_cross_post(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Post to multiple platforms."""
        content = args["content"]
        platforms = args["platforms"]
        image_url = args.get("image_url")

        results = {}

        for platform in platforms:
            if platform == "facebook":
                result = await self._execute_facebook_post({"message": content})
                results["facebook"] = result
            elif platform == "instagram":
                if image_url:
                    result = await self._execute_instagram_post({
                        "image_url": image_url,
                        "caption": content,
                    })
                    results["instagram"] = result
                else:
                    results["instagram"] = {"error": "Instagram requires an image"}
            elif platform == "twitter":
                result = await self._execute_twitter_post({"text": content[:280]})
                results["twitter"] = result
            elif platform == "linkedin":
                result = await self._execute_linkedin_post({"text": content})
                results["linkedin"] = result

        return {"cross_post_results": results}

    async def health_check(self) -> Dict[str, Any]:
        """Health check for Social Media MCP server."""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "platforms": {
                "facebook": {
                    "configured": config.facebook.is_configured(),
                    "page_id": config.facebook.page_id if config.facebook.is_configured() else None,
                },
                "instagram": {
                    "configured": config.instagram.is_configured(),
                    "account_id": config.instagram.business_account_id if config.instagram.is_configured() else None,
                },
                "twitter": {
                    "configured": config.twitter.is_configured(),
                },
                "linkedin": {
                    "configured": config.linkedin.is_configured(),
                    "organization_id": config.linkedin.organization_id if config.linkedin.organization_id else None,
                },
            },
            "tools_available": len(self._tools),
        }
