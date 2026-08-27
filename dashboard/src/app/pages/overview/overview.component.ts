import {
  Component,
  OnInit,
  OnDestroy
} from '@angular/core';

import { Router } from '@angular/router';

import { ApiService } from '../../services/api.service';


@Component({
  selector: 'app-overview',
  templateUrl: './overview.component.html',
  styleUrls: ['./overview.component.css']
})
export class OverviewComponent implements OnInit, OnDestroy {

  host: any = null;

  vms: any[] = [];

  private pollHandle: any = null;

  constructor(
    private api: ApiService,
    private router: Router
  ) {}


  ngOnInit(): void {

    this.loadHost();

    this.loadVMs();

    /*
     * Refresh monitoring every 5 seconds.
     */

    this.pollHandle = setInterval(() => {
      this.loadHost();
      this.loadVMs();
    }, 5000);
  }

  ngOnDestroy(): void {
    if (this.pollHandle) {
      clearInterval(this.pollHandle);
    }
  }


  loadHost(): void {

    this.api.getHostMetrics()
      .subscribe({
        next: data => {
          this.host = data;
        },

        error: error => {
          console.error(
            'Host monitoring error:',
            error
          );
        }
      });
  }


  loadVMs(): void {

    this.api.getVMs()
      .subscribe({
        next: response => {
          this.vms = response.vms;
        },

        error: error => {
          console.error(
            'VM monitoring error:',
            error
          );
        }
      });
  }


  openVM(vm: any): void {
    this.router.navigate(['/vms', vm.name]);
  }


  goToCreateVM(): void {
    this.router.navigate(['/create-vm']);
  }


  startVM(vm: any, event: Event): void {
    event.stopPropagation();

    this.api.startVM(vm.name)
      .subscribe(() => {
        this.loadVMs();
      });
  }


  stopVM(vm: any, event: Event): void {
    event.stopPropagation();

    this.api.stopVM(vm.name)
      .subscribe(() => {
        this.loadVMs();
      });
  }


  restartVM(vm: any, event: Event): void {
    event.stopPropagation();

    this.api.restartVM(vm.name)
      .subscribe(() => {
        this.loadVMs();
      });
  }


  deleteVM(vm: any, event: Event): void {
    event.stopPropagation();

    const confirmed = confirm(
      `Delete VM ${vm.name}?`
    );

    if (!confirmed) {
      return;
    }

    this.api.deleteVM(vm.name)
      .subscribe(() => {
        this.loadVMs();
      });
  }
}
