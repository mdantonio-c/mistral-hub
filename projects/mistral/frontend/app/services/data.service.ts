import {Injectable} from '@angular/core';
import {ApiService} from '/rapydo/src/app/services/api';

@Injectable()
export class DataService {
    // private _datasets: any[] = [];

    constructor(private api: ApiService) { }

    /**
     * Get all the available datasets.
     */
    getDatsets() {
        return this.api.get('datasets');
    }

    /**
     * Request for data extraction.
     */
    extractData() {
        let body = {
            datasets: ["vlm5"],
            filters: {
                reftime: "2019-06-03",
                origin: "GRIB1,080",
                level: "GRIB1,1"
            }
        }
        return this.api.post('data', body, { "rawResponse": true });
    }

}
