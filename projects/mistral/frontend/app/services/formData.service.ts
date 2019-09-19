import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';

import {WorkflowService} from './workflow.service';
import {STEPS} from './workflow.model';
import {DataService, Filters, RapydoResponse, SummaryStats, TaskSchedule} from "./data.service";

export class FormData {
    name: string = '';
    datasets: string[] = [];
    filters: Filters[] = [];
    postprocessors: any[] = [];
    schedule: TaskSchedule;

    clear() {
        this.name = '';
        this.datasets = [];
        this.filters = [];
        this.postprocessors = [];
        this.schedule = null;
    }

    setSchedule(schedule: TaskSchedule) {
        this.schedule = schedule;
    }

    defaultName() {
        this.name = this.datasets.join(' ').trim();
    }
}

export const additionalVariables = [
    {code: 'B12194', desc: 'Air density'},
    {code: 'B13003', desc: 'Relative humidity'},
    {code: 'B11001', desc: 'Wind direction'},
    {code: 'B11002', desc: 'Wind speed'},
];

@Injectable({
  providedIn: 'root'
})
export class FormDataService {

    private formData: FormData = new FormData();
    private isDatasetFormValid: boolean = false;
    private isFilterFormValid: boolean = false;
    private isPostprocessFormValid: boolean = false;

    constructor(private workflowService: WorkflowService, private dataService: DataService) {
    }

    getDatasets() {
        return this.dataService.getDatsets();
    }

    setDatasets(data: string[]) {
        // Update Datasets only when the Dataset Form had been validated successfully
        this.isDatasetFormValid = true;
        this.formData.datasets = data;
        // Validate Dataset Step in Workflow
        this.workflowService.validateStep(STEPS.dataset);
    }

    isDatasetSelected(datasetId: string): boolean {
        return this.formData.datasets.some(x => x === datasetId);
    }

    getFilters() {
        return this.dataService.getSummary(this.formData.datasets);
    }

    getSummaryStats(): Observable<RapydoResponse<SummaryStats>> {
        let q = this.formData.filters.map(filter => filter.query).join(';');
        return this.dataService.getSummary(
            this.formData.datasets, q, true);
    }

    setFilters(data: any) {
        // Update Filters only when the Filter Form had been validated successfully
        this.isFilterFormValid = true;
        this.formData.filters = data;
        // Validate Filter Step in Workflow
        this.workflowService.validateStep(STEPS.filter);
    }

    isFilterSelected(filter) {
        for (let f of this.formData.filters) {
            if (f.name === filter.t &&
                f.values.filter(i => i.desc === filter.desc).length) {
                return true;
            }
        }
        return false;
    }

    setPostProcessor(data: any) {
        // Update Postprocess only when the Postprocess Form had been validated successfully
        this.isPostprocessFormValid = true;
        this.formData.postprocessors = data;
        // Validate Filter Step in Workflow
        this.workflowService.validateStep(STEPS.postprocess);
    }

    getFormData(): FormData {
        // Return the entire Form Data
        return this.formData;
    }

    resetFormData(): FormData {
        // Reset the workflow
        this.workflowService.resetSteps();
        // Return the form data after all this.* members had been reset
        this.formData.clear();
        this.isDatasetFormValid = this.isFilterFormValid = this.isPostprocessFormValid = false;
        return this.formData;
    }

    isFormValid() {
        // Return true if all forms had been validated successfully; otherwise, return false
        return this.isDatasetFormValid &&
            this.isFilterFormValid &&
            this.isPostprocessFormValid;
    }

}
