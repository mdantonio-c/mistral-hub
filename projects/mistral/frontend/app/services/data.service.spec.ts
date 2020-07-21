import { TestBed, inject } from "@angular/core/testing";
import {
  HttpClientTestingModule,
  HttpTestingController,
} from "@angular/common/http/testing";
import { ApiService } from "@rapydo/services/api";
import { DataService } from "@app/services/data.service";

class ApiServiceStub {}

describe("DataService", () => {
  let service, http;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        DataService,
        { provide: ApiService, useClass: ApiServiceStub },
      ],
    });
    service = TestBed.inject(DataService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it("should be created", inject([DataService], (service: DataService) => {
    expect(service).toBeTruthy();
  }));
});
