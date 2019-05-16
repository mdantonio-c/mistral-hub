import { Routes } from '@angular/router';

import { AuthGuard } from '/rapydo/src/app/app.auth.guard';

import { DataComponent } from './components/data'

export const appRoutes: Routes = [
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

