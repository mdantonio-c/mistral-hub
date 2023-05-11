import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable, of } from "rxjs";
import { catchError, map, switchMap } from "rxjs/operators";
import { ApiService } from "@rapydo/services/api";
import { COLORS, VAR_TABLE } from "./data";
import { environment } from "@rapydo/../environments/environment";
import {
  FieldsSummary,
  Observation,
  ObsFilter,
  Station,
  ObservationResponse,
} from "@app/types";

@Injectable({
  providedIn: "root",
})
export class ObsService {
  private _min: number;
  private _max: number;
  private _data: ObservationResponse;

  constructor(private api: ApiService, private http: HttpClient) {}

  /**
   * Get field values for the observation filter.
   * At the moment, only apply the following fields: reftime, product, network.
   * @param filter
   */
  getFields(filter: ObsFilter): Observable<FieldsSummary> {
    let params = {
      q: `${ObsService.parseReftime(
        filter.reftime,
        filter.reftime,
        filter.time,
      )};product:${filter.product};license:${filter.license}`,
      SummaryStats: false,
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
    // console.log(`q: ${params.q}`);
    return this.api.get("/api/fields", params);
  }

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
    station: Station,
  ): Observable<ObservationResponse> {
    let parsedReftime = "";
    if (filter.dateInterval && filter.dateInterval.length > 0) {
      parsedReftime = `${ObsService.parseReftime(
        filter.dateInterval[0],
        filter.dateInterval[1],
        filter.time,
      )}`;
    } else {
      parsedReftime = `${ObsService.parseReftime(
        filter.reftime,
        filter.reftime,
        filter.time,
      )}`;
    }
    let params = {
      q: parsedReftime,
      lat: station.lat,
      lon: station.lon,
      networks: station.net,
      stationDetails: true,
    };
    if (filter.timerange && filter.timerange !== "") {
      params["q"] += `;timerange:${filter.timerange}`;
    }
    if (filter.level && filter.level !== "") {
      params["q"] += `;level:${filter.level}`;
    }
    if (filter.license && filter.license !== "") {
      params["q"] += `;license:${filter.license}`;
    }
    if (filter.product && filter.product !== "") {
      params["q"] += `;product:${filter.product}`;
    }
    if (filter.allStationProducts == false) {
      params["allStationProducts"] = filter.allStationProducts;
    }
    return this.api.get("/api/observations", params);
    //.pipe(map((data: Observation[], descriptions: Descriptions[]) => (data.data, data.descr)));
  }

  /**
   * Get data to view. Keep them in cache or update them if required.
   * @param filter
   * @param update
   */
  getData(filter: ObsFilter, update = false): Observable<ObservationResponse> {
    return of(this._data).pipe(
      switchMap((data) => {
        if (!update && data) {
          return of(data);
        } else {
          return this.loadObservations(filter);
        }
      }),
    );
  }

  /**
   * Get observation data.
   * @param filter
   * @param reliabilityCheck request for value reliability. Default to true.
   */
  private loadObservations(filter: ObsFilter): Observable<ObservationResponse> {
    this._data = null;
    let params = {
      q: `${ObsService.parseReftime(
        filter.reftime,
        filter.reftime,
        filter.time,
      )};product:${filter.product};license:${filter.license}`,
    };
    if (filter.reliabilityCheck) {
      params["reliabilityCheck"] = filter.reliabilityCheck;
    }
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
    if (filter.interval) {
      params["interval"] = filter.interval;
    }
    if (filter.last) {
      params["last"] = filter.last;
    }
    // console.log(`q: ${params.q}`);
    return this.api
      .get<ObservationResponse>("/api/observations", params)
      .pipe(map((data: ObservationResponse) => (this._data = data)));
  }

  download(
    filter: ObsFilter,
    from: Date,
    to: Date,
    format: string,
  ): Observable<Blob> {
    let params = {
      q: `${ObsService.parseReftime(from, to, filter.time)};product:${
        filter.product
      };license:${filter.license}`,
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
    if (filter.reliabilityCheck) {
      params["reliabilityCheck"] = filter.reliabilityCheck;
    }
    return this.http
      .post<Blob>(environment.backendURI + "/api/observations", null, {
        params: params,
        responseType: "blob" as "json",
      })
      .pipe(catchError(this.api.parseErrorBlob));
  }

  private static parseReftime(from: Date, to: Date, time?: number[]): string {
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
    let fromTime = "00:00";
    let toTime = "23:59";
    if (time && time.length === 2) {
      fromTime = `${String(time[0]).padStart(2, "0")}:00`;
      toTime = `${String(time[1]).padStart(2, "0")}:59`;
    }
    return `reftime: >=${fDate} ${fromTime},<=${tDate} ${toTime}`;
  }

  private getColorIndex(d, min, max) {
    let delta = (max - min) / COLORS.length;
    return Math.max(
      0,
      Math.min(COLORS.length - 1, Math.floor((d - min) / delta)),
    );
  }

  getColor(d, min, max, rel = 1) {
    if (rel == 0) {
      return "undefined";
    } else return COLORS[this.getColorIndex(d, min, max)];
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

  getUnit(product): string {
    let code_dictionary = this._data.descr[product];
    return code_dictionary.unit;
  }

  getProductDescr(product): string {
    let code_dictionary = this._data.descr[product];
    return code_dictionary.descr;
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
   * @param precision {Number}
   */
  static showData(val: number, type: string, precision = 5) {
    const bCode = VAR_TABLE.find((x) => x.bcode === type);
    const scale = bCode && bCode.scale ? bCode.scale : 1;
    const offset = bCode && bCode.offset ? bCode.offset : 0;
    return (val * scale + offset).toPrecision(precision).replace(/\.?0+$/, "");
  }

  /**
   * Return the 'user' unit if available in the 'bcode' table which is conversions and
   * custom units of measurement are allowed.
   * @param type {String} The meaning of the value (e.g. temperature)
   * @param unit {String} the unit of measurement of the product if given. Null otherwise.
   */
  static showUserUnit(type: string, unit: string = null): string | null {
    const bcode = VAR_TABLE.find((x) => x.bcode === type);
    return bcode && bcode.userunit ? bcode.userunit : unit;
  }
}
