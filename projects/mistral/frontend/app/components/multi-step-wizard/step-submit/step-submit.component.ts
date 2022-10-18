import { Component, Input, ElementRef, OnInit, ViewChild } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { FormBuilder, FormGroup, Validators } from "@angular/forms";
import { FormData, FormDataService } from "@app/services/formData.service";
import { User } from "@rapydo/types";
import {
  ScheduleType,
  RepeatEvery,
  SummaryStats,
  TaskSchedule,
  RequestHourlyReport,
} from "@app/types";
import { DataService } from "@app/services/data.service";
import { NotificationService } from "@rapydo/services/notification";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { StepComponent } from "../step.component";
import { fromEvent } from "rxjs";
import { exhaustMap, tap } from "rxjs/operators";
import { NgxSpinnerService } from "ngx-spinner";
import { AuthService } from "@rapydo/services/auth";

@Component({
  selector: "step-submit",
  templateUrl: "./step-submit.component.html",
})
export class StepSubmitComponent extends StepComponent implements OnInit {
  title = "Submit my request";
  summaryStats: SummaryStats = { c: 0, s: 0 };
  requestReport: RequestHourlyReport = {};
  @Input() formData: FormData;
  isFormValid = false;
  scheduleForm: FormGroup;
  schedule: TaskSchedule = null;
  user: User;

  @ViewChild("submitButton", { static: true }) submitButton: ElementRef;

  constructor(
    protected router: Router,
    protected route: ActivatedRoute,
    private formBuilder: FormBuilder,
    public dataService: DataService,
    protected formDataService: FormDataService,
    private modalService: NgbModal,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private authService: AuthService
  ) {
    super(formDataService, router, route);
    this.scheduleForm = this.formBuilder.group({
      repeatType: [ScheduleType.CRONTAB, Validators.required],
      cPeriod: [RepeatEvery.DAY],
      time: ["00:00"],
      weekDay: [],
      monthDay: [],
      every: [1],
      period: [RepeatEvery.HOUR],
    });
  }

  ngOnInit() {
    this.user = this.authService.getUser();
    this.formData = this.formDataService.getFormData();
    this.isFormValid = this.formDataService.isFormValid();
    this.spinner.show("summary-spinner");
    this.formDataService
      .getSummaryStats()
      .subscribe(
        (response) => {
          this.summaryStats = response;
          if (this.summaryStats.c === 0) {
            this.notify.showWarning(
              "The applied filter do not produce any result. " +
                "Please choose different filters."
            );
          }
          if (
            this.summaryStats.s &&
            this.user.max_output_size &&
            this.summaryStats.s > this.user.max_output_size
          ) {
            this.notify.showWarning(
              "Size exceeds the allowed one for a single request"
            );
          }
        },
        (error) => {
          this.notify.showError("Error loading summary stats");
        }
      )
      .add(() => {
        this.spinner.hide("summary-spinner");
      });
    this.dataService.getHourlyReport().subscribe((response) => {
      this.requestReport = response;
      if (this.requestReport && this.requestReport.remaining === 0) {
        this.notify.showError(
          "The max number of requests par hour has been reached: Please wait next hour to submit new requests "
        );
      }
    });

    // default request name
    // this.formData.defaultName();
    window.scroll(0, 0);
    fromEvent(this.submitButton.nativeElement, "click")
      .pipe(
        tap((_) => this.spinner.show()),
        exhaustMap(() =>
          this.dataService.extractData(
            this.formData.request_name,
            this.formData.reftime,
            this.formData.datasets.map((x) => x.id),
            this.formData.filters,
            this.formData.schedule,
            this.formData.postprocessors,
            this.formData.output_format,
            this.formData.push,
            this.formData.opendata,
            this.formData.only_reliable
          )
        )
      )
      .subscribe(
        (resp) => {
          this.schedule = null;
          this.formData = this.formDataService.resetFormData();
          this.isFormValid = false;
          // Navigate to the 'My Requests' page
          this.router.navigate(["app/requests"]);
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        this.spinner.hide();
      });
  }
  checkDataReady() {
    let dataReadyDatasets = ["lm2.2", "lm5", "cosmo_2I_fcruc"];
    let requestedDatasets = this.formData.datasets.map((x) => x.id);
    if (
      requestedDatasets.length == 1 &&
      requestedDatasets.every((elem) => dataReadyDatasets.indexOf(elem) > -1)
    ) {
      return true;
    } else return false;
  }

  emptyName() {
    return (
      !this.formData.request_name ||
      this.formData.request_name.trim().length === 0
    );
  }

  showSchedule(content) {
    const modalRef = this.modalService.open(content);
    if (this.schedule) {
      this.loadSchedule();
    }
    modalRef.result.then(
      (result) => {
        switch (result) {
          case "save":
            // add schedule
            switch (this.scheduleForm.get("repeatType").value) {
              case ScheduleType.CRONTAB:
                this.schedule = {
                  type: ScheduleType.CRONTAB,
                  time: this.scheduleForm.get("time").value,
                  day_of_week: this.scheduleForm.get("weekDay").value,
                  day_of_month: this.scheduleForm.get("monthDay").value,
                  repeat: this.scheduleForm.get("cPeriod").value,
                };
                break;
              case ScheduleType.PERIOD:
                this.schedule = {
                  type: ScheduleType.PERIOD,
                  every: this.scheduleForm.get("every").value,
                  repeat: this.scheduleForm.get("period").value,
                };
                break;
              case ScheduleType.DATA_READY:
                this.schedule = {
                  type: ScheduleType.DATA_READY,
                };
                break;
            }
            this.formData.setSchedule(this.schedule);
            console.log("added schedule:", this.schedule);
            break;
          case "remove":
            this.formData.schedule = null;
            this.schedule = null;
            this.reset();
            break;
        }
      },
      (reason) => {
        // do nothing
      }
    );
  }

  private loadSchedule() {
    this.scheduleForm.setValue({
      repeatType: this.schedule.type,
      cPeriod:
        this.schedule.type === ScheduleType.CRONTAB
          ? this.schedule.repeat
          : RepeatEvery.DAY,
      time:
        this.schedule.type === ScheduleType.CRONTAB
          ? this.schedule.time
          : "00:00",
      every:
        this.schedule.type === ScheduleType.PERIOD ? this.schedule.every : 1,
      period:
        this.schedule.type === ScheduleType.PERIOD
          ? this.schedule.repeat
          : RepeatEvery.HOUR,
    });
  }

  private reset() {
    this.scheduleForm.reset({
      repeatType: ScheduleType.CRONTAB,
      cPeriod: RepeatEvery.DAY,
      time: "00:00",
      weekDay: "",
      monthDay: "",
      every: 1,
      period: RepeatEvery.HOUR,
    });
  }

  goToPrevious() {
    // Navigate to the postprocess page
    this.router.navigate(["../", "postprocess"], { relativeTo: this.route });
  }

  toggleOpenDataSchedule() {
    this.formData.opendata = !this.formData.opendata;
  }

  onPeriodSelected(period) {
    if (period === "minute") {
      // set the minimum period allowed
      this.scheduleForm.patchValue({
        every: 15,
      });
    } else {
      this.scheduleForm.patchValue({
        every: 1,
      });
    }
  }

  checkOpenData() {
    if (
      this.user &&
      this.user.roles.admin_root &&
      this.formData.datasets.length == 1 &&
      this.formData.datasets[0].is_public &&
      this.formData.datasets[0].category !== "OBS"
    ) {
      return true;
    } else return false;
  }
  fillDayofMonths() {
    let range = [];
    for (var i = 1; i < 32; i++) {
      range.push(i);
    }
    return range;
  }
}
