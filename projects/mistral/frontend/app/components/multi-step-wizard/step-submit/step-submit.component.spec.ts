import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { StepSubmitComponent } from './step-submit.component';

describe('StepSubmitComponent', () => {
    let component: StepSubmitComponent;
    let fixture: ComponentFixture<StepSubmitComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [StepSubmitComponent]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(StepSubmitComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});