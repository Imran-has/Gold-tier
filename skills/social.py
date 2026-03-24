"""
Social Media Skills for Gold Tier
Skills for Facebook, Instagram, Twitter/X, and LinkedIn operations.
"""

from typing import Any, Dict, List, Optional

from config.settings import RiskLevel
from .base import BaseSkill, SkillResult, register_skill


@register_skill
class PostToFacebookSkill(BaseSkill):
    """Skill to post content to Facebook."""

    name = "post_to_facebook"
    description = "Create a post on Facebook page"
    risk_level = RiskLevel.MEDIUM
    requires_mcp = "social"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Post content",
                },
                "link": {
                    "type": "string",
                    "description": "Optional URL to share",
                },
                "scheduled_time": {
                    "type": "string",
                    "description": "ISO datetime for scheduling (optional)",
                },
            },
            "required": ["message"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute Facebook post creation."""
        self.logger.info("Creating Facebook post")

        scheduled = parameters.get("scheduled_time")
        return SkillResult(
            success=True,
            data={
                "platform": "facebook",
                "status": "scheduled" if scheduled else "posted",
                "message_preview": parameters["message"][:100],
                "note": "Requires Social MCP server connection",
            },
        )


@register_skill
class PostToInstagramSkill(BaseSkill):
    """Skill to post content to Instagram."""

    name = "post_to_instagram"
    description = "Create a post on Instagram (requires image)"
    risk_level = RiskLevel.MEDIUM
    requires_mcp = "social"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "Public URL of image to post",
                },
                "caption": {
                    "type": "string",
                    "description": "Post caption",
                },
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Hashtags to include (without #)",
                },
                "location": {
                    "type": "string",
                    "description": "Location tag (optional)",
                },
            },
            "required": ["image_url"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute Instagram post creation."""
        self.logger.info("Creating Instagram post")

        hashtag_count = len(parameters.get("hashtags", []))
        return SkillResult(
            success=True,
            data={
                "platform": "instagram",
                "status": "posted",
                "hashtag_count": hashtag_count,
                "note": "Requires Social MCP server connection",
            },
        )


@register_skill
class PostToTwitterSkill(BaseSkill):
    """Skill to post content to Twitter/X."""

    name = "post_to_twitter"
    description = "Create a tweet on Twitter/X"
    risk_level = RiskLevel.MEDIUM
    requires_mcp = "social"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Tweet content (max 280 characters)",
                    "maxLength": 280,
                },
                "reply_to": {
                    "type": "string",
                    "description": "Tweet ID to reply to (optional)",
                },
                "media_urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "URLs of media to attach",
                },
            },
            "required": ["text"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute Twitter post creation."""
        text = parameters["text"]

        if len(text) > 280:
            return SkillResult(
                success=False,
                error="Tweet exceeds 280 character limit",
            )

        self.logger.info("Creating Twitter post")

        return SkillResult(
            success=True,
            data={
                "platform": "twitter",
                "status": "posted",
                "character_count": len(text),
                "is_reply": bool(parameters.get("reply_to")),
                "note": "Requires Social MCP server connection",
            },
        )


@register_skill
class PostToLinkedInSkill(BaseSkill):
    """Skill to post content to LinkedIn."""

    name = "post_to_linkedin"
    description = "Create a post on LinkedIn (personal or company page)"
    risk_level = RiskLevel.MEDIUM
    requires_mcp = "social"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Post content",
                },
                "visibility": {
                    "type": "string",
                    "enum": ["PUBLIC", "CONNECTIONS"],
                    "description": "Post visibility",
                    "default": "PUBLIC",
                },
                "as_organization": {
                    "type": "boolean",
                    "description": "Post as company/organization page",
                    "default": False,
                },
            },
            "required": ["text"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute LinkedIn post creation."""
        self.logger.info("Creating LinkedIn post")

        return SkillResult(
            success=True,
            data={
                "platform": "linkedin",
                "status": "posted",
                "visibility": parameters.get("visibility", "PUBLIC"),
                "as_organization": parameters.get("as_organization", False),
                "note": "Requires Social MCP server connection",
            },
        )


@register_skill
class GetLinkedInAnalyticsSkill(BaseSkill):
    """Skill to get LinkedIn analytics."""

    name = "get_linkedin_analytics"
    description = "Get LinkedIn post and profile analytics"
    risk_level = RiskLevel.LOW
    requires_mcp = "social"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "Specific post ID (optional)",
                },
                "include_profile": {
                    "type": "boolean",
                    "description": "Include profile analytics",
                    "default": True,
                },
            },
            "required": [],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute LinkedIn analytics retrieval."""
        self.logger.info("Getting LinkedIn analytics")

        return SkillResult(
            success=True,
            data={
                "platform": "linkedin",
                "post_id": parameters.get("post_id"),
                "status": "fetched",
                "note": "Requires Social MCP server connection",
            },
        )


@register_skill
class CrossPostSkill(BaseSkill):
    """Skill to post content across multiple platforms."""

    name = "cross_post"
    description = "Post content to multiple social media platforms"
    risk_level = RiskLevel.MEDIUM
    requires_mcp = "social"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content to post",
                },
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["facebook", "instagram", "twitter", "linkedin"],
                    },
                    "description": "Platforms to post to",
                },
                "image_url": {
                    "type": "string",
                    "description": "Image URL (required for Instagram)",
                },
                "adapt_content": {
                    "type": "boolean",
                    "description": "Adapt content for each platform",
                    "default": True,
                },
            },
            "required": ["content", "platforms"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute cross-platform posting."""
        platforms = parameters["platforms"]
        content = parameters["content"]

        self.logger.info(f"Cross-posting to: {', '.join(platforms)}")

        results = {}
        for platform in platforms:
            if platform == "instagram" and not parameters.get("image_url"):
                results[platform] = {"status": "skipped", "reason": "Image required"}
            elif platform == "twitter" and len(content) > 280:
                if parameters.get("adapt_content", True):
                    results[platform] = {"status": "adapted", "truncated": True}
                else:
                    results[platform] = {"status": "skipped", "reason": "Content too long"}
            else:
                results[platform] = {"status": "posted"}

        return SkillResult(
            success=True,
            data={
                "platforms": platforms,
                "results": results,
                "note": "Requires Social MCP server connection",
            },
        )


@register_skill
class GetSocialAnalyticsSkill(BaseSkill):
    """Skill to get analytics from social media platforms."""

    name = "get_social_analytics"
    description = "Get analytics and insights from social media platforms"
    risk_level = RiskLevel.LOW
    requires_mcp = "social"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["facebook", "instagram", "twitter", "linkedin"],
                    },
                    "description": "Platforms to get analytics from",
                },
                "period": {
                    "type": "string",
                    "enum": ["day", "week", "month"],
                    "default": "week",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific metrics to retrieve",
                },
            },
            "required": ["platforms"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute analytics retrieval."""
        platforms = parameters["platforms"]
        period = parameters.get("period", "week")

        self.logger.info(f"Getting analytics for: {', '.join(platforms)}")

        return SkillResult(
            success=True,
            data={
                "platforms": platforms,
                "period": period,
                "analytics": {
                    platform: {"status": "fetched"} for platform in platforms
                },
                "note": "Requires Social MCP server connection",
            },
        )


@register_skill
class DeleteSocialPostSkill(BaseSkill):
    """Skill to delete posts from social media platforms."""

    name = "delete_social_post"
    description = "Delete a post from a social media platform"
    risk_level = RiskLevel.HIGH
    requires_mcp = "social"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "enum": ["facebook", "instagram", "twitter", "linkedin"],
                    "description": "Platform to delete from",
                },
                "post_id": {
                    "type": "string",
                    "description": "ID of the post to delete",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for deletion (for audit)",
                },
            },
            "required": ["platform", "post_id"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute post deletion."""
        self.logger.info(f"Deleting post {parameters['post_id']} from {parameters['platform']}")

        return SkillResult(
            success=True,
            data={
                "platform": parameters["platform"],
                "post_id": parameters["post_id"],
                "status": "deleted",
                "note": "Requires Social MCP server connection",
            },
        )


@register_skill
class ScheduleContentSkill(BaseSkill):
    """Skill to schedule content for future posting."""

    name = "schedule_content"
    description = "Schedule content for future posting across platforms"
    risk_level = RiskLevel.LOW
    requires_mcp = "social"

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content to post",
                },
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["facebook", "instagram", "twitter", "linkedin"],
                    },
                },
                "scheduled_time": {
                    "type": "string",
                    "description": "ISO datetime to post",
                },
                "image_url": {
                    "type": "string",
                    "description": "Image URL (optional)",
                },
            },
            "required": ["content", "platforms", "scheduled_time"],
        }

    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute content scheduling."""
        self.logger.info(f"Scheduling content for {parameters['scheduled_time']}")

        return SkillResult(
            success=True,
            data={
                "platforms": parameters["platforms"],
                "scheduled_time": parameters["scheduled_time"],
                "status": "scheduled",
                "note": "Requires Social MCP server connection",
            },
        )
