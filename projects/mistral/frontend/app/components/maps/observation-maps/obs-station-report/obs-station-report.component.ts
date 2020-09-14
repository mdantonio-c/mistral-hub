import { Component, Input, OnInit, Output, EventEmitter } from "@angular/core";
import {
  NgbActiveModal,
  NgbModal,
  NgbNavChangeEvent,
} from "@ng-bootstrap/ng-bootstrap";
import {
  Observation,
  ObsFilter,
  ObsService,
  Station,
  StationDetail,
} from "../services/obs.service";

import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import * as moment from "moment";

const STATION_NAME_CODE = "B01019";

export interface DataSeries {
  name: string;
  code: string;
  unit?: string;
  timerange?: string;
  level?: string;
  series: SeriesItem[];
}
export interface SeriesItem {
  name: string; // reftime ISO 8601 e.g. 2020-09-07T00:00:00
  value: any;
}

@Component({
  selector: "app-obs-station-report",
  templateUrl: "./obs-station-report.component.html",
  styleUrls: ["./obs-station-report.component.css"],
})
export class ObsStationReportComponent implements OnInit {
  @Input() station: Station;
  @Input() filter: ObsFilter;

  name: string;
  report: Observation;
  active;

  multi: DataSeries[];
  single: DataSeries[];

  // chart options
  colorScheme = {
    domain: ["#5AA454", "#E44D25", "#CFC0BB", "#7aa3e5", "#a8385d", "#aae3f5"],
  };

  constructor(
    private obsService: ObsService,
    public activeModal: NgbActiveModal,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {}

  ngOnInit() {
    // Get station specifics and data for timeseries
    this.loadReport();
  }

  onNavChange(changeEvent: NgbNavChangeEvent) {
    // console.log(`nav changed to varcode: ${changeEvent.nextId}`);
    this.updateGraphData(changeEvent.nextId);
  }

  private loadReport() {
    setTimeout(() => this.spinner.show("timeseries-spinner"), 0);
    this.obsService
      .getStationTimeSeries(this.filter, this.station)
      .subscribe(
        (data: Observation[]) => {
          // console.log(data);
          this.report = data[0];
          let multi = this.normalize(data[0]);
          Object.assign(this, { multi });
          // console.log(JSON.stringify(this.multi));
          this.single = [multi[0]];
          this.active = this.single[0].code;
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        setTimeout(() => this.spinner.hide("timeseries-spinner"), 0);
      });
  }

  getName() {
    if (this.report && this.report.station.details) {
      let nameDetail: StationDetail = this.report.station.details.find(
        (x) => x.code === STATION_NAME_CODE
      );
      if (nameDetail) {
        return nameDetail.value;
      }
    }
  }

  getUserUnit(varcode: string) {
    return ObsService.showUserUnit(varcode);
  }

  xAxisLabelFormatting() {
    return moment(this.filter.reftime).format("MMMM Do YYYY");
  }

  xAxisTickFormattingFn = this.xAxisTickFormatting.bind(this);

  private xAxisTickFormatting(val) {
    // val: 2020-09-07T04:00:00
    return moment(val).format("HH:mm");
  }

  download() {
    // TODO
    console.log("download");
  }

  private updateGraphData(varcode: string) {
    this.single = this.multi.filter((x: DataSeries) => x.code === varcode);
  }

  private normalize(data: Observation): DataSeries[] {
    let res: DataSeries[] = [];
    data.products.forEach((v) => {
      let s: DataSeries = {
        name: v.description,
        code: v.varcode,
        unit: v.unit,
        series: [],
      };
      v.values.forEach((obs) => {
        s.series.push({
          name: obs.reftime,
          value: ObsService.showData(obs.value, v.varcode),
        });
      });
      res.push(s);
    });
    return res;
  }
}
