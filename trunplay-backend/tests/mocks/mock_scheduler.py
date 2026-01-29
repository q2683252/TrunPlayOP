"""
Mock Scheduler for testing.

Simulates cron job scheduling without actual system cron operations.
"""
from typing import Dict, List, Optional, Any


class MockScheduler:
    """Mock implementation of Scheduler for testing."""

    def __init__(self):
        self.scheduled_jobs: Dict[str, Dict[str, Any]] = {}
        self.fail_mode: Optional[str] = None  # "write_error", "reload_error"
        self._call_history: List[Dict[str, Any]] = []
        self._triggered_plans: List[str] = []

    def _record_call(self, method: str, **kwargs):
        """Record method calls for verification."""
        self._call_history.append({"method": method, **kwargs})

    def schedule_plan(self, plan_id: str, time_str: str, days: str) -> bool:
        """Schedule a plan for execution."""
        self._record_call("schedule_plan", plan_id=plan_id, time_str=time_str, days=days)

        if self.fail_mode == "write_error":
            return False

        try:
            cron_expr = self._build_cron(time_str, days)
            self.scheduled_jobs[plan_id] = {
                "cron": cron_expr,
                "time": time_str,
                "days": days,
                "enabled": True,
            }
            return True
        except ValueError:
            return False

    def cancel_plan(self, plan_id: str) -> bool:
        """Cancel a scheduled plan."""
        self._record_call("cancel_plan", plan_id=plan_id)

        if plan_id in self.scheduled_jobs:
            del self.scheduled_jobs[plan_id]
            return True
        return False

    def is_scheduled(self, plan_id: str) -> bool:
        """Check if a plan is scheduled."""
        self._record_call("is_scheduled", plan_id=plan_id)
        return plan_id in self.scheduled_jobs

    def get_schedule(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get schedule info for a plan."""
        self._record_call("get_schedule", plan_id=plan_id)
        return self.scheduled_jobs.get(plan_id)

    def get_all_schedules(self) -> Dict[str, Dict[str, Any]]:
        """Get all scheduled plans."""
        self._record_call("get_all_schedules")
        return dict(self.scheduled_jobs)

    def enable_plan(self, plan_id: str) -> bool:
        """Enable a scheduled plan."""
        self._record_call("enable_plan", plan_id=plan_id)

        if plan_id in self.scheduled_jobs:
            self.scheduled_jobs[plan_id]["enabled"] = True
            return True
        return False

    def disable_plan(self, plan_id: str) -> bool:
        """Disable a scheduled plan."""
        self._record_call("disable_plan", plan_id=plan_id)

        if plan_id in self.scheduled_jobs:
            self.scheduled_jobs[plan_id]["enabled"] = False
            return True
        return False

    def reload_cron(self) -> bool:
        """Reload the cron daemon."""
        self._record_call("reload_cron")

        if self.fail_mode == "reload_error":
            return False
        return True

    def _build_cron(self, time_str: str, days: str) -> str:
        """Build a cron expression from time and days."""
        parts = time_str.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid time format: {time_str}")

        hour, minute = parts
        # Convert days from 1-7 (Mon-Sun) to cron format 0-6 (Sun-Sat)
        # Or keep as-is if already in correct format
        return f"{minute} {hour} * * {days}"

    # ==================== Test Helper Methods ====================

    def trigger_plan(self, plan_id: str):
        """Simulate triggering a plan (for testing)."""
        self._record_call("trigger_plan", plan_id=plan_id)
        self._triggered_plans.append(plan_id)

    def get_triggered_plans(self) -> List[str]:
        """Get list of triggered plans."""
        return list(self._triggered_plans)

    def clear_triggered_plans(self):
        """Clear the list of triggered plans."""
        self._triggered_plans.clear()

    def get_call_history(self, method: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get call history, optionally filtered by method name."""
        if method:
            return [c for c in self._call_history if c["method"] == method]
        return self._call_history

    def clear_call_history(self):
        """Clear call history."""
        self._call_history.clear()

    def reset(self):
        """Reset all state."""
        self.scheduled_jobs.clear()
        self._call_history.clear()
        self._triggered_plans.clear()
        self.fail_mode = None
