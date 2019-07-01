import { NgModule, ModuleWithProviders } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { RapydoModule } from '/rapydo/src/app/rapydo.module';
import { AuthGuard } from '/rapydo/src/app/app.auth.guard';

import { DataComponent } from './components/data'

const routes: Routes = [
  {
    path: '',
    redirectTo: '/app/data',
    pathMatch: 'full'
  },
  {
    path: 'app',
    redirectTo: '/app/data',
    pathMatch: 'full'
  },
  {
    path: 'app/data',
    component: DataComponent,
    canActivate: [AuthGuard],
    runGuardsAndResolvers: 'always',
  },
];

@NgModule({
	imports: [
		RapydoModule,
    RouterModule.forChild(routes),
	],
	declarations: [
		DataComponent
	],

	providers: [
	],

	exports: [
		RouterModule
	]

})
export class CustomModule {
} 