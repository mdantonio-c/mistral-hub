import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DatasetsRestyleComponent } from './datasets-restyle.component';

describe('DatasetsRestyleComponent', () => {
  let component: DatasetsRestyleComponent;
  let fixture: ComponentFixture<DatasetsRestyleComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DatasetsRestyleComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DatasetsRestyleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
