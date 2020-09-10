import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import { catchError } from "rxjs/operators";
import { ApiService } from "@rapydo/services/api";
import { COLORS, VAR_TABLE } from "./data";
import { environment } from "@rapydo/../environments/environment";

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
  product: any[];
  available_products: any[];
  level?: any[];
  network?: any[];
  timerange?: any[];
}

export interface Station {
  ident?: string;
  altitude?: string;
  network: string;
  lat: number;
  lon: number;
  details?: StationDetail[];
}

export interface StationDetail {
  code: string;
  value: string;
  description: string;
}

export interface ObsValues {
  level: string;
  level_desc: string;
  reftime: string;
  timerange: string;
  timerange_desc: string;
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

export interface SingleObsData {
  description: string;
  scale: number;
  unit: string;
  value: ObsValues;
  varcode: string;
}

export interface Observation {
  station: Station;
  products?: ObsData[];
}

@Injectable({
  providedIn: "root",
})
export class ObsService {
  private _min: number;
  private _max: number;

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

  getObservations(filter: ObsFilter) {
    return this.api.get("observations", "", filter);
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
    return this.api.get("observations", "", params);
  }

  /**
   * Get observation data.
   * @param filter
   * @param reliabilityCheck request for value reliability. Default to true.
   */
  getData(
    filter: ObsFilter,
    reliabilityCheck = true
  ): Observable<Observation[]> {
    let d = [
      `${filter.reftime.getFullYear()}`,
      `${filter.reftime.getMonth() + 1}`.padStart(2, "0"),
      `${filter.reftime.getDate()}`.padStart(2, "0"),
    ].join("-");
    let params = {
      q: `reftime: >=${d} 00:00,<=${d} 23:59;product:${filter.product}`,
      reliabilityCheck: reliabilityCheck,
    };
    if (filter.onlyStations) {
      params["onlyStations"] = true;
    }
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
    return this.api.get("observations", "", params);
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
      .post<Blob>(environment.apiUrl + "/observations", null, {
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
    let bcode = VAR_TABLE.find((x) => x.bcode === type);
    if (!bcode) {
      console.warn(
        `Bcode not available for product ${type}. No offset or scale applied!`
      );
    } else {
      scale = bcode.scale;
      offset = bcode.offset;
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
