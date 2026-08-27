import platform
import socket
import time

import psutil
from fastapi import APIRouter


# ============================================================
# Host Monitoring Router
# ============================================================
# All endpoints will start with:
#
#     /api/host
#
# Example:
#     GET /api/host
#     GET /api/host/cpu
#     GET /api/host/memory
#     GET /api/host/disk
#     GET /api/host/network
#     GET /api/host/uptime
# ============================================================

router = APIRouter(
    prefix="/api/host",
    tags=["Host"],
)


# ============================================================
# Helper function
# ============================================================

def bytes_to_gb(value: int) -> float:
    """
    Convert bytes to GB.
    """
    return round(value / (1024 ** 3), 2)


# ============================================================
# GET /api/host
# ============================================================

@router.get("")
def get_host_info():
    """
    Return basic information about the main KVM server.

    This is the physical server where the dashboard and KVM
    virtualization are running.
    """

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        # ----------------------------------------------------
        # Server information
        # ----------------------------------------------------
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),

        # ----------------------------------------------------
        # CPU
        # ----------------------------------------------------
        "cpu": {
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "usage_percent": psutil.cpu_percent(interval=0.5),
        },

        # ----------------------------------------------------
        # RAM
        # ----------------------------------------------------
        "memory": {
            "total_gb": bytes_to_gb(memory.total),
            "used_gb": bytes_to_gb(memory.used),
            "available_gb": bytes_to_gb(memory.available),
            "usage_percent": memory.percent,
        },

        # ----------------------------------------------------
        # Root disk
        # ----------------------------------------------------
        "disk": {
            "mount": "/",
            "total_gb": bytes_to_gb(disk.total),
            "used_gb": bytes_to_gb(disk.used),
            "free_gb": bytes_to_gb(disk.free),
            "usage_percent": disk.percent,
        },

        # ----------------------------------------------------
        # Host uptime
        # ----------------------------------------------------
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }


# ============================================================
# GET /api/host/cpu
# ============================================================

@router.get("/cpu")
def get_cpu():
    """
    Detailed CPU monitoring information.
    """

    # Overall CPU usage
    overall_usage = psutil.cpu_percent(interval=0.5)

    # CPU usage for every logical processor
    per_cpu_usage = psutil.cpu_percent(
        interval=0.5,
        percpu=True,
    )

    # CPU frequency
    frequency = psutil.cpu_freq()

    # Load average
    load_average = psutil.getloadavg()

    return {
        "usage_percent": overall_usage,

        "per_cpu_percent": per_cpu_usage,

        "logical_cores": psutil.cpu_count(
            logical=True
        ),

        "physical_cores": psutil.cpu_count(
            logical=False
        ),

        "load_average": {
            "1_min": round(load_average[0], 2),
            "5_min": round(load_average[1], 2),
            "15_min": round(load_average[2], 2),
        },

        "frequency_mhz": {
            "current": round(frequency.current, 2)
            if frequency
            else None,

            "min": round(frequency.min, 2)
            if frequency
            else None,

            "max": round(frequency.max, 2)
            if frequency
            else None,
        },
    }


# ============================================================
# GET /api/host/memory
# ============================================================

@router.get("/memory")
def get_memory():
    """
    Detailed RAM and swap information.
    """

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        # ----------------------------------------------------
        # RAM
        # ----------------------------------------------------
        "ram": {
            "total_gb": bytes_to_gb(memory.total),
            "used_gb": bytes_to_gb(memory.used),
            "available_gb": bytes_to_gb(memory.available),
            "free_gb": bytes_to_gb(memory.free),
            "usage_percent": memory.percent,
        },

        # ----------------------------------------------------
        # Swap
        # ----------------------------------------------------
        "swap": {
            "total_gb": bytes_to_gb(swap.total),
            "used_gb": bytes_to_gb(swap.used),
            "free_gb": bytes_to_gb(swap.free),
            "usage_percent": swap.percent,
        },
    }


# ============================================================
# GET /api/host/disk
# ============================================================

@router.get("/disk")
def get_disk():
    """
    Disk usage information for the main filesystem.
    """

    disk = psutil.disk_usage("/")

    return {
        "mount": "/",

        "total_gb": bytes_to_gb(
            disk.total
        ),

        "used_gb": bytes_to_gb(
            disk.used
        ),

        "free_gb": bytes_to_gb(
            disk.free
        ),

        "usage_percent": disk.percent,
    }


# ============================================================
# GET /api/host/disks
# ============================================================

@router.get("/disks")
def get_all_disks():
    """
    Return information about all mounted disks/filesystems.

    Useful when your KVM host has multiple disks such as:

        /
        /data
        /var/lib/libvirt
        /mnt/vm-storage

    This helps the dashboard show where VM storage exists.
    """

    disks = []

    for partition in psutil.disk_partitions(
        all=False
    ):

        try:
            usage = psutil.disk_usage(
                partition.mountpoint
            )

            disks.append(
                {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,

                    "total_gb": bytes_to_gb(
                        usage.total
                    ),

                    "used_gb": bytes_to_gb(
                        usage.used
                    ),

                    "free_gb": bytes_to_gb(
                        usage.free
                    ),

                    "usage_percent": usage.percent,
                }
            )

        except PermissionError:
            # Some system filesystems may not allow access.
            continue

    return {
        "disks": disks
    }


# ============================================================
# GET /api/host/network
# ============================================================

@router.get("/network")
def get_network():
    """
    Network interface information.

    Includes:

    - Interface name
    - UP/DOWN status
    - Link speed
    - IPv4 addresses
    - IPv6 addresses
    - MAC address
    - RX/TX traffic
    """

    interfaces = {}

    # Network interface status
    interface_stats = psutil.net_if_stats()

    # Network addresses
    interface_addresses = psutil.net_if_addrs()

    # Network traffic counters
    interface_counters = psutil.net_io_counters(
        pernic=True
    )

    for name, stats in interface_stats.items():

        addresses = []

        for address in interface_addresses.get(
            name,
            []
        ):

            # IPv4
            if address.family == socket.AF_INET:

                addresses.append(
                    {
                        "family": "IPv4",
                        "address": address.address,
                        "netmask": address.netmask,
                    }
                )

            # IPv6
            elif address.family == socket.AF_INET6:

                addresses.append(
                    {
                        "family": "IPv6",
                        "address": address.address,
                        "netmask": address.netmask,
                    }
                )

            # MAC address
            else:

                # AF_PACKET is normally used on Linux
                if hasattr(
                    socket,
                    "AF_PACKET"
                ) and address.family == socket.AF_PACKET:

                    addresses.append(
                        {
                            "family": "MAC",
                            "address": address.address,
                        }
                    )

        counter = interface_counters.get(name)

        interfaces[name] = {
            "is_up": stats.isup,

            "speed_mbps": stats.speed,

            "mtu": stats.mtu,

            "addresses": addresses,

            "traffic": {
                "bytes_sent": counter.bytes_sent
                if counter
                else 0,

                "bytes_received": counter.bytes_recv
                if counter
                else 0,

                "packets_sent": counter.packets_sent
                if counter
                else 0,

                "packets_received": counter.packets_recv
                if counter
                else 0,
            },
        }

    return {
        "interfaces": interfaces
    }


# ============================================================
# GET /api/host/uptime
# ============================================================

@router.get("/uptime")
def get_uptime():
    """
    Return server uptime information.
    """

    boot_time = psutil.boot_time()

    uptime_seconds = int(
        time.time() - boot_time
    )

    days = uptime_seconds // 86400

    hours = (
        uptime_seconds % 86400
    ) // 3600

    minutes = (
        uptime_seconds % 3600
    ) // 60

    seconds = uptime_seconds % 60

    return {
        "boot_time": boot_time,

        "uptime_seconds": uptime_seconds,

        "uptime": {
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
        },
    }
