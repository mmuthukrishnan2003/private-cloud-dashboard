import subprocess

from fastapi import APIRouter, HTTPException

from ..services import disk_service
from ..services import iso_service

router = APIRouter(
    prefix="/api/storage",
    tags=["Storage"],
)


@router.get("/pools")
def list_storage_pools():
    """
    Return all libvirt storage pools.

    This is what the Create VM page will use for:

        Storage Pool: NVMe-01
        Storage Pool: default
        Storage Pool: SSD-01
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

    pools = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    return {
        "pools": pools
    }


@router.get("/pool/{pool_name}")
def get_pool(pool_name: str):
    """
    Get information about one storage pool.
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

    return {
        "pool": pool_name,
        "info": result.stdout,
    }


@router.get("/pool/{pool_name}/capacity")
def get_pool_capacity(pool_name: str):
    """
    Structured capacity figures for a storage pool, used by the
    Create VM page:

        Total:      1.8 TB
        Used:       700 GB
        Available:  1.1 TB
    """

    try:
        return disk_service.get_pool_capacity(pool_name)

    except disk_service.DiskValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/isos")
def list_isos():
    """
    List available install ISOs (from the "isos" storage pool) for
    the Create VM page's OS selector.
    """

    return {"isos": iso_service.list_isos()}
