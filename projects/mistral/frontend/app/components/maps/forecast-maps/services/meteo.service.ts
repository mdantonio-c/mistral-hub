import { Injectable } from "@angular/core";
import { Observable, forkJoin, of } from "rxjs";
import { ApiService } from "@rapydo/services/api";
import { environment } from "@rapydo/../environments/environment";

export interface MeteoFilter {
  field: string;
  level_pe: string;
  level_pr: string;
  run: string;
  iffruns: string;
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
  private maps_url: string = "";

  constructor(private api: ApiService) {
    this.maps_url = environment.CUSTOM.MAPS_URL;
  }

  private get_params(params: MeteoFilter): Record<string, unknown> {
    return JSON.parse(JSON.stringify(params));
  }
  getMapset(params: MeteoFilter): Observable<MeteoMapset> {
    return this.api.get(
      `${this.maps_url}/api/maps/ready`,
      this.get_params(params)
    );
  }

  getMapLegend(params: MeteoFilter): Observable<Blob> {
    const options = {
      conf: {
        responseType: "blob",
      },
    };
    return this.api.get(
      `${this.maps_url}/api/maps/legend`,
      this.get_params(params),
      options
    );
  }

  getMapImage(params: MeteoFilter, offset: string): Observable<Blob> {
    const options = {
      conf: {
        responseType: "blob",
      },
    };
    return this.api.get(
      `${this.maps_url}/api/maps/offset/${offset}`,
      this.get_params(params),
      options
    );
  }

  getAllMapImages(params: MeteoFilter, offsets: string[]): Observable<any[]> {
    const observables = [];
    for (let i = 0; i < offsets.length; i++) {
      observables.push(this.getMapImage(params, offsets[i]));
    }
    return forkJoin(observables);
  }
}
