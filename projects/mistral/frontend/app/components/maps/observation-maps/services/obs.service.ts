import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable, forkJoin, of} from 'rxjs';
import 'rxjs/add/operator/map';
import 'rxjs/add/operator/share';
import {ApiService} from '@rapydo/services/api';
import {FIELDS_SUMMARY} from "./data";

export interface ObsFilter {
    product: string;
    reftime: Date;
    network?: string;
    timerange?: string;
    level?: string;
    bbox?: BoundingBox;
    onlyStations?: boolean;
}
export interface Network {
    id: number;
    memo: string;
    desc?: string;
}
export interface Product {
    code: string;
    desc?: string;
}
export interface BoundingBox {
    latMin: number;
    lonMin: number;
    latMax: number;
    lonMax: number;
}

export interface FieldsSummary {
    items: Items;
}

export interface Items {
    level?: any[];
    network?: any[];
    product?: any[];
    timerange?: any[];
}

@Injectable({
    providedIn: 'root'
})
export class ObsService {

    constructor(private api: ApiService) {
    }

    getFields(): Observable<FieldsSummary> {
       //return this.api.get('fields', '', {type: 'OBS'});
        return of(FIELDS_SUMMARY);
    }

    getObservations(filter: ObsFilter) {
        return this.api.get('observations', '', filter);
    }

    getData(filter: ObsFilter) {
        let d = [
            `${filter.reftime.getFullYear()}`,
            `${filter.reftime.getMonth()+1}`.padStart(2, '0'),
            `${filter.reftime.getDate()}`.padStart(2, '0')
            ].join('-');
        let params = {
            q: `reftime: >=${d} 00:00,<=${d} 23:59;product:${filter.product}`
        }
        if (filter.onlyStations) {
            params['onlyStations'] = true
        }
        if (filter.timerange && filter.timerange !== '') {
            params['q'] += `;timerange:${filter.timerange}`;
        }
        if (filter.level && filter.level !== '') {
            params['q'] += `;level:${filter.level}`;
        }
        // ONLY network and boundingbox as distinct params
        if (filter.network && filter.network !== '') {
            params['networks'] = filter.network;
        }
        if (filter.bbox) {
            params['bounding-box'] = `latmin:${filter.bbox.latMin},lonmin:${filter.bbox.lonMin}` +
                `,latmax:${filter.bbox.latMax},lonmax:${filter.bbox.lonMax}`;
        }
        return this.api.get('observations', '', params);
    }
}
