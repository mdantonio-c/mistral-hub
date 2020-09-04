import { Component, Input, OnInit, Output, EventEmitter } from "@angular/core";
import { NgbActiveModal, NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { ObsFilter, ObsService, Station } from "../services/obs.service";

import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";

@Component({
  selector: "app-obs-station-report",
  templateUrl: "./obs-station-report.component.html",
  styleUrls: ["./obs-station-report.component.css"],
})
export class ObsStationReportComponent implements OnInit {
  @Input() station: Station;
  @Input() name = "n/a";
  @Input() filter: ObsFilter;

  constructor(
    private obsService: ObsService,
    public activeModal: NgbActiveModal,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {}

  ngOnInit() {
    // Get station specifics and data for timeseries
    setTimeout(() => this.spinner.show("timeseries-spinner"), 0);
    this.obsService
      .getStationTimeSeries(this.filter, this.station)
      .subscribe(
        (data) => {
          console.log(data);
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        setTimeout(() => this.spinner.hide("timeseries-spinner"), 0);
      });
  }

  download() {
    console.log("download");
  }
}
