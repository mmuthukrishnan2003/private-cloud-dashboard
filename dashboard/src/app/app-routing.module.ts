import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { OverviewComponent } from './pages/overview/overview.component';
import { CreateVmComponent } from './pages/create-vm/create-vm.component';
import { VmDetailComponent } from './pages/vms/vm-detail/vm-detail.component';

const routes: Routes = [
  { path: '', component: OverviewComponent, pathMatch: 'full' },
  { path: 'create-vm', component: CreateVmComponent },
  { path: 'vms/:name', component: VmDetailComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
