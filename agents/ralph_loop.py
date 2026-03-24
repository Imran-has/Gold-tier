"""
Ralph Wiggum Loop - Autonomous Task Execution Engine
Implements Plan -> Execute -> Verify -> Retry cycle for robust task completion.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from config.settings import config, PLANS_DIR, LOGS_DIR
from .base import BaseAgent, Event, EventType


class TaskStatus(Enum):
    """Status of a task in the Ralph Wiggum Loop."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class TaskStep:
    """Individual step in a task plan."""
    id: str
    description: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0


@dataclass
class TaskPlan:
    """Execution plan for a task."""
    task_id: str
    task_description: str
    steps: List[TaskStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    current_step_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "action": s.action,
                    "parameters": s.parameters,
                    "expected_outcome": s.expected_outcome,
                    "status": s.status.value,
                    "result": s.result,
                    "error": s.error,
                    "attempts": s.attempts,
                }
                for s in self.steps
            ],
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "current_step_index": self.current_step_index,
        }


@dataclass
class TaskResult:
    """Result of a completed task."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    plan: Optional[TaskPlan] = None
    total_attempts: int = 0
    lessons_learned: List[str] = field(default_factory=list)
    completed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "plan": self.plan.to_dict() if self.plan else None,
            "total_attempts": self.total_attempts,
            "lessons_learned": self.lessons_learned,
            "completed_at": self.completed_at.isoformat(),
        }


class RalphWiggumLoop(BaseAgent):
    """
    The Ralph Wiggum Loop autonomously executes multi-step tasks.

    Named after the "I'm helping!" meme, this loop:
    1. Plans - Analyzes the task and creates an execution plan
    2. Executes - Runs each step of the plan
    3. Verifies - Checks results against expected outcomes
    4. Retries - If verification fails, adjusts and retries
    5. Reports - Documents the outcome and any lessons learned

    "I'm in danger!" - but we handle it gracefully.
    """

    def __init__(self):
        super().__init__("ralph_wiggum_loop")
        self.config = config.ralph_loop
        self.skill_registry: Dict[str, Callable] = {}
        self.active_tasks: Dict[str, TaskPlan] = {}
        self.completed_tasks: Dict[str, TaskResult] = {}

    def register_skill(self, action_name: str, skill_func: Callable) -> None:
        """Register a skill that can be used in task execution."""
        self.skill_registry[action_name] = skill_func
        self.logger.info(f"Registered skill: {action_name}")

    async def start(self) -> None:
        """Start the Ralph Wiggum Loop."""
        self.is_running = True
        self.logger.info("Ralph Wiggum Loop started - I'm helping!")
        self.audit_log("ralph_loop_started", {"config": {
            "max_retries": self.config.max_retries,
            "retry_delay": self.config.retry_delay_seconds,
        }})

    async def stop(self) -> None:
        """Stop the Ralph Wiggum Loop."""
        self.is_running = False
        self.logger.info("Ralph Wiggum Loop stopped")
        self.audit_log("ralph_loop_stopped", {
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
        })

    async def process(self, event: Event) -> TaskResult:
        """Process a task event through the Ralph Wiggum Loop."""
        task_id = event.data.get("task_id", event.id)
        task_description = event.data.get("description", "Unknown task")

        self.logger.info(f"Processing task: {task_description}")
        self.audit_log("task_received", {"task_id": task_id, "description": task_description})

        # Phase 1: Plan
        plan = await self._plan(task_id, task_description, event.data)
        if not plan:
            return TaskResult(
                task_id=task_id,
                success=False,
                error="Failed to create execution plan",
            )

        self.active_tasks[task_id] = plan

        # Phase 2-4: Execute, Verify, Retry (loop)
        result = await self._execute_plan(plan)

        # Phase 5: Report
        await self._report(result)

        # Clean up
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
        self.completed_tasks[task_id] = result

        return result

    async def _plan(
        self,
        task_id: str,
        description: str,
        context: Dict[str, Any]
    ) -> Optional[TaskPlan]:
        """
        Phase 1: Create an execution plan for the task.
        This is where the AI analyzes the task and breaks it into steps.
        """
        self.logger.info(f"Planning task: {task_id}")

        plan = TaskPlan(
            task_id=task_id,
            task_description=description,
            status=TaskStatus.PLANNING,
        )

        # If steps are provided in context, use them
        if "steps" in context:
            for i, step_data in enumerate(context["steps"]):
                step = TaskStep(
                    id=f"{task_id}_step_{i}",
                    description=step_data.get("description", ""),
                    action=step_data.get("action", ""),
                    parameters=step_data.get("parameters", {}),
                    expected_outcome=step_data.get("expected_outcome", ""),
                )
                plan.steps.append(step)
        else:
            # Create a default single-step plan
            plan.steps.append(TaskStep(
                id=f"{task_id}_step_0",
                description=description,
                action=context.get("action", "execute"),
                parameters=context.get("parameters", {}),
                expected_outcome=context.get("expected_outcome", "Task completed successfully"),
            ))

        # Save plan to disk
        self._save_plan(plan)
        self.audit_log("plan_created", {
            "task_id": task_id,
            "steps_count": len(plan.steps),
        })

        return plan

    async def _execute_plan(self, plan: TaskPlan) -> TaskResult:
        """
        Phase 2-4: Execute the plan with verification and retry logic.
        """
        plan.status = TaskStatus.EXECUTING
        total_attempts = 0

        for i, step in enumerate(plan.steps):
            plan.current_step_index = i
            step_success = False

            while step.attempts < self.config.max_retries and not step_success:
                step.attempts += 1
                total_attempts += 1

                self.logger.info(
                    f"Executing step {i+1}/{len(plan.steps)}: {step.description} "
                    f"(attempt {step.attempts})"
                )

                # Execute
                step.status = TaskStatus.EXECUTING
                try:
                    result = await self._execute_step(step)
                    step.result = result
                except Exception as e:
                    step.error = str(e)
                    self.logger.error(f"Step execution error: {e}")
                    step.status = TaskStatus.RETRYING
                    await asyncio.sleep(self.config.retry_delay_seconds)
                    continue

                # Verify
                step.status = TaskStatus.VERIFYING
                verification = await self._verify_step(step)

                if verification["success"]:
                    step.status = TaskStatus.COMPLETED
                    step_success = True
                    self.logger.info(f"Step {i+1} completed successfully")
                else:
                    step.error = verification.get("error", "Verification failed")
                    self.logger.warning(
                        f"Step {i+1} verification failed: {step.error}. "
                        f"Retrying..."
                    )
                    step.status = TaskStatus.RETRYING
                    await asyncio.sleep(self.config.retry_delay_seconds)

            if not step_success:
                # Step failed after all retries
                step.status = TaskStatus.FAILED
                plan.status = TaskStatus.FAILED
                self._save_plan(plan)

                self.audit_log("step_failed", {
                    "task_id": plan.task_id,
                    "step_id": step.id,
                    "attempts": step.attempts,
                    "error": step.error,
                }, success=False)

                return TaskResult(
                    task_id=plan.task_id,
                    success=False,
                    error=f"Step '{step.description}' failed after {step.attempts} attempts: {step.error}",
                    plan=plan,
                    total_attempts=total_attempts,
                )

            self.audit_log("step_completed", {
                "task_id": plan.task_id,
                "step_id": step.id,
                "attempts": step.attempts,
            })

        # All steps completed
        plan.status = TaskStatus.COMPLETED
        self._save_plan(plan)

        return TaskResult(
            task_id=plan.task_id,
            success=True,
            result=plan.steps[-1].result if plan.steps else None,
            plan=plan,
            total_attempts=total_attempts,
        )

    async def _execute_step(self, step: TaskStep) -> Any:
        """Execute a single step using the registered skill."""
        action = step.action

        if action in self.skill_registry:
            skill = self.skill_registry[action]
            return await skill(step.parameters)
        else:
            self.logger.warning(f"No skill registered for action: {action}")
            # Return a placeholder for unregistered actions
            return {"status": "no_skill_registered", "action": action}

    async def _verify_step(self, step: TaskStep) -> Dict[str, Any]:
        """
        Verify that a step completed successfully.
        Can be overridden for custom verification logic.
        """
        # Default verification: check if result exists and no error
        if step.error:
            return {"success": False, "error": step.error}

        if step.result is None:
            return {"success": False, "error": "No result returned"}

        # Check for error indicators in result
        if isinstance(step.result, dict):
            if step.result.get("error"):
                return {"success": False, "error": step.result["error"]}
            if step.result.get("status") == "failed":
                return {"success": False, "error": step.result.get("message", "Step failed")}

        return {"success": True}

    async def _report(self, result: TaskResult) -> None:
        """
        Phase 5: Report the outcome and document lessons learned.
        """
        self.logger.info(
            f"Task {result.task_id} {'completed successfully' if result.success else 'failed'}"
        )

        # Extract lessons learned if learning is enabled
        if self.config.enable_learning and not result.success:
            lessons = self._extract_lessons(result)
            result.lessons_learned = lessons

        # Emit completion event
        event = Event(
            type=EventType.TASK_COMPLETED if result.success else EventType.TASK_FAILED,
            source=self.name,
            data=result.to_dict(),
        )
        self.emit_event(event)

        # Persist result
        self._save_result(result)

        self.audit_log("task_completed", {
            "task_id": result.task_id,
            "success": result.success,
            "total_attempts": result.total_attempts,
            "lessons_learned": result.lessons_learned,
        }, success=result.success)

    def _extract_lessons(self, result: TaskResult) -> List[str]:
        """Extract lessons learned from a failed task."""
        lessons = []

        if result.plan:
            for step in result.plan.steps:
                if step.status == TaskStatus.FAILED:
                    lessons.append(
                        f"Step '{step.description}' failed with error: {step.error}"
                    )
                    if step.attempts > 1:
                        lessons.append(
                            f"Step required {step.attempts} attempts before final failure"
                        )

        return lessons

    def _save_plan(self, plan: TaskPlan) -> Path:
        """Save a task plan to disk."""
        PLANS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = PLANS_DIR / f"{plan.task_id}.json"
        with open(file_path, "w") as f:
            json.dump(plan.to_dict(), f, indent=2)
        return file_path

    def _save_result(self, result: TaskResult) -> Path:
        """Save a task result to disk."""
        results_dir = LOGS_DIR / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        file_path = results_dir / f"{result.task_id}_result.json"
        with open(file_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        return file_path

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the Ralph Wiggum Loop."""
        base_health = await super().health_check()
        return {
            **base_health,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "registered_skills": list(self.skill_registry.keys()),
            "config": {
                "max_retries": self.config.max_retries,
                "retry_delay_seconds": self.config.retry_delay_seconds,
            },
        }
