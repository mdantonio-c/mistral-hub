import {Component, Output, EventEmitter, Injector} from '@angular/core';
import {saveAs as importedSaveAs} from "file-saver";
import {BasePaginationComponent} from '@rapydo/components/base.pagination.component';

import {DataService} from "@app/services/data.service";
import {environment} from '@rapydo/../environments/environment';

export interface Request {

}

@Component({
    selector: 'app-requests',
    templateUrl: './requests.component.html'
})
export class RequestsComponent extends BasePaginationComponent<Request> {
    expanded: any = {};
    @Output() onLoad: EventEmitter<null> = new EventEmitter<null>();

    constructor(protected injector: Injector, public dataService: DataService) {
        super(injector);
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
        return source_url + '?access_token=' + token;
    }

    downloadByUrl(filename) {
        const downloadUrl = this.getFileURL(filename);
        var link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        link.style.visibility = "hidden";
        link.click();
    }

    toggleExpandRow(row) {
        this.table.rowDetail.toggleExpandRow(row);
    }

}
