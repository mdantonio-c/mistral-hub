import { async, ComponentFixture, TestBed } from "@angular/core/testing";

import { ObsServiceComponent } from "./obs.service.component";

describe("ObsServiceComponent", () => {
  let component: ObsServiceComponent;
  let fixture: ComponentFixture<ObsServiceComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ObsServiceComponent],
    }).compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ObsServiceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
