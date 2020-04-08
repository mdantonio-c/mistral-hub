import {Observable} from 'rxjs/Rx';
import {HttpClient} from '@angular/common/http';

import {ApiService} from '@rapydo/services/api';
import {DataService, RapydoResponse, StorageUsage} from "./data.service";
import {
    MockDerivedVariables,
    MockGribTemplateResponse,
    MockShapeTemplateResponse,
    MockStorageUsageResponse
} from "./data.mock";

export class DataServiceStub extends DataService {
    constructor() {
        super({} as ApiService, {} as HttpClient)
    }

    getStorageUsage(): Observable<RapydoResponse<StorageUsage>> {
        return Observable.of(MockStorageUsageResponse.Response);
    }

    getDerivedVariables(): Observable<any> {
        return Observable.of(MockDerivedVariables);
    }

    getTemplates(param): Observable<any> {
        if (param == 'grib') {
            return Observable.of(MockGribTemplateResponse.Response);
        } else if (param == 'shp') {
            return Observable.of(MockShapeTemplateResponse.Response);
        }
    }
}
