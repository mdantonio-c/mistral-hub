import {NgModule, ModuleWithProviders} from '@angular/core';
import {NgbTimeAdapter} from '@ng-bootstrap/ng-bootstrap';
import {RouterModule, Routes} from '@angular/router';
import {DatePipe} from '@angular/common';

import {RapydoModule} from '/rapydo/src/app/rapydo.module';
import {AuthGuard} from '/rapydo/src/app/app.auth.guard';

import {HomeComponent} from './custom.home'
import {DataComponent} from './components/data/data.component';
import {RequestsComponent} from "./components/requests/requests.component";
import {SchedulesComponent} from "./components/schedules/schedules.component";
import {DashboardComponent} from "./components/dashboard/dashboard.component";
import {StorageUsageComponent} from "./components/dashboard/storage-usage/storage-usage.component";
import {NgbTimeStringAdapter} from './adapters/timepicker-adapter';

/* Multi-Step Wizard Components */
import {MultiStepWizardComponent} from './components/multi-step-wizard/multi-step-wizard.component';
import {NavbarComponent} from './components/multi-step-wizard/navbar/navbar.component';
import {StepDatasetsComponent} from './components/multi-step-wizard/step-datasets/step-datasets.component'
import {StepFiltersComponent} from './components/multi-step-wizard/step-filters/step-filters.component';
import {StepPostprocessComponent} from "./components/multi-step-wizard/step-postprocess/step-postprocess.component";
import {StepSubmitComponent} from "./components/multi-step-wizard/step-submit/step-submit.component";

import {FormatDatePipe} from './pipes/format-date.pipe';
import {WorkflowGuard} from "./services/workflow-guard.service";

const appRoutes: Routes = [
    {
        path: 'app/data',
        component: DataComponent, canActivate: [AuthGuard], runGuardsAndResolvers: 'always',
        children: [
            {path: '', redirectTo: '/app/data/(step:datasets)', pathMatch: 'full'},
            {path: 'datasets', component: StepDatasetsComponent, outlet: 'step'},
            {path: 'filters', component: StepFiltersComponent, outlet: 'step', canActivate: [WorkflowGuard]},
            {path: 'postprocess', component: StepPostprocessComponent, outlet: 'step', canActivate: [WorkflowGuard]},
            {path: 'submit', component: StepSubmitComponent, outlet: 'step', canActivate: [WorkflowGuard]}
        ]
    },
    {path: 'app/requests', component: DashboardComponent, canActivate: [AuthGuard]},
    {path: 'app', redirectTo: '/app/data/(step:datasets)', pathMatch: 'full'},
    {path: '', redirectTo: '/app/data/(step:datasets)', pathMatch: 'full'},
];

@NgModule({
    imports: [
        RapydoModule,
        RouterModule.forChild(appRoutes)
    ],
    declarations: [
        HomeComponent,
        DataComponent,
        MultiStepWizardComponent,
        NavbarComponent,
        StepDatasetsComponent,
        StepFiltersComponent,
        StepPostprocessComponent,
        StepSubmitComponent,
        DashboardComponent,
        StorageUsageComponent,
        RequestsComponent,
        SchedulesComponent,
        FormatDatePipe
    ],
    providers: [
        DatePipe, {provide: NgbTimeAdapter, useClass: NgbTimeStringAdapter}],
    exports: [
        RouterModule
    ]
})

export class CustomModule {
} 
