import {Injectable} from '@angular/core';
import {ApiService} from '/rapydo/src/app/services/api';

export interface RapydoBundle<T> {
    Meta: RapydoMeta;
    Response: RapydoResponse<T>;
}

export interface RapydoMeta {
    data_type: string;
    elements: number;
    errors: number;
    status: number;
}

export interface RapydoResponse<T> {
    data: T;
    errors: any;
}

export interface SummaryStats {
    b?: string[];
    e?: string[];
    c: number;
    s: number;
}

/**
 * Expected filter names:
 *
 * area
 * level
 * origin
 * proddef
 * product
 * quantity
 * run
 * task
 * timerange
 */
export interface Filters {
    name: string;
    values: any[];
    query: string;
}

export class Dataset {
    id = '';
    description ? = '';
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
    extractData(datasets: string[], filters?: Filters[]) {
        let data = {datasets: datasets};
        if (filters && filters.length) {
            data['filters'] = {};
            filters.forEach(f => {
                let i = f.query.indexOf(':');
                let f_name = f.query.slice(0, i).trim();
                let f_query = f.query.slice(i + 1, f.query.length).trim();
                data['filters'][f_name] = f_query;
            });
        }
        return this.api.post('data', data, {"rawResponse": true});
    }

}
