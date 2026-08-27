# Next Implementation Stage — What Was Added

This extends the original starter dashboard with the production VM workflow
outlined in the original spec (section 30):

## Backend (`backend/app/`)

- **`services/vm_builder.py`** *(new)* — builds libvirt domain XML from
  scratch (no `virt-install` shell-out), supporting both libvirt-managed
  networks and plain host bridges (`br0`).
- **`services/disk_service.py`** *(new)* — qcow2 disk creation via
  `qemu-img`, storage pool capacity lookups, and all validation from
  section 27 (pool exists, size available, server-generated path, free
  target device name).
- **`services/iso_service.py`** *(new)* — lists `.iso` volumes from a
  libvirt storage pool named `isos`, used by the OS/ISO selector.
- **`services/libvirt_service.py`** *(extended)* — adds `create_vm()`,
  `get_vm_stats()` (CPU/RAM/disk/network), `get_vm_ip()` (guest agent →
  DHCP lease → ARP fallback), and `get_console_info()` (VNC socket lookup).
- **`routers/vms.py`** *(extended)* — `POST /api/vms` (create), `GET
  /{name}/stats`, `GET /{name}/ip`, `GET /{name}/disks`, `POST
  /{name}/disks` (add disk), and a `WebSocket /{name}/console` route that
  bridges the browser to the VM's VNC socket for the web console.
- **`routers/storage.py`** *(extended)* — `GET /pool/{name}/capacity`
  (structured total/used/available) and `GET /isos`.

## Frontend (`dashboard/src/app/`)

- **`pages/overview/`** — the original dashboard content, now living at
  the `/` route (previously it was hardcoded into `app.component`).
- **`pages/create-vm/`** — the Create VM form from section 25, wired to
  load pools/networks/ISOs, show live pool capacity, and submit to
  `POST /api/vms`.
- **`pages/vms/vm-detail/`** — per-VM page with live stats, the disk
  table + Add Disk form from section 27, and an embedded console using
  [`@novnc/novnc`](https://github.com/novnc/noVNC) connected over the new
  console WebSocket.
- **`app.component`** is now a thin shell (topbar + `<router-outlet>`);
  routing lives in `app-routing.module.ts`, wired up in `app.module.ts`.

## Setup steps

1. Create a libvirt storage pool named `isos` (any type) and drop your
   Ubuntu ISO(s) into it — this is what populates the ISO dropdown.
2. `npm install @novnc/novnc` inside `dashboard/` for the console viewer.
3. Nginx (`nginx/dashboard.conf`) now forwards WebSocket upgrade headers
   on `/api/`, required for the console proxy — redeploy the config.
4. `qemu-img` must be on `PATH` on the host (it ships with `qemu-utils`,
   already implied by the `qemu-kvm` package installed in
   `scripts/install-host.sh`).

## Known caveats worth knowing about

- The console proxy is a raw TCP↔WebSocket byte pump — it doesn't
  authenticate the WebSocket connection beyond whatever auth you put in
  front of the dashboard itself. If the dashboard is ever exposed beyond
  a trusted network, put real auth in front of it before relying on this.
- `get_vm_ip()` can return an empty list for a while after boot — DHCP
  leases and guest-agent data aren't available until the guest OS has
  actually come up.
- IP/stat polling from the frontend is a simple 5s `setInterval`; for
  many concurrent dashboard users you'd want to move this to a shared
  WebSocket/SSE push from the backend instead of N pollers hitting
  libvirt independently.
