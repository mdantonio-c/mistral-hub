import {Injectable} from '@angular/core';
import {ApiService} from '/rapydo/src/app/services/api';
import {Observable, of} from 'rxjs';

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
    type: ScheduleType;
    time?: string;    // hh:mm
    every?: number;
    repeat?: RepeatEvery;
}

export enum RepeatEvery {
    MINUTE = 'minute',
    HOUR = 'hour',
    DAY = 'day',
    WEEK = 'week',
    MONTH = 'month'
}

export enum ScheduleType {
    CRONTAB = 'crontab',
    PERIOD = 'period',
    DATA_READY = 'data-ready'
}

export interface DateSchedule {
    /** The year, for example 2019 */
    year: number;
    /** The month, for example 1=Jan ... 12=Dec */
    month: number;
    /** The day of month, starting at 1 */
    day: number;
}

export interface TimeSchedule {
    /** The hour in the `[0, 23]` range. */
    hour: number;
    /** The minute in the `[0, 59]` range. */
    minute: number;
}

export const additionalVariables = [
    {code: 'B12194', desc: 'Air density'},
    {code: 'B13003', desc: 'Relative humidity'},
    {code: 'B11001', desc: 'Wind direction'},
    {code: 'B11002', desc: 'Wind speed'},
];

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
    extractData(name: string, datasets: string[], filters?: Filters[], schedule?: TaskSchedule, postprocessors?: any[]) {
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
        if (schedule) {
            switch (schedule.type) {
                case ScheduleType.CRONTAB:
                    // expected hh:mm
                    const split = schedule.time.split(':');
                    data['crontab-settings'] = {
                        hour: parseInt(split[0].replace(/^0/, '')),
                        minute: parseInt(split[1].replace(/^0/, ''))
                    };
                    if (schedule.repeat === RepeatEvery.WEEK) {
                        data['crontab-settings']['day_of_week'] = 1;     // every Monday
                    } else if (schedule.repeat === RepeatEvery.MONTH) {
                        data['crontab-settings']['day_of_month'] = 1;   // every first of the month
                    }
                    break;
                case ScheduleType.PERIOD:
                    // managed values: days, hours, minutes
                    data['period-settings'] = {
                        every: schedule.every,
                        period: `${schedule.repeat}s`
                    };
                    break;
            }
        }
        if (postprocessors && postprocessors.length) {
            data['postprocessors'] = postprocessors;
        }
        const endpoint = schedule ? 'schedules' : 'data';
        return this.api.post(endpoint, data, {"rawResponse": true});
    }

    /**
     * Download data for a completed extraction request
     */
    downloadData(filename): Observable<any> {
        const options = {
            rawResponse: true,
            conf: {
                responseType: 'blob',
                observe: 'response',
            }
        };
        return this.api.get('data', filename, {}, options);
    }

    toggleScheduleActiveState(scheduleId, toState: boolean) {
        const data = {
            is_active: toState
        }
        return this.api.patch('schedules', scheduleId, data);
    }

    getLastScheduledRequest(scheduleId): Observable<RapydoBundle<any>> {
        return this.api.get(`schedules/${scheduleId}/requests`, '', {last: true}, {"rawResponse": true});
    }

    getVariableDescription(code): string {
        return additionalVariables.find(av => av.code === code).desc;
    }

}
