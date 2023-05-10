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
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";

import { AppModule } from "@rapydo/app.module";
import { AdminAttributionsComponent } from "./admin-attributions";
import { AdminModule } from "@rapydo/components/admin/admin.module";
import { Attribution } from "../../types";

import { environment } from "@rapydo/../environments/environment";

describe("AdminAttributionsComponent", () => {
  let injector: TestBed;
  let httpMock: HttpTestingController;
  let fixture: ComponentFixture<AdminAttributionsComponent>;
  let component: AdminAttributionsComponent;

  const attributions: Array<Attribution> = [
    {
      id: "x",
      name: "A",
      descr: "AAA",
      url: "AAAA",
    },
  ];

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [
        AppModule,
        AdminModule,
        BrowserAnimationsModule,
        HttpClientTestingModule,
      ],
    }).compileComponents();

    injector = getTestBed();
    httpMock = injector.inject(HttpTestingController);
    fixture = TestBed.createComponent(AdminAttributionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const req = httpMock.expectOne(
      environment.backendURI + "/api/admin/attributions",
    );
    expect(req.request.method).toEqual("GET");
    req.flush(attributions);

    httpMock.verify();
  }));

  it("component initialization", () => {
    expect(component).toBeDefined();
  });
});
