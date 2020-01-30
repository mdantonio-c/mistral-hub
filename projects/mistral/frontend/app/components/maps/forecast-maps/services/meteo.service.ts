import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable, of} from 'rxjs';

export interface MeteoFilter {
    field: string,
    run: string,
    resolution: string,
    platform: string,
    modality: string,
    area: string
}

@Injectable({
    providedIn: 'root'
})
export class MeteoService {

    constructor(private http: HttpClient) {
    }

}
