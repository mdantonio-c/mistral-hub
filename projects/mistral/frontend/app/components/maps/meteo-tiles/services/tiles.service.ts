import { Injectable } from '@angular/core';
import { ApiService } from '@rapydo/services/api';
import {Observable, forkJoin, of} from 'rxjs';

export interface RunAvailable {
    reftime: string;
    platform?: string;
}
@Injectable({
    providedIn: 'root'
})
export class TilesService {

    constructor(private api: ApiService) {
    }

    /**
     * Check and retrieve the last available run for a given resolution.
     * @param res resolution at 2.2. km or 5 km
     * @param run optionally a specific run between 00 and 12 cam be passed.
     */
    getLastRun(res: string, run?: string): Observable<RunAvailable> {
        let params = {
            'res': res
        }
        if (run) { params['run'] = run; }
        return this.api.get('tiles', '', params);
    }
}
