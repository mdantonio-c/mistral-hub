import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable, of } from "rxjs";
import { catchError, map, switchMap } from "rxjs/operators";
import { ApiService } from "@rapydo/services/api";
import { COLORS, VAR_TABLE } from "./data";
import { environment } from "@rapydo/../environments/environment";
import { FieldsSummary, Observation, ObsFilter, Station } from "@app/types";

@Injectable({
  providedIn: "root",
})
export class ObsService {
  private _min: number;
  private _max: number;
  private _data: Observation[] = [];

  constructor(private api: ApiService, private http: HttpClient) {}

  /**
   * Get field values for the observation filter.
   * At the moment, only apply the following fields: reftime, product, network.
   * @param filter
   */
  getFields(filter: ObsFilter): Observable<FieldsSummary> {
    let d = [
      `${filter.reftime.getFullYear()}`,
      `${filter.reftime.getMonth() + 1}`.padStart(2, "0"),
      `${filter.reftime.getDate()}`.padStart(2, "0"),
    ].join("-");
    let params = {
      q: `reftime: >=${d} 00:00,<=${d} 23:59;product:${filter.product}`,
      allAvailableProducts: true,
    };
    // do NOT narrow resulting filter by timerange and level
    /*
        if (filter.timerange && filter.timerange !== "") {
          params["q"] += `;timerange:${filter.timerange}`;
        }
        if (filter.level && filter.level !== "") {
          params["q"] += `;level:${filter.level}`;
        }
         */
    if (filter.network && filter.network !== "") {
      params["q"] += `;network:${filter.network}`;
    }
    return this.api.get("fields", "", params);
  }

  // getObservations(filter: ObsFilter) {
  //   return this.api.get("observations", "", filter);
  // }

  /**
   * Get station specifics and data for timeseries.
   *
   * required filter:
   * networks, lat and lon for static stations, ident for mobile stations(if reftime is not specified there will be a
   * default one)
   *
   * possible filters : reftime (can be useful also level and timerange?) if level, timerange or product are in query,
   * they are at the moment ignored in this case
   *
   * The param stationDetails has to be true.
   *
   * @return expected a single element array
   */
  getStationTimeSeries(
    filter: ObsFilter,
    station: Station
  ): Observable<Observation[]> {
    let d = [
      `${filter.reftime.getFullYear()}`,
      `${filter.reftime.getMonth() + 1}`.padStart(2, "0"),
      `${filter.reftime.getDate()}`.padStart(2, "0"),
    ].join("-");
    let params = {
      q: `reftime: >=${d} 00:00,<=${d} 23:59`,
      lat: station.lat,
      lon: station.lon,
      networks: station.network,
      stationDetails: true,
    };
    if (filter.timerange && filter.timerange !== "") {
      params["q"] += `;timerange:${filter.timerange}`;
    }
    if (filter.level && filter.level !== "") {
      params["q"] += `;level:${filter.level}`;
    }
    return this.api.get("observations", "", params);
  }

  /**
   * Get data to view. Keep them in cache or update them if required.
   * @param filter
   * @param update
   */
  getData(filter: ObsFilter, update = false): Observable<Observation[]> {
    return of(this._data).pipe(
      switchMap((data) => {
        if (!update && data.length !== 0) {
          return of(data);
        } else {
          return this.loadObservations(filter);
        }
      })
    );
  }

  /**
   * Get observation data.
   * @param filter
   * @param reliabilityCheck request for value reliability. Default to true.
   */
  private loadObservations(
    filter: ObsFilter,
    reliabilityCheck = true
  ): Observable<Observation[]> {
    this._data = [];
    let d = [
      `${filter.reftime.getFullYear()}`,
      `${filter.reftime.getMonth() + 1}`.padStart(2, "0"),
      `${filter.reftime.getDate()}`.padStart(2, "0"),
    ].join("-");
    let params = {
      q: `reftime: >=${d} 00:00,<=${d} 23:59;product:${filter.product}`,
      reliabilityCheck: reliabilityCheck,
    };
    // ignore only station filter
    // if (filter.onlyStations) {
    //   params["onlyStations"] = true;
    // }
    if (filter.timerange && filter.timerange !== "") {
      params["q"] += `;timerange:${filter.timerange}`;
    }
    if (filter.level && filter.level !== "") {
      params["q"] += `;level:${filter.level}`;
    }
    // ONLY network and boundingbox as distinct params
    if (filter.network && filter.network !== "") {
      params["networks"] = filter.network;
    }
    if (filter.bbox) {
      params["bounding_box"] =
        `latmin:${filter.bbox.latMin},lonmin:${filter.bbox.lonMin}` +
        `,latmax:${filter.bbox.latMax},lonmax:${filter.bbox.lonMax}`;
    }
    return this.api
      .get("observations", "", params)
      .pipe(map((data: Observation[]) => (this._data = data)));
  }

  download(
    filter: ObsFilter,
    from: Date,
    to: Date,
    format: string
  ): Observable<Blob> {
    let fDate = [
      `${from.getFullYear()}`,
      `${from.getMonth() + 1}`.padStart(2, "0"),
      `${from.getDate()}`.padStart(2, "0"),
    ].join("-");
    let tDate = [
      `${to.getFullYear()}`,
      `${to.getMonth() + 1}`.padStart(2, "0"),
      `${to.getDate()}`.padStart(2, "0"),
    ].join("-");
    let params = {
      q: `reftime: >=${fDate} 00:00,<=${tDate} 23:59;product:${filter.product}`,
      output_format: format,
    };
    if (filter.timerange && filter.timerange !== "") {
      params["q"] += `;timerange:${filter.timerange}`;
    }
    if (filter.level && filter.level !== "") {
      params["q"] += `;level:${filter.level}`;
    }
    // ONLY network and boundingbox as distinct params
    if (filter.network && filter.network !== "") {
      params["networks"] = filter.network;
    }
    return this.http
      .post<Blob>(environment.backendURI + "/api/observations", null, {
        params: params,
        responseType: "blob" as "json",
      })
      .pipe(catchError(this.api.parseErrorBlob));
  }

  private getColorIndex(d, min, max) {
    let delta = (max - min) / COLORS.length;
    return Math.max(
      0,
      Math.min(COLORS.length - 1, Math.floor((d - min) / delta))
    );
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
    let median = 0,
      numsLen = numbers.length;
    numbers.sort();

    if (
      numsLen % 2 ===
      0 // is even
    ) {
      // average of two middle numbers
      median = (numbers[numsLen / 2 - 1] + numbers[numsLen / 2]) / 2;
    } else {
      // is odd
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
    let scale = 1,
      offset = 0;
    let bCode = VAR_TABLE.find((x) => x.bcode === type);
    if (!bCode) {
      console.warn(
        `Bcode not available for product ${type}. No offset or scale applied!`
      );
    } else {
      scale = bCode.scale;
      offset = bCode.offset;
    }
    return (val * scale + offset).toPrecision(precision).replace(/\.?0+$/, "");
  }

  /**
   *
   * @param type {String} The meaning of the value (e.g. temperature)
   */
  static showUserUnit(type: string): string | null {
    let bcode = VAR_TABLE.find((x) => x.bcode === type);
    if (!bcode) {
      console.warn(
        `Bcode not available for product ${type}. No userunit available!`
      );
      return null;
    }
    return bcode.userunit;
  }
}
