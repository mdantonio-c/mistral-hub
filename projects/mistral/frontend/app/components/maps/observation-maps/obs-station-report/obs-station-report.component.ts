import { Component, Input, OnInit, Output, EventEmitter } from "@angular/core";
import { NgbActiveModal, NgbModal } from "@ng-bootstrap/ng-bootstrap";
import {
  Observation,
  ObsFilter,
  ObsService,
  Station,
  StationDetail,
} from "../services/obs.service";
// import { multi } from './data';

import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import { VAR_TABLE } from "../services/data";

const STATION_NAME_CODE = "B01019";

export interface DataSeries {
  name: string;
  code: string;
  unit: string;
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
  active = 0;

  multi: any[];

  // chart options
  showLabels = true;
  animations = false;
  xAxis = true;
  yAxis = true;
  // xAxisLabel = 'Date';
  // yAxisLabel = 'Value';
  timeline = true;

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

  download() {
    console.log("download");
  }

  /*
  onSelect(data): void {
    console.log('Item clicked', JSON.parse(JSON.stringify(data)));
  }

  onActivate(data): void {
    console.log('Activate', JSON.parse(JSON.stringify(data)));
  }

  onDeactivate(data): void {
    console.log('Deactivate', JSON.parse(JSON.stringify(data)));
  }
   */

  getGraphData(varcode: string) {
    return this.multi.filter((x: DataSeries) => x.code === varcode);
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
