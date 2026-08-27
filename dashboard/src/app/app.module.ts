import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { RouterModule } from '@angular/router';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

import { CreateVmComponent } from './pages/create-vm/create-vm.component';
import { VmsComponent } from './pages/vms/vms.component';
import { VmDetailComponent } from './pages/vms/vm-detail/vm-detail.component';

@NgModule({
  declarations: [
    AppComponent,
    CreateVmComponent,
    VmsComponent,
    VmDetailComponent
  ],

  imports: [
    BrowserModule,
    AppRoutingModule,
    RouterModule,
    ReactiveFormsModule,
    HttpClientModule
  ],

  providers: [],

  bootstrap: [
    AppComponent
  ]
})
export class AppModule {}
