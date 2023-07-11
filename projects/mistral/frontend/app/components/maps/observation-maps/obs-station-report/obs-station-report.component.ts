import { Component, Input, OnInit } from "@angular/core";
import { NgbActiveModal, NgbNavChangeEvent } from "@ng-bootstrap/ng-bootstrap";
import {
  Observation,
  ObsFilter,
  Station,
  StationDetail,
  DataSeries,
  ObservationResponse,
  DescriptionDict,
  ObsData,
} from "@app/types";
import { ObsService } from "../services/obs.service";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import * as moment from "moment";
import * as shape from "d3-shape";
import { randomize } from "./data.mock";

const STATION_NAME_CODE = "B01019";

@Component({
  selector: "app-obs-station-report",
  templateUrl: "./obs-station-report.component.html",
  styleUrls: ["./obs-station-report.component.css"],
})
export class ObsStationReportComponent implements OnInit {
  @Input() station: Station;
  @Input() filter: ObsFilter;
  @Input() selectedProduct: ObsFilter;
  @Input() localTimeData: boolean = false;

  name: string;
  level: string;
  timerange: string;
  license: string;
  report: Observation;
  descriptions: DescriptionDict;
  active;
  curve = shape.curveCardinal.tension(0);

  multi: DataSeries[];
  single: DataSeries[];

  // chart options
  multiColorScheme = {
    domain: ["#5AA454", "#E44D25", "#CFC0BB", "#7aa3e5", "#a8385d", "#aae3f5"],
  };

  monoColorScheme = {
    domain: ["#87a7e7"],
  };

  constructor(
    private obsService: ObsService,
    public activeModal: NgbActiveModal,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
  ) {}

  ngOnInit() {
    // Get station specifics and data for timeseries
    this.loadReport();
  }

  onNavChange(changeEvent: NgbNavChangeEvent) {
    // console.log(`nav changed to varcode: ${changeEvent.nextId}`);
    this.updateGraphData(changeEvent.nextId);
  }

  getNavItemName(element: ObsData) {
    return `${element.var}-${element.lev}-${element.trange}`;
  }

  private loadReport() {
    setTimeout(() => this.spinner.show("timeseries-spinner"), 0);
    this.obsService
      .getStationTimeSeries(this.filter, this.station)
      .subscribe(
        (response: ObservationResponse) => {
          let data = response.data;
          // data = randomize(data);
          this.descriptions = response.descr;
          this.report = data[0];
          let multi = this.normalize(data[0]);
          Object.assign(this, { multi });
          // console.log(JSON.stringify(this.multi));
          let meteogramToShow: string;
          if (this.selectedProduct) {
            // it means that the filter contains multiple products
            meteogramToShow = `${this.selectedProduct.product}-${this.selectedProduct.level}-${this.selectedProduct.timerange}`;
          } else {
            meteogramToShow = `${this.filter.product}-${this.filter.level}-${this.filter.timerange}`;
          }
          this.single = this.multi.filter(
            (x: DataSeries) =>
              `${x.code}-${x.level}-${x.timerange}` === meteogramToShow,
          );
          this.active = meteogramToShow;
          //console.log("single: ", this.single, "multi: ", multi);
        },
        (error) => {
          this.notify.showError(error);
        },
      )
      .add(() => {
        setTimeout(() => this.spinner.hide("timeseries-spinner"), 0);
      });
  }

  getName() {
    if (this.report && this.report.stat.details) {
      let nameDetail: StationDetail = this.report.stat.details.find(
        (x) => x.var === STATION_NAME_CODE,
      );
      if (nameDetail) {
        return nameDetail.val;
      }
    }
  }

  getUserUnit(elementId: string) {
    const varcode = elementId.split("-")[0];
    const unit: string = this.single[0].unit;
    return ObsService.showUserUnit(varcode, unit);
  }

  xAxisLabelFormatting() {
    if (this.filter.dateInterval && this.filter.dateInterval.length > 0) {
      if (
        this.filter.dateInterval[0].getDay() !=
        this.filter.dateInterval[1].getDay()
      ) {
        return `${moment(this.filter.dateInterval[0]).format(
          "MMMM Do YYYY",
        )} - ${moment(this.filter.dateInterval[1]).format("MMMM Do YYYY")}`;
      } else {
        return `${moment(this.filter.dateInterval[0]).format("MMMM Do YYYY")}`;
      }
    } else {
      return moment(this.filter.reftime).format("MMMM Do YYYY");
    }
  }

  xAxisTickFormattingFn = this.xAxisTickFormatting.bind(this);

  /**
   * Format date ticks.
   * Only shows times that are multiples of 2.
   * @param val date string (eg. 2020-09-07T04:00:00)
   * @param dateFormat
   * @private
   */
  private xAxisTickFormatting(val, dateFormat = "HH:mm") {
    const time = this.localTimeData ? moment.utc(val).local() : moment(val);
    const h = time.hour();
    const m = time.minute();
    return m === 0 && h % 2 === 0 ? time.format(dateFormat) : "";
  }

  private updateGraphData(navItemId: string) {
    this.single = this.multi.filter(
      (x: DataSeries) => `${x.code}-${x.level}-${x.timerange}` === navItemId,
    );
  }

  private normalize(data: Observation): DataSeries[] {
    let res: DataSeries[] = [];
    data.prod.forEach((v) => {
      let s: DataSeries = {
        name: this.descriptions[v.var].descr || "n/a",
        code: v.var,
        level: v.lev,
        timerange: v.trange,
        unit: this.descriptions[v.var].unit,
        series: [],
      };
      v.val.forEach((obs) => {
        s.series.push({
          name: obs.ref,
          value: ObsService.showData(obs.val, v.var),
        });
      });
      res.push(s);
    });
    return res;
  }
}
