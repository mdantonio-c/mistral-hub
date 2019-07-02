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

  // TODO
  getDatasets() {
    return this.dataService.getDatsets();
  }

  getFormData(): FormData {
    // Return the entire Form Data
    return this.formData;
  }

}
