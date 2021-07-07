import { Component, Input } from "@angular/core";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { async, ComponentFixture, TestBed } from "@angular/core/testing";
import { RouterTestingModule } from "@angular/router/testing";
import { Router } from "@angular/router";
import { ReactiveFormsModule, FormBuilder } from "@angular/forms";
import { NgbModule } from "@ng-bootstrap/ng-bootstrap";
import { DatePipe } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { NgxSpinnerModule } from "ngx-spinner";
import { HttpClientModule, HttpClient } from "@angular/common/http";

import { NotificationService } from "@rapydo/services/notification";
import { ApiService } from "@rapydo/services/api";
import { StepSubmitComponent } from "./step-submit.component";
import { FormatDatePipe } from "@app/pipes/format-date.pipe";
import { FormDataService } from "@app/services/formData.service";
import { FormDataServiceStub } from "@app/services/formData.service.stub";
import { BytesPipe } from "@rapydo/pipes/bytes";
import { DataService } from "@app/services/data.service";
import { DataServiceStub } from "@app/services/data.service.stub";
import { AuthService } from "@rapydo/services/auth";
import { AuthServiceStub } from "@app/services/auth.service.stub";

class NotificationServiceStub {}

@Component({
  selector: "mst-my-request-details",
  template: "<div></div>",
})
class StubMyRequestDetailsComponent {
  @Input() onSubmitStep;
}
describe("StepSubmitComponent", () => {
  let component: StepSubmitComponent;
  let fixture: ComponentFixture<StepSubmitComponent>;
  let router: Router;
  // create new instance of FormBuilder
  const formBuilder: FormBuilder = new FormBuilder();

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [
        StepSubmitComponent,
        FormatDatePipe,
        BytesPipe,
        StubMyRequestDetailsComponent,
      ],
      imports: [
        BrowserAnimationsModule,
        FormsModule,
        ReactiveFormsModule,
        RouterTestingModule.withRoutes([]),
        NgbModule,
        NgxSpinnerModule,
        HttpClientModule,
      ],
      providers: [
        HttpClient,
        DatePipe,
        AuthService,
        ApiService,
        { provide: FormBuilder, useValue: formBuilder },
        { provide: FormDataService, useClass: FormDataServiceStub },
        { provide: DataService, useClass: DataServiceStub },
        { provide: AuthService, useClass: AuthServiceStub },
        { provide: NotificationService, useClass: NotificationServiceStub },
      ],
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(StepSubmitComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
