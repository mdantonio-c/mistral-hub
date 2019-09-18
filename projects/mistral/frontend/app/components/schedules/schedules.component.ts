import {Component, ChangeDetectorRef} from '@angular/core';
import {saveAs as importedSaveAs} from "file-saver";
import {BasePaginationComponent} from '/rapydo/src/app/components/base.pagination.component';

import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import {ApiService} from '/rapydo/src/app/services/api';
import {AuthService} from '/rapydo/src/app/services/auth';
import {NotificationService} from '/rapydo/src/app/services/notification';
import {FormlyService} from '/rapydo/src/app/services/formly'
import {DataService} from "../../services/data.service";

@Component({
    selector: 'app-schedules',
    templateUrl: './schedules.component.html',
    styleUrls: ['./schedules.component.css']
})
export class SchedulesComponent extends BasePaginationComponent {
    expanded: any = {};
    loadingLast = false;    // it should be bound to the single row!

    constructor(
        protected api: ApiService,
        protected auth: AuthService,
        protected notify: NotificationService,
        protected modalService: NgbModal,
        protected formly: FormlyService,
        protected changeDetectorRef: ChangeDetectorRef,
        private dataService: DataService,
    ) {
        super(api, auth, notify, modalService, formly, changeDetectorRef);
        this.init('schedule');

        this.server_side_pagination = true;
        this.endpoint = 'schedules';
        this.counter_endpoint = 'schedules';
        this.initPaging(20);
        this.list();
    }

    list() {
        return this.get(this.endpoint);
    }

    loadLastSubmission(row) {
        this.loadingLast = true;
        this.dataService.getLastScheduledRequest(row.id).subscribe(
            response => {
                row.last = response.Response.data;
                console.log(row.last);
                // TODO what about the requests count? should be updated
                //row.requests_count = response.Meta.elements;
            },
            (error) => {
                this.notify.showError('Unable to load the last submission');
                // show reason
                this.notify.extractErrors(error.error.Response, this.notify.ERROR);
            }
        ).add(() => {
            this.loadingLast = false;
        });
    }

    toggleExpandRow(row, flag) {
        if (flag === 'open') {
            // load last request
            this.loadLastSubmission(row);
        }
        // open or close schedule details
        this.table.rowDetail.toggleExpandRow(row);
    }

    remove(scheduleID) {
        console.log(`remove this schedule ${scheduleID}`);
        return this.delete('schedules', scheduleID);
    }

    download(filename) {
        this.dataService.downloadData(filename).subscribe(
            resp => {
                const contentType = resp.headers['content-type'] || 'application/octet-stream';
                const blob = new Blob([resp.body], {type: contentType});
                importedSaveAs(blob, filename);
            },
            error => {
                this.notify.showError(`Unable to download file: ${filename}`);
            }
        );
    }

    toggleActiveState(row) {
        const scheduleId = row.id;
        const currState = row.enabled;
        const action = (!currState) ? 'Activate' : 'Deactivate';
        console.log(`${action} schedule [ID:${scheduleId}]. Current state: ${currState}`);
        this.dataService.toggleScheduleActiveState(scheduleId, !currState).subscribe(
            response => {
                console.log(response);
                row.enabled = !currState;
            },
            error => {
                this.notify.extractErrors(error.error.Response, this.notify.ERROR);
            }
        );
    }
}
