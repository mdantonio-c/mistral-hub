import {Component, DebugElement} from '@angular/core';
import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {ApiService} from '@rapydo/services/api';
import {NotificationService} from '@rapydo/services/notification';
import {DataComponent} from './data.component';

@Component({
    selector: 'loading',
    template: '<div class=\'loader\'></div>'
})
class StubLoadingComponent {}

@Component({
    selector: 'multi-step-wizard',
    template: '<div style="text-align: center">multi step wizard</div>'
})
class StubMultiStepWizardComponent {}

class ApiServiceStub {}
class NotificationServiceStub {}

describe('DataComponent', () => {
    let component: DataComponent;
    let fixture: ComponentFixture<DataComponent>;
    let de: DebugElement;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [
                DataComponent,
                StubLoadingComponent,
                StubMultiStepWizardComponent
            ],
            providers: [
                {provide: ApiService, useClass: ApiServiceStub},
                {provide: NotificationService, userClass: NotificationServiceStub}
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(DataComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
