import { async, ComponentFixture, TestBed } from "@angular/core/testing";
import { Component, DebugElement } from "@angular/core";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { By } from "@angular/platform-browser";
import { NgbModule } from "@ng-bootstrap/ng-bootstrap";

import { DashboardComponent } from "./dashboard.component";
// import { AppModule } from '@rapydo/app.module';

@Component({
  selector: "app-requests",
  template: "<p>requests template</p>",
})
class StubRequestsComponent {}

@Component({
  selector: "app-schedules",
  template: "<p>schedules template</p>",
})
class StubSchedulesComponent {}

@Component({
  selector: "app-storage-usage",
  template: "<div>storage-usage</div>",
})
class StubStorageUsageComponent {}

@Component({
  selector: "app-request-hourly-report",
  template: "<div>hourly-report</div>",
})
class StubHourlyReportComponent {}

describe("DashboardComponent", () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;
  let de: DebugElement;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      // imports: [AppModule]
      declarations: [
        DashboardComponent,
        StubStorageUsageComponent,
        StubRequestsComponent,
        StubSchedulesComponent,
        StubHourlyReportComponent,
      ],
      imports: [BrowserAnimationsModule, NgbModule],
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    de = fixture.debugElement;
    fixture.detectChanges();
  });

  it("should create the component", () => {
    expect(component).toBeTruthy();
  });

  it("should render the template", () => {
    // expect(de.query(By.css('.mdl-cell')).properties.innerHTML).not.toContain('Loading');
    expect(de.queryAll(By.directive(StubRequestsComponent)).length).toEqual(1);
  });
});
