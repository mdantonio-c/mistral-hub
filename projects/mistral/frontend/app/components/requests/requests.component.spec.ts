import { Component, DebugElement } from "@angular/core";
import { Injectable } from "@angular/core";
import { async, ComponentFixture, TestBed } from "@angular/core/testing";
import { RouterTestingModule } from "@angular/router/testing";
import { Router } from "@angular/router";
import { NgxDatatableModule } from "@swimlane/ngx-datatable";
import { MomentModule } from "ngx-moment";
import { NgbModule } from "@ng-bootstrap/ng-bootstrap";
import { of } from "rxjs";
import { HttpClient } from "@angular/common/http";
import { Router } from "@angular/router";
import { ToastrModule } from "ngx-toastr";
import { NgxSpinnerModule } from "ngx-spinner";

import { RequestsComponent } from "./requests.component";
import { BytesPipe } from "@rapydo/pipes/bytes";
import { AuthService } from "@rapydo/services/auth";
import { NotificationService } from "@rapydo/services/notification";
import { ConfirmationModals } from "@rapydo/services/confirmation.modals";
import { ProjectOptions } from "@app/customization";
import { FormlyService } from "@rapydo/services/formly";
import { ApiService } from "@rapydo/services/api";
import { DataService } from "../../services/data.service";
import { DataServiceStub } from "../../services/data.service.stub";
import {
  MockRequestsNoDataResponse,
  MockRequestsResponse,
  MockRequestsTotalResponse,
} from "../../services/data.mock";

@Component({
  selector: "loading",
  template: "<div></div>",
})
class StubLoadingComponent {}

@Injectable()
class ApiServiceStub extends ApiService {
  constructor() {
    super({} as HttpClient, {} as Router, {} as any, {} as NotificationService);
  }

  get(
    endpoint: string,
    data: Record<string, unknown> = {},
    options: Record<string, unknown> = {}
  ) {
    if (data["get_total"] === true) {
      return of(MockRequestsTotalResponse);
    } else {
      return of(MockRequestsResponse);
    }
  }
}
class AuthServiceStub {}
class FormlyServiceStub {}

describe("RequestsComponent", () => {
  let component: RequestsComponent;
  let fixture: ComponentFixture<RequestsComponent>;
  let router: Router;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [RequestsComponent, StubLoadingComponent, BytesPipe],
      imports: [
        NgxDatatableModule,
        MomentModule,
        NgbModule,
        ToastrModule.forRoot({
          maxOpened: 5,
          preventDuplicates: true,
          countDuplicates: true,
          resetTimeoutOnDuplicate: true,
          closeButton: true,
          enableHtml: true,
          progressBar: true,
          progressAnimation: "increasing",
          positionClass: "toast-bottom-right",
        }),
        RouterTestingModule.withRoutes([]),
        NgxSpinnerModule,
      ],
      providers: [
        NotificationService,
        ProjectOptions,
        ConfirmationModals,
        { provide: DataService, useClass: DataServiceStub },
        { provide: ApiService, useClass: ApiServiceStub },
        { provide: AuthService, useClass: AuthServiceStub },
        { provide: FormlyService, useClass: FormlyServiceStub },
      ],
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(RequestsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    router = TestBed.inject(Router);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
