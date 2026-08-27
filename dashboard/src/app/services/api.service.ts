import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import {
  VM,
  CreateVMRequest,
  VMStats,
  VMIpInfo,
  VMDisk,
  AddDiskRequest,
  StoragePoolCapacity,
  ISOImage
} from '../models/vm.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {

  /*
   * ------------------------------------------------------
   * API BASE URL
   * ------------------------------------------------------
   *
   * Angular browser:
   *
   *   http://172.16.0.111:8080/api/...
   *
   * Nginx:
   *
   *   /api -> http://127.0.0.1:8000/api/
   *
   * Therefore Angular only needs:
   *
   *   /api
   *
   * Do NOT use localhost:8000 here.
   */

  private api = '/api';

  constructor(
    private http: HttpClient
  ) {}


  // ======================================================
  // HOST MONITORING
  // ======================================================

  /*
   * Get complete host/server metrics.
   *
   * Expected FastAPI endpoint:
   *
   * GET /api/host/metrics
   */
  getHostMetrics() {
    return this.http.get<any>(
      `${this.api}/host/metrics`
    );
  }


  /*
   * Get basic host information.
   *
   * Expected FastAPI endpoint:
   *
   * GET /api/host
   */
  getHost() {
    return this.http.get<any>(
      `${this.api}/host`
    );
  }


  // ======================================================
  // NETWORK
  // ======================================================

  /*
   * Get configured/libvirt network bridges.
   *
   * Expected FastAPI endpoint:
   *
   * GET /api/network/bridges
   */
  getBridges() {
    return this.http.get<any>(
      `${this.api}/network/bridges`
    );
  }


  /*
   * Get host network interfaces.
   *
   * Expected FastAPI endpoint:
   *
   * GET /api/network/interfaces
   */
  getInterfaces() {
    return this.http.get<any>(
      `${this.api}/network/interfaces`
    );
  }


  /*
   * Get networks used by the virtualization host.
   *
   * Expected FastAPI endpoint:
   *
   * GET /api/host/networks
   */
  getNetworks() {
    return this.http.get<any>(
      `${this.api}/host/networks`
    );
  }


  // ======================================================
  // STORAGE POOLS
  // ======================================================

  /*
   * Get available libvirt storage pools.
   *
   * Example response:
   *
   * {
   *   pools: [
   *     "default",
   *     "vm-storage"
   *   ]
   * }
   */
  getStoragePools() {
    return this.http.get<{ pools: string[] }>(
      `${this.api}/storage/pools`
    );
  }


  /*
   * Get capacity information for a storage pool.
   *
   * Example:
   *
   * GET /api/storage/pool/default/capacity
   */
  getStoragePoolCapacity(poolName: string) {
    return this.http.get<StoragePoolCapacity>(
      `${this.api}/storage/pool/${encodeURIComponent(poolName)}/capacity`
    );
  }


  /*
   * Get ISO images available on the server.
   *
   * Expected response:
   *
   * {
   *   isos: ISOImage[]
   * }
   */
  getISOs() {
    return this.http.get<{ isos: ISOImage[] }>(
      `${this.api}/storage/isos`
    );
  }


  // ======================================================
  // UBUNTU ISO
  // ======================================================

  /*
   * Download an official Ubuntu Server ISO.
   *
   * Example:
   *
   * POST /api/storage/ubuntu/download/22.04
   *
   * The backend should download the ISO from the
   * official Ubuntu release server.
   */
  downloadUbuntu(version: string) {
    return this.http.post<any>(
      `${this.api}/storage/ubuntu/download/${encodeURIComponent(version)}`,
      {}
    );
  }


  // ======================================================
  // STORAGE FILE UPLOAD
  // ======================================================

  /*
   * Upload an ISO / virtual disk file from the local PC.
   *
   * Supported files can be handled by the FastAPI backend,
   * for example:
   *
   * - ISO
   * - QCOW2
   * - RAW
   * - IMG
   * - VHD
   * - VHDX
   * - VMDK
   *
   * The backend should validate the actual file type.
   */
  uploadStorageFile(file: File) {

    const formData = new FormData();

    formData.append(
      'file',
      file
    );

    return this.http.post<any>(
      `${this.api}/storage/upload`,
      formData
    );
  }


  // ======================================================
  // VIRTUAL MACHINES
  // ======================================================

  /*
   * Get all VMs.
   *
   * Expected response:
   *
   * {
   *   vms: VM[]
   * }
   */
  getVMs() {
    return this.http.get<{ vms: VM[] }>(
      `${this.api}/vms`
    );
  }


  /*
   * Get a single VM.
   */
  getVM(name: string) {
    return this.http.get<VM>(
      `${this.api}/vms/${encodeURIComponent(name)}`
    );
  }


  /*
   * Create a new VM.
   */
  createVM(request: CreateVMRequest) {
    return this.http.post<{
      success: boolean;
      vm: VM;
    }>(
      `${this.api}/vms`,
      request
    );
  }


  /*
   * Get VM CPU / RAM / network statistics.
   */
  getVMStats(name: string) {
    return this.http.get<VMStats>(
      `${this.api}/vms/${encodeURIComponent(name)}/stats`
    );
  }


  /*
   * Get VM IP address information.
   */
  getVMIp(name: string) {
    return this.http.get<VMIpInfo>(
      `${this.api}/vms/${encodeURIComponent(name)}/ip`
    );
  }


  // ======================================================
  // VM DISKS
  // ======================================================

  /*
   * Get all disks attached to a VM.
   *
   * Expected response:
   *
   * {
   *   disks: VMDisk[]
   * }
   */
  getVMDisks(name: string) {
    return this.http.get<{ disks: VMDisk[] }>(
      `${this.api}/vms/${encodeURIComponent(name)}/disks`
    );
  }


  /*
   * Add a new disk to an existing VM.
   */
  addVMDisk(
    name: string,
    request: AddDiskRequest
  ) {
    return this.http.post<{
      success: boolean;
      disk: VMDisk;
    }>(
      `${this.api}/vms/${encodeURIComponent(name)}/disks`,
      request
    );
  }


  // ======================================================
  // VM POWER CONTROL
  // ======================================================

  /*
   * Start VM.
   */
  startVM(name: string) {
    return this.http.post<any>(
      `${this.api}/vms/${encodeURIComponent(name)}/start`,
      {}
    );
  }


  /*
   * Stop VM.
   */
  stopVM(name: string) {
    return this.http.post<any>(
      `${this.api}/vms/${encodeURIComponent(name)}/stop`,
      {}
    );
  }


  /*
   * Restart VM.
   */
  restartVM(name: string) {
    return this.http.post<any>(
      `${this.api}/vms/${encodeURIComponent(name)}/restart`,
      {}
    );
  }


  /*
   * Delete VM.
   */
  deleteVM(name: string) {
    return this.http.delete<any>(
      `${this.api}/vms/${encodeURIComponent(name)}`
    );
  }


  // ======================================================
  // VM CONSOLE / NOVNC
  // ======================================================

  /*
   * Build the WebSocket URL used by noVNC.
   *
   * HTTP:
   *
   *   ws://172.16.0.111:8080/api/vms/ubuntu/console
   *
   * HTTPS:
   *
   *   wss://172.16.0.111:8080/api/vms/ubuntu/console
   *
   * Nginx proxies this WebSocket connection to FastAPI.
   */
  getConsoleWebSocketUrl(name: string): string {

    const protocol =
      window.location.protocol === 'https:'
        ? 'wss:'
        : 'ws:';

    return `${protocol}//${window.location.host}${this.api}/vms/${encodeURIComponent(name)}/console`;
  }

}
