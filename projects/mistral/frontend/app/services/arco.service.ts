import { Injectable } from "@angular/core";
import { Observable, of } from "rxjs";
import { retry, switchMap, map } from "rxjs/operators";
import { ApiService } from "@rapydo/services/api";
import { LocalStorageService } from "@rapydo/services/localstorage";
import { AccessKey, ArcoDataset } from "@app/types";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { saveAs } from "file-saver-es";
import { environment } from "@rapydo/../environments/environment";

@Injectable({
  providedIn: "root",
})
export class ArcoService {
  constructor(
    private api: ApiService,
    private local_storage: LocalStorageService,
    private http: HttpClient,
  ) {
    this.local_storage.userChanged.subscribe((user) => {
      if (user === this.local_storage.LOGGED_IN) {
        this.fetchAndSaveKey();
      } else if (user === this.local_storage.LOGGED_OUT) {
        this.removeKey();
      }
    });
  }

  private fetchAndSaveKey() {
    this.getAccessKey().subscribe({
      next: (key: AccessKey) => {
        this.saveKey(key);
      },
      error: (error: { status: number }) => {
        // If 404, create one
        if (error.status === 404) {
          this.createAccessKey().subscribe((key: AccessKey) => {
            this.saveKey(key);
          });
        }
      },
    });
  }

  private saveKey(key: AccessKey) {
    localStorage.setItem("access_key", key.key);
  }

  private removeKey() {
    localStorage.removeItem("access_key");
  }

  public getAccessKey(): Observable<AccessKey> {
    // return this.api.get("/api/access-key");
    // return this.api.get("/api/access-key");
    // Mock data for testing
    // return new Observable<AccessKey>((observer) => {
    //   observer.next({
    //   id: 1,
    //   key: "mock-access-key-12345",
    //   creation: new Date().toISOString(),
    //   expiration: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    //   scope: "read:write"
    //   });
    //   observer.complete();
    // });
    return this.api.get("/api/access-key");
  }

  public createAccessKey(expiration?: Date): Observable<AccessKey> {
    const expirationSeconds = expiration
      ? Math.floor((expiration.getTime() - Date.now()) / 1000)
      : undefined;
    const data = expirationSeconds
      ? { lifetime_seconds: expirationSeconds }
      : {};
    return this.api.post("/api/access-key", data);
  }

  public rotateAccessKey(expiration?: Date): Observable<AccessKey> {
    return this.revokeAccessKey().pipe(
      switchMap(() => this.createAccessKey(expiration)),
    );
    // return this.api.put("/api/access-key", data);
  }

  public revokeAccessKey(): Observable<void> {
    return this.api.delete("/api/access-key");
  }

  public validateAccessKey(): Observable<any> {
    return this.api.get("/api/access-key/validate");
  }

  public getArcoDatasets(): Observable<ArcoDataset[]> {
    return this.api.get<any[]>("/api/arco/datasets").pipe(
      map((items) => {
        return items.map((item) => {
          return {
            id: item.id,
            name: item.attrs.model,
            folder: item.folder,
            description: this.generateDescription(item),
            category: "SEA",
            format: item.fileformat,
            source: "arco",
            attribution: "ItaliaMeteo-ARPAE",
            attribution_url: null,
            group_license: "CCBY_COMPLIANT",
            license: "CCBY4.0",
            is_public: true,
            bounding: item.bounding,
            attribution_description:
              "Agenzia ItaliaMeteo in cooperation with Arpae Emilia-Romagna Idro-Meteo-Clima Service",
            group_license_description: "Group of licenses CC BY compliant",
            license_description: "CC BY 4.0",
            license_url:
              "https://creativecommons.org/licenses/by/4.0/legalcode",
          } as ArcoDataset;
        });
      }),
    );
  }

  private generateDescription(item: any): string {
    const attrs = item.attrs || {};
    const parts: string[] = [];

    // Model
    let model = attrs.model || attrs.product_name || "";
    if (model === "WW3 MEDITA") {
      model = "WW3 sea wave model";
    }
    if (model) parts.push(model);

    // Forecast Range
    if (attrs.emission_date && attrs.stop_date) {
      try {
        // emission_date: "2025-12-10 00:00 UTC" -> "2025-12-10T00:00:00Z"
        const startStr = attrs.start_date
          .replace(" UTC", "Z")
          .replace(" ", "T");
        const startDate = new Date(startStr);
        const stopDate = new Date(attrs.stop_date);
        if (item.attrs.forecast_length_hours) {
          const hours = Number(item.attrs.forecast_length_hours);
          const sign = typeof hours === 'number' ? (hours >= 0 ? '+' : '') : '';
          parts.push(`forecast range ${sign}${hours}h`);
        }

        if (!isNaN(startDate.getTime()) && !isNaN(stopDate.getTime())) {
          // const diffMs = stopDate.getTime() - startDate.getTime();
          // // 
          // const diffHours = Math.round(diffMs / (1000 * 60 * 60)); // minus 24h offset
          const formatDate = (date: Date) => {
            const dd = String(date.getDate()).padStart(2, '0');
            const mm = String(date.getMonth() + 1).padStart(2, '0');
            const yyyy = date.getFullYear();
            return `${dd}/${mm}/${yyyy}`;
          };
          parts.push(`time range from ${formatDate(startDate)} to ${formatDate(stopDate)}`);
          
        }
      } catch (e) {
        console.warn("Error parsing dates", e);
      }
    }

    // Run Time
    if (attrs.emission_date) {
      const match = attrs.emission_date.match(/(\d{2}):(\d{2})/);
      if (match) {
        parts.push(`run ${match[1]} UTC`);
      }
    }

    // Domain
    let domain = "";
    if (attrs.area) {
      domain += `${attrs.area} domain`;
    }

    let coords = "";
    if (
      attrs.northernmost_latitude &&
      attrs.southernmost_latitude &&
      attrs.westernmost_longitude &&
      attrs.easternmost_longitude
    ) {
      const n = parseFloat(attrs.northernmost_latitude);
      const s = parseFloat(attrs.southernmost_latitude);
      const w = parseFloat(attrs.westernmost_longitude);
      const e = parseFloat(attrs.easternmost_longitude);

      const fmt = (val: number, isLat: boolean) => {
        const dir = isLat ? (val >= 0 ? "N" : "S") : (val >= 0 ? "E" : "W");
        return `${Math.abs(val)}°${dir}`;
      };
      coords = `${fmt(n, true)}, ${fmt(s, true)}, ${fmt(w, false)}, ${fmt(e, false)}`;
    }

    if (domain && coords) {
      parts.push(`${domain}: ${coords}`);
    } else if (domain) {
      parts.push(domain);
    } else if (coords) {
      parts.push(`domain: ${coords}`);
    }

    let description = parts.join(", ");
    description += " ; experimental distribution in Zarr format";

    return description;
  }

  public download(objectPath: string, fileName: string) {
    const key = localStorage.getItem("access_key");
    if (key) {
      this.executeDownload(key, objectPath, fileName);
    } else {
      this.getAccessKey().subscribe(
        (k) => {
          this.saveKey(k);
          this.executeDownload(k.key, objectPath, fileName);
        },
        (error) => {
          console.error("No access key found");
        },
      );
    }
  }

  private executeDownload(key: string, objectPath: string, fileName: string) {
    const headers = new HttpHeaders({
      Authorization: "Basic " + btoa(key + ":"),
    });

    const url = environment.backendURI + "/api/arco/" + objectPath;

    this.http
      .get(url, { headers, responseType: "blob" })
      .pipe(retry(3))
      .subscribe((blob) => {
        saveAs(blob, fileName);
      });
  }
}
