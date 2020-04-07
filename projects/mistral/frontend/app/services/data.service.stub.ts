import {Observable } from 'rxjs/Rx';
import {HttpClient} from '@angular/common/http';

import {ApiService} from '@rapydo/services/api';
import {DataService, StorageUsage} from "./data.service";
import {MockDerivedVariables, MockStorageUsageResponse} from "./data.mock";

export class DataServiceStub extends DataService {
    constructor(){
        super({} as ApiService, {} as HttpClient)
    }

    getStorageUsage(): Observable<StorageUsage> {
        return Observable.of(MockStorageUsageResponse);
    }

    getDerivedVariables(): Observable<any> {
        return Observable.of(MockDerivedVariables);
    }
}
