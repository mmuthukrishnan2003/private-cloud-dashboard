import os
import subprocess
import tempfile
from pathlib import Path


CLOUD_INIT_DIR = Path(
    "/var/lib/libvirt/images/cloud-init"
)


def create_cloud_init(
    vm_name: str,
    username: str,
    password: str | None,
    hostname: str,
    ip_address: str | None,
    prefix: int | None,
    gateway: str | None,
    dns_servers: list[str],
) -> str:
    """
    Create a cloud-init ISO for the VM.

    This ISO contains:
        - hostname
        - user account
        - password
        - network configuration

    Ubuntu will read this during first boot.
    """

    CLOUD_INIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    vm_dir = CLOUD_INIT_DIR / vm_name

    vm_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    user_data = f"""#cloud-config

hostname: {hostname}

manage_etc_hosts: true

users:
  - name: {username}
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: sudo
    shell: /bin/bash
"""

    if password:
        user_data += f"""
    lock_passwd: false
    plain_text_passwd: "{password}"
"""

    user_data += """
ssh_pwauth: true

package_update: true

packages:
  - qemu-guest-agent

runcmd:
  - systemctl enable --now qemu-guest-agent
"""

    # ---------------------------------------------------------
    # Static IP configuration
    # ---------------------------------------------------------

    if ip_address and prefix and gateway:

        dns = ", ".join(
            f'"{x}"'
            for x in dns_servers
        )

        network_config = f"""version: 2

ethernets:

  ens3:

    dhcp4: false

    addresses:
      - {ip_address}/{prefix}

    routes:
      - to: default
        via: {gateway}

    nameservers:
      addresses:
        - {dns}
"""

    else:

        # DHCP configuration.
        network_config = """version: 2

ethernets:

  ens3:
    dhcp4: true
"""

    meta_data = f"""instance-id: {vm_name}
local-hostname: {hostname}
"""

    user_file = vm_dir / "user-data"
    network_file = vm_dir / "network-config"
    meta_file = vm_dir / "meta-data"

    user_file.write_text(user_data)
    network_file.write_text(network_config)
    meta_file.write_text(meta_data)

    iso_path = vm_dir / f"{vm_name}-cloud-init.iso"

    # ---------------------------------------------------------
    # Generate cloud-init ISO
    # ---------------------------------------------------------

    subprocess.run(
        [
            "cloud-localds",
            "--network-config",
            str(network_file),
            str(iso_path),
            str(user_file),
        ],
        check=True,
    )

    return str(iso_path)
