import { Component, Input, OnInit } from "@angular/core";
import {
  NgbActiveModal,
  NgbDate,
  NgbDateStruct,
  NgbCalendar,
  NgbDateParserFormatter,
} from "@ng-bootstrap/ng-bootstrap";
import { ObsFilter } from "@app/types";
import { User } from "@rapydo/types";
import { ObsService } from "../services/obs.service";
import { NgxSpinnerService } from "ngx-spinner";
import { NotificationService } from "@rapydo/services/notification";
import { AuthService } from "@rapydo/services/auth";
import { environment } from "@rapydo/../environments/environment";
import { saveAs as importedSaveAs } from "file-saver-es";
import * as moment from "moment";

const LAST_DAYS = +environment.CUSTOM.LASTDAYS || 10;

@Component({
  selector: "app-obs-download",
  templateUrl: "./obs-download.component.html",
  styleUrls: ["./obs-download.component.css"],
})
export class ObsDownloadComponent implements OnInit {
  @Input() filter: ObsFilter;
  hoveredDate: NgbDate | null = null;

  fromDate: NgbDate | null;
  toDate: NgbDate | null;
  maxDate: NgbDate | null;
  minDate: NgbDateStruct | null;
  showWarning: boolean;
  maxDays: number;
  isAuthenticated: boolean | null;
  downloadMessage: string =
    "You can select a single date and then click Download to get the data. Or you can select two different dates to identify a range of days and then click Download.";
  allFormats: string[] = ["JSON", "BUFR"];
  model: any = {
    format: "JSON",
    fromDate: null,
    toDate: null,
  };
  private user: User | null;

  constructor(
    private authService: AuthService,
    public activeModal: NgbActiveModal,
    private obsService: ObsService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private calendar: NgbCalendar,
    public formatter: NgbDateParserFormatter,
  ) {
    this.maxDate = calendar.getToday();
    this.fromDate = calendar.getToday();
    this.toDate = null; // calendar.getNext(calendar.getToday(), "d", 10);
    this.showWarning = false;
    this.maxDays = null;
    this.isAuthenticated = false;
  }

  ngOnInit() {
    /*if (this.filter && this.filter.reftime) {
      //set the time to all day
      this.filter.time = [0, 23];
      this.setDateRange(this.filter.reftime);
    }*/
    this.user = this.authService.getUser();
    if (!this.user) {
      this.isAuthenticated = false;
      this.applyMinDate();
      this.maxDays = 3;
    } else {
      this.isAuthenticated = true;
      this.maxDays = 10;
    }
  }
  dateDiffInDays(from: NgbDate, to: NgbDate): number {
    const fromDate = new Date(from.year, from.month - 1, from.day);
    const toDate = new Date(to.year, to.month - 1, to.day);
    const diffTime = toDate.getTime() - fromDate.getTime();
    return diffTime / (1000 * 3600 * 24) + 1;
  }

  onDateSelection(date: NgbDate) {
    console.log(this.fromDate);
    console.log(date);
    console.log(
      `from: ${this.fromDate}, to ${
        this.toDate
      } date: ${date} è dopo? ${date.after(this.fromDate)} `,
    );
    if (!this.fromDate && !this.toDate) {
      this.fromDate = date;
    } else if (
      this.fromDate &&
      !this.toDate &&
      date &&
      (date.equals(this.fromDate) || date.after(this.fromDate))
    ) {
      this.toDate = date;
      // check if the interval is allowed
      const daysSelected = this.dateDiffInDays(this.fromDate, date);
      if (daysSelected > this.maxDays) {
        this.showWarning = true;
        this.fromDate = date;
        this.toDate = null;
      }
    } else {
      this.toDate = null;
      this.fromDate = date;
      this.showWarning = false;
    }
  }

  private setDateRange(d: Date) {
    console.log(`selected date: ${d}`);
    console.log(this.filter);
    this.fromDate = NgbDate.from({
      day: d.getDate(),
      month: d.getMonth() + 1,
      year: d.getFullYear(),
    });
    this.toDate = this.fromDate;
  }

  isHovered(date: NgbDate) {
    return (
      this.fromDate &&
      !this.toDate &&
      this.hoveredDate &&
      date.after(this.fromDate) &&
      date.before(this.hoveredDate)
    );
  }

  isInside(date: NgbDate) {
    return this.toDate && date.after(this.fromDate) && date.before(this.toDate);
  }

  isRange(date: NgbDate) {
    return (
      date.equals(this.fromDate) ||
      (this.toDate && date.equals(this.toDate)) ||
      this.isInside(date) ||
      this.isHovered(date)
    );
  }

  validateInput(currentValue: NgbDate | null, input: string): NgbDate | null {
    const parsed = this.formatter.parse(input);
    return parsed && this.calendar.isValid(NgbDate.from(parsed))
      ? NgbDate.from(parsed)
      : currentValue;
  }

  download() {
    if (!this.toDate) {
      this.toDate = this.fromDate;
    }
    console.log(this.filter);
    this.model.fromDate = new Date(
      Date.UTC(this.fromDate.year, this.fromDate.month - 1, this.fromDate.day),
    );
    this.model.toDate = new Date(
      Date.UTC(this.toDate.year, this.toDate.month - 1, this.toDate.day),
    );

    this.spinner.show();
    const format = this.model.format;

    let fileExtension = "";
    switch (this.model.format) {
      case "BUFR":
        fileExtension = ".bufr";
        break;
      case "JSON":
        fileExtension = ".jsonl";
    }
    let basename =
      `${this.filter.product}_` +
      `${this.fromDate.year}${this.fromDate.month}${this.fromDate.day}-` +
      `${this.toDate.year}${this.toDate.month}${this.toDate.day}`;
    this.obsService
      .download(
        this.filter,
        this.model.fromDate,
        this.model.toDate,
        this.model.format,
      )
      .subscribe(
        (blob) => {
          importedSaveAs(blob, `${basename}${fileExtension}`);
        },
        (error) => {
          console.error(error);
          this.notify.showError("Unable to download data");
        },
      )
      .add(() => {
        this.spinner.hide();
        this.activeModal.close();
      });
  }

  private applyMinDate() {
    let d = moment.utc().subtract(LAST_DAYS - 1, "days");
    this.minDate = {
      year: d.year(),
      month: d.month() + 1,
      day: d.date(),
    };
  }
}
