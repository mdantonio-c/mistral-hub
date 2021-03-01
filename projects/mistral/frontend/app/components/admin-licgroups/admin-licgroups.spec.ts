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
import { AdminLicgroupsComponent } from "./admin-licgroups";
import { AdminModule } from "@rapydo/components/admin/admin.module";
import { LicenseGroup } from "../../types";

import { environment } from "@rapydo/../environments/environment";

describe("AdminLicgroupsComponent", () => {
  let injector: TestBed;
  let httpMock: HttpTestingController;
  let fixture: ComponentFixture<AdminLicgroupsComponent>;
  let component: AdminLicgroupsComponent;

  const licgroups: Array<LicenseGroup> = [
    {
      id: "x",
      name: "A",
      descr: "AAA",
      is_public: true,
      dballe_dsn: "AAAA",
    },
  ];

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [AppModule, AdminModule, HttpClientTestingModule],
    }).compileComponents();

    injector = getTestBed();
    httpMock = injector.inject(HttpTestingController);
    fixture = TestBed.createComponent(AdminLicgroupsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const req = httpMock.expectOne(
      environment.backendURI + "/api/admin/licensegroups"
    );
    expect(req.request.method).toEqual("GET");
    req.flush(licgroups);

    httpMock.verify();
  }));

  it("component initialization", () => {
    expect(component).toBeDefined();
  });
});
