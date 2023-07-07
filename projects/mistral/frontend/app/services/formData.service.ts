import { Injectable } from "@angular/core";
import { Observable } from "rxjs";
import * as moment from "moment";

import { WorkflowService } from "@app/services/workflow.service";
import { STEPS } from "@app/services/workflow.model";
import {
  Filters,
  Dataset,
  SummaryStats,
  TaskSchedule,
  RefTime,
  FieldsSummary,
  RequestArgs,
} from "@app/types";
import { DataService } from "./data.service";

export class FormData {
  request_name: string = "";
  reftime: RefTime = this.defaultRefTime();
  datasets: Dataset[] = [];
  filters: Filters[] = [];
  postprocessors: any[] = [];
  schedule: TaskSchedule;
  output_format = "";
  only_reliable: boolean = false;
  push: boolean = false;
  opendata: boolean = false;

  clear() {
    this.request_name = "";
    this.datasets = [];
    this.filters = [];
    this.postprocessors = [];
    this.output_format = "";
    this.schedule = null;
    this.reftime = this.defaultRefTime();
    this.only_reliable = false;
    this.push = false;
    this.opendata = false;
  }

  setSchedule(schedule: TaskSchedule) {
    this.schedule = schedule;
  }

  defaultName() {
    this.request_name = this.datasets.join(" ").trim();
  }

  defaultRefTime(): RefTime {
    return {
      from: moment
        .utc()
        .set({ hour: 0, minute: 0, second: 0, millisecond: 0 })
        .subtract(1, "days")
        .toDate(),
      to: moment.utc().toDate(),
    };
  }
}

@Injectable({
  providedIn: "root",
})
export class FormDataService {
  private formData: FormData = new FormData();
  private isDatasetFormValid: boolean = false;
  private isFilterFormValid: boolean = false;
  private isPostprocessFormValid: boolean = false;

  constructor(
    private workflowService: WorkflowService,
    private dataService: DataService,
  ) {}

  getDatasets(): Observable<Dataset[]> {
    return this.dataService.getDatasets(true);
  }

  setDatasets(data: Dataset[]) {
    // Update Datasets only when the Dataset Form had been validated successfully
    this.isDatasetFormValid = true;
    this.formData.datasets = data;
    // Validate Dataset Step in Workflow
    this.workflowService.validateStep(STEPS.dataset);
  }

  isDatasetSelected(datasetId: string): boolean {
    return this.formData.datasets.some((x) => x.id === datasetId);
  }

  /**
   * Retrieve the filters available for the selected datasets.
   * Optionally the dataset coverage can be restricted with respect to the reference time.
   * If reftime is omitted the whole historical dataset will be considered.
   */
  getFilters(filters?: Filters[]): Observable<FieldsSummary> {
    let q = null;
    if (filters) {
      q = filters.map((f) => f.query).join(";");
    }
    let reftime = this.parseRefTime();
    if (reftime) {
      // prepend the reftime
      q = q !== "" ? [reftime, q].join(";") : reftime;
    }
    console.log(`query for summary: ${q}`);
    return this.dataService.getSummary(
      this.formData.datasets.map((x) => x.id),
      false,
      q,
    );
  }

  /**
   * Return arkimet query for reftime or null.
   */
  private parseRefTime(): string {
    let query = null;
    if (this.formData.reftime) {
      let arr = [];
      if (this.formData.reftime.from) {
        arr.push(
          `>=${moment
            .utc(this.formData.reftime.from)
            .format("YYYY-MM-DD HH:mm")}`,
        );
      }
      if (this.formData.reftime.to) {
        arr.push(
          `<=${moment
            .utc(this.formData.reftime.to)
            .format("YYYY-MM-DD HH:mm")}`,
        );
      }
      query = `reftime: ${arr.join(",")}`;
      console.log(query);
    }
    return query;
  }

  getReftime() {
    return this.formData.reftime;
  }

  getDefaultRefTime() {
    return this.formData.defaultRefTime();
  }

  setReftime(value?: RefTime) {
    if (value === undefined) {
      // default reftime
      this.formData.reftime = this.formData.defaultRefTime();
    } else {
      this.formData.reftime = value;
    }
  }

  getSummaryStats(): Observable<SummaryStats> {
    let q = this.formData.filters.map((f) => f.query).join(";");
    let reftime = this.parseRefTime();
    if (reftime) {
      // prepend the reftime
      q = q !== "" ? [reftime, q].join(";") : reftime;
    }
    console.log(`query for summary stats ${q}`);
    return this.dataService.getSummary(
      this.formData.datasets.map((x) => x.id),
      true,
      q,
    );
  }

  setFilters(data: Filters[]) {
    // Update Filters only when the Filter Form had been validated successfully
    this.isFilterFormValid = true;
    this.formData.filters = data;
    // Validate Filter Step in Workflow
    this.workflowService.validateStep(STEPS.filter);
  }

  /**
   * Check if a filter returned from api/fields is currently selected in the form data.
   * @param filter the filter  model return as response containing the desc field
   * @param type filter type (e.g. level, area, product, etc.)
   */
  isFilterSelected(filter, type) {
    for (let f of this.formData.filters) {
      if (
        f.name === type &&
        f.values.filter((i) => i.desc === filter.desc).length
      ) {
        return true;
      }
    }
    return false;
  }

  setPostProcessor(data: any[]) {
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
    this.isDatasetFormValid =
      this.isFilterFormValid =
      this.isPostprocessFormValid =
        false;
    return this.formData;
  }

  isFormValid() {
    // Return true if all forms had been validated successfully; otherwise, return false
    return (
      this.isDatasetFormValid &&
      this.isFilterFormValid &&
      this.isPostprocessFormValid
    );
  }

  setOutputFormat(data: any) {
    this.formData.output_format = data;
  }

  setQCFilter(data: boolean) {
    this.formData.only_reliable = data;
  }
}
