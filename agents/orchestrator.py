"""
Gold Tier Orchestrator
Main orchestrator that coordinates all Gold tier components.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import (
    config,
    IntegrationStatus,
    LOGS_DIR,
    REPORTS_DIR,
)
from .base import BaseAgent, Event, EventType, agent_registry
from .ralph_loop import RalphWiggumLoop, TaskResult


class GoldOrchestrator(BaseAgent):
    """
    Main orchestrator for Gold tier operations.
    Coordinates MCP servers, skills, and the Ralph Wiggum Loop.
    """

    def __init__(self):
        super().__init__("gold_orchestrator")
        self.ralph_loop = RalphWiggumLoop()
        self.mcp_servers: Dict[str, Any] = {}
        self.integration_status: Dict[str, IntegrationStatus] = {}
        self._startup_time: Optional[datetime] = None

    async def start(self) -> None:
        """Start the Gold tier orchestrator and all components."""
        self.is_running = True
        self._startup_time = datetime.now()
        self.logger.info("Starting Gold Tier Orchestrator...")

        # Register with global registry
        agent_registry.register(self)
        agent_registry.register(self.ralph_loop)

        # Start Ralph Wiggum Loop
        await self.ralph_loop.start()

        # Initialize MCP servers (they will be started lazily)
        await self._initialize_mcp_servers()

        # Check integration status
        self.integration_status = config.get_integration_status()

        self.audit_log("orchestrator_started", {
            "integrations": {k: v.value for k, v in self.integration_status.items()},
        })

        self.logger.info("Gold Tier Orchestrator started successfully")

    async def stop(self) -> None:
        """Stop the Gold tier orchestrator and all components."""
        self.logger.info("Stopping Gold Tier Orchestrator...")

        # Stop Ralph Wiggum Loop
        await self.ralph_loop.stop()

        # Stop MCP servers
        for name, server in self.mcp_servers.items():
            if hasattr(server, 'stop'):
                await server.stop()
                self.logger.info(f"Stopped MCP server: {name}")

        self.is_running = False
        self.audit_log("orchestrator_stopped", {})
        self.logger.info("Gold Tier Orchestrator stopped")

    async def process(self, event: Event) -> Any:
        """Process an event through the orchestrator."""
        self.logger.info(f"Processing event: {event.type.value}")

        if event.type == EventType.TASK_RECEIVED:
            # Route task to Ralph Wiggum Loop
            return await self.ralph_loop.process(event)
        elif event.type == EventType.AUDIT_TRIGGERED:
            # Handle audit request
            return await self._handle_audit(event)
        else:
            self.logger.warning(f"Unhandled event type: {event.type.value}")
            return None

    async def _initialize_mcp_servers(self) -> None:
        """Initialize MCP server references."""
        # MCP servers will be imported and started on demand
        self.mcp_servers = {
            "odoo": None,
            "social": None,
            "audit": None,
        }
        self.logger.info("MCP server placeholders initialized")

    async def _handle_audit(self, event: Event) -> Dict[str, Any]:
        """Handle an audit event."""
        audit_type = event.data.get("audit_type", "full")
        self.logger.info(f"Running {audit_type} audit...")

        report = await self.generate_audit_report(audit_type)

        # Save report
        self._save_audit_report(report)

        return report

    async def execute_task(
        self,
        description: str,
        action: str,
        parameters: Dict[str, Any] = None,
        steps: List[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Execute a task through the Ralph Wiggum Loop.
        Convenience method for programmatic task submission.
        """
        event = Event(
            type=EventType.TASK_RECEIVED,
            source="orchestrator",
            data={
                "description": description,
                "action": action,
                "parameters": parameters or {},
                "steps": steps,
            },
        )
        return await self.ralph_loop.process(event)

    async def generate_audit_report(self, audit_type: str = "full") -> Dict[str, Any]:
        """Generate an audit report of the system state."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "audit_type": audit_type,
            "system_status": {
                "orchestrator_running": self.is_running,
                "uptime_seconds": (datetime.now() - self._startup_time).total_seconds()
                if self._startup_time else 0,
            },
            "integration_status": {k: v.value for k, v in self.integration_status.items()},
            "ralph_loop_status": await self.ralph_loop.health_check(),
            "mcp_servers": {},
            "recent_tasks": {
                "active": len(self.ralph_loop.active_tasks),
                "completed": len(self.ralph_loop.completed_tasks),
            },
        }

        # Add MCP server status
        for name, server in self.mcp_servers.items():
            if server and hasattr(server, 'health_check'):
                report["mcp_servers"][name] = await server.health_check()
            else:
                report["mcp_servers"][name] = {"status": "not_started"}

        return report

    async def generate_ceo_briefing(self) -> Dict[str, Any]:
        """Generate a CEO-level briefing of system and business status."""
        audit_report = await self.generate_audit_report()

        briefing = {
            "generated_at": datetime.now().isoformat(),
            "executive_summary": self._generate_executive_summary(audit_report),
            "system_health": self._assess_system_health(audit_report),
            "integration_summary": self._summarize_integrations(audit_report),
            "recommendations": self._generate_recommendations(audit_report),
            "detailed_report": audit_report,
        }

        # Save briefing
        self._save_ceo_briefing(briefing)

        return briefing

    def _generate_executive_summary(self, report: Dict[str, Any]) -> str:
        """Generate executive summary from audit report."""
        status = report.get("system_status", {})
        integrations = report.get("integration_status", {})

        configured_count = sum(
            1 for v in integrations.values()
            if v in ["configured", "connected"]
        )
        total_integrations = len(integrations)

        return (
            f"Gold Tier AI Employee is {'operational' if status.get('orchestrator_running') else 'offline'}. "
            f"{configured_count}/{total_integrations} integrations configured. "
            f"Ralph Wiggum Loop is handling tasks autonomously."
        )

    def _assess_system_health(self, report: Dict[str, Any]) -> str:
        """Assess overall system health."""
        if not report.get("system_status", {}).get("orchestrator_running"):
            return "CRITICAL"

        integrations = report.get("integration_status", {})
        errors = sum(1 for v in integrations.values() if v == "error")

        if errors > 0:
            return "WARNING"
        return "HEALTHY"

    def _summarize_integrations(self, report: Dict[str, Any]) -> Dict[str, str]:
        """Summarize integration status for briefing."""
        integrations = report.get("integration_status", {})
        summary = {}

        for name, status in integrations.items():
            if status == "connected":
                summary[name] = "Active and connected"
            elif status == "configured":
                summary[name] = "Configured, ready to connect"
            elif status == "not_configured":
                summary[name] = "Not configured - action required"
            else:
                summary[name] = f"Status: {status}"

        return summary

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on audit."""
        recommendations = []
        integrations = report.get("integration_status", {})

        for name, status in integrations.items():
            if status == "not_configured":
                recommendations.append(
                    f"Configure {name.title()} integration to enable full functionality"
                )
            elif status == "error":
                recommendations.append(
                    f"Investigate and resolve {name.title()} integration error"
                )

        if not recommendations:
            recommendations.append("All systems nominal. Continue monitoring.")

        return recommendations

    def _save_audit_report(self, report: Dict[str, Any]) -> Path:
        """Save audit report to disk."""
        audit_dir = REPORTS_DIR / "audits"
        audit_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = audit_dir / f"audit_{timestamp}.json"

        with open(file_path, "w") as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Audit report saved: {file_path}")
        return file_path

    def _save_ceo_briefing(self, briefing: Dict[str, Any]) -> Path:
        """Save CEO briefing to disk."""
        briefing_dir = REPORTS_DIR / "briefings"
        briefing_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = briefing_dir / f"ceo_briefing_{timestamp}.json"

        with open(file_path, "w") as f:
            json.dump(briefing, f, indent=2)

        self.logger.info(f"CEO briefing saved: {file_path}")
        return file_path

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        base_health = await super().health_check()

        return {
            **base_health,
            "integration_status": {k: v.value for k, v in self.integration_status.items()},
            "ralph_loop": await self.ralph_loop.health_check(),
            "mcp_servers": {
                name: "initialized" if server else "not_started"
                for name, server in self.mcp_servers.items()
            },
            "uptime_seconds": (datetime.now() - self._startup_time).total_seconds()
            if self._startup_time else 0,
        }

    def get_system_readiness_report(self) -> Dict[str, Any]:
        """Generate a system readiness report for validation."""
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "READY" if self.is_running else "NOT_READY",
            "components": {
                "orchestrator": {
                    "status": "running" if self.is_running else "stopped",
                    "ready": self.is_running,
                },
                "ralph_wiggum_loop": {
                    "status": "running" if self.ralph_loop.is_running else "stopped",
                    "ready": self.ralph_loop.is_running,
                    "registered_skills": list(self.ralph_loop.skill_registry.keys()),
                },
                "mcp_servers": {
                    name: {
                        "status": "initialized" if server else "not_started",
                        "ready": server is not None,
                    }
                    for name, server in self.mcp_servers.items()
                },
            },
            "integrations": {
                name: {
                    "status": status.value,
                    "configured": status in [IntegrationStatus.CONFIGURED, IntegrationStatus.CONNECTED],
                }
                for name, status in self.integration_status.items()
            },
            "recommendations": self._generate_recommendations({
                "integration_status": {k: v.value for k, v in self.integration_status.items()}
            }),
        }
