import { async, ComponentFixture, TestBed } from "@angular/core/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { CUSTOM_ELEMENTS_SCHEMA } from "@angular/core";
import { RouterTestingModule } from "@angular/router/testing";
import { Router } from "@angular/router";
import { ReactiveFormsModule, FormBuilder } from "@angular/forms";
import { NgbModule } from "@ng-bootstrap/ng-bootstrap";
import { DatePipe } from "@angular/common";
import { NgxSpinnerModule } from "ngx-spinner";

import { NotificationService } from "@rapydo/services/notification";
import { StepFiltersComponent } from "./step-filters.component";
import { FormDataService } from "../../../services/formData.service";
import { FormDataServiceStub } from "../../../services/formData.service.stub";
import { FormatDatePipe } from "../../../pipes/format-date.pipe";
import { DisableControlDirective } from "@app/directives/disable-control";

import { BytesPipe } from "@rapydo/pipes/pipes";
import { ArkimetService } from "../../../services/arkimet.service";

class NotificationServiceStub {}

describe("StepFiltersComponent", () => {
  let component: StepFiltersComponent;
  let fixture: ComponentFixture<StepFiltersComponent>;
  let router: Router;
  // create new instance of FormBuilder
  const formBuilder: FormBuilder = new FormBuilder();

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [
        StepFiltersComponent,
        FormatDatePipe,
        BytesPipe,
        DisableControlDirective,
      ],
      imports: [
        BrowserAnimationsModule,
        ReactiveFormsModule,
        RouterTestingModule.withRoutes([]),
        NgxSpinnerModule,
        NgbModule,
      ],
      schemas: [CUSTOM_ELEMENTS_SCHEMA],
      providers: [
        DatePipe,
        ArkimetService,
        { provide: FormBuilder, useValue: formBuilder },
        { provide: FormDataService, useClass: FormDataServiceStub },
        { provide: NotificationService, useClass: NotificationServiceStub },
      ],
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(StepFiltersComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    router = TestBed.inject(Router);
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
