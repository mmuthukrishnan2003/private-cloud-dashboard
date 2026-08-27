import ipaddress
import socket
import subprocess

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/api/network",
    tags=["Network"],
)


def run_command(command: list[str]) -> str:
    """
    Execute a Linux command and return stdout.
    """

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout


@router.get("/bridges")
def list_bridges():
    """
    Return Linux bridge interfaces.

    Example:

        br0
        virbr0
    """

    result = subprocess.run(
        [
            "ip",
            "-o",
            "link",
            "show",
            "type",
            "bridge",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    bridges = []

    for line in result.stdout.splitlines():

        # Example:
        # 5: br0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
        parts = line.split(":")

        if len(parts) >= 2:
            name = parts[1].strip()

            if name:
                bridges.append(name)

    return {
        "bridges": bridges
    }


@router.get("/interfaces")
def list_interfaces():
    """
    Return network interfaces visible on the host.
    """

    result = subprocess.run(
        [
            "ip",
            "-br",
            "link",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    interfaces = []

    for line in result.stdout.splitlines():

        parts = line.split()

        if not parts:
            continue

        interfaces.append({
            "name": parts[0],
            "state": parts[1] if len(parts) > 1 else "UNKNOWN",
        })

    return {
        "interfaces": interfaces
    }


@router.get("/check-ip/{ip}")
def check_ip(ip: str):
    """
    Basic IP address validation.

    This does not guarantee that an IP is free.
    """

    try:
        address = ipaddress.ip_address(ip)

        return {
            "valid": True,
            "ip": str(address),
            "version": address.version,
        }

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid IP address",
        )
