import {Component, DebugElement} from '@angular/core';
import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {NgxDatatableModule} from '@swimlane/ngx-datatable';
import {MomentModule} from 'ngx-moment';
import {NgbModule} from '@ng-bootstrap/ng-bootstrap';
import {ConfirmationPopoverModule} from 'angular-confirmation-popover';
import {Observable} from 'rxjs/Rx';
import {HttpClient} from '@angular/common/http';
import {ToastrModule} from 'ngx-toastr';

import {SchedulesComponent} from './schedules.component';
import {BytesPipe} from '@rapydo/pipes/pipes';
import {AuthService} from '@rapydo/services/auth';
import {NotificationService} from '@rapydo/services/notification';
import {FormlyService} from '@rapydo/services/formly'
import {ApiService} from '@rapydo/services/api';
import {DataService} from "../../services/data.service";
import {DataServiceStub} from "../../services/data.service.stub";
import {
    MockSchedulesNoDataResponse,
    MockSchedulesResponse,
    MockSchedulesTotalResponse
} from "../../services/data.mock";


@Component({
    selector: 'loading',
    template: '<div class=\'loader\'></div>'
})
class StubLoadingComponent {
}
class ApiServiceStub extends ApiService {
    constructor() {
        super({} as HttpClient);
    }

    get(endpoint: string, id = "", data = {}, options = {}) {
        if (data['get_total'] === true) {
            return Observable.of(MockSchedulesTotalResponse.Response);
        } else {
            return Observable.of(MockSchedulesResponse.Response);
        }
    }
}
class AuthServiceStub {}
class FormlyServiceStub {}

describe('SchedulesComponent', () => {
    let component: SchedulesComponent;
    let fixture: ComponentFixture<SchedulesComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [
                SchedulesComponent,
                StubLoadingComponent,
                BytesPipe
            ],
            imports: [
                NgxDatatableModule,
                MomentModule,
                NgbModule,
                ConfirmationPopoverModule.forRoot(
                    // set defaults here
                    {
                        confirmButtonType: 'danger',
                        appendToBody: true
                    }
                ),
                ToastrModule.forRoot({
                    maxOpened: 5,
                    preventDuplicates: true,
                    countDuplicates: true,
                    resetTimeoutOnDuplicate: true,
                    closeButton: true,
                    enableHtml: true,
                    progressBar: true,
                    progressAnimation: 'increasing',
                    positionClass: 'toast-bottom-right'
                })
            ],
            providers: [
                NotificationService,
                {provide: DataService, useClass: DataServiceStub},
                {provide: ApiService, useClass: ApiServiceStub},
                {provide: AuthService, useClass: AuthServiceStub},
                {provide: FormlyService, useClass: FormlyServiceStub}
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(SchedulesComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
