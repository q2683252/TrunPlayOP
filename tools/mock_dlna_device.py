#!/usr/bin/env python3
"""
Mock DLNA Media Renderer (TV) for TrunPlay testing.

Implements:
- SSDP discovery responder (responds to M-SEARCH)
- HTTP server for device description XML
- Basic AVTransport SOAP endpoint

Usage:
    python3 mock_dlna_device.py [--name "Living Room TV"] [--port 8080]
"""

import argparse
import asyncio
import socket
import struct
import uuid
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SSDP Constants
SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900

class DLNADevice:
    """Represents a mock DLNA Media Renderer device."""

    def __init__(self, name: str, http_port: int, udn: str = None):
        self.name = name
        self.http_port = http_port
        self.udn = udn or f"uuid:{uuid.uuid4()}"
        self.ip = self._get_local_ip()
        self.location = f"http://{self.ip}:{self.http_port}/description.xml"

        # Playback state
        self.transport_state = "STOPPED"
        self.current_uri = ""
        self.current_uri_metadata = ""
        self.volume = 50

    def _get_local_ip(self) -> str:
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def get_description_xml(self) -> str:
        """Generate UPnP device description XML."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
        <friendlyName>{self.name}</friendlyName>
        <manufacturer>TrunPlay Mock</manufacturer>
        <manufacturerURL>https://github.com/trunplay</manufacturerURL>
        <modelDescription>Mock DLNA TV for Testing</modelDescription>
        <modelName>MockTV-1000</modelName>
        <modelNumber>1.0</modelNumber>
        <modelURL>https://github.com/trunplay</modelURL>
        <serialNumber>MOCK-{self.http_port}</serialNumber>
        <UDN>{self.udn}</UDN>
        <serviceList>
            <service>
                <serviceType>urn:schemas-upnp-org:service:AVTransport:1</serviceType>
                <serviceId>urn:upnp-org:serviceId:AVTransport</serviceId>
                <SCPDURL>/AVTransport/scpd.xml</SCPDURL>
                <controlURL>/AVTransport/control</controlURL>
                <eventSubURL>/AVTransport/event</eventSubURL>
            </service>
            <service>
                <serviceType>urn:schemas-upnp-org:service:RenderingControl:1</serviceType>
                <serviceId>urn:upnp-org:serviceId:RenderingControl</serviceId>
                <SCPDURL>/RenderingControl/scpd.xml</SCPDURL>
                <controlURL>/RenderingControl/control</controlURL>
                <eventSubURL>/RenderingControl/event</eventSubURL>
            </service>
        </serviceList>
    </device>
</root>'''

    def get_ssdp_response(self, st: str) -> str:
        """Generate SSDP M-SEARCH response."""
        return (
            "HTTP/1.1 200 OK\r\n"
            f"CACHE-CONTROL: max-age=1800\r\n"
            f"DATE: {datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
            "EXT:\r\n"
            f"LOCATION: {self.location}\r\n"
            f"SERVER: Linux/3.0 UPnP/1.0 TrunPlay-Mock/1.0\r\n"
            f"ST: {st}\r\n"
            f"USN: {self.udn}::{st}\r\n"
            "\r\n"
        )

    def handle_soap_action(self, action: str, body: str) -> str:
        """Handle SOAP action and return response."""
        logger.info(f"SOAP Action: {action}")

        if action == "SetAVTransportURI":
            # Extract URI from SOAP body
            try:
                root = ET.fromstring(body)
                ns = {'s': 'http://schemas.xmlsoap.org/soap/envelope/',
                      'u': 'urn:schemas-upnp-org:service:AVTransport:1'}
                uri_elem = root.find('.//CurrentURI')
                if uri_elem is not None:
                    self.current_uri = uri_elem.text or ""
                    logger.info(f"Set URI: {self.current_uri}")
            except:
                pass
            return self._soap_response("SetAVTransportURIResponse", "AVTransport")

        elif action == "Play":
            self.transport_state = "PLAYING"
            logger.info(f"▶ Playing: {self.current_uri}")
            return self._soap_response("PlayResponse", "AVTransport")

        elif action == "Pause":
            self.transport_state = "PAUSED_PLAYBACK"
            logger.info("⏸ Paused")
            return self._soap_response("PauseResponse", "AVTransport")

        elif action == "Stop":
            self.transport_state = "STOPPED"
            logger.info("⏹ Stopped")
            return self._soap_response("StopResponse", "AVTransport")

        elif action == "GetTransportInfo":
            return self._soap_response("GetTransportInfoResponse", "AVTransport", f'''
                <CurrentTransportState>{self.transport_state}</CurrentTransportState>
                <CurrentTransportStatus>OK</CurrentTransportStatus>
                <CurrentSpeed>1</CurrentSpeed>
            ''')

        elif action == "GetPositionInfo":
            return self._soap_response("GetPositionInfoResponse", "AVTransport", '''
                <Track>1</Track>
                <TrackDuration>01:30:00</TrackDuration>
                <TrackMetaData></TrackMetaData>
                <TrackURI></TrackURI>
                <RelTime>00:05:30</RelTime>
                <AbsTime>00:05:30</AbsTime>
                <RelCount>330</RelCount>
                <AbsCount>330</AbsCount>
            ''')

        elif action == "SetVolume":
            try:
                root = ET.fromstring(body)
                vol_elem = root.find('.//DesiredVolume')
                if vol_elem is not None:
                    self.volume = int(vol_elem.text or 50)
                    logger.info(f"🔊 Volume: {self.volume}")
            except:
                pass
            return self._soap_response("SetVolumeResponse", "RenderingControl")

        elif action == "GetVolume":
            return self._soap_response("GetVolumeResponse", "RenderingControl", f'''
                <CurrentVolume>{self.volume}</CurrentVolume>
            ''')

        else:
            logger.warning(f"Unknown action: {action}")
            return self._soap_response(f"{action}Response", "AVTransport")

    def _soap_response(self, action: str, service: str, body: str = "") -> str:
        """Generate SOAP response envelope."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <u:{action} xmlns:u="urn:schemas-upnp-org:service:{service}:1">
            {body}
        </u:{action}>
    </s:Body>
</s:Envelope>'''


class DLNAHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for DLNA device description and control."""

    device: DLNADevice = None

    def log_message(self, format, *args):
        logger.debug(f"HTTP: {args[0]}")

    def do_GET(self):
        if self.path == "/description.xml":
            content = self.device.get_description_xml().encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "text/xml; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if "/control" in self.path:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            # Extract SOAP action from header
            soap_action = self.headers.get('SOAPAction', '')
            action = soap_action.strip('"').split('#')[-1]

            response = self.device.handle_soap_action(action, body)
            response_bytes = response.encode('utf-8')

            self.send_response(200)
            self.send_header("Content-Type", "text/xml; charset=utf-8")
            self.send_header("Content-Length", len(response_bytes))
            self.end_headers()
            self.wfile.write(response_bytes)
        else:
            self.send_response(404)
            self.end_headers()


class SSDPResponder:
    """SSDP M-SEARCH responder for device discovery."""

    def __init__(self, device: DLNADevice):
        self.device = device
        self.running = False

    async def start(self):
        """Start listening for SSDP M-SEARCH requests."""
        self.running = True

        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass

        sock.bind(('', SSDP_PORT))

        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(SSDP_ADDR), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.setblocking(False)

        logger.info(f"SSDP responder listening on {SSDP_ADDR}:{SSDP_PORT}")

        loop = asyncio.get_event_loop()

        while self.running:
            try:
                data, addr = await loop.run_in_executor(None, lambda: sock.recvfrom(1024))
                message = data.decode('utf-8', errors='ignore')

                if "M-SEARCH" in message:
                    # Check if searching for MediaRenderer
                    if "MediaRenderer" in message or "ssdp:all" in message or "upnp:rootdevice" in message:
                        logger.info(f"📡 Received M-SEARCH from {addr[0]}:{addr[1]}")

                        # Send response
                        response = self.device.get_ssdp_response("urn:schemas-upnp-org:device:MediaRenderer:1")
                        sock.sendto(response.encode('utf-8'), addr)
                        logger.info(f"📤 Sent SSDP response to {addr[0]}:{addr[1]}")

            except BlockingIOError:
                await asyncio.sleep(0.1)
            except Exception as e:
                if self.running:
                    logger.error(f"SSDP error: {e}")
                await asyncio.sleep(0.5)

        sock.close()

    def stop(self):
        self.running = False


async def run_dlna_device(name: str, port: int):
    """Run the mock DLNA device."""
    device = DLNADevice(name, port)

    logger.info("=" * 60)
    logger.info(f"🖥️  Mock DLNA Device: {device.name}")
    logger.info(f"📍 IP: {device.ip}")
    logger.info(f"🌐 HTTP Port: {port}")
    logger.info(f"🔗 Location: {device.location}")
    logger.info(f"🆔 UDN: {device.udn}")
    logger.info("=" * 60)

    # Start HTTP server in thread
    DLNAHTTPHandler.device = device
    http_server = HTTPServer(('', port), DLNAHTTPHandler)
    http_thread = Thread(target=http_server.serve_forever, daemon=True)
    http_thread.start()
    logger.info(f"HTTP server started on port {port}")

    # Start SSDP responder
    ssdp = SSDPResponder(device)

    try:
        await ssdp.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        ssdp.stop()
        http_server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Mock DLNA Media Renderer for testing")
    parser.add_argument("--name", default="Mock TV (TrunPlay Test)", help="Device friendly name")
    parser.add_argument("--port", type=int, default=8089, help="HTTP port for device description")
    args = parser.parse_args()

    try:
        asyncio.run(run_dlna_device(args.name, args.port))
    except KeyboardInterrupt:
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
