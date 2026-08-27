import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..services.libvirt_service import libvirt_service
from ..services import disk_service
from ..services import iso_service


router = APIRouter(
    prefix="/api/vms",
    tags=["Virtual Machines"],
)


class CreateVMRequest(BaseModel):
    """
    Data submitted by the Create VM form.
    """

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    os: str = "Ubuntu 22.04 LTS"

    iso: str | None = Field(
        default=None,
        description="ISO volume name from /api/storage/isos, or null for no install media",
    )

    vcpus: int = Field(
        ge=1,
        le=128,
    )

    ram_gb: int = Field(
        ge=1,
        le=1024,
    )

    storage_pool: str

    disk_gb: int = Field(
        ge=10,
        le=10000,
    )

    network: str


class AddDiskRequest(BaseModel):
    """
    Data submitted by the "Add Disk" form on a VM's storage page.
    """

    storage_pool: str

    size_gb: int = Field(
        ge=1,
        le=10000,
    )


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


@router.post("")
def create_vm(request: CreateVMRequest):
    """
    Create a new VM, end to end.

    Follows the workflow from the dashboard design:

        1. Validate VM name
        2. Validate CPU / RAM (handled by pydantic Field constraints)
        3. Validate storage pool
        4. Validate requested disk size
        5. Validate network / bridge
        6. Create qcow2 disk
        7. Build libvirt XML, attach disk + network + ISO
        8. Define + start VM
    """

    try:
        libvirt_service.validate_name(request.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        libvirt_service.validate_network(request.network)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    iso_path = None

    if request.iso:
        isos = {iso["name"]: iso["path"] for iso in iso_service.list_isos()}

        if request.iso not in isos:
            raise HTTPException(
                status_code=400,
                detail=f"ISO '{request.iso}' was not found",
            )

        iso_path = isos[request.iso]

    try:
        disk_path = disk_service.create_qcow2_disk(
            request.storage_pool,
            request.name,
            request.disk_gb,
        )
    except disk_service.DiskValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        vm_info = libvirt_service.create_vm(request, disk_path, iso_path)

        return {
            "success": True,
            "vm": vm_info,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@router.get("/{name}")
def get_vm(name: str):
    """
    Get a specific VM.
    """

    domain = libvirt_service.get_domain(name)

    if domain is None:
        raise HTTPException(
            status_code=404,
            detail="VM not found",
        )

    return libvirt_service.domain_information(
        domain
    )


@router.get("/{name}/stats")
def get_vm_stats(name: str):
    """
    CPU, memory, disk and network statistics for a running VM.
    """

    try:
        return libvirt_service.get_vm_stats(name)

    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{name}/ip")
def get_vm_ip(name: str):
    """
    Discover the VM's current IP address(es).
    """

    try:
        return libvirt_service.get_vm_ip(name)

    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{name}/disks")
def get_vm_disks(name: str):
    """
    List disks currently attached to the VM.
    """

    try:
        return {"disks": disk_service.list_vm_disks(name)}

    except disk_service.DiskValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{name}/disks")
def add_vm_disk(name: str, request: AddDiskRequest):
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
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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


@router.delete("/{name}")
def delete_vm(name: str):
    """
    Delete VM definition.

    Storage deletion is intentionally not automatic.
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


@router.websocket("/{name}/console")
async def vm_console(websocket: WebSocket, name: str):
    """
    Bridge a browser WebSocket connection to the VM's VNC socket.

    The frontend connects a noVNC client to this endpoint. Binary
    frames are relayed unmodified in both directions -- this is
    intentionally protocol-agnostic (no VNC parsing happens here).
    """

    try:
        console = libvirt_service.get_console_info(name)
    except RuntimeError as exc:
        await websocket.close(code=4404, reason=str(exc))
        return

    await websocket.accept(subprotocol="binary")

    try:
        reader, writer = await asyncio.open_connection(
            console["host"], console["port"]
        )
    except OSError as exc:
        await websocket.close(code=4502, reason=f"Could not reach VNC socket: {exc}")
        return

    async def pump_socket_to_ws():
        try:
            while True:
                data = await reader.read(4096)

                if not data:
                    break

                await websocket.send_bytes(data)

        except Exception:
            pass

    async def pump_ws_to_socket():
        try:
            while True:
                data = await websocket.receive_bytes()
                writer.write(data)
                await writer.drain()

        except WebSocketDisconnect:
            pass

        except Exception:
            pass

    try:
        await asyncio.gather(
            pump_socket_to_ws(),
            pump_ws_to_socket(),
        )
    finally:
        writer.close()
