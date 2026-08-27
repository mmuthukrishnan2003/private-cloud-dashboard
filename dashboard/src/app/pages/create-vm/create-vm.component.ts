import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';

interface IsoImage {
  name: string;
  path: string;
  size_gb?: number;
}

interface StoragePool {
  name: string;
  path?: string;
  type?: string;
}

interface StorageCapacity {
  total_gb: number;
  used_gb: number;
  available_gb: number;
}

interface Network {
  name: string;
  type?: string;
  bridge?: string;
}

@Component({
  selector: 'app-create-vm',
  templateUrl: './create-vm.component.html',
  styleUrls: ['./create-vm.component.css']
})
export class CreateVmComponent implements OnInit {

  // Host/server name displayed in the Create VM page
  hostName = 'KVM Host';

  // Available ISO images
  isos: IsoImage[] = [];

  // Available libvirt storage pools
  pools: StoragePool[] = [];

  // Storage capacity information
  capacity: StorageCapacity | null = null;

  // Available VM networks
  networks: Network[] = [];

  // VM creation form
  form: FormGroup;

  // UI state
  submitting = false;
  loading = true;
  errorMessage = '';

  /*
   * Change this if your FastAPI backend uses another URL.
   *
   * If Angular is served through Nginx and Nginx proxies /api
   * to FastAPI, keeping /api is recommended.
   */
  private apiUrl = '/api';

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private router: Router
  ) {
    this.form = this.fb.group({

      // VM name
      name: [
        '',
        [
          Validators.required,
          Validators.minLength(2),
          Validators.maxLength(64)
        ]
      ],

      // CPU cores
      vcpus: [
        2,
        [
          Validators.required,
          Validators.min(1),
          Validators.max(128)
        ]
      ],

      // RAM in MB
      memory_mb: [
        2048,
        [
          Validators.required,
          Validators.min(512),
          Validators.max(131072)
        ]
      ],

      // Disk size in GB
      disk_gb: [
        20,
        [
          Validators.required,
          Validators.min(1),
          Validators.max(10000)
        ]
      ],

      // Storage pool
      storage_pool: [
        'default',
        Validators.required
      ],

      // ISO image
      iso: [
        ''
      ],

      // Network
      network: [
        'default'
      ]
    });
  }

  ngOnInit(): void {
    this.loadHostInformation();
  }

  /**
   * Load information required by the Create VM page.
   *
   * These API calls are intentionally separated so that one
   * failed endpoint does not prevent the rest of the page
   * from loading.
   */
  loadHostInformation(): void {
    this.loading = true;

    // Host information
    this.http.get<any>(`${this.apiUrl}/host`)
      .subscribe({
        next: (response) => {
          this.hostName =
            response?.hostname ||
            response?.host_name ||
            response?.name ||
            'KVM Host';
        },
        error: () => {
          // Keep a safe fallback if the endpoint does not exist.
          this.hostName = 'KVM Host';
        }
      });

    // ISO images
    this.http.get<any>(`${this.apiUrl}/vms/isos`)
      .subscribe({
        next: (response) => {
          this.isos =
            response?.isos ||
            response ||
            [];
        },
        error: () => {
          this.isos = [];
        }
      });

    // Storage pools
    this.http.get<any>(`${this.apiUrl}/vms/storage-pools`)
      .subscribe({
        next: (response) => {
          this.pools =
            response?.pools ||
            response ||
            [];

          // Select the first available pool if the default
          // pool is not present.
          if (
            this.pools.length > 0 &&
            !this.pools.some(pool => pool.name === 'default')
          ) {
            this.form.patchValue({
              storage_pool: this.pools[0].name
            });
          }
        },
        error: () => {
          // Provide a fallback so the template can still render.
          this.pools = [
            {
              name: 'default',
              type: 'dir'
            }
          ];
        }
      });

    // Storage capacity
    this.http.get<any>(`${this.apiUrl}/vms/storage-capacity`)
      .subscribe({
        next: (response) => {
          this.capacity =
            response?.capacity ||
            response ||
            null;
        },
        error: () => {
          this.capacity = null;
        }
      });

    // Networks
    this.http.get<any>(`${this.apiUrl}/vms/networks`)
      .subscribe({
        next: (response) => {
          this.networks =
            response?.networks ||
            response ||
            [];
        },
        error: () => {
          // Default libvirt network fallback.
          this.networks = [
            {
              name: 'default',
              type: 'NAT',
              bridge: 'virbr0'
            }
          ];
        },
        complete: () => {
          this.loading = false;
        }
      });

    /*
     * In case the network request completes very quickly or
     * fails before the complete callback, remove the loading
     * state after the initialization work has started.
     */
    setTimeout(() => {
      this.loading = false;
    }, 500);
  }

  /**
   * Called when the Create VM form is submitted.
   */
  submit(): void {

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    // Check available storage before submitting.
    if (
      this.capacity &&
      this.form.value.disk_gb > this.capacity.available_gb
    ) {
      this.errorMessage =
        `Not enough storage. Only ${this.capacity.available_gb} GB is available.`;

      return;
    }

    this.submitting = true;
    this.errorMessage = '';

    const payload = {
      name: this.form.value.name,
      vcpus: Number(this.form.value.vcpus),
      memory_mb: Number(this.form.value.memory_mb),
      disk_gb: Number(this.form.value.disk_gb),
      storage_pool: this.form.value.storage_pool,
      iso: this.form.value.iso || null,
      network: this.form.value.network || 'default'
    };

    console.log('Creating VM:', payload);

    /*
     * Send the VM creation request to FastAPI.
     *
     * If your backend endpoint is different, change only
     * the URL below.
     */
    this.http.post<any>(
      `${this.apiUrl}/vms`,
      payload
    ).subscribe({
      next: () => {
        this.submitting = false;

        // Return to the VM list after successful creation.
        this.router.navigate(['/vms']);
      },

      error: (error) => {
        console.error('VM creation failed:', error);

        this.errorMessage =
          error?.error?.detail ||
          error?.error?.message ||
          'Failed to create VM. Please check the backend logs.';

        this.submitting = false;
      }
    });
  }

  /**
   * Cancel VM creation and return to the VM list.
   */
  cancel(): void {
    this.router.navigate(['/vms']);
  }

  /**
   * Convenient getter for form controls in the HTML.
   */
  get f() {
    return this.form.controls;
  }
}
