import { ComponentFixture, TestBed } from "@angular/core/testing";
import { RouterTestingModule } from "@angular/router/testing";
import { Router } from "@angular/router";
import { ReactiveFormsModule, FormBuilder } from "@angular/forms";
import { NgbModule } from "@ng-bootstrap/ng-bootstrap";
import { DebugElement, Input, Component } from "@angular/core";
import { DatePipe } from "@angular/common";

import { StepPostprocessComponent } from "./step-postprocess.component";
import { FormDataService } from "../../../services/formData.service";
import { FormDataServiceStub } from "../../../services/formData.service.stub";
import { DataServiceStub } from "../../../services/data.service.stub";
import { DataService } from "../../../services/data.service";
import { FormatDatePipe } from "../../../pipes/format-date.pipe";

import { NotificationService } from "@rapydo/services/notification";
import { ConfirmationModals } from "@rapydo/services/confirmation.modals";
import { BytesPipe } from "@rapydo/pipes/bytes";
import { AuthService } from "@rapydo/services/auth";
import { AuthServiceStub } from "@app/services/auth.service.stub";

class NotificationServiceStub {}

@Component({
  selector: "step-postprocess-map",
  template: '<div class="container" style="margin-top: 30px;"></div>',
})
class StubStepPostprocessMapComponent {
  @Input() formGroup;
  // ilon, ilat, flon, flat
  @Input() ilonControl;
  @Input() ilatControl;
  @Input() flonControl;
  @Input() flatControl;
}

@Component({
  selector: "mst-my-request-details",
  template: "<div></div>",
})
class StubMyRequestDetailsComponent {}

describe("StepPostprocessComponent", () => {
  let component: StepPostprocessComponent;
  let fixture: ComponentFixture<StepPostprocessComponent>;
  let de: DebugElement;
  let router: Router;
  // create new instance of FormBuilder
  const formBuilder: FormBuilder = new FormBuilder();

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [
        StepPostprocessComponent,
        StubStepPostprocessMapComponent,
        StubMyRequestDetailsComponent,
        FormatDatePipe,
        BytesPipe,
      ],
      imports: [
        ReactiveFormsModule,
        RouterTestingModule.withRoutes([]),
        NgbModule,
      ],
      providers: [
        DatePipe,
        ConfirmationModals,
        { provide: FormBuilder, useValue: formBuilder },
        { provide: FormDataService, useClass: FormDataServiceStub },
        { provide: DataService, useClass: DataServiceStub },
        { provide: NotificationService, useClass: NotificationServiceStub },
        { provide: AuthService, useClass: AuthServiceStub },
      ],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(StepPostprocessComponent);
    component = fixture.componentInstance;
    de = fixture.debugElement;
    fixture.detectChanges();
    router = TestBed.inject(Router);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
