import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable, forkJoin, of} from 'rxjs';
import 'rxjs/add/operator/map';
import 'rxjs/add/operator/share';
import {ApiService} from '@rapydo/services/api';
import {COLORS, FIELDS_SUMMARY, VAR_TABLE} from "./data";

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
    id?: number;
    ident?: string;
    altitude?: string;
    network: string;
    lat: number;
    lon: number;
}

export interface ObsValues {
    level: string;
    reftime: string;
    timerange: string;
    value: number;
    is_reliable?: boolean;
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
    values: ObsValues[];
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
    private _min: number;
    private _max: number;

    constructor(private api: ApiService) {
    }

    getFields(): Observable<FieldsSummary> {
       //return this.api.get('fields', '', {type: 'OBS'});
        return of(FIELDS_SUMMARY);
    }

    getObservations(filter: ObsFilter) {
        return this.api.get('observations', '', filter);
    }

    /**
     * Get observation data.
     * @param filter
     * @param reliabilityCheck request for value reliability. Default to true.
     */
    getData(filter: ObsFilter, reliabilityCheck = true): Observable<Observation[]> {
        let d = [
            `${filter.reftime.getFullYear()}`,
            `${filter.reftime.getMonth()+1}`.padStart(2, '0'),
            `${filter.reftime.getDate()}`.padStart(2, '0')
            ].join('-');
        let params = {
            q: `reftime: >=${d} 00:00,<=${d} 23:59;product:${filter.product}`,
            reliabilityCheck: reliabilityCheck
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

    private getColorIndex(d, min, max) {
        let delta = (max - min) / (COLORS.length);
        return Math.max(0, Math.min(COLORS.length - 1, Math.floor((d - min) / delta)));
    }

    getColor(d, min, max) {
        return COLORS[this.getColorIndex(d, min, max)];
    }

    // @ts-ignore
    get min(): number {
        return this._min;
    }
    // @ts-ignore
    set min(value: number) {
        this._min = value;
    }

    // @ts-ignore
    get max(): number {
        return this._max;
    }
    // @ts-ignore
    set max(value: number) {
        this._max = value;
    }

    /**
     * The "median" is the "middle" value in the list of numbers.
     *
     * @param {Array} numbers An array of numbers.
     * @return {Number} The calculated median value from the specified numbers.
     */
    static median(numbers: number[]): number {
        // median of [3, 5, 4, 4, 1, 1, 2, 3] = 3
        let median = 0, numsLen = numbers.length;
        numbers.sort();

        if (
            numsLen % 2 === 0 // is even
        ) {
            // average of two middle numbers
            median = (numbers[numsLen / 2 - 1] + numbers[numsLen / 2]) / 2;
        } else { // is odd
            // middle number only
            median = numbers[(numsLen - 1) / 2];
        }

        return median;
    }

    /**
     * Show the data applying offset and scale according to its type.
     * @param val {Number} The value to show
     * @param type {String} The meaning of the value (e.g. temperature)
     */
    static showData(val: number, type: string, precision = 5) {
        let bcode = VAR_TABLE.find(x => x.bcode === type);
        const scale = bcode.scale,
            offset = bcode.offset;
        return (val*scale+offset).toPrecision(precision).replace(/\.?0+$/,"");
    }
}
