import { Component, Input, ChangeDetectorRef, NgZone } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import { NgxSpinnerService } from "ngx-spinner";
@Component({
  selector: "app-province-expanded-report",
  templateUrl: "./province-expanded-report.component.html",
  styleUrls: ["./province-expanded-report.component.scss"],
})
export class ProvinceExpandedReportComponent {
  constructor(
    public activeModal: NgbActiveModal,
    private spinner: NgxSpinnerService,
    private cdr: ChangeDetectorRef,
    private zone: NgZone,
  ) {}

  @Input() lang!: string;
  @Input() prov!: string;
  selectedMetric: "Temperature" | "Total Precipitation" = "Temperature";
  yLabel = "Probability (%)";
  province;
  multi;
  processedData;

  colorSchemeTemp = {
    domain: ["#003366", "#99CCFF", "#FFFFFF", "#FF9999", "#8B0000"],
  };

  colorSchemePrec = {
    domain: ["#E65100", "#FFB300", "#FFFFFF", "#66BB6A", "#1B5E20"],
  };
  colorScheme = this.colorSchemeTemp;
  public selectMetric(metric: "Temperature" | "Total Precipitation") {
    this.selectedMetric = metric;
    if (metric == "Temperature") {
      this.multi = this.processedData.temp;
      this.colorScheme = { ...this.colorSchemeTemp };
    } else {
      this.multi = this.processedData.prec;
      this.colorScheme = { ...this.colorSchemePrec };
    }
    this.cdr.detectChanges();
  }

  public beforeOpen(layerId: string) {
    this.cdr.detectChanges();
    this.changeProvinceName(this.prov);
    this.loadReport(layerId);
  }
  changeProvinceName(prov: string) {
    this.province = prov;
    console.log(prov);
    if (prov == "Forli'-Cesena") {
      this.province = "Forli'";
    }
    if (prov == "Pesaro e Urbino") this.province = "Pesaro";
    if (prov == "Monza e Brianza" || prov == "Monza e della Brianza")
      this.province = "Monza";
    if (prov == "Sud Sardegna") this.province = "Carbonia";
    if (prov == "Verbano-Cusio-Ossola") this.province = "Verbania";
    if (prov == "Reggio di Calabria") this.province = "Reggio Calabria";
  }
  private loadReport(layerId: string) {
    this.loadProvinceData(layerId);
  }
  private async loadProvinceData(layerId: string) {
    try {
      const response = await fetch(
        `./app/custom/assets/images/json_out_subseasonal/${
          this.prov
        }.json?t=${new Date().getTime()}`,
        { cache: "no-store" },
      );
      const data = await response.json();
      this.processedData = this.prepareDataForChart(data);
      this.zone.run(() => {
        (this.selectedMetric as any) = layerId;
        if (layerId == "Temperature") {
          this.multi = this.processedData.temp;
          this.colorScheme = { ...this.colorSchemeTemp };
        } else {
          this.colorScheme = { ...this.colorSchemePrec };
          this.multi = this.processedData.prec;
        }
        this.cdr.markForCheck();
      });
    } catch (error) {
      console.error("Errore caricamento JSON provincia:", error);
    }
  }
  private prepareDataForChart(data) {
    const dataTempSet = data.variabili.Temperatura;
    const dataPrecSet = data.variabili.Precipitazione;
    const dataTemp = [];
    const dataPrec = [];

    dataTempSet.forEach((el) => {
      dataTemp.push({
        name: el.settimana,
        series: [
          {
            name: "Colder",
            value: el.quintili[0].value,
          },
          {
            name: "Below average",
            value: el.quintili[1].value,
          },
          { name: "Average", value: el.quintili[2].value },
          { name: "Above average", value: el.quintili[3].value },
          { name: "Warmer", value: el.quintili[4].value },
        ],
        soglie: el.soglie,
      });
    });
    dataPrecSet.forEach((el) => {
      dataPrec.push({
        name: el.settimana,
        series: [
          {
            name: "Drier",
            value: el.quintili[0].value,
          },
          {
            name: "Below average",
            value: el.quintili[1].value,
          },
          { name: "Average", value: el.quintili[2].value },
          { name: "Above average", value: el.quintili[3].value },
          { name: "Wetter", value: el.quintili[4].value },
        ],
        soglie: el.soglie,
      });
    });

    return { temp: dataTemp, prec: dataPrec };
  }
  onSelect(event) {
    console.log(event);
  }
}
