import { Component, DebugElement } from "@angular/core";
import { Injectable } from "@angular/core";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { async, ComponentFixture, TestBed } from "@angular/core/testing";
import { NgxDatatableModule } from "@swimlane/ngx-datatable";
import { MomentModule } from "ngx-moment";
import { NgbModule } from "@ng-bootstrap/ng-bootstrap";
import { of } from "rxjs";
import { HttpClient } from "@angular/common/http";
import { Router } from "@angular/router";
import { ToastrModule } from "ngx-toastr";
import { NgxSpinnerModule } from "ngx-spinner";

import { SchedulesComponent } from "./schedules.component";
import { BytesPipe } from "@rapydo/pipes/bytes";
import { AuthService } from "@rapydo/services/auth";
import { NotificationService } from "@rapydo/services/notification";
import { SSRService } from "@rapydo/services/ssr";
import { LocalStorageService } from "@rapydo/services/localstorage";
import { ConfirmationModals } from "@rapydo/services/confirmation.modals";
import { ProjectOptions } from "@app/customization";
import { FormlyService } from "@rapydo/services/formly";
import { ApiService } from "@rapydo/services/api";
import { DataService } from "../../services/data.service";
import { DataServiceStub } from "../../services/data.service.stub";
import {
  MockSchedulesNoDataResponse,
  MockSchedulesResponse,
  MockSchedulesTotalResponse,
} from "../../services/data.mock";

@Component({
  selector: "loading",
  template: "<div></div>",
})
class StubLoadingComponent {}

@Injectable()
class ApiServiceStub extends ApiService {
  constructor() {
    super(
      {} as HttpClient,
      {} as Router,
      {} as LocalStorageService,
      {} as NotificationService,
      {} as SSRService
    );
  }

  get(
    endpoint: string,
    data: Record<string, unknown> = {},
    options: Record<string, unknown> = {}
  ) {
    if (data["get_total"] === true) {
      return of(MockSchedulesTotalResponse);
    } else {
      return of(MockSchedulesResponse);
    }
  }
}
class AuthServiceStub {}
class FormlyServiceStub {}

describe("SchedulesComponent", () => {
  let component: SchedulesComponent;
  let fixture: ComponentFixture<SchedulesComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [SchedulesComponent, StubLoadingComponent, BytesPipe],
      imports: [
        BrowserAnimationsModule,
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
        NgxSpinnerModule,
      ],
      providers: [
        NotificationService,
        SSRService,
        LocalStorageService,
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
    fixture = TestBed.createComponent(SchedulesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
