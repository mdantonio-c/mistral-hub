import { Component, Input, OnInit } from "@angular/core";
import {
  ObsData,
  Observation,
  ObsFilter,
  ObsService,
  Station,
  StationDetail,
} from "../services/obs.service";
import { DataSeries } from "../obs-station-report/obs-station-report.component";
import { MockProductTimeSeries } from "../obs-station-report/data.mock";

import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import * as moment from "moment";

const STATION_NAME_CODE = "B01019";

@Component({
  selector: "app-obs-meteograms",
  templateUrl: "./obs-meteograms.component.html",
  styleUrls: ["./obs-meteograms.component.css"],
})
export class ObsMeteogramsComponent implements OnInit {
  filter: ObsFilter;
  multi: DataSeries[];
  report: Observation[];
  loading: boolean = false;

  // product info
  varcode: string;
  product: string;
  level: string;
  timerange: string;
  userunit: string;

  // chart options
  colorScheme = {
    domain: ["#5AA454", "#E44D25", "#CFC0BB", "#7aa3e5", "#a8385d", "#aae3f5"],
  };

  constructor(
    private obsService: ObsService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {}

  ngOnInit(): void {
    this.loading = true;
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

  private getName(station: Station) {
    if (station.details) {
      let nameDetail: StationDetail = station.details.find(
        (x) => x.code === STATION_NAME_CODE
      );
      if (nameDetail) {
        return nameDetail.value;
      }
    }
  }

  updateChart(filter: ObsFilter, update = false) {
    this.filter = filter;
    this.loading = true;
    setTimeout(() => this.spinner.show(), 0);
    this.obsService
      .getData(this.filter, update)
      .subscribe(
        (data: Observation[]) => {
          this.report = data;
          // console.log(this.report);
          // get product info
          if (data.length !== 0) {
            let obs = data[0];
            this.product = obs.products[0].description;
            this.varcode = obs.products[0].varcode;
            if (filter.level) {
              this.level = obs.products[0].values[0].level_desc;
            }
            if (filter.timerange) {
              this.timerange = obs.products[0].values[0].timerange_desc;
            }
          }
          let multi = this.normalize(data);
          Object.assign(this, { multi });
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        setTimeout(() => this.spinner.hide(), 0);
        this.loading = false;
      });
  }

  private normalize(data: Observation[]): DataSeries[] {
    let res: DataSeries[] = [];
    data.forEach((obs) => {
      let p: ObsData = obs.products[0];
      let s: DataSeries = {
        name: this.getName(obs.station) || "n/a",
        code: p.varcode,
        unit: p.unit,
        series: [],
      };
      s.series = p.values
        .filter((obs) => obs.is_reliable === true)
        .map((obs) => {
          return {
            name: obs.reftime,
            value: ObsService.showData(obs.value, p.varcode),
          };
        });
      res.push(s);
    });
    return res;
  }
}
