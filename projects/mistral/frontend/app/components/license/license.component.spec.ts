import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

import {LicenseComponent} from './license.component';
import {DataService} from "../../services/data.service";
import {DataServiceStub} from "../../services/data.service.stub";

import {NotificationService} from '@rapydo/services/notification';
import {NgxSpinnerModule} from "ngx-spinner";
import {NgxDatatableModule} from '@swimlane/ngx-datatable';


class NotificationServiceStub {
}

describe('LicenseComponent', () => {
    let component: LicenseComponent;
    let fixture: ComponentFixture<LicenseComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [LicenseComponent],
            imports: [
                BrowserAnimationsModule,
                NgxSpinnerModule,
                NgxDatatableModule,
            ],
            providers: [
                {provide: DataService, useClass: DataServiceStub},
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
