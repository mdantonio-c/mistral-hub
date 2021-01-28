import { async, ComponentFixture, TestBed } from "@angular/core/testing";
import { RequestHourlyReportComponent } from "./request-hourly-report.component";
import { BytesPipe } from "@rapydo/pipes/bytes";
import { DataService } from "../../../services/data.service";
import { NotificationService } from "@rapydo/services/notification";
import { DataServiceStub } from "../../../services/data.service.stub";

class NotificationServiceStub {}

describe("RequestHourlyReportComponent", () => {
  let component: RequestHourlyReportComponent;
  let fixture: ComponentFixture<RequestHourlyReportComponent>;
  let el: HTMLElement;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [RequestHourlyReportComponent, BytesPipe],
      providers: [
        { provide: DataService, useClass: DataServiceStub },
        { provide: NotificationService, useClass: NotificationServiceStub },
      ],
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(RequestHourlyReportComponent);
    component = fixture.componentInstance;
    el = fixture.debugElement.nativeElement;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
