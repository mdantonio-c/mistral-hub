import {Component, OnInit} from '@angular/core';
import {DataService} from "../../services/data.service";
import {NotificationService} from '@rapydo/services/notification';
import {ColumnMode} from '@swimlane/ngx-datatable';
import {NgxSpinnerService} from 'ngx-spinner';


@Component({
    selector: 'license',
    templateUrl: './license.component.html'
})
export class LicenseComponent implements OnInit {
    data;
    ColumnMode = ColumnMode;

    constructor(private dataService: DataService,
                private notify: NotificationService,
                private spinner: NgxSpinnerService) {
    }

    ngOnInit() {
        this.spinner.show();

        this.dataService.getDatasets(true).subscribe(
            response => {
                this.data = response;
                // console.log('Data loaded', this.data);
                if (this.data.length === 0) {
                    this.notify.showWarning("Unexpected result. The list of datasets is empty.");
                }
            },
            error => {
                this.notify.showError(error);
            }).add(() => {
            this.spinner.hide();
        });
    }

}

