import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';

import { OverviewComponent } from './pages/overview/overview.component';
import { CreateVmComponent } from './pages/create-vm/create-vm.component';
import { VmDetailComponent } from './pages/vms/vm-detail/vm-detail.component';


@NgModule({
  declarations: [
    AppComponent,
    OverviewComponent,
    CreateVmComponent,
    VmDetailComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    AppRoutingModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {}
