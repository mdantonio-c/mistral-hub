import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { StepPostprocessComponent } from './step-postprocess.component';

describe('StepPostprocessComponent', () => {
    let component: StepPostprocessComponent;
    let fixture: ComponentFixture<StepPostprocessComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [StepPostprocessComponent]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(StepPostprocessComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});