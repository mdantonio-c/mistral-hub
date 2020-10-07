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
} from "@app/types";
import { ObsService } from "../services/obs.service";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import * as moment from "moment";

const STATION_NAME_CODE = "B01019";

@Component({
  selector: "app-obs-station-report",
  templateUrl: "./obs-station-report.component.html",
  styleUrls: ["./obs-station-report.component.css"],
})
export class ObsStationReportComponent implements OnInit {
  @Input() station: Station;
  @Input() filter: ObsFilter;

  name: string;
  level: string;
  timerange: string;
  report: Observation;
  descriptions: DescriptionDict;
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
        //(data: Observation[], descriptions: Descriptions[]) => {
        (response: ObservationResponse) => {
          let data = response.data;
          this.descriptions = response.descr;
          //console.log("reponse ",response," data",data," descr ",descriptions)
          // console.log(data);
          this.report = data[0];
          /*          if (this.filter.level) {
            this.level = this.report.prod[0].val[0].level_desc;
          }
          if (this.filter.timerange) {
            this.timerange = this.report.prod[0].val[0].timerange_desc;
          }*/
          if (this.filter.level) {
            this.level = this.descriptions[this.report.prod[0].lev].desc;
          }
          if (this.filter.timerange) {
            this.timerange = this.descriptions[this.report.prod[0].trange].desc;
          }
          let multi = this.normalize(data[0]);
          Object.assign(this, { multi });
          //console.log(JSON.stringify(this.multi));
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
    if (this.report && this.report.stat.details) {
      let nameDetail: StationDetail = this.report.stat.details.find(
        (x) => x.var === STATION_NAME_CODE
      );
      if (nameDetail) {
        return nameDetail.val;
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
    this.single = this.multi.filter((x: DataSeries) => x.var === varcode);
  }

  private normalize(data: Observation): DataSeries[] {
    let res: DataSeries[] = [];
    data.prod.forEach((v) => {
      let s: DataSeries = {
        // name: v.description,
        code: v.var,
        // unit: v.unit,
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
