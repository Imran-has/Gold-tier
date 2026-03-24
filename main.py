#!/usr/bin/env python3
"""
Gold Tier Autonomous AI Employee - Main Entry Point
Initializes and runs all Gold tier components.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file BEFORE importing config
from dotenv import load_dotenv
env_path = Path(__file__).parent / "config" / ".env"
loaded = load_dotenv(env_path, override=True)
print(f"Loaded .env from: {env_path} (success: {loaded})")
print(f"LINKEDIN_ACCESS_TOKEN loaded: {'Yes' if os.environ.get('LINKEDIN_ACCESS_TOKEN') else 'No'}")

# Import base config classes and paths
from config.settings import (
    GoldConfig,
    IntegrationStatus,
    BASE_DIR,
    LOGS_DIR,
    EVENTS_DIR,
    PLANS_DIR,
    REPORTS_DIR,
)

# Create fresh config instance after .env is loaded
config = GoldConfig()
from agents.orchestrator import GoldOrchestrator
from agents.base import agent_registry
from mcp.odoo_server import OdooMCPServer
from mcp.social_server import SocialMCPServer
from mcp.audit_server import AuditMCPServer
from skills.base import skill_registry
from utils.recovery import error_recovery, graceful_degradation


# Setup logging
def setup_logging():
    """Configure logging for the application."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=config.log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOGS_DIR / "gold_main.log"),
        ],
    )
    return logging.getLogger("gold.main")


logger = setup_logging()


class GoldTierApplication:
    """
    Main application class for Gold Tier AI Employee.
    Manages initialization, startup, and shutdown of all components.
    """

    def __init__(self):
        self.orchestrator: GoldOrchestrator = None
        self.mcp_servers: dict = {}
        self.is_running = False
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> bool:
        """Initialize all Gold tier components."""
        logger.info("=" * 60)
        logger.info("GOLD TIER AUTONOMOUS AI EMPLOYEE")
        logger.info("=" * 60)
        logger.info("Initializing components...")

        # Create required directories
        self._create_directories()

        # Initialize orchestrator
        self.orchestrator = GoldOrchestrator()

        # Initialize MCP servers
        await self._initialize_mcp_servers()

        # Register circuit breakers for graceful degradation
        self._setup_circuit_breakers()

        # Register skills with Ralph Wiggum Loop
        self._register_skills()

        logger.info("Initialization complete")
        return True

    def _create_directories(self):
        """Create required directories."""
        directories = [
            BASE_DIR / "config" / "credentials",
            LOGS_DIR / "audit",
            LOGS_DIR / "errors",
            LOGS_DIR / "skills",
            LOGS_DIR / "results",
            EVENTS_DIR,
            PLANS_DIR,
            REPORTS_DIR / "audits",
            REPORTS_DIR / "briefings",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")

    async def _initialize_mcp_servers(self):
        """Initialize MCP servers."""
        logger.info("Initializing MCP servers...")

        # Odoo MCP Server
        self.mcp_servers["odoo"] = OdooMCPServer()
        logger.info("  - Odoo MCP Server initialized")

        # Social Media MCP Server
        self.mcp_servers["social"] = SocialMCPServer()
        logger.info("  - Social Media MCP Server initialized")

        # Audit MCP Server
        self.mcp_servers["audit"] = AuditMCPServer()
        logger.info("  - Audit MCP Server initialized")

    def _setup_circuit_breakers(self):
        """Setup circuit breakers for external services."""
        services = ["odoo", "facebook", "instagram", "twitter"]
        for service in services:
            graceful_degradation.register_circuit_breaker(
                service,
                failure_threshold=5,
                timeout_seconds=60,
            )
        logger.info("Circuit breakers configured for external services")

    def _register_skills(self):
        """Register skills with the Ralph Wiggum Loop."""
        skills = skill_registry.list_skills()
        logger.info(f"Registered {len(skills)} skills:")
        for skill in skills:
            logger.info(f"  - {skill['name']} ({skill['risk_level']})")

    async def start(self) -> None:
        """Start the Gold tier application."""
        logger.info("Starting Gold Tier AI Employee...")

        # Start orchestrator
        await self.orchestrator.start()
        logger.info("Orchestrator started")

        # Start MCP servers
        for name, server in self.mcp_servers.items():
            await server.start()
            logger.info(f"MCP Server '{name}' started")

        self.is_running = True
        logger.info("Gold Tier AI Employee is now running")

        # Generate initial system readiness report
        await self._generate_readiness_report()

    async def stop(self) -> None:
        """Stop the Gold tier application."""
        logger.info("Stopping Gold Tier AI Employee...")

        # Stop MCP servers
        for name, server in self.mcp_servers.items():
            await server.stop()
            logger.info(f"MCP Server '{name}' stopped")

        # Stop orchestrator
        if self.orchestrator:
            await self.orchestrator.stop()
            logger.info("Orchestrator stopped")

        self.is_running = False
        logger.info("Gold Tier AI Employee stopped")

    async def _generate_readiness_report(self) -> dict:
        """Generate and display system readiness report."""
        report = self.orchestrator.get_system_readiness_report()

        logger.info("")
        logger.info("=" * 60)
        logger.info("SYSTEM READINESS REPORT")
        logger.info("=" * 60)
        logger.info(f"Timestamp: {report['timestamp']}")
        logger.info(f"Overall Status: {report['overall_status']}")
        logger.info("")

        logger.info("COMPONENTS:")
        for name, status in report["components"].items():
            ready = "READY" if status.get("ready") else "NOT READY"
            logger.info(f"  [{ready}] {name}: {status.get('status', 'unknown')}")

        logger.info("")
        logger.info("INTEGRATIONS:")
        for name, status in report["integrations"].items():
            configured = "CONFIGURED" if status.get("configured") else "NOT CONFIGURED"
            logger.info(f"  [{configured}] {name}")

        logger.info("")
        logger.info("RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            logger.info(f"  - {rec}")

        logger.info("")
        logger.info("=" * 60)

        # Save report to file
        report_file = REPORTS_DIR / "readiness_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to: {report_file}")

        return report

    async def run_forever(self) -> None:
        """Run the application until shutdown signal."""
        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            pass

    def request_shutdown(self) -> None:
        """Request application shutdown."""
        self._shutdown_event.set()


async def main():
    """Main entry point."""
    app = GoldTierApplication()

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutdown signal received")
        app.request_shutdown()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: signal_handler())

    try:
        # Initialize
        await app.initialize()

        # Start
        await app.start()

        # Run until shutdown
        await app.run_forever()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        # Cleanup
        await app.stop()


def validate_integrations() -> dict:
    """Validate all integrations and return status."""
    from dotenv import load_dotenv

    # Load environment variables
    env_file = BASE_DIR / "config" / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    status = config.get_integration_status()

    print("\n" + "=" * 60)
    print("INTEGRATION VALIDATION")
    print("=" * 60)

    for name, integration_status in status.items():
        if integration_status == IntegrationStatus.CONFIGURED:
            print(f"  [OK] {name.title()}: Configured")
        elif integration_status == IntegrationStatus.CONNECTED:
            print(f"  [OK] {name.title()}: Connected")
        elif integration_status == IntegrationStatus.NOT_CONFIGURED:
            print(f"  [--] {name.title()}: Not configured")
        else:
            print(f"  [!!] {name.title()}: Error")

    print("=" * 60 + "\n")

    return {k: v.value for k, v in status.items()}


if __name__ == "__main__":
    # Check for validation-only mode
    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        validate_integrations()
        sys.exit(0)

    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
