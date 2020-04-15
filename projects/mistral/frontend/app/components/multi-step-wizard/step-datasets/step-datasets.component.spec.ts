import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {RouterTestingModule} from '@angular/router/testing';
import {Router} from '@angular/router';
import {ReactiveFormsModule, FormBuilder} from '@angular/forms';

import {NotificationService} from '@rapydo/services/notification';
import {StepDatasetsComponent} from './step-datasets.component';
import {FormDataService} from "../../../services/formData.service";
import {FormDataServiceStub} from "../../../services/formData.service.stub";

class NotificationServiceStub {
}

describe('StepDatasetsComponent', () => {
    let component: StepDatasetsComponent;
    let fixture: ComponentFixture<StepDatasetsComponent>;
    let router: Router;
    // create new instance of FormBuilder
    const formBuilder: FormBuilder = new FormBuilder();

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [StepDatasetsComponent],
            imports: [
                ReactiveFormsModule,
                RouterTestingModule.withRoutes([]),
            ],
            providers: [
                {provide: FormBuilder, useValue: formBuilder },
                {provide: FormDataService, useClass: FormDataServiceStub},
                {provide: NotificationService, useClass: NotificationServiceStub}
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(StepDatasetsComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
        router = TestBed.inject(Router);
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
