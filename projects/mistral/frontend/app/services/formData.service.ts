import {Injectable} from '@angular/core';

import {FormData, Dataset, Filters} from './formData.model';
import {WorkflowService} from './workflow.service';
import {STEPS} from './workflow.model';
import {DataService} from "./data.service";

@Injectable()
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

  setFilters(data: any) {
    // Update Filters only when the Filter Form had been validated successfully
    this.isFilterFormValid = true;
    this.formData.filters = data;
    // Validate Filter Step in Workflow
    this.workflowService.validateStep(STEPS.filter);
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
