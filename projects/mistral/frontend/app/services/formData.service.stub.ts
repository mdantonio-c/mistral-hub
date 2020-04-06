import {Observable } from 'rxjs/Rx';

import {FormDataService} from "./formData.service";
import {WorkflowService} from "./workflow.service";
import {DataService, SummaryStats} from "./data.service";
import {MockDatasetsResponse, MockFiltersResponse, MockSummaryStatsResponse} from "./data.mock";

export class FormDataServiceStub extends FormDataService {
    constructor() {
        super({} as WorkflowService, {} as DataService);
    }

    getDatasets(): any {
        return Observable.of(MockDatasetsResponse.Response);
    }

    getFilters(): any {
        return Observable.of(MockFiltersResponse.Response);
    }

    getSummaryStats(): Observable<SummaryStats> {
        return Observable.of(MockSummaryStatsResponse.Response);
    }

}
