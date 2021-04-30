import { Injectable } from "@angular/core";
import { ApiService } from "@rapydo/services/api";
import { Observable, forkJoin, of } from "rxjs";
import { RunAvailable } from "@app/types";
import { environment } from "@rapydo/../environments/environment";

@Injectable({
  providedIn: "root",
})
export class TilesService {
  private tiles_url: string = "";
  private external_url: boolean = false;

  constructor(private api: ApiService) {
    this.tiles_url = environment.CUSTOM.TILES_URL;
    this.external_url = this.tiles_url != "";
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
      externalURL: this.external_url,
      validationSchema: "RunAvailable",
    };

    return this.api.get(`${this.tiles_url}/api/tiles`, params, options);
  }
}
