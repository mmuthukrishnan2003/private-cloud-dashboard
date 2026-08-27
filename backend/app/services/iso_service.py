from pathlib import Path
import urllib.request

from .libvirt_service import libvirt_service


# ============================================================
# ISO STORAGE LOCATION
# ============================================================

ISO_PATH = Path(
    "/var/lib/libvirt/images/isos"
)


# ============================================================
# OFFICIAL UBUNTU ISO DEFINITIONS
# ============================================================

UBUNTU_ISOS = {
    "22.04": {
        "name": "Ubuntu 22.04.5 LTS",
        "url": (
            "https://releases.ubuntu.com/jammy/"
            "ubuntu-22.04.5-live-server-amd64.iso"
        ),
        "filename": "ubuntu-22.04.5-live-server-amd64.iso",
    },

    "24.04": {
        "name": "Ubuntu 24.04.4 LTS",
        "url": (
            "https://releases.ubuntu.com/noble/"
            "ubuntu-24.04.4-live-server-amd64.iso"
        ),
        "filename": "ubuntu-24.04.4-live-server-amd64.iso",
    },

    "26.04": {
        "name": "Ubuntu 26.04 LTS",
        "url": (
            "https://releases.ubuntu.com/resolute/"
            "ubuntu-26.04-live-server-amd64.iso"
        ),
        "filename": "ubuntu-26.04-live-server-amd64.iso",
    },
}


# ============================================================
# LIST ISO FILES
# ============================================================

def list_isos(iso_pool: str = "isos") -> list[dict]:
    """
    List ISO images available in the libvirt ISO storage pool.

    The storage pool is expected to be named "isos".

    Returns:
        [
            {
                "name": "ubuntu-22.04.5-live-server-amd64.iso",
                "path": "/var/lib/libvirt/images/isos/ubuntu-22.04.5-live-server-amd64.iso",
                "size_gb": 2.0
            }
        ]

    If the pool does not exist or is inactive,
    an empty list is returned.
    """

    conn = libvirt_service.connect()

    try:
        # Find the ISO storage pool.
        try:
            pool = conn.storagePoolLookupByName(
                iso_pool
            )
        except Exception:
            return []

        # Pool must be active.
        if not pool.isActive():
            return []

        # Refresh pool contents.
        pool.refresh(0)

        isos = []

        # Get all volumes inside the pool.
        for volume_name in pool.listVolumes():

            # Only return ISO files.
            if not volume_name.lower().endswith(".iso"):
                continue

            try:
                volume = pool.storageVolLookupByName(
                    volume_name
                )

                # volume.info()[1] = allocated size in bytes.
                size_bytes = volume.info()[1]

                isos.append(
                    {
                        "name": volume_name,
                        "path": volume.path(),
                        "size_gb": round(
                            size_bytes / (1024 ** 3),
                            2,
                        ),
                    }
                )

            except Exception:
                # Ignore individual broken volumes.
                continue

        return isos

    finally:
        # Close libvirt connection.
        try:
            conn.close()
        except Exception:
            pass


# ============================================================
# AVAILABLE UBUNTU VERSIONS
# ============================================================

def available_ubuntu_versions() -> list[dict]:
    """
    Return Ubuntu versions available for download
    from the dashboard.
    """

    return [
        {
            "version": version,
            **details,
        }
        for version, details in UBUNTU_ISOS.items()
    ]


# ============================================================
# DOWNLOAD UBUNTU ISO
# ============================================================

def download_ubuntu_iso(version: str) -> str:
    """
    Download an official Ubuntu Server ISO directly
    to the KVM host.

    Args:
        version:
            Ubuntu version key, for example:
            "22.04", "24.04", "26.04"

    Returns:
        Full path of downloaded ISO.
    """

    # Check requested version.
    if version not in UBUNTU_ISOS:
        raise ValueError(
            "Unsupported Ubuntu version"
        )

    item = UBUNTU_ISOS[version]

    # Create ISO directory if it does not exist.
    ISO_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Final ISO destination.
    destination = (
        ISO_PATH / item["filename"]
    )

    # Do not download again if already present.
    if destination.exists():
        return str(destination)

    # Download official Ubuntu ISO.
    urllib.request.urlretrieve(
        item["url"],
        destination,
    )

    return str(destination)
