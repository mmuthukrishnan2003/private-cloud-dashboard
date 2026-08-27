import { Component } from '@angular/core';


@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  // The shell holds only the topbar and <router-outlet>.
  // Page-specific logic lives in pages/overview,
  // pages/create-vm and pages/vms/vm-detail.
}
