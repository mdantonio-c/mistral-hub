import { Injectable } from "@angular/core";
import { Observable, forkJoin, of } from "rxjs";
import { ApiService } from "@rapydo/services/api";

export interface MeteoFilter {
  field: string;
  level_pe: string;
  level_pr: string;
  run: string;
  res: string;
  platform?: string;
  env?: string;
  area: string;
}

export interface MeteoMapset {
  offsets: string[];
  platform: string;
  reftime: string;
}

@Injectable({
  providedIn: "root",
})
export class MeteoService {
  constructor(private api: ApiService) {}

  getMapset(params: MeteoFilter): Observable<MeteoMapset> {
    return this.api.get("maps/ready", "", params);
  }

  getMapLegend(params: MeteoFilter): Observable<Blob> {
    let options = {
      conf: {
        responseType: "blob",
      },
    };
    return this.api.get("maps/legend", "", params, options);
  }

  getMapImage(params: MeteoFilter, offset: string): Observable<Blob> {
    let options = {
      conf: {
        responseType: "blob",
      },
    };
    return this.api.get("maps", offset, params, options);
  }

  getAllMapImages(params: MeteoFilter, offsets: string[]): Observable<any[]> {
    const observables = [];
    for (let i = 0; i < offsets.length; i++) {
      observables.push(this.getMapImage(params, offsets[i]));
    }
    return forkJoin(observables);
  }
}
