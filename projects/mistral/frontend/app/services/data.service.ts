import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable, of } from "rxjs";
import { map, share } from "rxjs/operators";
import { ApiService } from "@rapydo/services/api";
import { environment } from "@rapydo/../environments/environment";
import {
  DerivedVariables,
  Dataset,
  FieldsSummary,
  SummaryStats,
  Templates,
  RefTime,
  Filters,
  TaskSchedule,
  ScheduleType,
  RepeatEvery,
  OnOffSchedule,
  StorageUsage,
  OpenData,
} from "@app/types";

@Injectable({
  providedIn: "root",
})
export class DataService {
  private _derivedVariables: DerivedVariables[];

  constructor(private api: ApiService, private http: HttpClient) {}

  /**
   * Get all the available datasets.
   * @param licenceSpecs if true add licence information. Default to false.
   */
  getDatasets(licenceSpecs = false): Observable<Dataset[]> {
    const params = licenceSpecs ? { licenceSpecs: true } : {};
    return this.api.get("datasets", params);
  }

  /**
   * Get a dataset with a given ID.
   * @param datasetId
   * @param licenceSpecs
   */
  getDataset(datasetId: string, licenceSpecs = false): Observable<Dataset> {
    const params = licenceSpecs ? { licenceSpecs: true } : {};
    return this.api.get(`datasets/${datasetId}`, params);
  }

  getOpenData(datasetId): Observable<OpenData[]> {
    //Observable<DataExtractionRequest[]> {
    return this.api.get(`datasets/${datasetId}/opendata`);
    // return of(MockOpenDataResponse);
  }

  getSummary(
    datasets: string[],
    onlyStats?: boolean,
    query?: string
  ): Observable<FieldsSummary>;
  getSummary(
    datasets: string[],
    onlyStats: false,
    query?: string
  ): Observable<FieldsSummary>;
  getSummary(
    datasets: string[],
    onlyStats: true,
    query?: string
  ): Observable<SummaryStats>;
  /**
   * Get summary fields for a give list of datasets.
   * @param datasets
   */
  getSummary(
    datasets: string[],
    onlyStats?: boolean,
    query?: string
  ): Observable<FieldsSummary | SummaryStats> {
    let params = { datasets: datasets.join() };
    if (query) {
      params["q"] = query;
    }
    if (onlyStats) {
      params["onlySummaryStats"] = true;
    }
    return this.api.get("fields", params);
  }

  uploadTemplate(file: File) {
    let formData: FormData = new FormData();
    formData.append("file", file);
    let data = { file: formData };
    let ep = environment.backendURI + "/api/" + "templates";
    return this.http.post(ep, formData);
    //return this.api.post('templates', formData);
  }

  getTemplates(format?: string): Observable<Templates[]> {
    const param = format ? `?format=${format}` : "";
    return this.api.get(`templates${param}`);
  }

  /**
   * Request for data extraction.
   *
   * @param request_name
   * @param reftime
   * @param datasets
   * @param filters
   * @param schedule
   * @param postprocessors
   * @param outputformat
   */
  extractData(
    request_name: string,
    reftime: RefTime,
    datasets: string[],
    filters?: Filters[],
    schedule?: TaskSchedule,
    postprocessors?: any[],
    outputformat?: string,
    push?: boolean,
    opendata?: boolean,
    only_reliable?: boolean
  ) {
    let data = {
      request_name: request_name,
      reftime: reftime,
      dataset_names: datasets,
    };
    if (filters && filters.length) {
      data["filters"] = {};
      filters.forEach((f) => {
        data["filters"][f.name] = f.values.map((x) => {
          delete x["t"];
          return x;
        });
      });
    }
    if (schedule) {
      switch (schedule.type) {
        case ScheduleType.CRONTAB:
          // expected hh:mm
          const split = schedule.time.split(":");
          data["crontab-settings"] = {
            hour: parseInt(split[0].replace(/^0/, "")),
            minute: parseInt(split[1].replace(/^0/, "")),
          };
          if (schedule.repeat === RepeatEvery.WEEK) {
            data["crontab-settings"]["day_of_week"] = parseInt(
              schedule.day_of_week
            );
          } else if (schedule.repeat === RepeatEvery.MONTH) {
            data["crontab-settings"]["day_of_month"] = parseInt(
              schedule.day_of_month
            );
          }
          break;
        case ScheduleType.PERIOD:
          // managed values: days, hours, minutes
          data["period-settings"] = {
            every: schedule.every,
            period: `${schedule.repeat}s`,
          };
          break;
        case ScheduleType.DATA_READY:
          data["on-data-ready"] = true;
          break;
      }
    }
    if (postprocessors && postprocessors.length) {
      data["postprocessors"] = postprocessors;
    }
    if (outputformat) {
      data["output_format"] = outputformat;
    }
    if (only_reliable) {
      data["only_reliable"] = true;
    }
    let endpoint = schedule ? "schedules" : "data";
    if (push) {
      endpoint += "?push=true";
    }
    if (opendata) {
      data["opendata"] = true;
    }
    return this.api.post(endpoint, data);
  }

  /**
   * Download data for a completed extraction request
   */
  downloadData(filename): Observable<any> {
    const options = {
      conf: {
        responseType: "blob",
        observe: "response",
      },
    };
    return this.api.get(`data/${filename}`, {}, options);
  }

  toggleScheduleActiveState(
    scheduleId,
    toState: boolean
  ): Observable<OnOffSchedule> {
    const data = {
      is_active: toState,
    };
    return this.api.patch(`schedules/${scheduleId}`, data);
  }

  getLastScheduledRequest(scheduleId): Observable<any> {
    return this.api.get(
      `schedules/${scheduleId}/requests`,
      { last: true },
      { rawError: true }
    );
  }

  countScheduledRequests(scheduleId): Observable<any> {
    return this.api.get(`schedules/${scheduleId}/requests`, {
      get_total: true,
    });
  }

  getVariableDescription(code): string {
    if (this._derivedVariables === undefined) {
      console.warn(
        `Derived variables undefined so description cannot be retrieved for code ${code}`
      );
      return;
    }
    return this._derivedVariables.find((av) => av.code === code).desc;
  }

  getStorageUsage(): Observable<StorageUsage> {
    return this.api.get(`usage`);
  }

  getDerivedVariables(): Observable<DerivedVariables[]> {
    if (this._derivedVariables) {
      return of(this._derivedVariables);
    }

    return this.http
      .get<string>("/app/custom/assets/config/derived_variables.csv", {
        responseType: "text" as "json",
      })
      .pipe(
        map((response) => {
          this._derivedVariables = this.extractConfig(response);
          return this._derivedVariables;
        }),
        share()
      );
  }

  private extractConfig(csvData: string): DerivedVariables[] {
    let allTextLines = csvData.split(/\r?\n/);
    let lines = [];
    for (let i = 0; i < allTextLines.length; i++) {
      if (!allTextLines[i]) {
        continue;
      }
      // split content based on comma
      let data = allTextLines[i].split(",");
      if (!data[1]) {
        // ignore codes with no description
        continue;
      }
      lines.push({ code: data[0], desc: data[1] });
    }
    return lines;
  }
}
