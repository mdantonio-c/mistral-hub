import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {StorageUsageComponent} from './storage-usage.component';
import {BytesPipe} from '@rapydo/pipes/pipes';
import {DataService} from "../../../services/data.service";
import {NotificationService} from '@rapydo/services/notification';
import {DataServiceStub} from "../../../services/data.service.stub";

class NotificationServiceStub {}

describe('StorageUsageComponent', () => {
    let component: StorageUsageComponent;
    let fixture: ComponentFixture<StorageUsageComponent>;
    let el: HTMLElement;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            declarations: [StorageUsageComponent, BytesPipe],
            providers: [
                {provide: DataService, useClass: DataServiceStub},
                {provide: NotificationService, useClass: NotificationServiceStub}
            ]
        })
            .compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(StorageUsageComponent);
        component = fixture.componentInstance;
        el = fixture.debugElement.nativeElement;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
