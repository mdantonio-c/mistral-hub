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

export interface Station {
    ident?: string;
    altitude?: string;
    network: string;
    lat: number;
    lon: number;
}
/*
    description: "TEMPERATURE/DRY-BULB TEMPERATURE"
    scale: 2
    unit: "K"
    values: [
        {level: "103,2000,0,0", reftime: "Fri, 22 May 2020 00:00:00 GMT", timerange: "254,0,0", value: 287.75}
        {level: "103,2000,0,0", reftime: "Fri, 22 May 2020 05:00:00 GMT", timerange: "254,0,0", value: 287.75}
        {level: "103,2000,0,0", reftime: "Fri, 22 May 2020 06:00:00 GMT", timerange: "254,0,0", value: 290.75}
        {level: "103,2000,0,0", reftime: "Fri, 22 May 2020 07:00:00 GMT", timerange: "254,0,0", value: 292.65}
        {level: "103,2000,0,0", reftime: "Fri, 22 May 2020 08:00:00 GMT", timerange: "254,0,0", value: 294.65}
    ]
    varcode: "B12101"
 */
export interface ObsData {
    description: string;
    scale: number;
    unit: string;
    values: any[];
    varcode: string;
}

export interface Observation {
    station: Station;
    products?: ObsData[];
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

    getData(filter: ObsFilter): Observable<Observation[]> {
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

    getColor(v: number) {
        if (v < -28) { return "ffcc00"; }
        else if (v < -26) { return "ff9900"; }
        else if (v < -24) { return "ff6600"; }
        else if (v < -22) { return "ff0000"; }
        else if (v < -20) { return "cc0000"; }
        else if (v < -18) { return "990000"; }
        else if (v < -16) { return "660000"; }
        else if (v < -14) { return "660066"; }
        else if (v < -12) { return "990099"; }
        else if (v < -10) { return "cc00cc"; }
        else if (v < -8) { return "ff00ff"; }
        else if (v < -6) { return "bf00ff"; }
        else if (v < -4) { return "7200ff"; }
        else if (v < -2) { return "0000ff"; }
        else if (v < 0) { return "0059ff"; }
        else if (v < 2) { return "008cff"; }
        else if (v < 4) { return "00bfff"; }
        else if (v < 6) { return "00ffff"; }
        else if (v < 8) { return "00e5cc"; }
        else if (v < 10) { return "00cc7f"; }
        else if (v < 12) { return "00b200"; }
        else if (v < 14) { return "7fcc00"; }
        else if (v < 16) { return "cce500"; }
        else if (v < 18) { return "ffff00"; }
        else if (v < 20) { return "ffcc00"; }
        else if (v < 22) { return "ff9900"; }
        else if (v < 24) { return "ff6600"; }
        else if (v < 26) { return "ff0000"; }
        else if (v < 28) { return "cc0000"; }
        else if (v < 30) { return "990000"; }
        else if (v < 32) { return "660000"; }
        else if (v < 34) { return "660066"; }
        else if (v < 36) { return "990099"; }
        else if (v < 38) { return "cc00cc"; }
        else if (v < 40) { return "ff00ff"; }
        else if (v < 42) { return "bf00ff"; }
        else if (v < 44) { return "7200ff"; }
        else if (v < 46) { return "ffcc00"; }
        else { return "ff9900"; }
    }
}
