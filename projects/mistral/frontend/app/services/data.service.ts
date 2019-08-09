import {Injectable} from '@angular/core';
import {ApiService} from '/rapydo/src/app/services/api';

export interface SummaryStats {
    b?: string[],
    e?: string[],
    c: number,
    s: number
}

@Injectable({
  providedIn: 'root'
})
export class DataService {

    constructor(private api: ApiService) {
    }

    /**
     * Get all the available datasets.
     */
    getDatsets() {
        return this.api.get('datasets');
    }

    /**
     * Get summary fields for a give list of datasets.
     * @param datasets
     */
    getSummary(datasets: string[], query?: string, onlyStats?: boolean) {
        let params = {datasets: datasets.join()};
        if (query) {
            params['q'] = query;
        }
        if (onlyStats) {
            params['onlySummaryStats'] = true;
        }
        return this.api.get('fields', '', params);
    }

    /**
     * Request for data extraction.
     */
    extractData(data: any) {
        return this.api.post('data', data, {"rawResponse": true});
    }

}
