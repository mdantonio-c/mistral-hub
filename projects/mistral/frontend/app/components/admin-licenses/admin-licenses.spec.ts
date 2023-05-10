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
import { AdminLicensesComponent } from "./admin-licenses";
import { AdminModule } from "@rapydo/components/admin/admin.module";
import { License } from "../../types";

import { environment } from "@rapydo/../environments/environment";

describe("AdminLicensesComponent", () => {
  let injector: TestBed;
  let httpMock: HttpTestingController;
  let fixture: ComponentFixture<AdminLicensesComponent>;
  let component: AdminLicensesComponent;

  const licenses: Array<License> = [];

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [AppModule, AdminModule, HttpClientTestingModule],
    }).compileComponents();

    injector = getTestBed();
    httpMock = injector.inject(HttpTestingController);
    fixture = TestBed.createComponent(AdminLicensesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const req = httpMock.expectOne(
      environment.backendURI + "/api/admin/licenses",
    );
    expect(req.request.method).toEqual("GET");
    req.flush(licenses);

    httpMock.verify();
  }));

  it("component initialization", () => {
    expect(component).toBeDefined();
  });
});
