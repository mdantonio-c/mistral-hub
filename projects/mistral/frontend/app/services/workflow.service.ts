import {Injectable} from '@angular/core';

import {STEPS} from './workflow.model';

@Injectable()
export class WorkflowService {
    private workflow = [
        {step: STEPS.dataset, valid: false},
        {step: STEPS.filter, valid: false},
        {step: STEPS.postprocess, valid: false},
        {step: STEPS.submit, valid: false}
    ];

    validateStep(step: string) {
        // If the state is found, set the valid field to true
        let found = false;
        for (let i = 0; i < this.workflow.length && !found; i++) {
            if (this.workflow[i].step === step) {
                found = this.workflow[i].valid = true;
            }
        }
    }

    resetSteps() {
        // Reset all the steps in the Workflow to be invalid
        this.workflow.forEach(element => {
            element.valid = false;
        });
    }

    getFirstInvalidStep(step: string): string {
        // If all the previous steps are validated, return blank
        // Otherwise, return the first invalid step
        let found = false;
        let valid = true;
        let redirectToStep = '';
        for (let i = 0; i < this.workflow.length && !found && valid; i++) {
            let item = this.workflow[i];
            if (item.step === step) {
                found = true;
                redirectToStep = '';
            } else {
                valid = item.valid;
                redirectToStep = item.step;
            }
        }
        return redirectToStep;
    }
}
