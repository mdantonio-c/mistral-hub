import { Injectable } from "@angular/core";
import { ApiService } from "@rapydo/services/api";
import { Observable, forkJoin, of } from "rxjs";
import { RunAvailable } from "@app/types";
import { environment } from "@rapydo/../environments/environment";
import { HttpClient } from "@angular/common/http";
import { shareReplay } from "rxjs/operators";

@Injectable({
  providedIn: "root",
})
export class TilesService {
  // private tiles_url: string = "";
  private maps_url: string = "";
  private wms_url: string = "";
  // dicts to allow caching
  private _imgCache: Map<string, Observable<ArrayBuffer>> = new Map();
  private _geoJsonCache: Map<string, Observable<any>> = new Map();
  constructor(private api: ApiService, private http: HttpClient) {
    // this.tiles_url = environment.CUSTOM.TILES_URL;
    // this.external_url = this.tiles_url != "";
    this.maps_url = environment.CUSTOM.MAPS_URL;
    this.wms_url = environment.CUSTOM.TILES_URL;
  }

  getWMSUrl() {
    return this.wms_url;
  }
  getMapsUrl() {
    return this.maps_url;
  }

  /**
   * Check and retrieve the last available run for a given resolution.
   * @param dataset name (lm2.2, lm5, iff)
   * @param run optionally a specific run between 00 and 12 cam be passed.
   */
  getLastRun(dataset: string, run?: string): Observable<RunAvailable> {
    let params = {
      dataset: dataset,
    };
    if (run) {
      params["run"] = run;
    }

    const options = {
      validationSchema: "RunAvailable",
    };

    // const mockData: RunAvailable = {  // TODO: remove mock data
    //   dataset: dataset,
    //   reftime: "2023-01-01T00:00:00Z",
    //   platform: "mock-platform",
    //   area: "mock-area",
    //   start_offset: 0,
    //   end_offset: 24,
    //   step: 1,
    //   boundaries: {
    //     SW: [10],
    //     NE: [20]
    //   },
    // };

    // return of(mockData);
    if (dataset != "ww3") {
      return this.api.get(`${this.maps_url}/api/windy`, params, options);
    } else {
      return this.api.get(`${this.maps_url}/api/ww3/status`);
    }
  }

  getLastRadarData(radar_type: string): Observable<any> {
    return this.api.get(`${this.maps_url}/api/radar/${radar_type}/status`);
  }
  resetCache() {
    this._imgCache.clear();
    this._geoJsonCache.clear();
  }

  getImgComponent(
    dataset: string,
    foldername: string,
    filename: string,
    stream: boolean = false,
  ): Observable<ArrayBuffer> {
    let params = {
      dataset: dataset,
      foldername: foldername,
      filename: filename,
      stream: stream,
    };

    return this.http.get(`${this.maps_url}/api/windy`, {
      params,
      responseType: "arraybuffer",
    });
  }

  getImgComponentCached(
    dataset: string,
    foldername: string,
    filename: string,
    stream: boolean = false,
  ): Observable<ArrayBuffer> {
    const key = `${dataset}_${foldername}_${filename}`;
    if (!this._imgCache.has(key)) {
      const obs = this.http
        .get(`${this.maps_url}/api/windy`, {
          params: { dataset, foldername, filename, stream },
          responseType: "arraybuffer",
        })
        .pipe(shareReplay(1));
      this._imgCache.set(key, obs);
    }
    return this._imgCache.get(key)!;
  }

  getGeoJsonComponent(
    dataset: string,
    foldername: string,
    filename: string,
    stream: boolean = false,
  ): Observable<any> {
    let params = {
      dataset: dataset,
      foldername: foldername,
      filename: filename,
      stream: stream,
    };

    return this.api.get(`${this.maps_url}/api/windy`, params);
  }

  getGeoJsonComponentCached(
    dataset: string,
    foldername: string,
    filename: string,
    stream: boolean = false,
  ): Observable<any> {
    const key = `${dataset}_${foldername}_${filename}`;
    if (!this._geoJsonCache.has(key)) {
      const params = {
        dataset: dataset,
        foldername: foldername,
        filename: filename,
        stream: stream,
      };
      const obs = this.api
        .get(`${this.maps_url}/api/windy`, params)
        .pipe(shareReplay(1));
      this._geoJsonCache.set(key, obs);
    }
    return this._geoJsonCache.get(key)!;
  }

  getGeoJsonVectors(filename): Observable<any> {
    return this.api.get(`${this.maps_url}/api/ww3/vectors/${filename}`);
  }
}
