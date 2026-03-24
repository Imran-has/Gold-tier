"""
Base Agent Framework for Gold Tier
Provides foundation for all agent implementations.
"""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config.settings import LOGS_DIR, EVENTS_DIR, config


class EventType(Enum):
    """Types of events that can be processed."""
    TASK_RECEIVED = "task_received"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RECEIVED = "approval_received"
    ERROR = "error"
    AUDIT_TRIGGERED = "audit_triggered"
    INTEGRATION_STATUS = "integration_status"


@dataclass
class Event:
    """Event data structure for agent communication."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.TASK_RECEIVED
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=EventType(data.get("type", "task_received")),
            source=data.get("source", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
        )

    def save(self, directory: Optional[Path] = None) -> Path:
        """Save event to JSON file."""
        dir_path = directory or EVENTS_DIR
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"{self.id}.json"
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return file_path


class BaseAgent(ABC):
    """
    Base class for all Gold tier agents.
    Provides logging, event handling, and lifecycle management.
    """

    def __init__(self, name: str):
        self.name = name
        self.id = str(uuid.uuid4())
        self.logger = self._setup_logger()
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        self.is_running = False
        self._audit_log: List[Dict[str, Any]] = []

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for this agent."""
        logger = logging.getLogger(f"gold.{self.name}")
        logger.setLevel(getattr(logging, config.log_level))

        if not logger.handlers:
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(config.log_format))
            logger.addHandler(console_handler)

            # File handler
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(LOGS_DIR / f"{self.name}.log")
            file_handler.setFormatter(logging.Formatter(config.log_format))
            logger.addHandler(file_handler)

        return logger

    def register_handler(self, event_type: EventType, handler: Callable) -> None:
        """Register an event handler."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        self.logger.debug(f"Registered handler for {event_type.value}")

    def emit_event(self, event: Event) -> None:
        """Emit an event to all registered handlers."""
        event.save()
        handlers = self.event_handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler: {e}")

    def audit_log(self, action: str, details: Dict[str, Any], success: bool = True) -> None:
        """
        Record an action to the audit log.
        All actions must be auditable.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "agent_id": self.id,
            "action": action,
            "details": details,
            "success": success,
        }
        self._audit_log.append(entry)
        self.logger.info(f"AUDIT: {action} - success={success}")

        # Persist audit log entry
        self._persist_audit_entry(entry)

    def _persist_audit_entry(self, entry: Dict[str, Any]) -> None:
        """Persist audit entry to file."""
        audit_dir = LOGS_DIR / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        audit_file = audit_dir / f"audit_{date_str}.jsonl"

        with open(audit_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get the current audit log."""
        return self._audit_log.copy()

    @abstractmethod
    async def start(self) -> None:
        """Start the agent."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the agent."""
        pass

    @abstractmethod
    async def process(self, event: Event) -> Any:
        """Process an event."""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the agent."""
        return {
            "agent": self.name,
            "id": self.id,
            "is_running": self.is_running,
            "timestamp": datetime.now().isoformat(),
        }


class AgentRegistry:
    """Registry for managing multiple agents."""

    _instance = None
    _agents: Dict[str, BaseAgent] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, agent: BaseAgent) -> None:
        """Register an agent."""
        self._agents[agent.name] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)

    def all(self) -> Dict[str, BaseAgent]:
        """Get all registered agents."""
        return self._agents.copy()

    async def start_all(self) -> None:
        """Start all registered agents."""
        for agent in self._agents.values():
            await agent.start()

    async def stop_all(self) -> None:
        """Stop all registered agents."""
        for agent in self._agents.values():
            await agent.stop()

    async def health_check_all(self) -> Dict[str, Any]:
        """Health check all agents."""
        results = {}
        for name, agent in self._agents.items():
            results[name] = await agent.health_check()
        return results


# Global registry instance
agent_registry = AgentRegistry()
