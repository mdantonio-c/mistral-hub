import { Injectable } from "@angular/core";
import { ApiService } from "@rapydo/services/api";
import { Observable, forkJoin, of } from "rxjs";
import { RunAvailable } from "@app/types";

@Injectable({
  providedIn: "root",
})
export class TilesService {
  constructor(private api: ApiService) {}

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
    return this.api.get("tiles", "", params, {
      validationSchema: "RunAvailable",
    });
  }
}
