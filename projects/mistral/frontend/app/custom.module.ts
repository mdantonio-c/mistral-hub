import {NgModule, ModuleWithProviders} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

import {RapydoModule} from '/rapydo/src/app/rapydo.module';
import {AuthGuard} from '/rapydo/src/app/app.auth.guard';

/* Multi-Step Wizard Components */
import {MultiStepWizardComponent} from './components/multi-step-wizard/multi-step-wizard.component';
import {NavbarComponent} from './components/multi-step-wizard/navbar/navbar.component';
import {StepDatasetsComponent} from './components/multi-step-wizard/step-datasets/step-datasets.component'
import {StepFiltersComponent} from './components/multi-step-wizard/step-filters/step-filters.component';
import {StepPostprocessComponent} from "./components/multi-step-wizard/step-postprocess/step-postprocess.component";
import {StepSubmitComponent} from "./components/multi-step-wizard/step-submit/step-submit.component";

/* Shared Service */
import {FormDataService} from './services/formData.service';
import {WorkflowService} from './services/workflow.service';
import {DataService} from "./services/data.service";

import {DataComponent} from './components/data'

const routes: Routes = [
    { path: 'datasets', component: StepDatasetsComponent, outlet: 'step' },
    { path: 'filters', component: StepFiltersComponent, outlet: 'step' },
    { path: 'postprocess', component: StepPostprocessComponent, outlet: 'step' },
    { path: 'submit', component: StepSubmitComponent, outlet: 'step' },
    { path: 'app/data', component: DataComponent, canActivate: [AuthGuard], runGuardsAndResolvers: 'always' },
    { path: 'app', redirectTo: '/app/data', pathMatch: 'full' },
    { path: '', redirectTo: '/app/data', pathMatch: 'full' },
];

@NgModule({
    imports: [
        RapydoModule,
        RouterModule.forChild(routes),
    ],
    declarations: [
        DataComponent,
        MultiStepWizardComponent,
        NavbarComponent,
        StepDatasetsComponent,
        StepFiltersComponent,
        StepPostprocessComponent,
        StepSubmitComponent
    ],

    providers: [{provide: FormDataService, useClass: FormDataService},
              {provide: WorkflowService, useClass: WorkflowService},
        {provide: DataService, useClass: DataService}],

    exports: [
        RouterModule
    ]
})

export class CustomModule {
} 
