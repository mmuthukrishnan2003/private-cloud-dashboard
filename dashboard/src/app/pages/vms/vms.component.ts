import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-vms',
  templateUrl: './vms.component.html',
  styleUrls: ['./vms.component.css']
})
export class VmsComponent implements OnInit {

  // VM list received from the backend
  vms: any[] = [];

  constructor(private router: Router) {}

  ngOnInit(): void {
    // Temporary test data.
    // We will replace this with the FastAPI API shortly.
    this.vms = [];
  }

  /**
   * Navigate to Create VM page.
   */
  createVm(): void {
    this.router.navigate(['/create-vm']);
  }

  /**
   * Open VM details page.
   */
  openVm(vm: any): void {
    this.router.navigate(['/vms', vm.name]);
  }
}
