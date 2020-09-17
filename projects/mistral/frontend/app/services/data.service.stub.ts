import { Observable, of } from "rxjs";
import { Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";

import { ApiService } from "@rapydo/services/api";
import { DataService, StorageUsage } from "./data.service";
import {
  MockDerivedVariables,
  MockGribTemplateResponse,
  MockLicenseResponse,
  MockShapeTemplateResponse,
  MockStorageUsageResponse,
} from "./data.mock";

@Injectable()
export class DataServiceStub extends DataService {
  constructor() {
    super({} as ApiService, {} as HttpClient);
  }

  getStorageUsage(): Observable<StorageUsage> {
    return of(MockStorageUsageResponse);
  }

  getDerivedVariables(): Observable<any> {
    return of(MockDerivedVariables);
  }

  getTemplates(param): Observable<any> {
    if (param == "grib") {
      return of(MockGribTemplateResponse);
    } else if (param == "shp") {
      return of(MockShapeTemplateResponse);
    }
  }

  getDatasets(licenceSpecs = false) {
    return of(MockLicenseResponse);
  }
}
