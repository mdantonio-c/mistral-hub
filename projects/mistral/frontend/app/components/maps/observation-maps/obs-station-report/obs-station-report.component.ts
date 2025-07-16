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

  // to display only selected station details
  stationDetailsCodesList = ["B01019", "B01194", "B05001", "B06001", "B07030"];
  filteredStationDetails: StationDetail[] = [];

  // station report
  yScaleMin: number;
  yScaleMax: number;
  yRightScaleMin: number;
  yRightScaleMax: number;

  // chart options
  multiColorScheme = {
    domain: ["#5AA454", "#E44D25", "#CFC0BB", "#7aa3e5", "#a8385d", "#aae3f5"],
  };

  monoBarSchemeWind = {
    domain: ["#F9BF8F"],
  };
  monoLineSchemeWind = {
    domain: ["#5AA454"],
  };

  monoBarSchemeRain = {
    domain: ["#ADD8E6"],
  };
  monoLineSchemeRain = {
    domain: ["#FF0000"],
  };
  /* flag to track if there are wind products in the selected groundstation */
  existMixWindProduct: boolean = false;
  onlyWindProduct: boolean = false;

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
    this.addSecondaryXAxisLabels();
  }

  getNavItemName(element: ObsData) {
    return `${element.var}-${element.lev}-${element.trange}`;
  }

  filterStationDetails(stationData) {
    this.filteredStationDetails = stationData.filter((d) =>
      this.stationDetailsCodesList.includes(d.var),
    );
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
          // change on description
          if (this.descriptions) {
            this.descriptions["B01019"] = { descr: "Station name" };
            this.descriptions["B01194"] = { descr: "Network" };
            this.descriptions["B07030"] = {
              descr: "Station elevation above sea level",
            };
            if ("B13011" in this.descriptions) {
              this.descriptions["B13011"].descr = "Precipitation";
            }
            if ("B12101" in this.descriptions) {
              this.descriptions["B12101"].descr = "Temperature";
            }
          }
          // filter the station details to be displayed
          this.filterStationDetails(data[0].stat.details);

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
            // it means that the filter contains multiple products          console.log(this.existMixWindProduct,this.onlyWindProduct);

            meteogramToShow = `${this.selectedProduct.product}-${this.selectedProduct.level}-${this.selectedProduct.timerange}`;
          } else {
            meteogramToShow = `${this.filter.product}-${this.filter.level}-${this.filter.timerange}`;
          }
          this.single = this.multi.filter(
            (x: DataSeries) =>
              `${x.code}-${x.level}-${x.timerange}` === meteogramToShow,
          );
          if (
            this.selectedProduct &&
            (this.selectedProduct.product == "B11002" ||
              this.selectedProduct.product == "B11001")
          ) {
            meteogramToShow = "mixwind-0";
            this.buildWindProduct();
          }
          // to manage the case when for a station only wind products are available
          if (this.onlyWindProduct) {
            meteogramToShow = "mixwind-0";
            this.buildWindProduct();
          }
          this.active = meteogramToShow;
          this.updateYScaleRange(meteogramToShow);
        },
        (error) => {
          this.notify.showError(error);
        },
      )
      .add(() => {
        setTimeout(() => this.spinner.hide("timeseries-spinner"), 0);
        this.addSecondaryXAxisLabels();
      });
  }

  addSecondaryXAxisLabels() {
    setTimeout(
      () =>
        document
          .querySelectorAll(
            "g[custom-ngx-x-axis-ticks] > g.tick.ng-star-inserted",
          )
          .forEach((x) => {
            const input = "<svg>" + x.innerHTML + "</svg>";
            const parser = new DOMParser();
            const doc = parser.parseFromString(input, "image/svg+xml");
            const textElements = doc.querySelectorAll("text");
            textElements.forEach((el) => {
              const content = el.textContent?.trim();
              if (content && content.includes("\n")) {
                const text = document.createElementNS(
                  "http://www.w3.org/2000/svg",
                  "text",
                );
                const tspan = document.createElementNS(
                  "http://www.w3.org/2000/svg",
                  "tspan",
                );
                const date = content.split("\n")[1].trim();
                text.setAttribute("stroke-width", "0.01");
                text.setAttribute("text-anchor", "end");
                tspan.setAttribute("x", "0");
                tspan.setAttribute("dy", "1em");
                tspan.textContent = date;
                x.innerHTML = "";
                text.setAttribute("style", "font-size: 12px;");
                text.setAttribute("text-anchor", "middle");
                text.textContent = "00";
                text.appendChild(tspan);
                x.appendChild(text);
              }
            });
          }),
      0,
    );
  }

  getName() {
    if (this.report && this.report.stat.details) {
      let nameDetail: StationDetail = this.report.stat.details.find(
        (x) => x.var === STATION_NAME_CODE,
      );
      if (nameDetail) {
        return nameDetail.val;
      }
    } else if (
      this.station &&
      this.station?.details &&
      this.station?.details.length > 0
    ) {
      return this.station?.details[0]?.val;
    }
    return;
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
  private xAxisTickFormatting(val, dateFormat = "HH") {
    const time = moment.utc(val).local();
    const h = time.hour();
    const m = time.minute();
    //console.log(`ora: ${h} minuto: ${m} vero? ${(m === 0 && h % 2 === 0)} timeformat: ${time.format(dateFormat)}`)
    //return m === 0 && h % 6 === 0 ? time.format(dateFormat) : "";
    if (m === 0 && h % 6 === 0) {
      const timeLabel = time.format(dateFormat);
      if (h === 0) {
        const dateLabel = time.format("DD/MM");
        return `${timeLabel}\n${dateLabel}`;
      }
      return timeLabel;
    }
    return "";
  }

  xAxisNgStyleFn = this.xAxisNgStyle.bind(this);
  private xAxisNgStyle(tick) {
    const reftime = moment.utc(tick).local().format("HH:mm");
    const minutes = moment.utc(tick).local().format("mm");
    const hour = moment.utc(tick).local().format("HH");
    const h = parseInt(hour);
    let lineStyle = null;
    if (reftime === "00:00") {
      lineStyle = { stroke: "#009", "stroke-dasharray": "10" };
    } else if (minutes === "00" && h % 6 === 0) {
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
    // managing of wind products
    console.log(navItemId);
    if (navItemId === "mixwind-0") {
      this.buildWindProduct();
    } else {
      this.single = this.multi.filter(
        (x: DataSeries) => `${x.code}-${x.level}-${x.timerange}` === navItemId,
      );
    }
    this.updateYScaleRange(navItemId);
  }
  updateYScaleRange(navItemId: string) {
    switch (navItemId) {
      case "B12101-103,2000,0,0-254,0,0": // temperature
        if (this.single) {
          const allValues = this.single.flatMap((s) =>
            s.series.map((d) => parseFloat(d.value)),
          );
          const allPositive = allValues.every((v) => v >= 0);
          const minVal = Math.min(...allValues);
          const maxVal = Math.max(...allValues);
          if (allPositive) {
            this.yScaleMin = 0;
            this.yScaleMax = Math.round(maxVal + 10);
          } else {
            this.yScaleMax = Math.round(maxVal + 10);
            this.yScaleMin = Math.round(minVal - 10);
          }
        }
        break;
      case "B13003-103,2000,0,0-254,0,0": // relative humidity
        if (this.single) {
          this.yScaleMin = 0;
          this.yScaleMax = 100;
        }
        break;
      case "B10004-1,0,0,0-254,0,0": // pressure
        if (this.single) {
          const allValues = this.single.flatMap((s) =>
            s.series.map((d) => parseFloat(d.value)),
          );
          const minVal = Math.min(...allValues);
          const maxVal = Math.max(...allValues);
          this.yScaleMin = Math.round(minVal - 10);
          this.yScaleMax = Math.round(maxVal + 10);
        }
        break;
      case "B13013-1,0,0,0-254,0,0": // snow
        if (this.single) {
          const allValues = this.single.flatMap((s) =>
            s.series.map((d) => parseFloat(d.value)),
          );
          this.yScaleMin = 0;
          let ymax = 100;
          const maxVal = Math.max(...allValues);

          while (maxVal > ymax) {
            ymax += 100;
          }
          this.yScaleMax = ymax;
        }
        break;
    }
  }
  /* Build and filter data to display combined wind graph */
  private buildWindProduct() {
    let flag10m = false;
    this.single = this.multi.filter(
      (x: DataSeries) =>
        `${x.code}-${x.level}-${x.timerange}` === "B11002-103,2000,0,0-254,0,0",
    );

    //to manage 10 m above ground level  case
    if (this.single.length == 0) {
      this.single = this.multi.filter(
        (x: DataSeries) =>
          `${x.code}-${x.level}-${x.timerange}` ===
          "B11002-103,10000,0,0-254,0,0",
      );
      flag10m = true;
    }
    //console.log('wind speed',this.single);
    let windDirection;
    if (!flag10m) {
      windDirection = this.multi.filter(
        (x: DataSeries) =>
          `${x.code}-${x.level}-${x.timerange}` ===
          "B11001-103,2000,0,0-254,0,0",
      );
    } else {
      // to manage 10 m above ground case
      windDirection = this.multi.filter(
        (x: DataSeries) =>
          `${x.code}-${x.level}-${x.timerange}` ===
          "B11001-103,10000,0,0-254,0,0",
      );
    }
    //console.log('wind direction',windDirection);

    // combined wind graph must have the same number of data for direction and speed wind
    const commonNames = this.single[0].series
      .map((obj1) => obj1.name)
      .filter((name1) =>
        windDirection[0].series.some((obj2) => obj2.name == name1),
      );
    //console.log(commonNames);
    //console.log(this.single[0].series.filter(obj => commonNames.includes(obj.name)),windDirection[0].series.filter(obj => commonNames.includes(obj.name)));
    this.single[0].series = this.single[0].series.filter((obj) =>
      commonNames.includes(obj.name),
    );
    windDirection[0].series = windDirection[0].series.filter((obj) =>
      commonNames.includes(obj.name),
    );

    const windSpeedValues = this.single[0].series.map((v) => v.value);
    //const maxWindValue = Math.max(windSpeedValues);

    //const yScaleMax = Math.round(maxWindValue + 10 );
    //const yScaleMin = 0;

    // let bubbleWindDirection = Object.assign({}, windDirection);
    let bubbleWindDirection = JSON.parse(JSON.stringify(windDirection));
    let t = [];
    bubbleWindDirection[0].series.forEach((v, index) => {
      let s;
      // data for bubble series, in value is stored wind direction
      s = {
        name: v.name,
        x: v.name,
        y: parseFloat(windSpeedValues[index]),
        r: 2.5,
        value: v.value,
      };
      t.push(s);
    });
    bubbleWindDirection[0].series = t;
    this.windDirectionSeries = [bubbleWindDirection[0]];
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
    // get first timestamp of the request, if it is equals to the first record timestamp, then it starts by 0
    const fromTimeStamp = this.filter.reftime
      ? new Date(this.filter.reftime.setUTCHours(this.filter.time[0], 0, 0, 0))
          .toISOString()
          .split(".")[0]
      : this.filter.dateInterval[0].toISOString().split(".")[0];
    v.val.forEach((obs) => {
      if (obs.ref === fromTimeStamp) {
        accumulated += 0.0;
      } else {
        accumulated += obs.val;
      }
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
   * Check if there are wind speed and wind direction in the
   * groundstation report
   */
  private checkWindMixProductAvailable(data: Observation): void {
    let i: number = 0;
    let j: number = 0;

    data.prod.forEach((v) => {
      if (v.var == "B11001" || v.var == "B11002") {
        i = i + 1;
      } else {
        j = j + 1;
      }
    });

    if (i == 2) {
      if (j == 0) {
        this.onlyWindProduct = true;
      }
      this.existMixWindProduct = true;
    } else {
      this.existMixWindProduct = false;
    }
  }

  widhtOfWindData(): number {
    if (this.single[0].series.length > 35) {
      return this.single[0].series.length * 11;
    }
  }

  giveMeMetres() {
    return "m";
  }
  checkUTCShift(): string {
    const now = moment();
    const offsetHours = now.utcOffset() / 60;
    const sign = offsetHours >= 0 ? "+" : "-";
    return `(UTC${sign}${Math.abs(offsetHours)})`;
  }
}
