import {Component, Input} from '@angular/core';
import {FormBuilder, FormGroup, Validators} from '@angular/forms';
import {NgForm, NgControl} from '@angular/forms';
import {NgbDate, NgbCalendar, NgbDateParserFormatter} from '@ng-bootstrap/ng-bootstrap';
import {ObsFilter, ObsService} from "../services/obs.service";
import {NgxSpinnerService} from 'ngx-spinner';
import {NotificationService} from '@rapydo/services/notification';
import {saveAs as importedSaveAs} from "file-saver";

@Component({
    selector: 'app-obs-download',
    templateUrl: './obs-download.component.html',
    styleUrls: ['./obs-download.component.css']
})
export class ObsDownloadComponent {

    @Input() selectedDate;
    @Input() filter: ObsFilter;

    hoveredDate: NgbDate | null = null;

    fromDate: NgbDate | null;
    toDate: NgbDate | null;
    maxDate: NgbDate | null;

    allFormats: string[] = ['JSON', 'BUFR'];
    model: any = {
        format: 'JSON',
        fromDate: null,
        toDate: null
    };

    constructor(
        private obsService: ObsService,
        private notify: NotificationService,
        private spinner: NgxSpinnerService,
        private calendar: NgbCalendar,
        public formatter: NgbDateParserFormatter) {
        this.maxDate = calendar.getToday();
        this.fromDate = calendar.getToday();
        this.toDate = calendar.getNext(calendar.getToday(), 'd', 10);
    }

    onDateSelection(date: NgbDate) {
        if (!this.fromDate && !this.toDate) {
            this.fromDate = date;
        } else if (this.fromDate && !this.toDate && date && date.after(this.fromDate)) {
            this.toDate = date;
        } else {
            this.toDate = null;
            this.fromDate = date;
        }
    }

    isHovered(date: NgbDate) {
        return this.fromDate && !this.toDate && this.hoveredDate && date.after(this.fromDate) && date.before(this.hoveredDate);
    }

    isInside(date: NgbDate) {
        return this.toDate && date.after(this.fromDate) && date.before(this.toDate);
    }

    isRange(date: NgbDate) {
        return date.equals(this.fromDate) || (this.toDate && date.equals(this.toDate)) || this.isInside(date) || this.isHovered(date);
    }

    validateInput(currentValue: NgbDate | null, input: string): NgbDate | null {
        const parsed = this.formatter.parse(input);
        return parsed && this.calendar.isValid(NgbDate.from(parsed)) ? NgbDate.from(parsed) : currentValue;
    }

    download() {
        this.model.fromDate = new Date(this.fromDate.year, this.fromDate.month - 1, this.fromDate.day);
        this.model.toDate = new Date(this.toDate.year, this.toDate.month - 1, this.toDate.day);
        console.log('Download data', this.model);
        console.log('Download with filter', this.filter);
        this.spinner.show();
        let fileExtension = '';
        switch (this.model.format) {
            case "BUFR":
                fileExtension = ".bufr";
                break;
            case "JSON":
                fileExtension = ".jsonl";
        }
        let basename = `${this.filter.product}_` +
            `${this.fromDate.year}${this.fromDate.month}${this.fromDate.day}-` +
            `${this.toDate.year}${this.toDate.month}${this.toDate.day}`
        this.obsService.download(this.filter,
            this.model.fromDate,
            this.model.toDate,
            this.model.format).subscribe(
                blob => {
                    importedSaveAs(blob,`${basename}${fileExtension}`);
                },
                error => {
                    this.notify.showError(error);
                }
            ).add(() => {
                this.spinner.hide();
            });
    }
}
