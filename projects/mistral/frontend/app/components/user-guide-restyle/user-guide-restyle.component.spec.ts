import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UserGuideRestyleComponent } from './user-guide-restyle.component';

describe('UserGuideRestyleComponent', () => {
  let component: UserGuideRestyleComponent;
  let fixture: ComponentFixture<UserGuideRestyleComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ UserGuideRestyleComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UserGuideRestyleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
