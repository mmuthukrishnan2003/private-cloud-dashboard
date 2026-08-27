import re
import time

import libvirt

from .vm_builder import build_domain_xml, build_bridge_domain_xml


VM_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.\-]{0,99}$")


class LibvirtService:
    """
    Central service for KVM/libvirt operations.

    The dashboard talks to libvirt through this class.
    """

    def __init__(self):
        self.connection = None

    def connect(self):
        """
        Connect to the system libvirt daemon.
        """

        if self.connection is None:
            self.connection = libvirt.open("qemu:///system")

            if self.connection is None:
                raise RuntimeError(
                    "Unable to connect to libvirt"
                )

        return self.connection

    def list_vms(self):
        """
        Return all defined KVM virtual machines.
        """

        conn = self.connect()

        result = []

        for domain_id in conn.listAllDomains():
            result.append(
                self.domain_information(domain_id)
            )

        return result

    def domain_information(self, domain):
        """
        Convert a libvirt domain into dashboard information.
        """

        state, _, _, _, _ = domain.info()

        status_map = {
            libvirt.VIR_DOMAIN_NOSTATE: "No State",
            libvirt.VIR_DOMAIN_RUNNING: "Running",
            libvirt.VIR_DOMAIN_BLOCKED: "Blocked",
            libvirt.VIR_DOMAIN_PAUSED: "Paused",
            libvirt.VIR_DOMAIN_SHUTDOWN: "Stopped",
            libvirt.VIR_DOMAIN_SHUTOFF: "Stopped",
            libvirt.VIR_DOMAIN_CRASHED: "Crashed",
        }

        return {
            "id": domain.UUIDString(),
            "name": domain.name(),
            "status": status_map.get(
                state,
                "Unknown",
            ),
            "uuid": domain.UUIDString(),
        }

    def get_domain(self, name):
        """
        Find a VM by name.
        """

        conn = self.connect()

        try:
            return conn.lookupByName(name)
        except libvirt.libvirtError:
            return None

    def start_vm(self, name):
        """
        Start VM.
        """

        domain = self.get_domain(name)

        if domain is None:
            raise RuntimeError(
                f"VM '{name}' not found"
            )

        if not domain.isActive():
            domain.create()

        return True

    def stop_vm(self, name):
        """
        Gracefully shutdown VM.
        """

        domain = self.get_domain(name)

        if domain is None:
            raise RuntimeError(
                f"VM '{name}' not found"
            )

        if domain.isActive():
            domain.shutdown()

        return True

    def restart_vm(self, name):
        """
        Restart VM.
        """

        domain = self.get_domain(name)

        if domain is None:
            raise RuntimeError(
                f"VM '{name}' not found"
            )

        if domain.isActive():
            domain.reboot(
                flags=libvirt.VIR_DOMAIN_REBOOT_DEFAULT
            )
        else:
            domain.create()

        return True

    def delete_vm(self, name):
        """
        Remove VM from libvirt.

        IMPORTANT:
        Storage deletion should be handled separately so the
        dashboard can implement safe storage confirmation.
        """

        domain = self.get_domain(name)

        if domain is None:
            raise RuntimeError(
                f"VM '{name}' not found"
            )

        if domain.isActive():
            domain.destroy()

        domain.undefine()

        return True

    # ------------------------------------------------------------
    # VM creation
    # ------------------------------------------------------------

    def validate_name(self, name: str) -> None:
        """
        Validate a requested VM name.

        Enforced separately from Pydantic's length check so the
        error message is specific to naming rules, and so this can
        be reused by any future caller (e.g. a CLI import tool).
        """

        if not VM_NAME_PATTERN.match(name):
            raise ValueError(
                "VM name must start with a letter or number and "
                "contain only letters, numbers, '.', '_' and '-'"
            )

        if self.get_domain(name) is not None:
            raise ValueError(f"A VM named '{name}' already exists")

    def validate_network(self, network: str) -> str:
        """
        Confirm a requested network exists, either as a libvirt
        virtual network or as a host bridge device.

        Returns "network" or "bridge" describing which kind it is.
        """

        conn = self.connect()

        try:
            net = conn.networkLookupByName(network)

            if not net.isActive():
                raise ValueError(
                    f"Network '{network}' exists but is not active"
                )

            return "network"

        except libvirt.libvirtError:
            pass

        import os

        if os.path.exists(f"/sys/class/net/{network}/bridge"):
            return "bridge"

        raise ValueError(
            f"Network or bridge '{network}' was not found on this host"
        )

    def create_vm(self, request, disk_path: str, iso_path: str | None):
        """
        Define and start a new VM from an already-created disk image.

        Disk creation, pool/network/name validation, and capacity
        checks all happen upstream of this method (see routers/vms.py
        and services/disk_service.py) -- by the time this runs, the
        only remaining job is building the domain XML and handing it
        to libvirt.
        """

        conn = self.connect()

        network_kind = self.validate_network(request.network)

        ram_mb = request.ram_gb * 1024

        if network_kind == "bridge":
            domain_xml = build_bridge_domain_xml(
                name=request.name,
                vcpus=request.vcpus,
                ram_mb=ram_mb,
                disk_path=disk_path,
                bridge=request.network,
                iso_path=iso_path,
            )
        else:
            domain_xml = build_domain_xml(
                name=request.name,
                vcpus=request.vcpus,
                ram_mb=ram_mb,
                disk_path=disk_path,
                network=request.network,
                iso_path=iso_path,
            )

        domain = conn.defineXML(domain_xml)

        if domain is None:
            raise RuntimeError("libvirt rejected the generated domain XML")

        domain.create()

        return self.domain_information(domain)

    # ------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------

    def get_vm_stats(self, name: str) -> dict:
        """
        Return CPU, memory, disk and network statistics for a VM.

        CPU usage is derived from two samples of cumulative CPU
        time taken ~0.5s apart, similar to how `psutil.cpu_percent`
        works for the host.
        """

        domain = self.get_domain(name)

        if domain is None:
            raise RuntimeError(f"VM '{name}' not found")

        if not domain.isActive():
            return {
                "name": name,
                "status": "Stopped",
                "cpu": None,
                "memory": None,
                "disks": [],
                "network": [],
            }

        info_1 = domain.info()
        cpu_time_1 = info_1[4]
        t1 = time.time()

        time.sleep(0.3)

        info_2 = domain.info()
        cpu_time_2 = info_2[4]
        t2 = time.time()

        vcpus = info_2[3] or 1
        elapsed_ns = (t2 - t1) * 1_000_000_000

        cpu_percent = 0.0

        if elapsed_ns > 0:
            cpu_percent = round(
                (
                    (cpu_time_2 - cpu_time_1)
                    / elapsed_ns
                    / vcpus
                )
                * 100,
                2,
            )

        memory = {"total_mb": info_2[1], "used_mb": None}

        try:
            mem_stats = domain.memoryStats()

            if "available" in mem_stats and "unused" in mem_stats:
                used_kb = mem_stats["available"] - mem_stats["unused"]
                memory["used_mb"] = round(used_kb / 1024, 2)

            memory["total_mb"] = round(info_2[1] / 1024, 2)

        except libvirt.libvirtError:
            pass

        disk_stats = []

        import xml.etree.ElementTree as ET

        root = ET.fromstring(domain.XMLDesc(0))

        for disk in root.findall("./devices/disk"):
            target = disk.find("target")

            if target is None:
                continue

            dev = target.get("dev")

            try:
                rd_req, rd_bytes, wr_req, wr_bytes, errs = (
                    domain.blockStats(dev)
                )

                disk_stats.append(
                    {
                        "device": dev,
                        "read_bytes": rd_bytes,
                        "write_bytes": wr_bytes,
                    }
                )

            except libvirt.libvirtError:
                continue

        network_stats = []

        for iface in root.findall("./devices/interface/target"):
            dev = iface.get("dev")

            if not dev:
                continue

            try:
                (
                    rx_bytes,
                    rx_packets,
                    rx_errs,
                    rx_drop,
                    tx_bytes,
                    tx_packets,
                    tx_errs,
                    tx_drop,
                ) = domain.interfaceStats(dev)

                network_stats.append(
                    {
                        "device": dev,
                        "rx_bytes": rx_bytes,
                        "tx_bytes": tx_bytes,
                    }
                )

            except libvirt.libvirtError:
                continue

        return {
            "name": name,
            "status": "Running",
            "cpu": {
                "usage_percent": max(cpu_percent, 0.0),
                "vcpus": vcpus,
            },
            "memory": memory,
            "disks": disk_stats,
            "network": network_stats,
        }

    def get_vm_ip(self, name: str) -> dict:
        """
        Discover a running VM's IP address.

        Tries the QEMU guest agent first (most accurate), then
        falls back to the DHCP lease table for libvirt-managed
        networks.
        """

        domain = self.get_domain(name)

        if domain is None:
            raise RuntimeError(f"VM '{name}' not found")

        if not domain.isActive():
            return {"name": name, "ip_addresses": []}

        addresses = []

        sources = [
            libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT,
            libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE,
            libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_ARP,
        ]

        for source in sources:
            if addresses:
                break

            try:
                interfaces = domain.interfaceAddresses(source, 0)
            except libvirt.libvirtError:
                continue

            for iface_name, iface in (interfaces or {}).items():
                for addr in iface.get("addrs") or []:
                    if addr.get("type") == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                        addresses.append(addr["addr"])

        return {"name": name, "ip_addresses": addresses}

    # ------------------------------------------------------------
    # Console
    # ------------------------------------------------------------

    def get_console_info(self, name: str) -> dict:
        """
        Return the VNC connection details for a VM's graphical
        console, used by the websocket console proxy.
        """

        domain = self.get_domain(name)

        if domain is None:
            raise RuntimeError(f"VM '{name}' not found")

        if not domain.isActive():
            raise RuntimeError(f"VM '{name}' is not running")

        import xml.etree.ElementTree as ET

        root = ET.fromstring(domain.XMLDesc(0))
        graphics = root.find("./devices/graphics[@type='vnc']")

        if graphics is None:
            raise RuntimeError(
                f"VM '{name}' has no VNC console configured"
            )

        port = graphics.get("port")
        listen = graphics.get("listen", "127.0.0.1")

        if port is None or port == "-1":
            raise RuntimeError(
                f"VM '{name}' console port is not yet allocated "
                "(VM may still be starting)"
            )

        return {"host": listen, "port": int(port)}


libvirt_service = LibvirtService()
