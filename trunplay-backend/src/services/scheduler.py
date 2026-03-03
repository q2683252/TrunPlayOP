"""
Scheduler - Manages cron jobs for scheduled playback.
Integrates with OpenWrt cron system.
"""
import os
import re
import subprocess
import logging
import fcntl
from typing import Optional, List, Tuple
from datetime import datetime, time as dt_time
from dataclasses import dataclass
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# Cron file path - use config instead of hardcoded value
from ..config import get_config

@dataclass
class ScheduleInfo:
    """Next scheduled playback info."""
    plan_id: str
    plan_title: str
    next_time: datetime
    cron_expression: str


class Scheduler:
    """
    Manages scheduled playback using OpenWrt cron.
    """

    # Major Chinese holidays (fixed dates)
    HOLIDAYS = [
        (1, 1),   # New Year
        (5, 1),   # Labor Day
        (10, 1),  # National Day
        (10, 2),
        (10, 3),
    ]

    def __init__(self):
        self._config = get_config()
        self._crontab_file = self._config.crontab_file
        self._trigger_script = self._config.trigger_script
        self._ensure_crontab_exists()

    @contextmanager
    def _lock_crontab(self):
        """Context manager for exclusive crontab file lock."""
        lock_file = f"{self._crontab_file}.lock"
        lock_fd = None
        try:
            # Create lock file if it doesn't exist
            lock_fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
            # Acquire exclusive lock
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            logger.debug("Acquired crontab lock")
            yield
        finally:
            if lock_fd is not None:
                # Release lock
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
                logger.debug("Released crontab lock")

    def _ensure_crontab_exists(self):
        """Ensure crontab file exists."""
        cron_dir = os.path.dirname(self._crontab_file)
        if not os.path.exists(cron_dir):
            os.makedirs(cron_dir, exist_ok=True)

        if not os.path.exists(self._crontab_file):
            with open(self._crontab_file, "w") as f:
                f.write("# TrunPlay crontab\n")

    def schedule_plan(
        self,
        plan_id: str,
        plan_title: str,
        start_time: str,
        repeat_days: str,
        skip_holidays: bool = False
    ) -> bool:
        """
        Add or update cron job for a plan.

        Args:
            plan_id: Unique plan identifier
            plan_title: Plan title (for comments)
            start_time: Time in "HH:MM" format
            repeat_days: Comma-separated day numbers (1-7, 1=Monday)
            skip_holidays: Whether to skip major holidays
        """
        try:
            # Parse time
            hour, minute = self._parse_time(start_time)
            if hour is None:
                logger.error(f"Invalid start_time: {start_time}")
                return False

            # Convert repeat_days to cron format
            # cron uses 0-6 (0=Sunday), we use 1-7 (1=Monday)
            cron_days = self._convert_days_to_cron(repeat_days)
            if not cron_days:
                logger.error(f"Invalid repeat_days: {repeat_days}")
                return False

            # Build cron expression
            # Format: minute hour * * days
            cron_expr = f"{minute} {hour} * * {cron_days}"

            # Build cron line
            # Format: cron_expr command # TrunPlay: plan_id
            cron_tag = "# TrunPlay:"
            cron_line = f"{cron_expr} {self._trigger_script} {plan_id} {cron_tag} {plan_id}\n"

            # Use file lock for safe crontab modification
            with self._lock_crontab():
                # Remove existing entry for this plan
                self._remove_plan_cron_unlocked(plan_id)

                # Add new entry
                with open(self._crontab_file, "a") as f:
                    f.write(cron_line)

                # Reload cron
                self._reload_cron()

            logger.info(f"Scheduled plan {plan_id}: {cron_expr}")
            return True

        except Exception as e:
            logger.error(f"Error scheduling plan {plan_id}: {e}", exc_info=True)
            return False

    def cancel_plan(self, plan_id: str) -> bool:
        """Remove cron job for a plan."""
        try:
            with self._lock_crontab():
                removed = self._remove_plan_cron_unlocked(plan_id)
                if removed:
                    self._reload_cron()
                    logger.info(f"Cancelled schedule for plan {plan_id}")
            return removed
        except Exception as e:
            logger.error(f"Error cancelling plan {plan_id}: {e}", exc_info=True)
            return False

    def cancel_all(self) -> int:
        """Remove all TrunPlay cron jobs."""
        try:
            if not os.path.exists(self._crontab_file):
                return 0

            with self._lock_crontab():
                with open(self._crontab_file, "r") as f:
                    lines = f.readlines()

                removed_count = 0
                new_lines = []
                cron_tag = "# TrunPlay:"
                for line in lines:
                    if cron_tag not in line:
                        new_lines.append(line)
                    else:
                        removed_count += 1

                with open(self._crontab_file, "w") as f:
                    f.writelines(new_lines)

                if removed_count > 0:
                    self._reload_cron()

            logger.info(f"Cancelled all TrunPlay schedules: {removed_count} removed")
            return removed_count

        except Exception as e:
            logger.error(f"Error cancelling all schedules: {e}", exc_info=True)
            return 0

    def get_scheduled_plans(self) -> List[str]:
        """Get list of scheduled plan IDs."""
        try:
            if not os.path.exists(self._crontab_file):
                return []

            plan_ids = []
            cron_tag = "# TrunPlay:"
            with open(self._crontab_file, "r") as f:
                for line in f:
                    if cron_tag in line:
                        # Extract plan_id from comment
                        match = re.search(rf"{cron_tag}\s+(\S+)", line)
                        if match:
                            plan_ids.append(match.group(1))

            return plan_ids

        except Exception as e:
            logger.error(f"Error getting scheduled plans: {e}", exc_info=True)
            return []

    def get_next_run(self, plan_id: str) -> Optional[datetime]:
        """Calculate next run time for a plan from crontab."""
        try:
            if not os.path.exists(self._crontab_file):
                return None

            cron_tag = "# TrunPlay:"
            with open(self._crontab_file, "r") as f:
                for line in f:
                    if f"{cron_tag} {plan_id}" in line:
                        # Parse cron expression
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            minute = int(parts[0])
                            hour = int(parts[1])
                            days_str = parts[4]
                            return self._calculate_next_run(hour, minute, days_str)

            return None

        except Exception as e:
            logger.error(f"Error getting next run for {plan_id}: {e}", exc_info=True)
            return None

    def is_holiday(self, date: datetime = None) -> bool:
        """Check if date is a major Chinese holiday."""
        if date is None:
            date = datetime.now()

        month_day = (date.month, date.day)
        return month_day in self.HOLIDAYS

    def _parse_time(self, time_str: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse HH:MM time string."""
        try:
            parts = time_str.split(":")
            return int(parts[0]), int(parts[1])
        except Exception:
            return None, None

    def _convert_days_to_cron(self, repeat_days: str) -> Optional[str]:
        """
        Convert day numbers from our format to cron format.
        Our format: 1-7 (1=Monday, 7=Sunday)
        Cron format: 0-6 (0=Sunday, 1=Monday, ..., 6=Saturday)
        """
        try:
            days = [int(d.strip()) for d in repeat_days.split(",") if d.strip()]
            if not days:
                return None

            # Convert: our 1-6 -> cron 1-6, our 7 -> cron 0
            cron_days = []
            for d in days:
                if d == 7:
                    cron_days.append(0)
                elif 1 <= d <= 6:
                    cron_days.append(d)
                else:
                    return None

            return ",".join(str(d) for d in sorted(set(cron_days)))

        except Exception:
            return None

    def _calculate_next_run(self, hour: int, minute: int, days_str: str) -> Optional[datetime]:
        """Calculate next run datetime from cron parameters."""
        try:
            # Parse cron days back to our format
            cron_days = [int(d) for d in days_str.split(",")]
            # Convert cron format to Python weekday (0=Monday)
            # cron: 0=Sunday, 1=Monday, ..., 6=Saturday
            # Python: 0=Monday, 1=Tuesday, ..., 6=Sunday
            python_days = []
            for d in cron_days:
                if d == 0:
                    python_days.append(6)  # Sunday
                else:
                    python_days.append(d - 1)  # Monday=0, ..., Saturday=5

            now = datetime.now()
            target_time = dt_time(hour, minute)

            # Check today
            if now.weekday() in python_days:
                today_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if today_run > now:
                    return today_run

            # Find next day
            for i in range(1, 8):
                next_date = now + __import__("datetime").timedelta(days=i)
                if next_date.weekday() in python_days:
                    return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

            return None

        except Exception as e:
            logger.error(f"Error calculating next run: {e}")
            return None

    def _remove_plan_cron_unlocked(self, plan_id: str) -> bool:
        """
        Remove cron entry for a specific plan.
        IMPORTANT: This method assumes the caller has already acquired the crontab lock.
        """
        if not os.path.exists(self._crontab_file):
            return False

        with open(self._crontab_file, "r") as f:
            lines = f.readlines()

        new_lines = []
        removed = False
        cron_tag = "# TrunPlay:"
        for line in lines:
            if f"{cron_tag} {plan_id}" in line:
                removed = True
            else:
                new_lines.append(line)

        if removed:
            with open(self._crontab_file, "w") as f:
                f.writelines(new_lines)

        return removed

    def _reload_cron(self):
        """Reload cron daemon to pick up changes."""
        try:
            # OpenWrt uses busybox cron or crond
            # Try to reload via init script
            result = subprocess.run(
                ["/etc/init.d/cron", "reload"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                # Fallback: try restart
                subprocess.run(
                    ["/etc/init.d/cron", "restart"],
                    capture_output=True,
                    timeout=5
                )
            logger.debug("Cron reloaded")
        except subprocess.TimeoutExpired:
            logger.warning("Cron reload timed out")
        except Exception as e:
            logger.warning(f"Could not reload cron: {e}")


# Global instance
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """Get global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
