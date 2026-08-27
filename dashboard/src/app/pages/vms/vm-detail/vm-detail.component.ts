import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

import { ApiService } from '../../../services/api.service';
import { VM, VMStats, VMDisk } from '../../../models/vm.model';

// @novnc/novnc must be added to package.json: npm install @novnc/novnc
import RFB from '@novnc/novnc/lib/rfb';


@Component({
  selector: 'app-vm-detail',
  templateUrl: './vm-detail.component.html',
  styleUrls: ['./vm-detail.component.css']
})
export class VmDetailComponent implements OnInit, OnDestroy {

  @ViewChild('consoleCanvas', { static: false }) consoleCanvas?: ElementRef<HTMLDivElement>;

  name = '';

  vm: VM | null = null;
  stats: VMStats | null = null;
  disks: VMDisk[] = [];
  ipAddresses: string[] = [];

  pools: string[] = [];

  addDiskForm: FormGroup;
  addingDisk = false;
  addDiskError: string | null = null;

  consoleConnected = false;
  consoleError: string | null = null;
  private rfb: any = null;

  private pollHandle: any = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: ApiService,
    private fb: FormBuilder
  ) {
    this.addDiskForm = this.fb.group({
      storage_pool: ['', Validators.required],
      size_gb: [50, [Validators.required, Validators.min(1), Validators.max(10000)]]
    });
  }

  ngOnInit(): void {
    this.name = this.route.snapshot.paramMap.get('name') || '';

    this.loadAll();

    this.api.getStoragePools().subscribe({
      next: response => {
        this.pools = response.pools;

        if (this.pools.length) {
          this.addDiskForm.patchValue({ storage_pool: this.pools[0] });
        }
      }
    });

    // Refresh stats, disks and IP every 5 seconds.
    this.pollHandle = setInterval(() => this.loadAll(), 5000);
  }

  ngOnDestroy(): void {
    if (this.pollHandle) {
      clearInterval(this.pollHandle);
    }

    this.disconnectConsole();
  }

  loadAll(): void {
    this.api.getVM(this.name).subscribe({
      next: vm => (this.vm = vm),
      error: () => {}
    });

    this.api.getVMStats(this.name).subscribe({
      next: stats => (this.stats = stats),
      error: () => (this.stats = null)
    });

    this.api.getVMDisks(this.name).subscribe({
      next: response => (this.disks = response.disks),
      error: () => {}
    });

    this.api.getVMIp(this.name).subscribe({
      next: info => (this.ipAddresses = info.ip_addresses),
      error: () => (this.ipAddresses = [])
    });
  }

  // ------------------------------------------------------
  // Power actions
  // ------------------------------------------------------

  startVM(): void {
    this.api.startVM(this.name).subscribe(() => this.loadAll());
  }

  stopVM(): void {
    this.api.stopVM(this.name).subscribe(() => this.loadAll());
  }

  restartVM(): void {
    this.api.restartVM(this.name).subscribe(() => this.loadAll());
  }

  deleteVM(): void {
    if (!confirm(`Delete VM ${this.name}?`)) {
      return;
    }

    this.api.deleteVM(this.name).subscribe(() => {
      this.router.navigate(['/']);
    });
  }

  // ------------------------------------------------------
  // Storage
  // ------------------------------------------------------

  addDisk(): void {
    if (this.addDiskForm.invalid) {
      this.addDiskForm.markAllAsTouched();
      return;
    }

    this.addingDisk = true;
    this.addDiskError = null;

    this.api.addVMDisk(this.name, this.addDiskForm.value).subscribe({
      next: () => {
        this.addingDisk = false;
        this.loadAll();
      },
      error: error => {
        this.addingDisk = false;
        this.addDiskError = error?.error?.detail || 'Failed to add disk.';
      }
    });
  }

  // ------------------------------------------------------
  // Console
  // ------------------------------------------------------

  connectConsole(): void {
    if (!this.consoleCanvas) {
      return;
    }

    this.consoleError = null;

    const url = this.api.getConsoleWebSocketUrl(this.name);

    try {
      this.rfb = new RFB(this.consoleCanvas.nativeElement, url);

      this.rfb.addEventListener('connect', () => {
        this.consoleConnected = true;
      });

      this.rfb.addEventListener('disconnect', () => {
        this.consoleConnected = false;
      });
    } catch (err: any) {
      this.consoleError = err?.message || 'Failed to open console.';
    }
  }

  disconnectConsole(): void {
    if (this.rfb) {
      this.rfb.disconnect();
      this.rfb = null;
    }

    this.consoleConnected = false;
  }
}
