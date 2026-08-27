import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { VmsComponent } from './pages/vms/vms.component';
import { CreateVmComponent } from './pages/create-vm/create-vm.component';
import { VmDetailComponent } from './pages/vms/vm-detail/vm-detail.component';

const routes: Routes = [

  // VM list
  {
    path: 'vms',
    component: VmsComponent
  },

  // Create VM
  {
    path: 'create-vm',
    component: CreateVmComponent
  },

  // VM details
  {
    path: 'vms/:name',
    component: VmDetailComponent
  },

  // Default page
  {
    path: '',
    redirectTo: 'vms',
    pathMatch: 'full'
  },

  // Invalid routes
  {
    path: '**',
    redirectTo: 'vms'
  }
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes)
  ],
  exports: [
    RouterModule
  ]
})
export class AppRoutingModule {}
