import { Component, Input, ChangeDetectorRef, NgZone } from "@angular/core";
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
  linee?: any[];
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
    private zone: NgZone,
  ) {}
  @Input() lang!: string;
  @Input() prov!: string;
  province;
  selectedMetric: "TM" | "Tm" | "P" = "TM";
  provinceData!: ProvinceJson;
  boxplotData: { [metric: string]: MetricData[] } = {};
  lineChart = [];
  yMin: number = 0;
  yMax: number = 0;
  monthlySeriesMapTM = {};
  monthlySeriesMapTm = {};
  monthlySeriesMapP = {};
  currentMonthlyMap: any = {};
  currentResults = [];
  yLabel = "Temperature (°C)";
  colorScheme = "fire";

  public beforeOpen() {
    this.cdr.detectChanges();
    this.changeProvinceName(this.prov);
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
      this.zone.run(() => {
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
        this.createSeriesfroTooltips(this.boxplotData.TM, "TM");
        this.createSeriesfroTooltips(this.boxplotData.Tm, "Tm");
        this.createSeriesfroTooltips(this.boxplotData.P, "P");
        this.currentResults = this.boxplotData["TM"];
        this.currentMonthlyMap = this.monthlySeriesMapTM;
        this.buildLineChart("TM");
        console.log(this.monthlySeriesMapTM);
        console.log(this.lineChart);
        this.spinner.hide();
        /* setTimeout(() => {
        this.cdr.detectChanges();
      }, 0);*/
        this.cdr.markForCheck();

        console.log(this.boxplotData);
      });
    } catch (error) {
      console.error("Errore caricamento JSON provincia:", error);
      this.spinner.hide();
    }
  }
  public selectMetric(metric: "TM" | "Tm" | "P") {
    this.selectedMetric = metric;
    this.currentResults = this.boxplotData[metric];
    this.colorScheme = metric === "P" ? "ocean" : "fire";
    this.yLabel = metric === "P" ? "Precipitation (mm)" : "Temperature (°C)";
    switch (metric) {
      case "TM":
        this.currentMonthlyMap = this.monthlySeriesMapTM;
        break;
      case "Tm":
        this.currentMonthlyMap = this.monthlySeriesMapTm;
        break;
      case "P":
        this.currentMonthlyMap = this.monthlySeriesMapP;
        break;
    }
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
    const allValuesLines = this.lineChart.flatMap((s) =>
      s.series.map((v) => v.value).filter((v) => v !== null),
    );
    const allValuesBoxCharts = selected.flatMap((item) =>
      item.series.map((s) => s.value),
    );
    const minLines = Math.min(...allValuesLines);
    const maxLines = Math.max(...allValuesLines);
    const minBoxCharts = Math.min(...allValuesBoxCharts);
    const maxBoxCharts = Math.max(...allValuesBoxCharts);
    const min = Math.min(minLines, minBoxCharts);
    const max = Math.max(maxLines, maxBoxCharts);
    const padding = (max - min) * 0.25;
    this.yMin = Math.floor(min - padding);
    this.yMax = Math.ceil(max + padding);
  }

  createSeriesfroTooltips(data, varName: string) {
    if (varName == "TM") {
      data.forEach((item) => {
        this.monthlySeriesMapTM[item.name] = item.series;
      });
    } else if (varName == "Tm") {
      data.forEach((item) => {
        this.monthlySeriesMapTm[item.name] = item.series;
      });
    } else {
      data.forEach((item) => {
        this.monthlySeriesMapP[item.name] = item.series;
      });
    }
  }
  get boxUnit(): string {
    return this.selectedMetric === "P" ? "mm" : "°C";
  }
  changeProvinceName(prov: string) {
    this.province = this.prov;
    console.log(prov);
    if (prov == "Forli'-Cesena") {
      console.log("sono entrato");
      this.province = "Forli'";
    }
    if (prov == "Pesaro e Urbino") this.province = "Pesaro";
    if (prov == "Monza e Brianza" || prov == "Monza e della Brianza")
      this.province = "Monza";
    if (prov == "Sud Sardegna") this.province = "Carbonia";
    if (prov == "Verbano-Cusio-Ossola") this.province = "Verbania";
    if (prov == "Reggio di Calabria") this.province = "Reggio Calabria";
  }
}
