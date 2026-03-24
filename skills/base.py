"""
Base Skill Framework for Gold Tier
All AI capabilities are implemented as modular, reusable, and auditable skills.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from config.settings import RiskLevel, requires_approval, LOGS_DIR


class SkillStatus(Enum):
    """Status of skill execution."""
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SkillResult:
    """Result of a skill execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    execution_time_ms: float = 0
    audit_entry: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "requires_approval": self.requires_approval,
            "approval_reason": self.approval_reason,
            "execution_time_ms": self.execution_time_ms,
        }


class BaseSkill(ABC):
    """
    Base class for all Gold tier skills.
    Skills are modular, reusable, and auditable units of functionality.
    """

    # Class-level attributes to be overridden
    name: str = "base_skill"
    description: str = "Base skill"
    risk_level: RiskLevel = RiskLevel.LOW
    requires_mcp: Optional[str] = None  # Which MCP server this skill needs

    def __init__(self):
        self.logger = logging.getLogger(f"gold.skill.{self.name}")
        self._audit_log: List[Dict[str, Any]] = []

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> SkillResult:
        """Execute the skill with given parameters."""
        pass

    @abstractmethod
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Get JSON schema for skill parameters."""
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> Optional[str]:
        """
        Validate parameters against schema.
        Returns error message if invalid, None if valid.
        """
        schema = self.get_parameter_schema()
        required = schema.get("required", [])

        for field in required:
            if field not in parameters:
                return f"Missing required parameter: {field}"

        return None

    def check_approval_required(self) -> bool:
        """Check if this skill requires approval before execution."""
        return requires_approval(f"skill.{self.name}")

    async def run(
        self,
        parameters: Dict[str, Any],
        approval_callback: Optional[Callable] = None,
    ) -> SkillResult:
        """
        Run the skill with validation, approval check, and auditing.
        This is the main entry point for skill execution.
        """
        start_time = datetime.now()

        # Validate parameters
        validation_error = self.validate_parameters(parameters)
        if validation_error:
            return SkillResult(
                success=False,
                error=validation_error,
            )

        # Check if approval is required
        if self.check_approval_required():
            if approval_callback:
                approved = await approval_callback(self.name, parameters, self.risk_level)
                if not approved:
                    return SkillResult(
                        success=False,
                        requires_approval=True,
                        approval_reason=f"Skill '{self.name}' requires approval (risk: {self.risk_level.value})",
                    )
            else:
                return SkillResult(
                    success=False,
                    requires_approval=True,
                    approval_reason=f"Skill '{self.name}' requires approval (risk: {self.risk_level.value})",
                )

        # Execute the skill
        try:
            result = await self.execute(parameters)
            result.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        except Exception as e:
            self.logger.error(f"Skill execution error: {e}")
            result = SkillResult(
                success=False,
                error=str(e),
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

        # Audit the execution
        audit_entry = self._create_audit_entry(parameters, result)
        result.audit_entry = audit_entry
        self._persist_audit(audit_entry)

        return result

    def _create_audit_entry(
        self,
        parameters: Dict[str, Any],
        result: SkillResult,
    ) -> Dict[str, Any]:
        """Create an audit entry for the skill execution."""
        return {
            "timestamp": datetime.now().isoformat(),
            "skill": self.name,
            "risk_level": self.risk_level.value,
            "parameters": self._sanitize_parameters(parameters),
            "success": result.success,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
        }

    def _sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from parameters for logging."""
        sensitive_keys = ["password", "token", "secret", "api_key", "access_token"]
        sanitized = {}

        for key, value in parameters.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value

        return sanitized

    def _persist_audit(self, entry: Dict[str, Any]) -> None:
        """Persist audit entry to file."""
        audit_dir = LOGS_DIR / "skills"
        audit_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        audit_file = audit_dir / f"skills_{date_str}.jsonl"

        with open(audit_file, "a") as f:
            f.write(json.dumps(entry) + "\n")


class SkillRegistry:
    """
    Registry for managing and discovering skills.
    Provides a central place to register and retrieve skills.
    """

    _instance = None
    _skills: Dict[str, Type[BaseSkill]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, skill_class: Type[BaseSkill]) -> None:
        """Register a skill class."""
        skill = skill_class()
        self._skills[skill.name] = skill_class

    def get(self, name: str) -> Optional[BaseSkill]:
        """Get an instance of a skill by name."""
        skill_class = self._skills.get(name)
        if skill_class:
            return skill_class()
        return None

    def list_skills(self) -> List[Dict[str, Any]]:
        """List all registered skills with their metadata."""
        skills = []
        for name, skill_class in self._skills.items():
            skill = skill_class()
            skills.append({
                "name": skill.name,
                "description": skill.description,
                "risk_level": skill.risk_level.value,
                "requires_mcp": skill.requires_mcp,
                "parameter_schema": skill.get_parameter_schema(),
            })
        return skills

    def get_skills_by_risk(self, risk_level: RiskLevel) -> List[str]:
        """Get skills filtered by risk level."""
        matching = []
        for name, skill_class in self._skills.items():
            skill = skill_class()
            if skill.risk_level == risk_level:
                matching.append(name)
        return matching

    def get_skills_by_mcp(self, mcp_server: str) -> List[str]:
        """Get skills that require a specific MCP server."""
        matching = []
        for name, skill_class in self._skills.items():
            skill = skill_class()
            if skill.requires_mcp == mcp_server:
                matching.append(name)
        return matching


# Global registry instance
skill_registry = SkillRegistry()


def register_skill(skill_class: Type[BaseSkill]) -> Type[BaseSkill]:
    """Decorator to register a skill class."""
    skill_registry.register(skill_class)
    return skill_class
