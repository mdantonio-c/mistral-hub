import {Component, DebugElement} from '@angular/core';
import { Injectable } from '@angular/core';
import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {NgxDatatableModule} from '@swimlane/ngx-datatable';
import {MomentModule} from 'ngx-moment';
import {NgbModule} from '@ng-bootstrap/ng-bootstrap';
import {ConfirmationPopoverModule} from 'angular-confirmation-popover';
import {Observable} from 'rxjs/Rx';
import {HttpClient} from '@angular/common/http';
import {ToastrModule} from 'ngx-toastr';

import {LicenseComponent} from './license.component';
import {BytesPipe} from '@rapydo/pipes/pipes';
import {NotificationService} from '@rapydo/services/notification';
import {ProjectOptions} from '@app/custom.project.options';
import {FormlyService} from '@rapydo/services/formly'
import {ApiService} from '@rapydo/services/api';
import {DataService} from "../../services/data.service";
import {DataServiceStub} from "../../services/data.service.stub";
import {MockLicenseNoDataResponse, MockLicenseResponse} from "../../services/data.mock";

@Component({
    selector: 'loading',
    template: '<div class=\'loader\'></div>'
})
class StubLoadingComponent {
}

@Injectable()
class ApiServiceStub extends ApiService {
    constructor() {
        super({} as HttpClient);
    }

    get(endpoint: string, id = "", data = {}, options = {}) {
        return Observable.of(MockLicenseResponse);
    }
}
class FormlyServiceStub {}

describe('LicenseComponent', () => {
    let component: LicenseComponent;
    let fixture: ComponentFixture<LicenseComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [
                LicenseComponent,
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
                ProjectOptions,
                {provide: DataService, useClass: DataServiceStub},
                {provide: ApiService, useClass: ApiServiceStub},
                {provide: FormlyService, useClass: FormlyServiceStub}
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
