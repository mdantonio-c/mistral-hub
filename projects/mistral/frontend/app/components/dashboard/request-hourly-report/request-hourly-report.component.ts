import { Component, OnInit } from "@angular/core";
import { RequestHourlyReport } from "@app/types";
import { DataService } from "@app/services/data.service";
import { NotificationService } from "@rapydo/services/notification";

@Component({
  selector: "app-request-hourly-report",
  templateUrl: "./request-hourly-report.component.html",
})
export class RequestHourlyReportComponent implements OnInit {
  requestReport: RequestHourlyReport = { submitted: 0, total: 0, remaining: 0 };
  barValue = 0;

  constructor(
    private dataService: DataService,
    private notify: NotificationService,
  ) {}

  ngOnInit() {
    this.load();
  }

  load() {
    this.dataService.getHourlyReport().subscribe(
      (response) => {
        this.requestReport = response;
        this.barValue =
          (this.requestReport.submitted * 100) / this.requestReport.total;
      },

      (error) => {
        this.notify.showError(error);
      },
    );
  }
}
