import { Component, Input } from "@angular/core";
import { async, ComponentFixture, TestBed } from "@angular/core/testing";
import { RouterTestingModule } from "@angular/router/testing";
import { Router } from "@angular/router";
import { ReactiveFormsModule, FormBuilder } from "@angular/forms";
import { NgbModule } from "@ng-bootstrap/ng-bootstrap";
import { DatePipe } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { NgxSpinnerModule } from "ngx-spinner";

import { NotificationService } from "@rapydo/services/notification";
import { AuthService } from "@rapydo/services/auth";
import { ApiService } from "@rapydo/services/api";
import { StepSubmitComponent } from "./step-submit.component";
import { FormatDatePipe } from "../../../pipes/format-date.pipe";
import { FormDataService } from "../../../services/formData.service";
import { FormDataServiceStub } from "../../../services/formData.service.stub";
import { BytesPipe } from "@rapydo/pipes/bytes";
import { DataService } from "../../../services/data.service";
import { DataServiceStub } from "../../../services/data.service.stub";

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
        FormsModule,
        ReactiveFormsModule,
        RouterTestingModule.withRoutes([]),
        NgbModule,
        NgxSpinnerModule,
      ],
      providers: [
        DatePipe,
        AuthService,
        ApiService,
        { provide: FormBuilder, useValue: formBuilder },
        { provide: FormDataService, useClass: FormDataServiceStub },
        { provide: DataService, useClass: DataServiceStub },
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
