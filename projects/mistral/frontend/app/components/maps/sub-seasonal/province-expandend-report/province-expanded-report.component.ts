import {
  Component,
  Input,
  ChangeDetectorRef,
  NgZone,
  TemplateRef,
  ViewChild,
  ElementRef,
  AfterViewInit,
} from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import { NgxSpinnerService } from "ngx-spinner";

@Component({
  selector: "app-province-expanded-report",
  templateUrl: "./province-expanded-report.component.html",
  styleUrls: ["./province-expanded-report.component.scss"],
})
export class ProvinceExpandedReportComponent implements AfterViewInit {
  @ViewChild("tooltipTemplate", { static: true })
  tooltipTemplate: TemplateRef<any>;

  @ViewChild("containerRef", { static: false })
  containerRef: ElementRef;

  constructor(
    public activeModal: NgbActiveModal,
    private spinner: NgxSpinnerService,
    private cdr: ChangeDetectorRef,
    private zone: NgZone,
  ) {}

  @Input() lang!: string;
  @Input() prov!: string;
  @Input() weekList!: string[];
  selectedMetric: "Temperature" | "Total Precipitation" = "Temperature";
  yLabel = "Probability (%)";
  province;
  multi;
  processedData;

  colorSchemeTemp = {
    domain: ["#003366", "#99CCFF", "#E0E0E0", "#FF9999", "#8B0000"],
  };

  colorSchemePrec = {
    domain: ["#E65100", "#FFB300", "#E0E0E0", "#66BB6A", "#1B5E20"],
  };
  colorScheme = this.colorSchemeTemp;
  ngAfterViewInit() {
    setTimeout(() => {
      this.calculateLabelPositions();
    }, 500);
  }

  calculateLabelPositions() {
    if (!this.multi) return;
    const existingTexts = document.querySelectorAll(".bar-label-text");
    existingTexts.forEach((el) => el.remove());

    const seriesGroups = document.querySelectorAll(
      "g[ngx-charts-series-vertical]",
    );
    //console.log(seriesGroups);
    this.multi.forEach((week, weekIndex) => {
      //if(weekIndex===0) console.log(seriesGroups.length,this.multi.length);
      if (seriesGroups[weekIndex]) {
        const innerContainer =
          seriesGroups[weekIndex].querySelector("g.ng-star-inserted");
        //console.log(innerContainer);
        if (innerContainer) {
          const allBars = innerContainer.querySelectorAll("g[ngx-charts-bar]");
          const barsInWeek = Array.from(allBars).filter((barGroup) => {
            return !barGroup.classList.contains("ng-animating");
          });
          //console.log(barsInWeek);
          barsInWeek.forEach((barGroup, barIndex) => {
            const pathElement = barGroup.querySelector(
              "path.bar",
            ) as SVGGraphicsElement;

            if (pathElement && !pathElement.classList.contains("hidden")) {
              //const value=pathElement.ariaLabel.slice(-6).slice(0, 2);
              const value = week.series[barIndex]?.value;

              const bbox = pathElement.getBBox();
              //console.log(pathElement,value,bbox);
              if (bbox.height > 20) {
                //const value = week.series[barIndex].value;
                const text = document.createElementNS(
                  "http://www.w3.org/2000/svg",
                  "text",
                );
                const centerX = bbox.x + bbox.width / 2;
                const centerY = bbox.y + bbox.height / 2;
                text.setAttribute("x", centerX.toString());
                text.setAttribute("y", centerY.toString());
                text.setAttribute("text-anchor", "middle");
                text.setAttribute("dominant-baseline", "middle");
                text.setAttribute("fill", "white");
                text.setAttribute("font-size", "11");
                text.setAttribute("font-weight", "600");
                text.setAttribute("pointer-events", "none");
                text.style.textShadow = "0 0 3px rgba(0,0,0,0.8)";
                text.classList.add("bar-label-text");
                text.textContent = `${value}%`;
                pathElement.parentElement?.appendChild(text);
              }
            }
          });
        }
      }
    });
  }
  public getThresholds(
    weekName: string,
    layerId: string,
    quintile: string,
  ): string {
    if (!this.multi) return "";

    const weekData = this.multi.find((w) => w.name === weekName);
    if (!weekData || !weekData.soglie) return "";

    const quintileMap = {
      Colder: [0, 1],
      Drier: [0, 1],
      "Below average": [1, 2],
      Average: [2, 3],
      "Above average": [3, 4],
      Warmer: [4, 5],
      Wetter: [4, 5],
    };

    const indices = quintileMap[quintile];
    if (!indices) return "";

    const unit = layerId === "Temperature" ? "°C" : "mm";
    const minThreshold = weekData.soglie[indices[0]].value;
    const maxThreshold = weekData.soglie[indices[1]].value;

    return `${minThreshold}${unit} - ${maxThreshold}${unit}`;
  }

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

    setTimeout(() => {
      this.calculateLabelPositions();
    }, 500);
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

    dataTempSet.forEach((el, index) => {
      dataTemp.push({
        name: this.weekList[index].slice(0, -13),
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
    dataPrecSet.forEach((el, index) => {
      dataPrec.push({
        name: this.weekList[index].slice(0, -13),
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
