import {Component, ElementRef, Injector} from '@angular/core';
import {saveAs as importedSaveAs} from "file-saver";

import {BasePaginationComponent} from '@rapydo/components/base.pagination.component';

import {DataService} from "@app/services/data.service";

@Component({
    selector: 'app-schedules',
    templateUrl: './schedules.component.html'
})
export class SchedulesComponent extends BasePaginationComponent {
    expanded: any = {};
    loadingLast = false;    // it should be bound to the single row!

    constructor(protected injector: Injector, public dataService: DataService, private el: ElementRef) {
        super(injector);
        this.init('schedule');

        this.server_side_pagination = true;
        this.endpoint = 'schedules';
        this.counter_endpoint = 'schedules';
        this.initPaging(20);
        this.list();
    }

    ngOnInit() {
        // make sure the derived variables have been loaded
        this.dataService.getDerivedVariables().subscribe();
    }

    list() {
        return this.get(this.endpoint);
    }

    loadLastSubmission(row) {
        this.loadingLast = true;
        this.dataService.getLastScheduledRequest(row.id).subscribe(
            response => {
                row.last = response.Response.data;
                // what about the requests count? should be updated
                row.requests_count = response.Meta.total;
            },
            (error) => {
                if (error.status === 404) {
                    // No successful request is available for this schedule yet
                    // do nothing
                } else {
                    this.notify.showError('Unable to load the last submission');
                    // show reason
                    this.notify.extractErrors(error.error.Response, this.notify.ERROR);
                }
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

    toggleActiveState($event: MouseEvent, row) {
        // stop click event and propagation
        $event.stopPropagation();

        const action = (!row.enabled) ? 'Activate' : 'Deactivate';
        console.log(`${action} schedule [ID:${row.id}]. Current state: ${row.enabled}`);
        this.dataService.toggleScheduleActiveState(row.id, !row.enabled).subscribe(
            response => {
                row.enabled = response.data.enabled;
                let toggleBtn = this.el.nativeElement.querySelector('#act-btn-'+row.id);
                (row.enabled) ?
                    toggleBtn.classList.add('active') :
                    toggleBtn.classList.remove('active')
            },
            error => {
                this.notify.extractErrors(error, this.notify.ERROR);
            }
        );
    }
}
