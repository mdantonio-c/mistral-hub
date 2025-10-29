import { Component, Input, ChangeDetectorRef } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import { NgxSpinnerService } from "ngx-spinner";
import * as d3 from "d3-scale";

interface SeriesItem {
  name: string;
  value: number;
}

interface MetricData {
  name: string;
  series: SeriesItem[];
  linee?: any[]; // mantieni linee per eventuale uso futuro
}
interface ProvinceJson {
  provincia: string;
  variabili: {
    TM: MetricData[];
    Tm: MetricData[];
    P: MetricData[];
  };
}
const monthNames = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

@Component({
  selector: "app-province-report",
  templateUrl: "./province-report.component.html",
  styleUrls: ["./province-report.component.scss"],
})
export class ProvinceReportComponent {
  constructor(
    public activeModal: NgbActiveModal,
    private spinner: NgxSpinnerService,
    private cdr: ChangeDetectorRef,
  ) {}
  @Input() lang!: string;
  @Input() prov!: string;
  selectedMetric: "TM" | "Tm" | "P" = "TM";
  provinceData!: ProvinceJson;
  boxplotData: { [metric: string]: MetricData[] } = {};
  lineChart = [];

  public beforeOpen() {
    this.cdr.detectChanges();
    this.loadReport();
  }
  private loadReport() {
    this.loadProvinceData();
  }
  private async loadProvinceData() {
    try {
      this.spinner.show();
      const response = await fetch(
        `./app/custom/assets/images/json_out/${this.prov}.json`,
      );
      const data: ProvinceJson = await response.json();
      this.provinceData = data;

      const convertMonths = (metrics: MetricData[]): MetricData[] => {
        return metrics.map((m) => ({
          ...m,
          name: monthNames[parseInt(m.name) - 1] || m.name,
        }));
      };

      this.boxplotData = {
        TM: convertMonths(this.provinceData.variabili.TM),
        Tm: convertMonths(this.provinceData.variabili.Tm),
        P: convertMonths(this.provinceData.variabili.P),
      };
      this.buildLineChart("TM");
      console.log(this.lineChart);
      this.spinner.hide();
      setTimeout(() => {
        this.cdr.detectChanges();
      }, 0);
      console.log(this.boxplotData);
    } catch (error) {
      console.error("Errore caricamento JSON provincia:", error);
      this.spinner.hide();
    }
  }
  public selectMetric(metric: "TM" | "Tm" | "P") {
    this.selectedMetric = metric;
    this.buildLineChart(metric);
    this.cdr.detectChanges();
  }
  private buildLineChart(metric: "TM" | "Tm" | "P") {
    const selected = this.boxplotData[metric];

    this.lineChart = [
      {
        name: "Clima Media",
        series: selected.map((m) => ({
          name: m.name,
          value: m.linee?.find((l) => l.name === "clima_media")?.value ?? null,
        })),
      },
      {
        name: "Clima Min",
        series: selected.map((m) => ({
          name: m.name,
          value: m.linee?.find((l) => l.name === "clima_min")?.value ?? null,
        })),
      },
      {
        name: "Clima Max",
        series: selected.map((m) => ({
          name: m.name,
          value: m.linee?.find((l) => l.name === "clima_max")?.value ?? null,
        })),
      },
    ];

    console.log("Line chart data:", this.lineChart);
  }
}
