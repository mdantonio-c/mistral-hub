import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable, of} from 'rxjs';
import 'rxjs/add/operator/map';
import 'rxjs/add/operator/share';
import {ApiService} from '@rapydo/services/api';
import { environment } from '@rapydo/../environments/environment';

export interface SummaryStats {
    b?: number[];
    e?: number[];
    c: number;
    s: number;
}

export interface StorageUsage {
    quota: number;
    used: number;
}

export interface DerivedVariables {
    code: string;
    desc: string;
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

export interface Dataset {
    id: string;
    name: string;
    description?: string;
    category: string;
    format: string;

    // attribution
    attribution?: string;
    attribution_description?: string;
    attribution_url?: string;

    // group of license
    group_license?: string;
    group_license_description?: string;

    // license
    license?: string;
    license_description?: string;
    license_url?: string;
}

export interface RefTime {
    from: Date;
    to: Date;
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

@Injectable({
    providedIn: 'root'
})
export class DataService {
    private _derivedVariables: DerivedVariables[];

    constructor(
        private api: ApiService,
        private http: HttpClient) {
    }

    /**
     * Get all the available datasets.
     * @param licenceSpecs if true add licence information. Default to false.
     */
    getDatasets(licenceSpecs = false): Observable<Dataset[]> {
        let params = (licenceSpecs) ? {licenceSpecs: true} : {};
        return this.api.get('datasets', '', params);
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


    uploadTemplate(file: File){
        let formData: FormData = new FormData();
        formData.append('file', file);
        let data = {file: formData};
        let  ep = environment.apiUrl + "/" + 'templates';
        return this.http.post(ep, formData);
        //return this.api.post('templates', formData);
    }

    getTemplates(param: string){
        if (param){
            return this.api.get('templates?format='+param);
        }else{
            return this.api.get('templates');    
        }        
    }
    /**
     * Request for data extraction.
     */
    extractData(name: string, reftime: RefTime, datasets: string[],
                filters?: Filters[], schedule?: TaskSchedule,
                postprocessors?: any[], outputformat?: string) {
        let data = {
            name: name,
            reftime: reftime,
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
                case ScheduleType.DATA_READY:
                    data['on-data-ready'] = true;
                    break;
            }
        }
        if (postprocessors && postprocessors.length) {
            data['postprocessors'] = postprocessors;
        }
        if (outputformat){
            data['output_format'] = outputformat;
        }
        const endpoint = schedule ? 'schedules' : 'data';
        return this.api.post(endpoint, data);
    }

    /**
     * Download data for a completed extraction request
     */
    downloadData(filename): Observable<any> {
        const options = {
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
        };
        return this.api.patch('schedules', scheduleId, data);
    }

    getLastScheduledRequest(scheduleId): Observable<any> {
        return this.api.get(`schedules/${scheduleId}/requests`, '', {last: true});
    }

    getVariableDescription(code): string {
        if (this._derivedVariables === undefined) {
            console.warn(`Derived variables undefined so description cannot be retrieved for code ${code}`);
            return;
        }
        return this._derivedVariables.find(av => av.code === code).desc;
    }

    getStorageUsage(): Observable<StorageUsage> {
        return this.api.get(`usage`);
    }

    getDerivedVariables(): Observable<DerivedVariables[]> {
        if (this._derivedVariables) {
            return of(this._derivedVariables);
        } else {
            return this.http.get('/app/custom/assets/config/derived_variables.csv', {responseType: 'text'})
                .map(response => {
                    this._derivedVariables = this.extractConfig(response);
                    return this._derivedVariables;
                }).share();
        }
    }

    private extractConfig(csvData: string): DerivedVariables[] {
        let allTextLines = csvData.split(/\r?\n/);
        let lines = [];
        for (let i = 0; i < allTextLines.length; i++) {
            if (!allTextLines[i]) {
                continue;
            }
            // split content based on comma
            let data = allTextLines[i].split(',');
            if (!data[1]) {  // ignore codes with no description
                continue;
            }
            lines.push({code: data[0], desc: data[1]});
        }
        return lines;
    }

}
