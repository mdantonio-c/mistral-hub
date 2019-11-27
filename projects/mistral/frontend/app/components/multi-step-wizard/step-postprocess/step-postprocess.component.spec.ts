import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {RouterTestingModule} from '@angular/router/testing';
import {Router} from '@angular/router';
import {ReactiveFormsModule, FormBuilder} from '@angular/forms';
import {NgbModule} from '@ng-bootstrap/ng-bootstrap';
import {DatePipe} from '@angular/common';

import {NotificationService} from '@rapydo/services/notification';
import { StepPostprocessComponent } from './step-postprocess.component';
import {FormDataService} from "../../../services/formData.service";
import {FormDataServiceStub} from "../../../services/formData.service.stub";
import {DataServiceStub} from "../../../services/data.service.stub";
import {DataService} from "../../../services/data.service";

class NotificationServiceStub {
}

describe('StepPostprocessComponent', () => {
    let component: StepPostprocessComponent;
    let fixture: ComponentFixture<StepPostprocessComponent>;
    let router: Router;
    // create new instance of FormBuilder
    const formBuilder: FormBuilder = new FormBuilder();

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [StepPostprocessComponent],
            imports: [
                ReactiveFormsModule,
                RouterTestingModule.withRoutes([]),
                NgbModule.forRoot()
            ],
            providers: [
                DatePipe,
                {provide: FormBuilder, useValue: formBuilder},
                {provide: FormDataService, useClass: FormDataServiceStub},
                {provide: DataService, useClass: DataServiceStub},
                {provide: NotificationService, useClass: NotificationServiceStub}
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(StepPostprocessComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
        router = TestBed.get(Router);
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
