import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { StepFiltersComponent } from './step-filters.component';

describe('StepFiltersComponent', () => {
    let component: StepFiltersComponent;
    let fixture: ComponentFixture<StepFiltersComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [StepFiltersComponent]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(StepFiltersComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});