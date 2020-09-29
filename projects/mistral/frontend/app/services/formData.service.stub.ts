import { Observable, of } from "rxjs";
import { Injectable } from "@angular/core";

import { FormDataService } from "./formData.service";
import { WorkflowService } from "./workflow.service";
import { DataService } from "./data.service";
import { SummaryStats, Filters } from "@app/types";
import {
  MockDatasetsResponse,
  MockFiltersResponse,
  MockSummaryStatsResponse,
} from "./data.mock";

@Injectable()
export class FormDataServiceStub extends FormDataService {
  constructor() {
    super({} as WorkflowService, {} as DataService);
  }

  getDatasets(): any {
    return of(MockDatasetsResponse);
  }

  getFilters(filters?: Filters[]): any {
    return of(MockFiltersResponse);
  }

  getSummaryStats(): Observable<SummaryStats> {
    return of(MockSummaryStatsResponse);
  }
}
