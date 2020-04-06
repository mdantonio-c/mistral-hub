import {Component, Output, EventEmitter, ChangeDetectorRef} from '@angular/core';
import {saveAs as importedSaveAs} from "file-saver";
import {BasePaginationComponent} from '@rapydo/components/base.pagination.component';

import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import {ApiService} from '@rapydo/services/api';
import {AuthService} from '@rapydo/services/auth';
import {NotificationService} from '@rapydo/services/notification';
import {FormlyService} from '@rapydo/services/formly'
import {DataService} from "@app/services/data.service";
import {environment} from '@rapydo/../environments/environment';

@Component({
    selector: 'app-requests',
    templateUrl: './requests.component.html'
})
export class RequestsComponent extends BasePaginationComponent {
    expanded: any = {};
    @Output() onLoad: EventEmitter<null> = new EventEmitter<null>();

    constructor(
        protected api: ApiService,
        protected auth: AuthService,
        protected notify: NotificationService,
        protected modalService: NgbModal,
        protected formly: FormlyService,
        protected changeDetectorRef: ChangeDetectorRef,
        public dataService: DataService,
    ) {
        super(api, auth, notify, modalService, formly, changeDetectorRef);
        this.init("request");

        this.server_side_pagination = true;
        this.endpoint = 'requests';
        this.counter_endpoint = 'requests';
        this.initPaging(20);
        this.list();
    }

    ngOnInit() {
        // make sure the derived variables have been loaded
        this.dataService.getDerivedVariables().subscribe();
    }

    list() {
        this.get(this.endpoint);
        this.onLoad.emit();
    }

    remove(requestID) {
        console.log(`remove this request ${requestID}`);
        return this.delete('requests', requestID);
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

    private getFileURL(filename) {
        const source_url = `${environment.apiUrl}/data/${filename}`;
        let token = this.auth.getToken();
        return source_url + '&access_token=' + token;
    }

    downloadByUrl(filename) {
        // const downloadUrl = "http://localhost/app/custom/assets/images/cropped-logo-mistral-bianco-web.png";
        // const downloadUrl = this.getFileURL(filename);
        const downloadUrl = "https://imc-dev.hpc.cineca.it/api/images/cf2b1137-6a8f-4dab-b17a-f92f565cfd6b/content?type=image&access_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJ1c2VyX2lkIjoiNmUwYzNhZDEtMTZmYy00MzI1LWEwODctNDkxNzQ4NzA2ZGU0IiwianRpIjoiYmM1OGE3MjctZGI1OS00NmQ4LTljNzctZTdlNmFkODM2YWQxIiwiaWF0IjoxNTg2MTg0NjkyLCJuYmYiOjE1ODYxODQ2OTIsImV4cCI6MTU4ODc3NjY5Mn0.6E68zxDb_i9qFaCHNAj-7-YCCrFr19TfuZehpkeTP0iM6W0ttdrFh_NPXWYT003oEiS86eTdGDViFylbJN6HmA";

        var link = document.createElement('a');
        link.href = downloadUrl;
        // link.download = downloadUrl.substr(downloadUrl.lastIndexOf('/') + 1);
        link.download = filename;
        link.target = "_blank"; // ignored if download works properly
        link.style.visibility = "hidden";
        link.click();
    }

    toggleExpandRow(row) {
        this.table.rowDetail.toggleExpandRow(row);
    }

}
