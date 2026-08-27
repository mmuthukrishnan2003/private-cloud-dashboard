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
   * Nginx proxies /api requests to FastAPI.
   *
   * Browser:
   *
   * http://172.16.0.111:8080/api/...
   *
   * Nginx:
   *
   * http://127.0.0.1:8000/api/...
   */

  private api = '/api';

  constructor(
    private http: HttpClient
  ) {}


  // ------------------------------------------------------
  // Host monitoring
  // ------------------------------------------------------

  getHostMetrics() {
    return this.http.get<any>(
      `${this.api}/host/metrics`
    );
  }


  // ------------------------------------------------------
  // Networks
  // ------------------------------------------------------

  getNetworks() {
    return this.http.get<any>(
      `${this.api}/host/networks`
    );
  }


  // ------------------------------------------------------
  // Storage pools
  // ------------------------------------------------------

  getStoragePools() {
    return this.http.get<{ pools: string[] }>(
      `${this.api}/storage/pools`
    );
  }

  getStoragePoolCapacity(poolName: string) {
    return this.http.get<StoragePoolCapacity>(
      `${this.api}/storage/pool/${poolName}/capacity`
    );
  }

  getISOs() {
    return this.http.get<{ isos: ISOImage[] }>(
      `${this.api}/storage/isos`
    );
  }


  // ------------------------------------------------------
  // VMs
  // ------------------------------------------------------

  getVMs() {
    return this.http.get<{ vms: VM[] }>(
      `${this.api}/vms`
    );
  }

  getVM(name: string) {
    return this.http.get<VM>(
      `${this.api}/vms/${name}`
    );
  }

  createVM(request: CreateVMRequest) {
    return this.http.post<{ success: boolean; vm: VM }>(
      `${this.api}/vms`,
      request
    );
  }

  getVMStats(name: string) {
    return this.http.get<VMStats>(
      `${this.api}/vms/${name}/stats`
    );
  }

  getVMIp(name: string) {
    return this.http.get<VMIpInfo>(
      `${this.api}/vms/${name}/ip`
    );
  }

  getVMDisks(name: string) {
    return this.http.get<{ disks: VMDisk[] }>(
      `${this.api}/vms/${name}/disks`
    );
  }

  addVMDisk(name: string, request: AddDiskRequest) {
    return this.http.post<{ success: boolean; disk: VMDisk }>(
      `${this.api}/vms/${name}/disks`,
      request
    );
  }

  startVM(name: string) {
    return this.http.post(
      `${this.api}/vms/${name}/start`,
      {}
    );
  }


  stopVM(name: string) {
    return this.http.post(
      `${this.api}/vms/${name}/stop`,
      {}
    );
  }


  restartVM(name: string) {
    return this.http.post(
      `${this.api}/vms/${name}/restart`,
      {}
    );
  }


  deleteVM(name: string) {
    return this.http.delete(
      `${this.api}/vms/${name}`
    );
  }


  // ------------------------------------------------------
  // Console
  // ------------------------------------------------------

  /**
   * Build the WebSocket URL for a VM's console proxy.
   * Consumed by noVNC's RFB client in the VM detail page.
   */
  getConsoleWebSocketUrl(name: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}${this.api}/vms/${name}/console`;
  }
}
