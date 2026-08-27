# ============================================================
# storage.py
# KVM Dashboard - Storage Management API
# ============================================================

import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from ..services import disk_service
from ..services import iso_service


# ============================================================
# Router
# ============================================================

router = APIRouter(
    prefix="/api/storage",
    tags=["Storage"],
)


# ============================================================
# Upload Directory
# ============================================================
#
# Files uploaded from the user's PC will be stored here.
#
# Examples:
#
#   Ubuntu ISO
#   Windows ISO
#   QCOW2 disk
#   VMDK disk
#   VHD/VHDX disk
#   VDI disk
#
# ============================================================

UPLOAD_PATH = Path(
    "/var/lib/libvirt/images/uploads"
)


# ============================================================
# Supported Upload Formats
# ============================================================

ALLOWED_EXTENSIONS = {
    ".iso",
    ".qcow2",
    ".qcow",
    ".raw",
    ".img",
    ".vmdk",
    ".vhd",
    ".vhdx",
    ".vdi",
}


# ============================================================
# Storage Pools
# ============================================================

@router.get("/pools")
def list_storage_pools():
    """
    Return all libvirt storage pools.

    Example:

        NVMe-01
        default
        SSD-01
    """

    result = subprocess.run(
        [
            "virsh",
            "-c",
            "qemu:///system",
            "pool-list",
            "--all",
            "--name",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    # If virsh itself failed
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=(
                result.stderr.strip()
                or "Unable to list storage pools."
            ),
        )

    pools = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    return {
        "success": True,
        "pools": pools,
    }


# ============================================================
# Storage Pool Information
# ============================================================

@router.get("/pool/{pool_name}")
def get_pool(pool_name: str):
    """
    Get information about one libvirt storage pool.
    """

    result = subprocess.run(
        [
            "virsh",
            "-c",
            "qemu:///system",
            "pool-info",
            pool_name,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=404,
            detail=(
                result.stderr.strip()
                or f"Storage pool '{pool_name}' not found."
            ),
        )

    return {
        "success": True,
        "pool": pool_name,
        "info": result.stdout,
    }


# ============================================================
# Storage Pool Capacity
# ============================================================

@router.get("/pool/{pool_name}/capacity")
def get_pool_capacity(pool_name: str):
    """
    Return structured storage pool capacity.

    Example response:

        {
            "total_gb": 1800,
            "used_gb": 700,
            "available_gb": 1100
        }
    """

    try:

        return disk_service.get_pool_capacity(
            pool_name
        )

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
# ISO Listing
# ============================================================

@router.get("/isos")
def list_isos():
    """
    List installation ISO files available
    on the KVM server.

    Used by the Create VM page.
    """

    try:

        isos = iso_service.list_isos()

        return {
            "success": True,
            "isos": isos,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to list ISO files: {exc}",
        )


# ============================================================
# Upload ISO / Virtual Disk
# ============================================================

@router.post("/upload")
async def upload_storage_file(
    file: UploadFile = File(...)
):
    """
    Upload an ISO or virtual disk image
    from the user's PC to the KVM server.

    Supported formats:

        .iso
        .qcow2
        .qcow
        .raw
        .img
        .vmdk
        .vhd
        .vhdx
        .vdi

    Example:

        POST /api/storage/upload
    """

    # --------------------------------------------------------
    # Check filename
    # --------------------------------------------------------

    filename = Path(
        file.filename or ""
    ).name

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    # --------------------------------------------------------
    # Get extension
    # --------------------------------------------------------

    extension = Path(
        filename
    ).suffix.lower()

    # --------------------------------------------------------
    # Validate extension
    # --------------------------------------------------------

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file format. "
                "Supported: ISO, QCOW2, QCOW, RAW, "
                "IMG, VMDK, VHD, VHDX, VDI."
            ),
        )

    # --------------------------------------------------------
    # Create upload directory
    # --------------------------------------------------------

    try:

        UPLOAD_PATH.mkdir(
            parents=True,
            exist_ok=True,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to create upload directory: {exc}"
            ),
        )

    # --------------------------------------------------------
    # Destination
    # --------------------------------------------------------

    destination = (
        UPLOAD_PATH / filename
    )

    # --------------------------------------------------------
    # Prevent overwrite
    # --------------------------------------------------------

    if destination.exists():

        raise HTTPException(
            status_code=409,
            detail=(
                f"File '{filename}' already exists."
            ),
        )

    # --------------------------------------------------------
    # Save uploaded file
    #
    # Use 1 MB chunks so large ISO files do not need
    # to be loaded completely into RAM.
    # --------------------------------------------------------

    try:

        with destination.open("wb") as output:

            while True:

                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                output.write(chunk)

    except Exception as exc:

        # ----------------------------------------------------
        # Remove incomplete file
        # ----------------------------------------------------

        if destination.exists():

            try:
                destination.unlink()
            except Exception:
                pass

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {exc}",
        )

    finally:

        await file.close()

    # --------------------------------------------------------
    # File size
    # --------------------------------------------------------

    file_size = destination.stat().st_size

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "success": True,
        "message": "File uploaded successfully.",
        "filename": filename,
        "extension": extension,
        "path": str(destination),
        "size_bytes": file_size,
        "size_gb": round(
            file_size / 1024**3,
            2,
        ),
    }


# ============================================================
# Ubuntu Versions
# ============================================================

@router.get("/ubuntu")
def ubuntu_versions():
    """
    Return Ubuntu versions supported
    by the dashboard.
    """

    try:

        versions = (
            iso_service
            .available_ubuntu_versions()
        )

        return {
            "success": True,
            "versions": versions,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to get Ubuntu versions: {exc}"
            ),
        )


# ============================================================
# Download Ubuntu ISO
# ============================================================

@router.post("/ubuntu/download/{version}")
def download_ubuntu(version: str):
    """
    Download an Ubuntu ISO directly to
    the KVM server.

    Example:

        POST /api/storage/ubuntu/download/22.04
    """

    try:

        path = (
            iso_service
            .download_ubuntu_iso(version)
        )

        return {
            "success": True,
            "message": "Ubuntu ISO downloaded successfully.",
            "version": version,
            "path": path,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )
