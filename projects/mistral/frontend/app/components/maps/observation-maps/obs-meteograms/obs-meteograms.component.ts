import { Component, AfterViewInit } from "@angular/core";
import {
  ObsData,
  Observation,
  ObsFilter,
  Station,
  StationDetail,
  DataSeries,
  ObservationResponse,
  DescriptionDict,
} from "@app/types";
import { ObsService } from "../services/obs.service";

import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import * as moment from "moment";

const STATION_NAME_CODE = "B01019";

@Component({
  selector: "app-obs-meteograms",
  templateUrl: "./obs-meteograms.component.html",
  styleUrls: ["./obs-meteograms.component.css"],
})
export class ObsMeteogramsComponent implements AfterViewInit {
  filter: ObsFilter;
  multi: DataSeries[];
  report: Observation[];
  descriptions: DescriptionDict;
  loading: boolean = true;

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

  ngAfterViewInit(): void {
    this.loading = false;
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

  private TooltipDateFormat(val) {
    // val: 2020-09-07T04:00:00
    return moment(val).format("YYYY-MM-DD HH:mm");
  }

  private getName(station: Station) {
    if (station.details) {
      let nameDetail: StationDetail = station.details.find(
        (x) => x.var === STATION_NAME_CODE
      );
      if (nameDetail) {
        return nameDetail.val;
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
        (response: ObservationResponse) => {
          let data: Observation[] = response.data;
          this.descriptions = response.descr;
          this.report = data;
          // get product info
          if (data.length !== 0) {
            let obs = data[0];
            //this.product = obs.prod[0].description;
            this.product = response.descr[obs.prod[0].var].descr;
            this.varcode = obs.prod[0].var;
            /*if (filter.level) {
              this.level = obs.products[0].values[0].level_desc;
            }
            if (filter.timerange) {
              this.timerange = obs.products[0].values[0].timerange_desc;
            }*/
          }
          let multi = this.normalize(data);
          Object.assign(this, { multi });
          // console.log(multi);
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
      let p: ObsData = obs.prod[0];
      let s: DataSeries = {
        name: this.getName(obs.stat) || "n/a",
        code: p.var,
        series: [],
      };
      s.series = p.val
        .filter((obs) => obs.rel === 1)
        .map((obs) => {
          return {
            name: new Date(obs.ref),
            value: ObsService.showData(obs.val, p.var),
          };
        });
      res.push(s);
    });
    return res;
  }
}
