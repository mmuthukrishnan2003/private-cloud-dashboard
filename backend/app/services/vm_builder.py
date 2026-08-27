import uuid
import xml.etree.ElementTree as ET


def build_domain_xml(
    name: str,
    vcpus: int,
    ram_mb: int,
    disk_path: str,
    network: str,
    iso_path: str | None = None,
    disk_bus: str = "virtio",
    disk_target: str = "vda",
) -> str:
    """
    Build a libvirt domain XML definition for a new VM.

    This mirrors what `virt-install` would generate, but is built
    directly so the dashboard controls every field explicitly
    (no shell interpolation of user input).
    """

    domain = ET.Element("domain", type="kvm")

    ET.SubElement(domain, "name").text = name
    ET.SubElement(domain, "uuid").text = str(uuid.uuid4())

    memory = ET.SubElement(domain, "memory", unit="MiB")
    memory.text = str(ram_mb)

    current_memory = ET.SubElement(domain, "currentMemory", unit="MiB")
    current_memory.text = str(ram_mb)

    vcpu_el = ET.SubElement(domain, "vcpu", placement="static")
    vcpu_el.text = str(vcpus)

    os_el = ET.SubElement(domain, "os")
    ET.SubElement(os_el, "type", arch="x86_64", machine="q35").text = "hvm"

    if iso_path:
        ET.SubElement(os_el, "boot", dev="cdrom")

    ET.SubElement(os_el, "boot", dev="hd")

    features = ET.SubElement(domain, "features")
    ET.SubElement(features, "acpi")
    ET.SubElement(features, "apic")

    cpu_el = ET.SubElement(domain, "cpu", mode="host-passthrough")

    ET.SubElement(domain, "on_poweroff").text = "destroy"
    ET.SubElement(domain, "on_reboot").text = "restart"
    ET.SubElement(domain, "on_crash").text = "restart"

    devices = ET.SubElement(domain, "devices")

    ET.SubElement(devices, "emulator").text = "/usr/bin/qemu-system-x86_64"

    # ------------------------------------------------------------
    # Primary disk (created ahead of time as a qcow2 volume)
    # ------------------------------------------------------------

    disk = ET.SubElement(devices, "disk", type="file", device="disk")
    ET.SubElement(disk, "driver", name="qemu", type="qcow2")
    ET.SubElement(disk, "source", file=disk_path)
    ET.SubElement(
        disk, "target", dev=disk_target, bus=disk_bus
    )

    # ------------------------------------------------------------
    # Optional install ISO
    # ------------------------------------------------------------

    if iso_path:
        cdrom = ET.SubElement(devices, "disk", type="file", device="cdrom")
        ET.SubElement(cdrom, "driver", name="qemu", type="raw")
        ET.SubElement(cdrom, "source", file=iso_path)
        ET.SubElement(cdrom, "target", dev="sda", bus="sata")
        ET.SubElement(cdrom, "readonly")

    # ------------------------------------------------------------
    # Network interface
    #
    # `network` may be either the name of a libvirt virtual network
    # (e.g. "default") or a host bridge device (e.g. "br0"). We try
    # the bridge form first when it looks like one, otherwise a
    # libvirt network.
    # ------------------------------------------------------------

    interface = ET.SubElement(devices, "interface", type="network")
    ET.SubElement(interface, "source", network=network)
    ET.SubElement(interface, "model", type="virtio")

    # ------------------------------------------------------------
    # Console / graphics for the web console feature
    # ------------------------------------------------------------

    ET.SubElement(
        devices,
        "graphics",
        type="vnc",
        port="-1",
        autoport="yes",
        listen="127.0.0.1",
    )

    video = ET.SubElement(devices, "video")
    ET.SubElement(video, "model", type="qxl")

    ET.SubElement(devices, "console", type="pty")

    channel = ET.SubElement(devices, "channel", type="unix")
    ET.SubElement(
        channel, "target", type="virtio", name="org.qemu.guest_agent.0"
    )

    return ET.tostring(domain, encoding="unicode")


def build_bridge_domain_xml(*args, **kwargs) -> str:
    """
    Variant of build_domain_xml() for hosts that use a plain host
    bridge (e.g. br0) instead of a libvirt-managed virtual network.

    Kept separate so callers can be explicit about which network
    type they resolved, rather than guessing inside the XML builder.
    """

    name = kwargs["name"]
    vcpus = kwargs["vcpus"]
    ram_mb = kwargs["ram_mb"]
    disk_path = kwargs["disk_path"]
    bridge = kwargs["bridge"]
    iso_path = kwargs.get("iso_path")
    disk_bus = kwargs.get("disk_bus", "virtio")
    disk_target = kwargs.get("disk_target", "vda")

    xml_str = build_domain_xml(
        name=name,
        vcpus=vcpus,
        ram_mb=ram_mb,
        disk_path=disk_path,
        network="__placeholder__",
        iso_path=iso_path,
        disk_bus=disk_bus,
        disk_target=disk_target,
    )

    root = ET.fromstring(xml_str)
    interface = root.find("./devices/interface")

    interface.set("type", "bridge")
    source = interface.find("source")
    del source.attrib["network"]
    source.set("bridge", bridge)

    return ET.tostring(root, encoding="unicode")
