"""
SMB API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import get_db
from ..database import crud, schemas
from ..services.smb_client import get_smb_client

router = APIRouter(prefix="/smb", tags=["smb"])


@router.get("/servers", response_model=List[schemas.SmbServerResponse])
def get_smb_servers(db: Session = Depends(get_db)):
    """Get all SMB servers."""
    servers = crud.get_smb_servers(db)
    return servers


@router.post("/servers", response_model=schemas.SmbServerResponse)
def create_smb_server(server: schemas.SmbServerCreate, db: Session = Depends(get_db)):
    """Add a new SMB server."""
    db_server = crud.create_smb_server(db, server)
    return db_server


@router.put("/servers/{server_id}", response_model=schemas.SmbServerResponse)
def update_smb_server(
    server_id: str,
    server: schemas.SmbServerUpdate,
    db: Session = Depends(get_db)
):
    """Update an SMB server."""
    db_server = crud.update_smb_server(db, server_id, server)
    if not db_server:
        raise HTTPException(status_code=404, detail="SMB server not found")
    return db_server


@router.delete("/servers/{server_id}")
def delete_smb_server(server_id: str, db: Session = Depends(get_db)):
    """Delete an SMB server."""
    success = crud.delete_smb_server(db, server_id)
    if not success:
        raise HTTPException(status_code=404, detail="SMB server not found")
    return {"message": "SMB server deleted"}


@router.post("/servers/test")
async def test_smb_connection(request: schemas.SmbTestRequest):
    """Test SMB server connection."""
    smb_client = get_smb_client()

    success, message = await smb_client.test_connection(
        host=request.host,
        port=request.port,
        username=request.username,
        password=request.password
    )

    return {
        "success": success,
        "message": message
    }


@router.get("/servers/{server_id}/shares")
async def list_smb_shares(server_id: str, db: Session = Depends(get_db)):
    """List shares on an SMB server."""
    server = crud.get_smb_server(db, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="SMB server not found")

    smb_client = get_smb_client()
    shares = await smb_client.list_shares(
        host=server.host,
        port=server.port,
        username=server.username,
        password=server.password
    )

    # Update connection status
    connected = len(shares) > 0
    crud.update_smb_server_connection(db, server_id, connected)

    return {
        "server_id": server_id,
        "shares": [{"name": s.name, "path": s.path} for s in shares]
    }


@router.get("/servers/{server_id}/browse")
async def browse_smb_path(
    server_id: str,
    path: str = "",
    db: Session = Depends(get_db)
):
    """
    Browse files and folders on an SMB server at the given path.
    
    Args:
        server_id: ID of the SMB server
        path: Path to browse (empty for root/shares, e.g. "/share/folder")
    
    Returns:
        MediaBrowseResponse with list of files and folders
    """
    server = crud.get_smb_server(db, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="SMB server not found")
    
    smb_client = get_smb_client()
    items = await smb_client.list_files(
        host=server.host,
        path=path,
        port=server.port,
        username=server.username,
        password=server.password,
        server_id=server_id,
        server_name=server.hostname or server.host
    )
    
    # Calculate parent path
    parent_path = None
    if path:
        path_parts = path.strip("/").split("/")
        if len(path_parts) > 1:
            parent_path = "/" + "/".join(path_parts[:-1])
        else:
            parent_path = ""
    
    return schemas.MediaBrowseResponse(
        path=path,
        parent_path=parent_path,
        items=[
            schemas.MediaItem(
                id=item.id,
                name=item.name,
                path=item.path,
                uri=item.uri,
                type=item.type,
                source_type=schemas.MediaSourceType.SMB,
                server_id=item.server_id,
                size=item.size,
                last_modified=item.last_modified
            )
            for item in items
        ]
    )


@router.post("/servers/scan")
async def scan_smb_servers():
    """
    Scan local network for SMB servers.

    Attempts multiple scan methods in order:
    1. nmblookup (NetBIOS name query) - fastest, most compatible
    2. nmap port scan - if nmblookup not available
    3. IP range ping sweep - fallback method

    Returns list of discovered SMB servers with hostname and IP.
    """
    import subprocess
    import re
    import socket
    from typing import List, Dict, Set

    discovered_servers: List[Dict] = []
    seen_ips: Set[str] = set()

    # Method 1: Try nmblookup (NetBIOS) - Most reliable for SMB discovery
    try:
        logger.info("Attempting SMB scan using nmblookup...")
        result = subprocess.run(
            ["nmblookup", "-S", "*"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Parse nmblookup output
            # Format: "NAME <20> - <GROUP> B <ACTIVE>"
            for line in result.stdout.split('\n'):
                # Look for file server entries (type <20>)
                if '<20>' in line and '<GROUP>' not in line:
                    parts = line.split()
                    if len(parts) >= 1:
                        hostname = parts[0].strip()

                        # Try to resolve hostname to IP
                        try:
                            ip = socket.gethostbyname(hostname)
                            if ip not in seen_ips:
                                discovered_servers.append({
                                    "hostname": hostname,
                                    "ip": ip,
                                    "discovery_method": "nmblookup"
                                })
                                seen_ips.add(ip)
                                logger.info(f"Found SMB server via nmblookup: {hostname} ({ip})")
                        except socket.gaierror:
                            # Hostname resolution failed, skip
                            pass

            if discovered_servers:
                return {
                    "message": f"Found {len(discovered_servers)} SMB server(s) using nmblookup",
                    "servers": discovered_servers
                }
    except FileNotFoundError:
        logger.warning("nmblookup not found, trying alternative methods...")
    except subprocess.TimeoutExpired:
        logger.warning("nmblookup timed out")
    except Exception as e:
        logger.error(f"nmblookup scan error: {e}")

    # Method 2: Try nmap if available
    try:
        logger.info("Attempting SMB scan using nmap...")

        # Get local network range
        local_ip = _get_local_ip()
        if local_ip:
            # Convert to CIDR notation (e.g., 192.168.1.0/24)
            network_prefix = '.'.join(local_ip.split('.')[:3])
            target = f"{network_prefix}.0/24"

            result = subprocess.run(
                ["nmap", "-p", "445", "--open", "-T4", "--max-retries", "1", target],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Parse nmap output
                current_host = None
                for line in result.stdout.split('\n'):
                    # Look for "Nmap scan report for hostname (ip)"
                    host_match = re.search(r'Nmap scan report for (.+?)(?:\s+\(([0-9.]+)\))?$', line)
                    if host_match:
                        hostname = host_match.group(1)
                        ip = host_match.group(2) if host_match.group(2) else hostname
                        current_host = (hostname, ip)

                    # Look for open port 445
                    if current_host and '445/tcp' in line and 'open' in line:
                        hostname, ip = current_host
                        if ip not in seen_ips:
                            discovered_servers.append({
                                "hostname": hostname if hostname != ip else "",
                                "ip": ip,
                                "discovery_method": "nmap"
                            })
                            seen_ips.add(ip)
                            logger.info(f"Found SMB server via nmap: {hostname} ({ip})")
                        current_host = None

                if discovered_servers:
                    return {
                        "message": f"Found {len(discovered_servers)} SMB server(s) using nmap",
                        "servers": discovered_servers
                    }
    except FileNotFoundError:
        logger.warning("nmap not found, trying fallback method...")
    except subprocess.TimeoutExpired:
        logger.warning("nmap scan timed out")
    except Exception as e:
        logger.error(f"nmap scan error: {e}")

    # Method 3: Fallback - Simple IP sweep with SMB port check
    try:
        logger.info("Attempting SMB scan using IP sweep...")

        local_ip = _get_local_ip()
        if local_ip:
            network_prefix = '.'.join(local_ip.split('.')[:3])

            # Check common IP ranges (avoid scanning entire subnet)
            import asyncio

            async def check_smb_port(ip: str) -> bool:
                """Check if SMB port 445 is open."""
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, 445),
                        timeout=1.0
                    )
                    writer.close()
                    await writer.wait_closed()
                    return True
                except:
                    return False

            async def scan_range():
                tasks = []
                # Scan first 50 IPs and common ranges
                ranges_to_scan = list(range(1, 51)) + [100, 101, 200, 254]

                for i in ranges_to_scan:
                    ip = f"{network_prefix}.{i}"
                    if ip != local_ip:  # Skip self
                        tasks.append((ip, check_smb_port(ip)))

                results = await asyncio.gather(*[task for _, task in tasks])

                for (ip, _), is_open in zip(tasks, results):
                    if is_open and ip not in seen_ips:
                        # Try to get hostname
                        try:
                            hostname = socket.gethostbyaddr(ip)[0]
                        except:
                            hostname = ""

                        discovered_servers.append({
                            "hostname": hostname,
                            "ip": ip,
                            "discovery_method": "port_scan"
                        })
                        seen_ips.add(ip)
                        logger.info(f"Found SMB server via port scan: {ip}")

            await scan_range()

            if discovered_servers:
                return {
                    "message": f"Found {len(discovered_servers)} SMB server(s) using port scan",
                    "servers": discovered_servers
                }
    except Exception as e:
        logger.error(f"IP sweep scan error: {e}")

    # No servers found
    return {
        "message": "No SMB servers found. Ensure nmblookup or nmap is installed for better discovery.",
        "servers": [],
        "suggestion": "Install samba-common-bin (for nmblookup) or nmap for improved scanning"
    }


def _get_local_ip() -> str:
    """Get local IP address for network scanning."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""

