"""
DLNA Manager - Device discovery and playback control.
Implements UPnP/DLNA protocol for device discovery (SSDP) and control (SOAP).
"""
import asyncio
import socket
import time
import logging
import re
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    STOPPED = "STOPPED"
    LOADING = "LOADING"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


@dataclass
class DeviceControlUrls:
    base_url: str
    av_transport_url: str
    rendering_control_url: str


@dataclass
class PositionInfo:
    duration: int  # seconds
    position: int  # seconds


@dataclass
class TransportInfo:
    current_state: str  # STOPPED, PLAYING, PAUSED_PLAYBACK, etc.
    current_status: str  # OK, ERROR_OCCURRED


@dataclass
class DlnaDevice:
    id: str  # UDN
    name: str
    address: str
    type: str = "MediaRenderer"
    manufacturer: str = ""
    is_online: bool = True
    last_seen: int = 0
    location_url: str = ""
    source: str = "DISCOVERED"


@dataclass
class CurrentPlayback:
    state: PlaybackState = PlaybackState.STOPPED
    device: Optional[DlnaDevice] = None
    plan_id: Optional[str] = None
    plan_title: Optional[str] = None
    media_url: Optional[str] = None
    media_name: Optional[str] = None
    position: int = 0
    duration: int = 0
    volume: int = 50


class DlnaManager:
    """
    Manages DLNA device discovery and media playback control.
    """

    SSDP_ADDRESS = "239.255.255.250"
    SSDP_PORT = 1900
    M_SEARCH_TEMPLATE = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        "MAN: \"ssdp:discover\"\r\n"
        "MX: 3\r\n"
        "ST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n"
        "\r\n"
    )

    def __init__(self):
        self._devices: Dict[str, DlnaDevice] = {}
        self._control_urls: Dict[str, DeviceControlUrls] = {}
        self._is_discovering = False
        self._current_playback = CurrentPlayback()
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def devices(self) -> List[DlnaDevice]:
        return list(self._devices.values())

    @property
    def is_discovering(self) -> bool:
        return self._is_discovering

    @property
    def playback_state(self) -> PlaybackState:
        return self._current_playback.state

    @property
    def current_device(self) -> Optional[DlnaDevice]:
        return self._current_playback.device

    @property
    def current_playback(self) -> CurrentPlayback:
        return self._current_playback

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    async def close(self):
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # ==================== Device Discovery ====================

    async def start_discovery(self, timeout: float = 5.0) -> List[DlnaDevice]:
        """
        Discover DLNA devices on the network using SSDP M-SEARCH.
        """
        if self._is_discovering:
            return self.devices

        self._is_discovering = True
        discovered = []

        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            sock.bind(("", 0))

            # Send M-SEARCH
            search_msg = self.M_SEARCH_TEMPLATE.encode("utf-8")
            sock.sendto(search_msg, (self.SSDP_ADDRESS, self.SSDP_PORT))
            logger.info("Sent SSDP M-SEARCH")

            # Receive responses
            start_time = time.time()
            seen_locations = set()

            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(2048)
                    response = data.decode("utf-8", errors="ignore")

                    # Parse LOCATION header
                    location_match = re.search(r"LOCATION:\s*(.+)", response, re.IGNORECASE)
                    if location_match:
                        location = location_match.group(1).strip()
                        if location not in seen_locations:
                            seen_locations.add(location)
                            logger.debug(f"Found device at {location}")

                            # Fetch device description
                            device = await self._fetch_device_description(location, addr[0])
                            if device:
                                self._devices[device.id] = device
                                discovered.append(device)
                                logger.info(f"Discovered: {device.name} ({device.address})")

                except socket.timeout:
                    continue
                except Exception as e:
                    logger.warning(f"Error receiving SSDP response: {e}")

            sock.close()

        except Exception as e:
            logger.error(f"Discovery error: {e}")
        finally:
            self._is_discovering = False

        logger.info(f"Discovery complete. Found {len(discovered)} devices")
        return discovered

    async def _fetch_device_description(self, location_url: str, fallback_address: str) -> Optional[DlnaDevice]:
        """Fetch and parse device description XML."""
        try:
            client = await self._get_http_client()
            response = await client.get(location_url, timeout=5.0)
            response.raise_for_status()

            root = ET.fromstring(response.text)

            # XML namespaces
            ns = {"": "urn:schemas-upnp-org:device-1-0"}

            # Find device element
            device_elem = root.find(".//device", ns)
            if device_elem is None:
                # Try without namespace
                device_elem = root.find(".//device")

            if device_elem is None:
                return None

            # Extract device info
            friendly_name = self._get_xml_text(device_elem, "friendlyName", ns) or "Unknown Device"
            udn = self._get_xml_text(device_elem, "UDN", ns) or f"device_{int(time.time())}"
            device_type = self._get_xml_text(device_elem, "deviceType", ns) or ""
            manufacturer = self._get_xml_text(device_elem, "manufacturer", ns) or ""

            # Parse control URLs
            av_transport_url = ""
            rendering_control_url = ""

            service_list = device_elem.find("serviceList", ns) or device_elem.find("serviceList")
            if service_list:
                for service in service_list.findall("service", ns) or service_list.findall("service"):
                    service_type = self._get_xml_text(service, "serviceType", ns) or ""
                    control_url = self._get_xml_text(service, "controlURL", ns) or ""

                    if "AVTransport" in service_type:
                        av_transport_url = control_url
                    elif "RenderingControl" in service_type:
                        rendering_control_url = control_url

            # Build base URL
            from urllib.parse import urlparse
            parsed = urlparse(location_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            # Make control URLs absolute
            if av_transport_url and not av_transport_url.startswith("http"):
                av_transport_url = f"{base_url}{av_transport_url}"
            if rendering_control_url and not rendering_control_url.startswith("http"):
                rendering_control_url = f"{base_url}{rendering_control_url}"

            # Store control URLs
            self._control_urls[udn] = DeviceControlUrls(
                base_url=base_url,
                av_transport_url=av_transport_url,
                rendering_control_url=rendering_control_url
            )

            # Determine device type
            d_type = "MediaRenderer"
            if "TV" in device_type:
                d_type = "TV"

            return DlnaDevice(
                id=udn,
                name=friendly_name,
                address=parsed.hostname or fallback_address,
                type=d_type,
                manufacturer=manufacturer,
                is_online=True,
                last_seen=int(time.time() * 1000),
                location_url=location_url
            )

        except Exception as e:
            logger.error(f"Error fetching device description from {location_url}: {e}")
            return None

    def _get_xml_text(self, elem: ET.Element, tag: str, ns: dict) -> Optional[str]:
        """Get text content of XML element."""
        child = elem.find(tag, ns) if ns else elem.find(tag)
        if child is None:
            child = elem.find(tag)  # Try without namespace
        return child.text if child is not None else None

    async def add_device_manually(self, address: str, port: int = 8200) -> Optional[DlnaDevice]:
        """Add a device manually by IP address."""
        location_url = f"http://{address}:{port}/device.xml"
        device = await self._fetch_device_description(location_url, address)
        if device:
            device.source = "MANUAL"
            self._devices[device.id] = device
            logger.info(f"Manually added device: {device.name} ({address})")
        return device

    async def check_device_online(self, device_id: str) -> bool:
        """Check if a device is reachable."""
        device = self._devices.get(device_id)
        if not device:
            return False

        try:
            client = await self._get_http_client()
            response = await client.head(device.location_url, timeout=3.0)
            is_online = response.status_code == 200
            device.is_online = is_online
            if is_online:
                device.last_seen = int(time.time() * 1000)
            return is_online
        except Exception:
            device.is_online = False
            return False

    def get_device(self, device_id: str) -> Optional[DlnaDevice]:
        """Get device by ID."""
        return self._devices.get(device_id)

    def remove_device(self, device_id: str) -> bool:
        """Remove device from cache."""
        if device_id in self._devices:
            del self._devices[device_id]
            self._control_urls.pop(device_id, None)
            return True
        return False

    # ==================== Playback Control ====================

    async def play_media(
        self,
        device: DlnaDevice,
        media_url: str,
        media_name: str = "",
        start_position: int = 0,
        plan_id: str = "",
        plan_title: str = ""
    ) -> bool:
        """Start playing media on a device."""
        logger.info(f"[play_media] device={device.name}, url={media_url}, pos={start_position}")

        control_urls = self._control_urls.get(device.id)
        if not control_urls:
            logger.error(f"No control URLs for device: {device.name}")
            self._current_playback.state = PlaybackState.ERROR
            return False

        self._current_playback = CurrentPlayback(
            state=PlaybackState.LOADING,
            device=device,
            plan_id=plan_id,
            plan_title=plan_title,
            media_url=media_url,
            media_name=media_name or self._extract_filename(media_url)
        )

        try:
            # Step 1: SetAVTransportURI
            escaped_url = self._escape_xml(media_url)
            escaped_title = self._escape_xml(self._current_playback.media_name or "Media")

            # DIDL-Lite metadata
            didl_lite = self._build_didl_lite(escaped_url, escaped_title)

            success = await self._send_av_transport_action(
                control_urls,
                "SetAVTransportURI",
                f"""
                <InstanceID>0</InstanceID>
                <CurrentURI>{escaped_url}</CurrentURI>
                <CurrentURIMetaData>{didl_lite}</CurrentURIMetaData>
                """
            )

            if not success:
                logger.error("Failed to set AV Transport URI")
                self._current_playback.state = PlaybackState.ERROR
                return False

            # Step 2: Seek (if start_position > 0)
            if start_position > 0:
                await self._seek_internal(control_urls, start_position)

            # Step 3: Play
            success = await self._send_av_transport_action(
                control_urls,
                "Play",
                """
                <InstanceID>0</InstanceID>
                <Speed>1</Speed>
                """
            )

            if success:
                self._current_playback.state = PlaybackState.PLAYING
                logger.info(f"Playback started on {device.name}")
            else:
                self._current_playback.state = PlaybackState.ERROR
                logger.error("Play command failed")

            return success

        except Exception as e:
            logger.error(f"Error starting playback: {e}")
            self._current_playback.state = PlaybackState.ERROR
            return False

    async def pause(self) -> bool:
        """Pause playback."""
        if self._current_playback.state != PlaybackState.PLAYING:
            return False

        device = self._current_playback.device
        if not device:
            return False

        control_urls = self._control_urls.get(device.id)
        if not control_urls:
            return False

        success = await self._send_av_transport_action(
            control_urls, "Pause", "<InstanceID>0</InstanceID>"
        )

        if success:
            self._current_playback.state = PlaybackState.PAUSED
            logger.info("Playback paused")

        return success

    async def resume(self) -> bool:
        """Resume playback."""
        if self._current_playback.state != PlaybackState.PAUSED:
            return False

        device = self._current_playback.device
        if not device:
            return False

        control_urls = self._control_urls.get(device.id)
        if not control_urls:
            return False

        success = await self._send_av_transport_action(
            control_urls,
            "Play",
            """
            <InstanceID>0</InstanceID>
            <Speed>1</Speed>
            """
        )

        if success:
            self._current_playback.state = PlaybackState.PLAYING
            logger.info("Playback resumed")

        return success

    async def stop(self) -> bool:
        """Stop playback."""
        device = self._current_playback.device
        if device:
            control_urls = self._control_urls.get(device.id)
            if control_urls:
                await self._send_av_transport_action(
                    control_urls, "Stop", "<InstanceID>0</InstanceID>"
                )

        self._current_playback = CurrentPlayback()
        logger.info("Playback stopped")
        return True

    async def seek(self, position: int) -> bool:
        """Seek to position (in seconds)."""
        device = self._current_playback.device
        if not device:
            return False

        control_urls = self._control_urls.get(device.id)
        if not control_urls:
            return False

        return await self._seek_internal(control_urls, position)

    async def _seek_internal(self, control_urls: DeviceControlUrls, position: int) -> bool:
        """Internal seek implementation."""
        target_time = self._format_time(max(0, position))
        success = await self._send_av_transport_action(
            control_urls,
            "Seek",
            f"""
            <InstanceID>0</InstanceID>
            <Unit>REL_TIME</Unit>
            <Target>{target_time}</Target>
            """
        )
        if success:
            logger.debug(f"Seeked to {target_time}")
        return success

    async def set_volume(self, level: int) -> bool:
        """Set volume (0-100)."""
        device = self._current_playback.device
        if not device:
            return False

        control_urls = self._control_urls.get(device.id)
        if not control_urls:
            return False

        level = max(0, min(100, level))

        success = await self._send_rendering_control_action(
            control_urls,
            "SetVolume",
            f"""
            <InstanceID>0</InstanceID>
            <Channel>Master</Channel>
            <DesiredVolume>{level}</DesiredVolume>
            """
        )

        if success:
            self._current_playback.volume = level
            logger.debug(f"Volume set to {level}")

        return success

    async def get_volume(self) -> int:
        """Get current volume."""
        device = self._current_playback.device
        if not device:
            return self._current_playback.volume

        control_urls = self._control_urls.get(device.id)
        if not control_urls:
            return self._current_playback.volume

        response = await self._send_rendering_control_action_with_response(
            control_urls,
            "GetVolume",
            """
            <InstanceID>0</InstanceID>
            <Channel>Master</Channel>
            """
        )

        if response:
            match = re.search(r"<CurrentVolume>(\d+)</CurrentVolume>", response)
            if match:
                self._current_playback.volume = int(match.group(1))

        return self._current_playback.volume

    async def get_position_info(self) -> Optional[PositionInfo]:
        """Get current playback position."""
        device = self._current_playback.device
        if not device:
            return None

        control_urls = self._control_urls.get(device.id)
        if not control_urls:
            return None

        response = await self._send_av_transport_action_with_response(
            control_urls, "GetPositionInfo", "<InstanceID>0</InstanceID>"
        )

        if not response:
            return None

        try:
            duration_match = re.search(r"<TrackDuration>([^<]+)</TrackDuration>", response)
            position_match = re.search(r"<RelTime>([^<]+)</RelTime>", response)

            duration = self._parse_time(duration_match.group(1)) if duration_match else 0
            position = self._parse_time(position_match.group(1)) if position_match else 0

            self._current_playback.duration = duration
            self._current_playback.position = position

            return PositionInfo(duration=duration, position=position)

        except Exception as e:
            logger.error(f"Error parsing position info: {e}")
            return None

    async def get_transport_info(self) -> Optional[TransportInfo]:
        """Get transport state from device."""
        device = self._current_playback.device
        if not device:
            return None

        control_urls = self._control_urls.get(device.id)
        if not control_urls:
            return None

        response = await self._send_av_transport_action_with_response(
            control_urls, "GetTransportInfo", "<InstanceID>0</InstanceID>"
        )

        if not response:
            return None

        try:
            state_match = re.search(r"<CurrentTransportState>([^<]+)</CurrentTransportState>", response)
            status_match = re.search(r"<CurrentTransportStatus>([^<]+)</CurrentTransportStatus>", response)

            state = state_match.group(1) if state_match else "UNKNOWN"
            status = status_match.group(1) if status_match else "OK"

            # Update local state based on device state
            if state == "STOPPED" or state == "NO_MEDIA_PRESENT":
                self._current_playback.state = PlaybackState.STOPPED
            elif state == "PAUSED_PLAYBACK":
                self._current_playback.state = PlaybackState.PAUSED
            elif state == "PLAYING":
                self._current_playback.state = PlaybackState.PLAYING

            return TransportInfo(current_state=state, current_status=status)

        except Exception as e:
            logger.error(f"Error parsing transport info: {e}")
            return None

    # ==================== SOAP Helpers ====================

    async def _send_av_transport_action(self, control_urls: DeviceControlUrls, action: str, arguments: str) -> bool:
        """Send AVTransport SOAP action."""
        response = await self._send_soap_request(
            control_urls.av_transport_url,
            "urn:schemas-upnp-org:service:AVTransport:1",
            action,
            arguments
        )
        return response is not None

    async def _send_av_transport_action_with_response(
        self, control_urls: DeviceControlUrls, action: str, arguments: str
    ) -> Optional[str]:
        """Send AVTransport SOAP action and return response."""
        return await self._send_soap_request(
            control_urls.av_transport_url,
            "urn:schemas-upnp-org:service:AVTransport:1",
            action,
            arguments
        )

    async def _send_rendering_control_action(self, control_urls: DeviceControlUrls, action: str, arguments: str) -> bool:
        """Send RenderingControl SOAP action."""
        response = await self._send_soap_request(
            control_urls.rendering_control_url,
            "urn:schemas-upnp-org:service:RenderingControl:1",
            action,
            arguments
        )
        return response is not None

    async def _send_rendering_control_action_with_response(
        self, control_urls: DeviceControlUrls, action: str, arguments: str
    ) -> Optional[str]:
        """Send RenderingControl SOAP action and return response."""
        return await self._send_soap_request(
            control_urls.rendering_control_url,
            "urn:schemas-upnp-org:service:RenderingControl:1",
            action,
            arguments
        )

    async def _send_soap_request(
        self,
        control_url: str,
        service_type: str,
        action: str,
        arguments: str
    ) -> Optional[str]:
        """Send SOAP request to UPnP device."""
        soap_body = f'''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:{action} xmlns:u="{service_type}">
      {arguments}
    </u:{action}>
  </s:Body>
</s:Envelope>'''

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{service_type}#{action}"'
        }

        try:
            client = await self._get_http_client()
            response = await client.post(control_url, content=soap_body, headers=headers, timeout=10.0)

            if response.status_code == 200:
                logger.debug(f"SOAP {action} success")
                return response.text
            else:
                logger.warning(f"SOAP {action} failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"SOAP request error ({action}): {e}")
            return None

    # ==================== Utilities ====================

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    def _build_didl_lite(self, url: str, title: str) -> str:
        """Build DIDL-Lite metadata for SetAVTransportURI."""
        # Double-escape for SOAP embedding
        return (
            "&lt;DIDL-Lite xmlns=&quot;urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/&quot; "
            "xmlns:dc=&quot;http://purl.org/dc/elements/1.1/&quot; "
            "xmlns:upnp=&quot;urn:schemas-upnp-org:metadata-1-0/upnp/&quot;&gt;"
            "&lt;item id=&quot;0&quot; parentID=&quot;-1&quot; restricted=&quot;1&quot;&gt;"
            f"&lt;dc:title&gt;{title}&lt;/dc:title&gt;"
            "&lt;upnp:class&gt;object.item.videoItem&lt;/upnp:class&gt;"
            f"&lt;res protocolInfo=&quot;http-get:*:video/mp4:*&quot;&gt;{url}&lt;/res&gt;"
            "&lt;/item&gt;&lt;/DIDL-Lite&gt;"
        )

    def _format_time(self, seconds: int) -> str:
        """Format seconds to HH:MM:SS."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _parse_time(self, time_str: str) -> int:
        """Parse HH:MM:SS to seconds."""
        if not time_str or time_str == "NOT_IMPLEMENTED":
            return 0

        try:
            # Remove fractional seconds
            time_str = time_str.split(".")[0]
            parts = time_str.split(":")
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            else:
                return int(parts[0])
        except Exception:
            return 0

    def _extract_filename(self, url: str) -> str:
        """Extract filename from URL."""
        try:
            from urllib.parse import urlparse, unquote
            path = urlparse(url).path
            return unquote(path.split("/")[-1])
        except Exception:
            return "Media"


# Global instance
_dlna_manager: Optional[DlnaManager] = None


def get_dlna_manager() -> DlnaManager:
    """Get global DLNA manager instance."""
    global _dlna_manager
    if _dlna_manager is None:
        _dlna_manager = DlnaManager()
    return _dlna_manager
