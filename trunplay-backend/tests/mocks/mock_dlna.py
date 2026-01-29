"""
Mock DLNA Manager for testing.

Simulates DLNA device discovery and playback control without actual network operations.
"""
import asyncio
from typing import Dict, List, Optional, Any, Tuple


class MockDLNAManager:
    """Mock implementation of DLNAManager for testing."""

    def __init__(self):
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.playback_state: Dict[str, Dict[str, Any]] = {}
        self.fail_mode: Optional[str] = None  # "offline", "timeout", "soap_error"
        self._volume: Dict[str, int] = {}
        self._call_history: List[Dict[str, Any]] = []

    def _record_call(self, method: str, **kwargs):
        """Record method calls for verification."""
        self._call_history.append({"method": method, **kwargs})

    async def discover_devices(self, timeout: float = 5.0) -> List[Dict[str, Any]]:
        """Discover DLNA devices on the network."""
        self._record_call("discover_devices", timeout=timeout)

        if self.fail_mode == "timeout":
            await asyncio.sleep(timeout)
            raise asyncio.TimeoutError("Discovery timeout")

        return list(self.devices.values())

    async def play(self, device_id: str, url: str, title: str = "") -> bool:
        """Start playback on a device."""
        self._record_call("play", device_id=device_id, url=url, title=title)

        if self.fail_mode == "offline":
            return False
        if self.fail_mode == "soap_error":
            raise Exception("SOAP request failed")

        if device_id not in self.devices:
            return False

        self.playback_state[device_id] = {
            "state": "PLAYING",
            "url": url,
            "title": title,
            "position": 0,
            "duration": 3600,  # Default 1 hour
        }
        return True

    async def pause(self, device_id: str) -> bool:
        """Pause playback on a device."""
        self._record_call("pause", device_id=device_id)

        if self.fail_mode == "offline":
            return False

        if device_id in self.playback_state:
            self.playback_state[device_id]["state"] = "PAUSED"
            return True
        return False

    async def resume(self, device_id: str) -> bool:
        """Resume playback on a device."""
        self._record_call("resume", device_id=device_id)

        if self.fail_mode == "offline":
            return False

        if device_id in self.playback_state:
            self.playback_state[device_id]["state"] = "PLAYING"
            return True
        return False

    async def stop(self, device_id: str) -> bool:
        """Stop playback on a device."""
        self._record_call("stop", device_id=device_id)

        if self.fail_mode == "offline":
            return False

        if device_id in self.playback_state:
            del self.playback_state[device_id]
            return True
        return False

    async def seek(self, device_id: str, position: int) -> bool:
        """Seek to a position in the current media."""
        self._record_call("seek", device_id=device_id, position=position)

        if self.fail_mode == "offline":
            return False

        if device_id in self.playback_state:
            duration = self.playback_state[device_id].get("duration", 0)
            # Clamp position to valid range
            position = max(0, min(position, duration))
            self.playback_state[device_id]["position"] = position
            return True
        return False

    async def get_position(self, device_id: str) -> Tuple[int, int]:
        """Get current position and duration."""
        self._record_call("get_position", device_id=device_id)

        if self.fail_mode == "offline":
            return (0, 0)

        state = self.playback_state.get(device_id, {})
        return (state.get("position", 0), state.get("duration", 0))

    async def get_transport_state(self, device_id: str) -> Optional[str]:
        """Get transport state (PLAYING, PAUSED, STOPPED, etc.)."""
        self._record_call("get_transport_state", device_id=device_id)

        if self.fail_mode == "offline":
            return None

        state = self.playback_state.get(device_id)
        if state:
            return state.get("state")
        return "STOPPED"

    async def set_volume(self, device_id: str, level: int) -> bool:
        """Set volume level (0-100)."""
        self._record_call("set_volume", device_id=device_id, level=level)

        if self.fail_mode == "offline":
            return False

        # Clamp to 0-100
        level = max(0, min(100, level))
        self._volume[device_id] = level
        return True

    async def get_volume(self, device_id: str) -> int:
        """Get current volume level."""
        self._record_call("get_volume", device_id=device_id)

        if self.fail_mode == "offline":
            return 0

        return self._volume.get(device_id, 50)

    async def check_device_online(self, device_id: str) -> bool:
        """Check if a device is online."""
        self._record_call("check_device_online", device_id=device_id)

        if self.fail_mode == "offline":
            return False

        device = self.devices.get(device_id)
        if device:
            return device.get("is_online", True)
        return False

    async def close(self):
        """Close the manager and clean up resources."""
        self._record_call("close")
        self.playback_state.clear()

    # ==================== Test Helper Methods ====================

    def add_device(self, device_id: str, name: str, address: str, **kwargs) -> Dict[str, Any]:
        """Add a mock device for testing."""
        device = {
            "id": device_id,
            "name": name,
            "address": address,
            "port": kwargs.get("port", 1400),
            "is_online": kwargs.get("is_online", True),
            "manufacturer": kwargs.get("manufacturer", "Mock"),
            "model": kwargs.get("model", "Test Device"),
        }
        self.devices[device_id] = device
        return device

    def remove_device(self, device_id: str):
        """Remove a mock device."""
        self.devices.pop(device_id, None)
        self.playback_state.pop(device_id, None)

    def set_position(self, device_id: str, position: int, duration: int):
        """Set the current position and duration for a device."""
        if device_id in self.playback_state:
            self.playback_state[device_id]["position"] = position
            self.playback_state[device_id]["duration"] = duration

    def set_device_online(self, device_id: str, is_online: bool):
        """Set device online status."""
        if device_id in self.devices:
            self.devices[device_id]["is_online"] = is_online

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
        self.devices.clear()
        self.playback_state.clear()
        self._volume.clear()
        self._call_history.clear()
        self.fail_mode = None
