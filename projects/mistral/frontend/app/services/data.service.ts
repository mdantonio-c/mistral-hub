import {Injectable} from '@angular/core';
import {ApiService} from '/rapydo/src/app/services/api';
import {Observable} from 'rxjs';

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

export interface TaskSchedule {
    date: string;
    time: string;
    repeat: string;
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
    extractData(name: string, datasets: string[], filters?: Filters[]) {
        let data = {
            name: name,
            datasets: datasets
        };
        if (filters && filters.length) {
            data['filters'] = {};
            filters.forEach(f => {
                data['filters'][f.name] = f.values.map(x => {
                    delete x['t'];
                    return x;
                });
            });
        }
        return this.api.post('data', data, {"rawResponse": true});
    }

    /**
     * Download data for a completed extraction request
     * @param filename
     */
    downloadData(filename): Observable<any> {
        let options = {
			"rawResponse": true,
			"conf": {
				'responseType': 'blob',
				"observe": "response",
			}
		};
        return this.api.get('data', filename, {}, options);
    }

}
