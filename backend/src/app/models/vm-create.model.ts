export interface CreateVMRequest {

  // -------------------------------------------------------
  // Basic VM information
  // -------------------------------------------------------

  name: string;

  os: string;

  iso?: string | null;


  // -------------------------------------------------------
  // CPU / RAM
  // -------------------------------------------------------

  vcpus: number;

  ram_gb: number;


  // -------------------------------------------------------
  // Storage
  // -------------------------------------------------------

  storage_pool: string;

  disk_gb: number;

  disk_format: string;

  disk_bus: string;

  existing_disk?: string | null;


  // -------------------------------------------------------
  // Network
  // -------------------------------------------------------

  network_type: string;

  bridge?: string | null;

  ip_mode: string;

  ip_address?: string | null;

  prefix?: number | null;

  gateway?: string | null;

  dns_servers?: string[];


  // -------------------------------------------------------
  // GPU
  // -------------------------------------------------------

  gpu_mode: string;

  gpu_pci_address?: string | null;


  // -------------------------------------------------------
  // Cloud-init
  // -------------------------------------------------------

  hostname?: string;

  username?: string;

  password?: string;
}
