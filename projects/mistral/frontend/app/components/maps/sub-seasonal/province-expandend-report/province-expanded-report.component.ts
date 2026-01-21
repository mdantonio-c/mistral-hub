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
  yLabel;
  province;

  public selectMetric(metric: "Temperature" | "Total Precipitation") {
    this.selectedMetric = metric;
    this.yLabel =
      metric === "Total Precipitation"
        ? "Precipitation (mm)"
        : "Temperature (°C)";
    this.cdr.detectChanges();
  }

  public beforeOpen(layerId: string) {
    this.cdr.detectChanges();
    this.changeProvinceName(this.prov);
    this.zone.run(() => this.cdr.markForCheck());
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
}
