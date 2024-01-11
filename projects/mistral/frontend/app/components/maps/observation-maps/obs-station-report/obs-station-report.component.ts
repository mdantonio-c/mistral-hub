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
  SeriesItem,
} from "@app/types";
import { ObsService } from "../services/obs.service";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import * as moment from "moment";
import { curveMonotoneX } from "d3-shape";
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
  @Input() lang: string;
  @Input() extendedVisualization: boolean = true;

  name: string;
  level: string;
  timerange: string;
  license: string;
  report: Observation;
  descriptions: DescriptionDict;
  active;
  curve = curveMonotoneX;

  multi: DataSeries[];
  single: DataSeries[];
  // Combo Chart
  accumulatedSeries: DataSeries[];
  windDirectionSeries;

  // chart options
  multiColorScheme = {
    domain: ["#5AA454", "#E44D25", "#CFC0BB", "#7aa3e5", "#a8385d", "#aae3f5"],
  };

  monoBarScheme = {
    domain: ["#F9BF8F"],
  };
  monoLineScheme = {
    domain: ["#5AA454"],
  };

  /* flag to track if there are wind products in the selected groundstation */
  existMixWindProduct: boolean = false;

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
    console.log(`nav changed to varcode: ${changeEvent.nextId}`);
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
          //console.log('response',response)
          //console.log('DESCR-response.descr',this.descriptions);
          //console.log('DATA-response.data',data);
          //console.log('REPORT-data[0]',this.report);
          //console.log('numero di prodotti della stazione',data[0].prod.length)
          let multi = this.normalize(data[0]);
          this.checkWindMixProductAvailable(this.report);
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
        if (this.lang === "it") {
          return `${moment(this.filter.dateInterval[0])
            .locale("it")
            .format("D MMMM YYYY")} - ${moment(this.filter.dateInterval[1])
            .locale("it")
            .format("D MMMM YYYY")}`;
        } else {
          return `${moment(this.filter.dateInterval[0]).format(
            "MMMM Do YYYY",
          )} - ${moment(this.filter.dateInterval[1]).format("MMMM Do YYYY")}`;
        }
      } else {
        if (this.lang === "it") {
          return `${moment(this.filter.dateInterval[0])
            .locale("it")
            .format("D MMMM YYYY")}`;
        } else {
          return `${moment(this.filter.dateInterval[0]).format(
            "MMMM Do YYYY",
          )}`;
        }
      }
    } else {
      if (this.lang === "it") {
        return moment(this.filter.reftime).locale("it").format("D MMMM YYYY");
      } else {
        return moment(this.filter.reftime).format("MMMM Do YYYY");
      }
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
    //console.log(`ora: ${h} minuto: ${m} vero? ${(m === 0 && h % 2 === 0)} timeformat: ${time.format(dateFormat)}`)
    return m === 0 && h % 2 === 0 ? time.format(dateFormat) : "";
  }

  xAxisNgStyleFn = this.xAxisNgStyle.bind(this);
  private xAxisNgStyle(tick) {
    const reftime = moment.utc(tick).local().format("HH:mm");
    const minutes = moment.utc(tick).local().format("mm");
    let lineStyle = null;
    if (reftime === "00:00") {
      lineStyle = { stroke: "#009", "stroke-dasharray": "10" };
    } else if (minutes === "00") {
      lineStyle = { stroke: "#e4e4e4" };
    } else {
      lineStyle = { "stroke-opacity": 0 };
    }

    return lineStyle;
  }

  onlyDateChangeNgStyleFn = this.onlyDateChangeNgStyle.bind(this);
  private onlyDateChangeNgStyle(tick) {
    //console.log("only data change");
    const reftime = moment.utc(tick).local().format("HH:mm");
    const isMidnight = reftime === "00:00";
    //console.log(`is midnight? ${isMidnight}`);
    return isMidnight
      ? { stroke: "#009", "stroke-dasharray": "10" }
      : { "stroke-opacity": 0 };
  }

  private updateGraphData(navItemId: string) {
    // managing of wind
    if (navItemId === "mixwind-0") {
      this.single = this.multi.filter(
        (x: DataSeries) =>
          `${x.code}-${x.level}-${x.timerange}` ===
          "B11002-103,2000,0,0-254,0,0",
      );
      // to manage 10 m above ground level  case
      if (this.single.length == 0) {
        this.single = this.multi.filter(
          (x: DataSeries) =>
            `${x.code}-${x.level}-${x.timerange}` ===
            "B11002-103,10000,0,0-254,0,0",
        );
      }

      const windSpeedValues = this.single[0].series.map((v) => v.value);
      let windDirection = this.multi.filter(
        (x: DataSeries) =>
          `${x.code}-${x.level}-${x.timerange}` ===
          "B11001-103,2000,0,0-254,0,0",
      );
      // to manage 10 m above ground case
      if (windDirection.length == 0) {
        windDirection = this.multi.filter(
          (x: DataSeries) =>
            `${x.code}-${x.level}-${x.timerange}` ===
            "B11001-103,10000,0,0-254,0,0",
        );
      }
      let bubbleWindDirection = Object.assign({}, windDirection);
      let t = [];
      bubbleWindDirection[0].series.forEach((v, index) => {
        let s;
        // data for bubble series, in value is stored wind direction
        s = {
          name: v.name,
          x: v.name,
          y: parseFloat(windSpeedValues[index]),
          r: 5,
          value: v.value,
        };
        t.push(s);
      });
      bubbleWindDirection[0].series = t;
      this.windDirectionSeries = [bubbleWindDirection[0]];
      //console.log('single',this.single);
      //console.log('winddirectionseries',this.windDirectionSeries);
    } else {
      this.single = this.multi.filter(
        (x: DataSeries) => `${x.code}-${x.level}-${x.timerange}` === navItemId,
      );
    }
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
      if (v.var === "B13011") {
        let obj = Object.assign({}, s);
        obj.name = "accumulated data";
        obj.series = this.calculateAccumulated(v);
        this.accumulatedSeries = [obj];
      }
      res.push(s);
    });
    return res;
  }

  /**
   * Return accumulated values
   * @param v
   * @private
   */
  private calculateAccumulated(v: ObsData): SeriesItem[] {
    let series: SeriesItem[] = [];
    let accumulated = 0;
    v.val.forEach((obs) => {
      accumulated += obs.val;
      series.push({
        name: obs.ref,
        value: +accumulated.toFixed(2),
      });
    });
    return series;
  }

  yLeftAxisScale(min, max) {
    return { min: `${min}`, max: `${max}` };
  }

  yRightAxisScale(min, max) {
    return { min: `${min}`, max: `${max}` };
  }

  /*
   * Check if wind speed and wind direction is present in the
   * groundstation report
   */
  private checkWindMixProductAvailable(data: Observation): void {
    let i: number = 0;
    data.prod.forEach((v) => {
      if (v.var == "B11001" || v.var == "B11002") {
        i = i + 1;
      }
    });

    if (i == 2) {
      this.existMixWindProduct = true;
    } else {
      this.existMixWindProduct = false;
    }
  }
}
