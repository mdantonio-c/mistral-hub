import {Component, ViewChild, TemplateRef} from '@angular/core';
import {BasePaginationComponent} from '/rapydo/src/app/components/base.pagination.component';

import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import {ApiService} from '/rapydo/src/app/services/api';
import {AuthService} from '/rapydo/src/app/services/auth';
import {NotificationService} from '/rapydo/src/app/services/notification';
import {FormlyService} from '/rapydo/src/app/services/formly'

@Component({
    selector: 'app-requests',
    templateUrl: './requests.component.html'
})
export class RequestsComponent extends BasePaginationComponent {
    @ViewChild('myTable', { static: false }) table: any;
    expanded: any = {};

    constructor(
        protected api: ApiService,
        protected auth: AuthService,
        protected notify: NotificationService,
        protected modalService: NgbModal,
        protected formly: FormlyService,
    ) {
        super(api, auth, notify, modalService, formly);
        this.init("group");

		this.server_side_pagination = true;
		this.endpoint = 'requests';
		this.counter_endpoint = 'requests';
		this.initPaging(20);
		this.list();
    }

    list() {
        let user = this.auth.getUser();
        let params = {'uuid': user.uuid};
		return this.get(this.endpoint, params);
	}

	download(filename) {
      // TODO
      console.log(`download ${filename}`);
    }

    toggleExpandRow(row) {
        this.table.rowDetail.toggleExpandRow(row);
    }

    onDetailToggle(event) {
        console.log('Detail Toggled', event);
    }

}
