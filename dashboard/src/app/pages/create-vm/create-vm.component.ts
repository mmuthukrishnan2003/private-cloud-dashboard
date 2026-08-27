import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { ApiService } from '../../services/api.service';
import { StoragePoolCapacity, ISOImage } from '../../models/vm.model';


@Component({
  selector: 'app-create-vm',
  templateUrl: './create-vm.component.html',
  styleUrls: ['./create-vm.component.css']
})
export class CreateVmComponent implements OnInit {

  form: FormGroup;

  pools: string[] = [];
  networks: string[] = [];
  isos: ISOImage[] = [];

  capacity: StoragePoolCapacity | null = null;

  submitting = false;
  errorMessage: string | null = null;

  constructor(
    private fb: FormBuilder,
    private api: ApiService,
    private router: Router
  ) {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.pattern(/^[a-zA-Z0-9][a-zA-Z0-9_.\-]*$/)]],
      os: ['Ubuntu 22.04 LTS'],
      iso: [null],
      vcpus: [4, [Validators.required, Validators.min(1), Validators.max(128)]],
      ram_gb: [8, [Validators.required, Validators.min(1), Validators.max(1024)]],
      storage_pool: ['', Validators.required],
      disk_gb: [100, [Validators.required, Validators.min(10), Validators.max(10000)]],
      network: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    this.loadPools();
    this.loadNetworks();
    this.loadIsos();

    this.form.get('storage_pool')!.valueChanges.subscribe(pool => {
      if (pool) {
        this.loadCapacity(pool);
      }
    });
  }

  loadPools(): void {
    this.api.getStoragePools().subscribe({
      next: response => {
        this.pools = response.pools;

        if (this.pools.length && !this.form.value.storage_pool) {
          this.form.patchValue({ storage_pool: this.pools[0] });
        }
      },
      error: () => {
        this.pools = [];
      }
    });
  }

  loadNetworks(): void {
    this.api.getNetworks().subscribe({
      next: response => {
        this.networks = response.networks;

        if (this.networks.length && !this.form.value.network) {
          this.form.patchValue({ network: this.networks[0] });
        }
      },
      error: () => {
        this.networks = [];
      }
    });
  }

  loadIsos(): void {
    this.api.getISOs().subscribe({
      next: response => {
        this.isos = response.isos;
      },
      error: () => {
        this.isos = [];
      }
    });
  }

  loadCapacity(pool: string): void {
    this.api.getStoragePoolCapacity(pool).subscribe({
      next: capacity => {
        this.capacity = capacity;
      },
      error: () => {
        this.capacity = null;
      }
    });
  }

  cancel(): void {
    this.router.navigate(['/']);
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting = true;
    this.errorMessage = null;

    this.api.createVM(this.form.value).subscribe({
      next: response => {
        this.submitting = false;
        this.router.navigate(['/vms', response.vm.name]);
      },
      error: error => {
        this.submitting = false;
        this.errorMessage = error?.error?.detail || 'Failed to create VM.';
      }
    });
  }
}
