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
import { saveAs as importedSaveAs } from "file-saver";
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
    public formatter: NgbDateParserFormatter
  ) {
    this.maxDate = calendar.getToday();
    this.fromDate = calendar.getToday();
    this.toDate = calendar.getNext(calendar.getToday(), "d", 10);
  }

  ngOnInit() {
    if (this.filter && this.filter.reftime) {
      this.setDateRange(this.filter.reftime);
    }
    this.user = this.authService.getUser();
    if (!this.user) {
      this.applyMinDate();
    }
  }

  onDateSelection(date: NgbDate) {
    if (!this.fromDate && !this.toDate) {
      this.fromDate = date;
    } else if (
      this.fromDate &&
      !this.toDate &&
      date &&
      (date.equals(this.fromDate) || date.after(this.fromDate))
    ) {
      this.toDate = date;
    } else {
      this.toDate = null;
      this.fromDate = date;
    }
  }

  private setDateRange(d: Date) {
    console.log(`selected date: ${d}`);
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
    this.model.fromDate = new Date(
      this.fromDate.year,
      this.fromDate.month - 1,
      this.fromDate.day
    );
    this.model.toDate = new Date(
      this.toDate.year,
      this.toDate.month - 1,
      this.toDate.day
    );
    this.spinner.show();
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
        this.model.format
      )
      .subscribe(
        (blob) => {
          importedSaveAs(blob, `${basename}${fileExtension}`);
        },
        (error) => {
          console.error(error);
          this.notify.showError("Unable to download data");
        }
      )
      .add(() => {
        this.spinner.hide();
        this.activeModal.close();
      });
  }

  private applyMinDate() {
    let d = moment.utc().subtract(LAST_DAYS, "days");
    this.minDate = {
      year: d.year(),
      month: d.month() + 1,
      day: d.date(),
    };
  }
}
