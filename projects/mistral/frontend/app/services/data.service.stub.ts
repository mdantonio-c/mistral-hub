import { Observable } from "rxjs";
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
    return Observable.of(MockStorageUsageResponse);
  }

  getDerivedVariables(): Observable<any> {
    return Observable.of(MockDerivedVariables);
  }

  getTemplates(param): Observable<any> {
    if (param == "grib") {
      return Observable.of(MockGribTemplateResponse);
    } else if (param == "shp") {
      return Observable.of(MockShapeTemplateResponse);
    }
  }

  getDatasets(licenceSpecs = false) {
    return Observable.of(MockLicenseResponse);
  }
}
