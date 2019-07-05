import {Injectable} from '@angular/core';

import {FormData, Dataset, Filter} from './formData.model';
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
    // Update the Datasets only when the Dataset Form had been validated successfully
    this.isDatasetFormValid = true;
    this.formData.datasets = data;
    // Validate Dataset Step in Workflow
    this.workflowService.validateStep(STEPS.dataset);
  }

  isDatasetSelected(datasetId: string): boolean {
    return this.formData.datasets.some(x => x === datasetId);
  }

  getFormData(): FormData {
    // Return the entire Form Data
    return this.formData;
  }

  isFormValid() {
    // Return true if all forms had been validated successfully; otherwise, return false
    return this.isDatasetFormValid &&
      this.isFilterFormValid &&
      this.isPostprocessFormValid;
  }

}
