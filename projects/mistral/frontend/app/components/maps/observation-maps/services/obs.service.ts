import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable, forkJoin, of} from 'rxjs';
import 'rxjs/add/operator/map';
import 'rxjs/add/operator/share';
import {ApiService} from '@rapydo/services/api';

export interface ObsFilter {
    product: string,
}

@Injectable({
    providedIn: 'root'
})
export class ObsService {

    constructor(private api: ApiService) {
    }

    getObservations(filter: ObsFilter) {
        return this.api.get('observations', '', filter);
    }
}
