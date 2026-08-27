export interface VM {
  id: string;
  name: string;
  status: string;
  uuid: string;
}

export interface CreateVMRequest {
  name: string;
  os: string;
  iso: string | null;
  vcpus: number;
  ram_gb: number;
  storage_pool: string;
  disk_gb: number;
  network: string;
}

export interface VMCpuStats {
  usage_percent: number;
  vcpus: number;
}

export interface VMMemoryStats {
  total_mb: number;
  used_mb: number | null;
}

export interface VMDiskStats {
  device: string;
  read_bytes: number;
  write_bytes: number;
}

export interface VMNetworkStats {
  device: string;
  rx_bytes: number;
  tx_bytes: number;
}

export interface VMStats {
  name: string;
  status: string;
  cpu: VMCpuStats | null;
  memory: VMMemoryStats | null;
  disks: VMDiskStats[];
  network: VMNetworkStats[];
}

export interface VMIpInfo {
  name: string;
  ip_addresses: string[];
}

export interface VMDisk {
  target: string;
  bus: string;
  path: string;
  format: string;
  size_gb: number | null;
  status: string;
}

export interface AddDiskRequest {
  storage_pool: string;
  size_gb: number;
}

export interface StoragePoolCapacity {
  pool: string;
  total_gb: number;
  used_gb: number;
  available_gb: number;
}

export interface ISOImage {
  name: string;
  path: string;
  size_gb: number;
}
