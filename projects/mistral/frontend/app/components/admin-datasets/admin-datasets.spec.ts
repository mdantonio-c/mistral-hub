import {
  async,
  ComponentFixture,
  TestBed,
  getTestBed,
} from "@angular/core/testing";
import {
  HttpClientTestingModule,
  HttpTestingController,
} from "@angular/common/http/testing";

import { AppModule } from "@rapydo/app.module";
import { AdminDatasetsComponent } from "./admin-datasets";
import { AdminModule } from "@rapydo/components/admin/admin.module";
import { AdminDataset } from "../../types";

import { environment } from "@rapydo/../environments/environment";

describe("AdminDatasetsComponent", () => {
  let injector: TestBed;
  let httpMock: HttpTestingController;
  let fixture: ComponentFixture<AdminDatasetsComponent>;
  let component: AdminDatasetsComponent;

  const datasets: Array<AdminDataset> = [];

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [AppModule, AdminModule, HttpClientTestingModule],
    }).compileComponents();

    injector = getTestBed();
    httpMock = injector.inject(HttpTestingController);
    fixture = TestBed.createComponent(AdminDatasetsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const req = httpMock.expectOne(
      environment.backendURI + "/api/admin/datasets",
    );
    expect(req.request.method).toEqual("GET");
    req.flush(datasets);

    httpMock.verify();
  }));

  it("component initialization", () => {
    expect(component).toBeDefined();
  });
});
