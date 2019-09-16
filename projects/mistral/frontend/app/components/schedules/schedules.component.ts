import {Component, ViewChild, TemplateRef} from '@angular/core';
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
    @ViewChild('mySchedulesTable', {static: false}) table: any;
    expanded: any = {};

    constructor(
        protected api: ApiService,
        protected auth: AuthService,
        protected notify: NotificationService,
        protected modalService: NgbModal,
        protected formly: FormlyService,
        private dataService: DataService
    ) {
        super(api, auth, notify, modalService, formly);
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

    toggleExpandRow(row) {
        this.table.rowDetail.toggleExpandRow(row);
    }

    toggleActiveState(row) {
        console.log(row);
        console.log(`Activate/Deactivate schedule [ID:${row.id}]`);
    }
}
