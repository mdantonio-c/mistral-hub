import {ComponentFixture, TestBed} from '@angular/core/testing';
import {RouterTestingModule} from '@angular/router/testing';
import {Router} from '@angular/router';
import {ReactiveFormsModule, FormBuilder} from '@angular/forms';
import {NgbModule} from '@ng-bootstrap/ng-bootstrap';
import {DebugElement, Input, Component} from '@angular/core';

import {NotificationService} from '@rapydo/services/notification';
import {StepPostprocessComponent} from './step-postprocess.component';
import {FormDataService} from "../../../services/formData.service";
import {FormDataServiceStub} from "../../../services/formData.service.stub";
import {DataServiceStub} from "../../../services/data.service.stub";
import {DataService} from "../../../services/data.service";

class NotificationServiceStub {
}

@Component({
    selector: 'step-postprocess-map',
    template: '<div class="container" style="margin-top: 30px;"></div>'
})
class StubStepPostprocessMapComponent {
    @Input() formGroup;
	// ilon, ilat, flon, flat
	@Input() ilonControl;
	@Input() ilatControl;
	@Input() flonControl;
	@Input() flatControl;
}

describe('StepPostprocessComponent', () => {
    let component: StepPostprocessComponent;
    let fixture: ComponentFixture<StepPostprocessComponent>;
    let de: DebugElement;
    let router: Router;
    // create new instance of FormBuilder
    const formBuilder: FormBuilder = new FormBuilder();

    beforeEach(() => {
        TestBed.configureTestingModule({
            declarations: [StepPostprocessComponent, StubStepPostprocessMapComponent],
            imports: [
                ReactiveFormsModule,
                RouterTestingModule.withRoutes([]),
                NgbModule
            ],
            providers: [
                {provide: FormBuilder, useValue: formBuilder},
                {provide: FormDataService, useClass: FormDataServiceStub},
                {provide: DataService, useClass: DataServiceStub},
                {provide: NotificationService, useClass: NotificationServiceStub}
            ]
        })
            .compileComponents();
    });

    beforeEach(() => {
        fixture = TestBed.createComponent(StepPostprocessComponent);
        component = fixture.componentInstance;
        de = fixture.debugElement;
        fixture.detectChanges();
        router = TestBed.inject(Router);
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
