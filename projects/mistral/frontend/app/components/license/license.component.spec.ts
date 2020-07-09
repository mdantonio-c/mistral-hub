import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {NotificationService} from '@rapydo/services/notification';
import {LicenseComponent} from './step-datasets.component';
import {DataService} from "../../../services/data.service";

class NotificationServiceStub {
}

describe('LicenseComponent', () => {
    let component: StepDatasetsComponent;
    let fixture: ComponentFixture<LicenseComponent>;
    
    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [LicenseComponent],
            imports: [
                
            ],
            providers: [
                {provide: dataService, useClass: dataServiceStub},
                {provide: NotificationService, useClass: NotificationServiceStub}
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(LicenseComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
