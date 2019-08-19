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

    @ViewChild('dataSize', { static: false }) public dataSize: TemplateRef<any>;
	@ViewChild('submissionDate', { static: false }) public submissionDate: TemplateRef<any>;
	@ViewChild('dataStatus', { static: false }) public dataStatus: TemplateRef<any>;
	@ViewChild('controlsCell', { static: false }) public controlsCell: TemplateRef<any>;
	@ViewChild('emptyHeader', { static: false }) public emptyHeader: TemplateRef<any>;

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

    ngAfterViewInit(): void {
		this.columns = [
	        {name: 'Product', prop: "name", flexGrow: 2},
	        {name: 'Submission date', prop: "submission_date", flexGrow: 1, cellTemplate: this.submissionDate},
	        {name: 'Size', prop: "size", flexGrow: 0.5, cellTemplate: this.dataSize},
	        {name: 'Status', prop: "status", flexGrow: 0.5, cellTemplate: this.dataStatus},
			{name: 'controls', prop: 'controls', cellTemplate: this.controlsCell, headerTemplate: this.emptyHeader, flexGrow: 0.2},
		];
	}

}
