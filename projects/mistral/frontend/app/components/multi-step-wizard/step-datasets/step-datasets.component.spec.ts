import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { StepDatasetsComponent } from './step-datasets.component';

describe('StepDatasetsComponent', () => {
    let component: StepDatasetsComponent;
    let fixture: ComponentFixture<StepDatasetsComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [StepDatasetsComponent]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(StepDatasetsComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});