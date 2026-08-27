from .libvirt_service import libvirt_service


def list_isos(iso_pool: str = "isos") -> list[dict]:
    """
    List ISO images available in the ISO storage pool.

    Expects a libvirt storage pool (conventionally named "isos")
    containing .iso volumes, e.g. ubuntu-22.04.4-live-server-amd64.iso.

    Returns an empty list, rather than raising, if the pool does
    not exist -- the Create VM page treats "no ISO pool configured"
    as a normal, recoverable state.
    """

    conn = libvirt_service.connect()

    try:
        pool = conn.storagePoolLookupByName(iso_pool)
    except Exception:
        return []

    if not pool.isActive():
        return []

    pool.refresh(0)

    isos = []

    for volume_name in pool.listVolumes():
        if not volume_name.lower().endswith(".iso"):
            continue

        volume = pool.storageVolLookupByName(volume_name)

        isos.append(
            {
                "name": volume_name,
                "path": volume.path(),
                "size_gb": round(volume.info()[1] / 1024**3, 2),
            }
        )

    return isos
