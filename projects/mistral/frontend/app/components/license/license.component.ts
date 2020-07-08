import {Component, OnInit} from '@angular/core';
import {NotificationService} from '@rapydo/services/notification';
import {DataService} from "@app/services/data.service";
import {ColumnMode} from '@swimlane/ngx-datatable';
import {NgxSpinnerService} from 'ngx-spinner';

@Component({
    selector: 'license',
    templateUrl: './license.component.html'
})
export class LicenseComponent implements OnInit {
    title = 'titolo';
    data;
    ColumnMode = ColumnMode;

    constructor(private dataService: DataService,
                private notify: NotificationService,
                private spinner: NgxSpinnerService) {
        
	console.log('constructor');
    }

    ngOnInit() {
        this.spinner.show();

        this.dataService.getDatasetsLicense().subscribe(
        //this.dataService.getDatasets().subscribe(
            response => {
                this.data = response;
                console.log('Data loaded', this.data);
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

