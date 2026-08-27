import os
import re
import subprocess
import uuid

from .libvirt_service import libvirt_service


DISK_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.\-]+$")

# Devices are handed out in this order as disks are attached.
DISK_TARGET_ORDER = ["vda", "vdb", "vdc", "vdd", "vde", "vdf", "vdg", "vdh"]


class DiskValidationError(Exception):
    """Raised when a disk operation fails validation."""


def get_pool(pool_name: str):
    """
    Look up a libvirt storage pool object, raising a clear error
    if it does not exist rather than letting a libvirt exception
    bubble up unformatted.
    """

    conn = libvirt_service.connect()

    try:
        pool = conn.storagePoolLookupByName(pool_name)
    except Exception:
        raise DiskValidationError(
            f"Storage pool '{pool_name}' does not exist"
        )

    if not pool.isActive():
        raise DiskValidationError(
            f"Storage pool '{pool_name}' is not active"
        )

    return pool


def get_pool_capacity(pool_name: str) -> dict:
    """
    Return capacity/allocation/available figures for a pool, in GB.

    Used by the Create VM page to show:

        Total:      1.8 TB
        Used:       700 GB
        Available:  1.1 TB
    """

    pool = get_pool(pool_name)

    pool.refresh(0)

    state, capacity, allocation, available = pool.info()

    def to_gb(value_bytes):
        return round(value_bytes / 1024**3, 2)

    return {
        "pool": pool_name,
        "total_gb": to_gb(capacity),
        "used_gb": to_gb(allocation),
        "available_gb": to_gb(available),
    }


def get_pool_path(pool_name: str) -> str:
    """
    Resolve the filesystem path backing a storage pool by reading
    its XML description.
    """

    pool = get_pool(pool_name)

    xml_desc = pool.XMLDesc(0)

    import xml.etree.ElementTree as ET

    root = ET.fromstring(xml_desc)
    path_el = root.find("./target/path")

    if path_el is None or not path_el.text:
        raise DiskValidationError(
            f"Storage pool '{pool_name}' has no filesystem path"
        )

    return path_el.text


def validate_disk_request(pool_name: str, size_gb: int) -> None:
    """
    Validate a requested disk against pool capacity.

    Raises DiskValidationError on any problem.
    """

    if size_gb <= 0:
        raise DiskValidationError("Disk size must be greater than zero")

    capacity = get_pool_capacity(pool_name)

    # Leave a small safety margin (5%) so the pool never fills
    # completely, which can crash unrelated running VMs.
    usable = capacity["available_gb"] * 0.95

    if size_gb > usable:
        raise DiskValidationError(
            "Requested disk size ("
            f"{size_gb} GB) exceeds available capacity "
            f"({capacity['available_gb']} GB) in pool '{pool_name}'"
        )


def next_free_target(existing_targets: list[str]) -> str:
    """
    Return the next unused disk target device name (vda, vdb, ...).
    """

    for target in DISK_TARGET_ORDER:
        if target not in existing_targets:
            return target

    raise DiskValidationError(
        "No free disk target device names remain for this VM"
    )


def create_qcow2_disk(pool_name: str, vm_name: str, size_gb: int) -> str:
    """
    Create a new qcow2 disk image inside a storage pool.

    The disk path is always generated server-side from the pool
    path and a generated identifier -- it is never taken directly
    from user input.

    Returns the absolute path to the created disk image.
    """

    validate_disk_request(pool_name, size_gb)

    pool_path = get_pool_path(pool_name)

    disk_id = uuid.uuid4().hex[:8]
    safe_vm_name = re.sub(r"[^a-zA-Z0-9_.\-]", "_", vm_name)

    disk_filename = f"{safe_vm_name}-{disk_id}.qcow2"
    disk_path = os.path.join(pool_path, disk_filename)

    if os.path.exists(disk_path):
        # Astronomically unlikely given the random suffix, but
        # never silently overwrite an existing file.
        raise DiskValidationError(
            f"Generated disk path already exists: {disk_path}"
        )

    result = subprocess.run(
        [
            "qemu-img",
            "create",
            "-f",
            "qcow2",
            disk_path,
            f"{size_gb}G",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise DiskValidationError(
            f"Failed to create disk image: {result.stderr.strip()}"
        )

    # Refresh the pool so libvirt is aware of the new volume.
    pool = get_pool(pool_name)
    pool.refresh(0)

    return disk_path


def list_vm_disks(name: str) -> list[dict]:
    """
    List the disks currently attached to a VM by parsing its live
    or persistent domain XML.
    """

    import xml.etree.ElementTree as ET

    domain = libvirt_service.get_domain(name)

    if domain is None:
        raise DiskValidationError(f"VM '{name}' not found")

    xml_desc = domain.XMLDesc(0)
    root = ET.fromstring(xml_desc)

    disks = []

    for disk in root.findall("./devices/disk"):
        if disk.get("device") != "disk":
            continue

        target = disk.find("target")
        source = disk.find("source")
        driver = disk.find("driver")

        target_dev = target.get("dev") if target is not None else None

        size_gb = None

        if source is not None and source.get("file"):
            try:
                size_bytes = os.path.getsize(source.get("file"))
                size_gb = round(size_bytes / 1024**3, 2)
            except OSError:
                size_gb = None

        disks.append(
            {
                "target": target_dev,
                "bus": target.get("bus") if target is not None else None,
                "path": source.get("file") if source is not None else None,
                "format": driver.get("type") if driver is not None else None,
                "size_gb": size_gb,
                "status": "Active" if domain.isActive() else "Attached",
            }
        )

    return disks


def add_disk(name: str, pool_name: str, size_gb: int) -> dict:
    """
    Create a new qcow2 disk and attach it to a running or stopped
    VM, persistently.

    Performs all validation described in the dashboard design:

        * VM exists
        * storage pool exists
        * requested size is available
        * disk path is generated by the server
        * target device name is not already used
    """

    domain = libvirt_service.get_domain(name)

    if domain is None:
        raise DiskValidationError(f"VM '{name}' not found")

    existing = list_vm_disks(name)
    existing_targets = [d["target"] for d in existing if d["target"]]

    target = next_free_target(existing_targets)

    disk_path = create_qcow2_disk(pool_name, name, size_gb)

    disk_xml = (
        "<disk type='file' device='disk'>"
        "<driver name='qemu' type='qcow2'/>"
        f"<source file='{disk_path}'/>"
        f"<target dev='{target}' bus='virtio'/>"
        "</disk>"
    )

    import libvirt

    flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG

    if domain.isActive():
        flags |= libvirt.VIR_DOMAIN_AFFECT_LIVE

    domain.attachDeviceFlags(disk_xml, flags)

    return {
        "target": target,
        "path": disk_path,
        "size_gb": size_gb,
        "pool": pool_name,
    }
