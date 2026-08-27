```python
"""
VM API routes.

Provides:
- List VMs
- Create VM
- VM details
- VM statistics
- VM IP discovery
- VM disk management
- Start / stop / restart
- Delete VM
- Browser console WebSocket
"""

import asyncio

from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field

from ..services.libvirt_service import libvirt_service
from ..services import disk_service
from ..services import iso_service


# ============================================================
# Router
# ============================================================

router = APIRouter(
    prefix="/api/vms",
    tags=["Virtual Machines"],
)


# ============================================================
# Request Models
# ============================================================

class CreateVMRequest(BaseModel):
    """
    Data submitted by the Create VM form.
    """

    # --------------------------------------------------------
    # Basic VM information
    # --------------------------------------------------------

    name: str = Field(
        min_length=1,
        max_length=100,
        description="VM name",
    )

    os: str = Field(
        default="Ubuntu 22.04 LTS",
        description="Guest operating system",
    )

    iso: str | None = Field(
        default=None,
        description=(
            "ISO volume name returned by /api/storage/isos, "
            "or null when no ISO is required"
        ),
    )

    # --------------------------------------------------------
    # CPU / RAM
    # --------------------------------------------------------

    vcpus: int = Field(
        default=2,
        ge=1,
        le=128,
        description="Number of virtual CPUs",
    )

    ram_gb: int = Field(
        default=4,
        ge=1,
        le=1024,
        description="RAM in GB",
    )

    # --------------------------------------------------------
    # Storage
    # --------------------------------------------------------

    storage_pool: str = Field(
        description="libvirt storage pool name",
    )

    disk_gb: int = Field(
        default=20,
        ge=10,
        le=10000,
        description="New virtual disk size in GB",
    )

    disk_format: str = Field(
        default="qcow2",
        description="Disk image format",
    )

    disk_bus: str = Field(
        default="virtio",
        description="Virtual disk bus",
    )

    existing_disk: str | None = Field(
        default=None,
        description="Existing disk image path or volume",
    )

    # --------------------------------------------------------
    # Network
    # --------------------------------------------------------

    network_type: str = Field(
        default="bridge",
        description="Network mode: bridge, nat, none, etc.",
    )

    bridge: str | None = Field(
        default=None,
        description="Linux bridge name, for example br0",
    )

    ip_mode: str = Field(
        default="dhcp",
        description="IP mode: dhcp or static",
    )

    ip_address: str | None = Field(
        default=None,
        description="Static IP address",
    )

    prefix: int | None = Field(
        default=None,
        ge=1,
        le=32,
        description="Network prefix length",
    )

    gateway: str | None = Field(
        default=None,
        description="Default gateway",
    )

    dns_servers: list[str] = Field(
        default_factory=list,
        description="DNS server addresses",
    )

    # --------------------------------------------------------
    # Backward compatibility
    # --------------------------------------------------------
    #
    # Older backend code uses:
    #
    #     request.network
    #
    # Keep this field optional so old libvirt_service.py code
    # does not immediately break while the new form uses
    # network_type / bridge.
    # --------------------------------------------------------

    network: str | None = Field(
        default=None,
        description=(
            "Legacy network/bridge field. "
            "If supplied, it takes priority over bridge."
        ),
    )

    # --------------------------------------------------------
    # GPU
    # --------------------------------------------------------

    gpu_mode: str = Field(
        default="none",
        description="GPU mode: none, passthrough, etc.",
    )

    gpu_pci_address: str | None = Field(
        default=None,
        description="PCI address for GPU passthrough",
    )

    # --------------------------------------------------------
    # Cloud-init
    # --------------------------------------------------------

    hostname: str | None = Field(
        default=None,
        description="Guest hostname",
    )

    username: str | None = Field(
        default=None,
        description="Initial guest username",
    )

    password: str | None = Field(
        default=None,
        description="Initial guest password",
    )


class AddDiskRequest(BaseModel):
    """
    Data submitted by the Add Disk form.
    """

    storage_pool: str = Field(
        description="Storage pool where the disk will be created",
    )

    size_gb: int = Field(
        ge=1,
        le=10000,
        description="Disk size in GB",
    )


# ============================================================
# Helper
# ============================================================

def get_requested_network(request: CreateVMRequest) -> str:
    """
    Return the network/bridge value that should be used by
    the existing libvirt service.

    Priority:
        1. Legacy 'network' field
        2. New 'bridge' field
        3. 'default' libvirt network
    """

    return (
        request.network
        or request.bridge
        or "default"
    )


# ============================================================
# VM List
# ============================================================

@router.get("")
def list_vms():
    """
    List all KVM VMs.
    """

    try:
        return {
            "vms": libvirt_service.list_vms()
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# Create VM
# ============================================================

@router.post("")
def create_vm(request: CreateVMRequest):
    """
    Create a new KVM VM.

    Workflow:

        1. Validate VM name
        2. Validate network
        3. Validate ISO
        4. Create qcow2 disk
        5. Build libvirt XML
        6. Define VM
        7. Start VM
    """

    # --------------------------------------------------------
    # 1. Validate VM name
    # --------------------------------------------------------

    try:
        libvirt_service.validate_name(
            request.name
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # --------------------------------------------------------
    # 2. Resolve network
    # --------------------------------------------------------

    requested_network = get_requested_network(request)

    try:
        libvirt_service.validate_network(
            requested_network
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # --------------------------------------------------------
    # 3. Validate IP configuration
    # --------------------------------------------------------

    if request.ip_mode not in {
        "dhcp",
        "static",
    }:
        raise HTTPException(
            status_code=400,
            detail="ip_mode must be 'dhcp' or 'static'",
        )

    if request.ip_mode == "static":

        if not request.ip_address:
            raise HTTPException(
                status_code=400,
                detail=(
                    "ip_address is required "
                    "when ip_mode is 'static'"
                ),
            )

        if request.prefix is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "prefix is required "
                    "when ip_mode is 'static'"
                ),
            )

        if not request.gateway:
            raise HTTPException(
                status_code=400,
                detail=(
                    "gateway is required "
                    "when ip_mode is 'static'"
                ),
            )

    # --------------------------------------------------------
    # 4. Validate GPU configuration
    # --------------------------------------------------------

    if request.gpu_mode != "none":
        if not request.gpu_pci_address:
            raise HTTPException(
                status_code=400,
                detail=(
                    "gpu_pci_address is required "
                    "when GPU mode is enabled"
                ),
            )

    # --------------------------------------------------------
    # 5. Validate ISO
    # --------------------------------------------------------

    iso_path = None

    if request.iso:

        try:
            iso_list = iso_service.list_isos()

            isos = {
                iso["name"]: iso["path"]
                for iso in iso_list
            }

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Could not list ISO images: {exc}",
            )

        if request.iso not in isos:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"ISO '{request.iso}' "
                    "was not found"
                ),
            )

        iso_path = isos[request.iso]

    # --------------------------------------------------------
    # 6. Create virtual disk
    # --------------------------------------------------------

    disk_path = None

    # If an existing disk is provided, do not create another
    # disk image.
    if request.existing_disk:

        disk_path = request.existing_disk

    else:

        try:
            disk_path = disk_service.create_qcow2_disk(
                request.storage_pool,
                request.name,
                request.disk_gb,
            )

        except disk_service.DiskValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            )

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Could not create VM disk: {exc}",
            )

    # --------------------------------------------------------
    # 7. Create VM using libvirt service
    # --------------------------------------------------------

    try:

        # The existing libvirt_service.create_vm()
        # receives the complete request object.
        #
        # request.network is kept populated here so older
        # service code continues to work.

        request.network = requested_network

        vm_info = libvirt_service.create_vm(
            request,
            disk_path,
            iso_path,
        )

        return {
            "success": True,
            "message": f"VM '{request.name}' created successfully",
            "vm": vm_info,
        }

    except Exception as exc:

        # VM creation failed after disk creation.
        # Do not automatically delete the disk because it
        # may be useful for troubleshooting/recovery.

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# VM Details
# ============================================================

@router.get("/{name}")
def get_vm(name: str):
    """
    Get detailed information about a VM.
    """

    try:
        domain = libvirt_service.get_domain(name)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    if domain is None:
        raise HTTPException(
            status_code=404,
            detail="VM not found",
        )

    try:
        return libvirt_service.domain_information(
            domain
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# VM Statistics
# ============================================================

@router.get("/{name}/stats")
def get_vm_stats(name: str):
    """
    CPU, memory, disk and network statistics
    for a running VM.
    """

    try:
        return libvirt_service.get_vm_stats(name)

    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# VM IP
# ============================================================

@router.get("/{name}/ip")
def get_vm_ip(name: str):
    """
    Discover the VM's current IP address(es).
    """

    try:
        return libvirt_service.get_vm_ip(name)

    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# VM Disks
# ============================================================

@router.get("/{name}/disks")
def get_vm_disks(name: str):
    """
    List disks currently attached to the VM.
    """

    try:
        return {
            "disks": disk_service.list_vm_disks(name)
        }

    except disk_service.DiskValidationError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# Add VM Disk
# ============================================================

@router.post("/{name}/disks")
def add_vm_disk(
    name: str,
    request: AddDiskRequest,
):
    """
    Create and attach a new disk to an existing VM.
    """

    try:

        disk = disk_service.add_disk(
            name,
            request.storage_pool,
            request.size_gb,
        )

        return {
            "success": True,
            "disk": disk,
        }

    except disk_service.DiskValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# Start VM
# ============================================================

@router.post("/{name}/start")
def start_vm(name: str):
    """
    Start VM.
    """

    try:

        libvirt_service.start_vm(name)

        return {
            "success": True,
            "message": f"{name} started",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# Stop VM
# ============================================================

@router.post("/{name}/stop")
def stop_vm(name: str):
    """
    Stop VM.
    """

    try:

        libvirt_service.stop_vm(name)

        return {
            "success": True,
            "message": f"{name} stopped",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# Restart VM
# ============================================================

@router.post("/{name}/restart")
def restart_vm(name: str):
    """
    Restart VM.
    """

    try:

        libvirt_service.restart_vm(name)

        return {
            "success": True,
            "message": f"{name} restarted",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# Delete VM
# ============================================================

@router.delete("/{name}")
def delete_vm(name: str):
    """
    Delete VM definition.

    The virtual disk is NOT automatically deleted.
    """

    try:

        libvirt_service.delete_vm(name)

        return {
            "success": True,
            "message": f"{name} deleted",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# VM Console WebSocket
# ============================================================

@router.websocket("/{name}/console")
async def vm_console(
    websocket: WebSocket,
    name: str,
):
    """
    Bridge browser WebSocket traffic to the VM's VNC socket.

    noVNC connects to this endpoint.

    Binary WebSocket frames are forwarded directly between:
    
        Browser <-> FastAPI <-> VNC socket
    """

    # --------------------------------------------------------
    # Get VNC console information
    # --------------------------------------------------------

    try:

        console = libvirt_service.get_console_info(
            name
        )

    except RuntimeError as exc:

        await websocket.close(
            code=4404,
            reason=str(exc),
        )

        return

    except Exception as exc:

        await websocket.close(
            code=4500,
            reason=str(exc),
        )

        return

    # --------------------------------------------------------
    # Accept browser WebSocket
    # --------------------------------------------------------

    try:

        await websocket.accept(
            subprotocol="binary"
        )

    except Exception:
        return

    # --------------------------------------------------------
    # Connect to VNC socket
    # --------------------------------------------------------

    try:

        reader, writer = await asyncio.open_connection(
            console["host"],
            console["port"],
        )

    except OSError as exc:

        await websocket.close(
            code=4502,
            reason=f"Could not reach VNC socket: {exc}",
        )

        return

    # --------------------------------------------------------
    # VNC -> Browser
    # --------------------------------------------------------

    async def pump_socket_to_ws():
        """
        Read data from VNC and send it to browser.
        """

        try:

            while True:

                data = await reader.read(4096)

                if not data:
                    break

                await websocket.send_bytes(
                    data
                )

        except (
            WebSocketDisconnect,
            ConnectionError,
            asyncio.CancelledError,
        ):
            pass

        except Exception:
            pass

    # --------------------------------------------------------
    # Browser -> VNC
    # --------------------------------------------------------

    async def pump_ws_to_socket():
        """
        Read binary frames from browser and send them
        to the VNC socket.
        """

        try:

            while True:

                data = await websocket.receive_bytes()

                writer.write(data)

                await writer.drain()

        except WebSocketDisconnect:
            pass

        except (
            ConnectionError,
            asyncio.CancelledError,
        ):
            pass

        except Exception:
            pass

    # --------------------------------------------------------
    # Run both directions simultaneously
    # --------------------------------------------------------

    try:

        await asyncio.gather(
            pump_socket_to_ws(),
            pump_ws_to_socket(),
        )

    finally:

        # Always close the VNC connection when the browser
        # disconnects or an error occurs.

        try:
            writer.close()
            await writer.wait_closed()

        except Exception:
            pass

        try:
            await websocket.close()

        except Exception:
            pass
```
