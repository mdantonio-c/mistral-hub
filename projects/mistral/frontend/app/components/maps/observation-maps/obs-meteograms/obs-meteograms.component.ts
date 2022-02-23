import { Component } from "@angular/core";
import {
  ObsData,
  Observation,
  ObsFilter,
  Station,
  StationDetail,
  MultiStationDataSeries,
  ObservationResponse,
  DescriptionDict,
} from "@app/types";
import { ObsService } from "../services/obs.service";
import { tap, delay, catchError, finalize } from "rxjs/operators";
import { throwError } from "rxjs";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import * as moment from "moment";

const STATION_NAME_CODE = "B01019";

@Component({
  selector: "app-obs-meteograms",
  templateUrl: "./obs-meteograms.component.html",
  styleUrls: ["./obs-meteograms.component.css"],
})
export class ObsMeteogramsComponent {
  filter: ObsFilter;
  multi: MultiStationDataSeries[];
  report: Observation[];
  descriptions: DescriptionDict;
  loading: boolean = false;

  // product info
  varcode: string;
  product: string;
  level: string;
  timerange: string;
  unit: string;

  // chart options
  colorScheme = {
    domain: ["#5AA454", "#E44D25", "#CFC0BB", "#7aa3e5", "#a8385d", "#aae3f5"],
  };

  constructor(
    private obsService: ObsService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {}

  getUserUnit(varcode: string) {
    return ObsService.showUserUnit(varcode, this.unit);
  }

  xAxisLabelFormatting() {
    return moment(this.filter.reftime).format("MMMM Do YYYY");
  }

  xAxisTickFormattingFn = this.xAxisTickFormatting.bind(this);

  private xAxisTickFormatting(val) {
    // val: 2020-09-07T04:00:00
    return moment(val).format("HH:mm");
  }

  TooltipDateFormat(val) {
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
    console.log("update the chart");
    this.filter = filter;
    this.loading = true;
    this.spinner.show();
    this.obsService
      .getData(this.filter, update)
      .pipe(
        // delay output by 1 sec
        // I don't know why but at the moment this does the trick
        delay(1000),
        tap((response: ObservationResponse) => {
          let data: Observation[] = response.data;
          this.descriptions = response.descr;
          this.report = data;
          // get product info
          if (data.length !== 0) {
            let obs = data[0];
            this.product = response.descr[obs.prod[0].var].descr;
            this.unit = response.descr[obs.prod[0].var].unit;
            this.varcode = obs.prod[0].var;
          }
          let multi = this.normalize(data);
          Object.assign(this, { multi });
        }),
        catchError((err) => {
          console.error("Error loading data", err);
          this.notify.showError(err);
          return throwError(err);
        }),
        finalize(() => {
          this.spinner.hide();
          this.loading = false;
        })
      )
      .subscribe();
  }

  private normalize(data: Observation[]): MultiStationDataSeries[] {
    let res: MultiStationDataSeries[] = [];
    data.forEach((obs) => {
      let p: ObsData = obs.prod[0];
      let s: MultiStationDataSeries = {
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
