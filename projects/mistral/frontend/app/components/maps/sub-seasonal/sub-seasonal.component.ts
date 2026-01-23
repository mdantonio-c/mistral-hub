import { BaseMapComponent } from "../base-map.component";
import {
  Component,
  Injector,
  Input,
  OnInit,
  ChangeDetectorRef,
} from "@angular/core";
import * as L from "leaflet";
import {
  CARTODB_LICENSE_HREF,
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
  STADIA_LICENSE_HREF,
  ViewModes,
} from "../meteo-tiles/meteo-tiles.config";
import { Params } from "@angular/router";
import * as moment from "moment";
import { Variables, Layers, legendConfig } from "./side-nav/data";
import { TilesService } from "../meteo-tiles/services/tiles.service";
import { environment } from "@rapydo/../environments/environment";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { ProvinceExpandedReportComponent } from "./province-expandend-report/province-expanded-report.component";

@Component({
  selector: "app-sub-seasonal",
  templateUrl: "./sub-seasonal.component.html",
  styleUrls: ["./sub-seasonal.component.scss"],
})
export class SubSeasonalComponent extends BaseMapComponent implements OnInit {
  @Input() minZoom: number = 4;
  @Input() maxZoom: number = 7;

  selectedWeek;
  selectedLayer;
  wmsPath;
  run;
  weekList = [];
  bounds = new L.LatLngBounds(new L.LatLng(25, -20), new L.LatLng(55, 50));
  private maps_url: string = "";
  private legendControl;
  constructor(
    injector: Injector,
    private tileService: TilesService,
    private modalService: NgbModal,
    private cdr: ChangeDetectorRef,
  ) {
    super(injector);
    this.options["layers"] = [this.LAYER_LIGHTMATTER];
    this.wmsPath = this.tileService.getWMSUrl();
    this.selectedLayer = Variables[Object.keys(Variables)[0]].label;
    this.maps_url = environment.CUSTOM.MAPS_URL;
  }

  options = {
    zoomControl: false,
    // center: L.latLng([41.3, 12.5]),
    maxBoundsViscosity: 1.0,
    maxBounds: this.bounds,
    minZoom: this.minZoom,
    maxZoom: this.maxZoom,
    timeDimension: false,
    timeDimensionControl: false,
  };

  LAYER_LIGHTMATTER = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}{r}.png",
    {
      id: "mapbox.light",
      attribution: `&copy; ${CARTODB_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
      maxZoom: this.maxZoom,
      minZoom: this.minZoom,
    },
  );

  layersControl = {
    baseLayers: {
      "Carto Map Light": this.LAYER_LIGHTMATTER,
    },
  };

  protected centerMap() {
    if (this.map) {
      //const mapCenter = super.getMapCenter();
      // map center for ICON
      const mapCenter = L.latLng(45, 12.5);
      this.map.fitBounds(this.bounds);
      this.map.setZoom(this.minZoom + 1);
    }
  }
  public receiveWeek(week: string) {
    try {
      console.log("week", week);
      this.selectedWeek = week;
      this.toggleLayer(this.selectedLayer, true);
    } catch (error) {
      console.log("Error in defining week", error);
    }
  }
  protected onMapReady(map: L.Map) {
    this.map = map;
    setTimeout(() => {
      this.map.setView([41.3, 12.5], 5);
    }, 200);
    //this.centerMap();
    this.addIBorderLayer(map);
    this.addProvinceBullets(map);
  }

  ngOnInit(): void {
    super.ngOnInit();
    this.loadWeeks();
    this.route.queryParams.subscribe((params: Params) => {
      const lang = params["lang"];
      if (["it", "en"].includes(lang)) {
        this.lang = lang;
      }
    });
  }
  public printDatasetDescription(): string {
    return "Sub-seasonal";
  }
  public printVarDescSupport(layerId: string): string {
    return "";
  }
  public printDatasetProduct(): string {
    return "";
  }
  protected toggleLayer(obj, receiveWeek: boolean = false) {
    try {
      if (!receiveWeek) this.selectedLayer = Variables[obj].label;
      else this.selectedLayer = obj;
      if (this.map.hasLayer(this.layersControl["overlays"])) {
        this.map.removeLayer(this.layersControl["overlays"]);
      }
      const key = Object.keys(Variables).find(
        (k) => Variables[k].label === this.selectedLayer,
      );
      const date = this.extractAndFormatDate(this.selectedWeek);
      this.addLayerGroup(key, date);
      this.layersControl["overlays"].addTo(this.map);
      this.updateLegends(key);
    } catch (error) {
      console.log("Error in toggling layer", error);
    }
  }
  public printReferenceDate() {
    return "";
  }

  getTileWms(layerId: string, time: string) {
    const isMobile = L.Browser.mobile;
    return L.tileLayer.wms(this.wmsPath, {
      layers: layerId,
      transparent: true,
      format: "image/png",
      tileSize: isMobile ? 256 : 1024,
      time: time,
    } as any);
  }
  public loadWeeks(reload: boolean = false) {
    fetch(`${this.maps_url}/api/sub-seasonal/status`)
      .then((response) => response.json())
      .then((data) => {
        const from = new Date(data.from);
        const to = new Date(data.to);
        this.run = `${data.run.slice(6, 8)}-${data.run.slice(
          4,
          6,
        )}-${data.run.slice(0, 4)}`;
        this.weekList = this.getWeeksBetween(from, to);
        this.afterWeeksLoaded();
      });
  }
  private getWeeksBetween(from: Date, to: Date): string[] {
    try {
      const format = (d: Date) =>
        `${String(d.getDate()).padStart(2, "0")}/${String(
          d.getMonth() + 1,
        ).padStart(2, "0")}/${d.getFullYear()}`;

      const weeks: string[] = [];

      let current = new Date(from);

      while (current <= to) {
        const start = new Date(current);
        const end = new Date(current);
        end.setDate(end.getDate() + 6);

        weeks.push(`${format(start)} - ${format(end)}`);
        current.setDate(current.getDate() + 7);
      }

      return weeks;
    } catch (error) {
      console.log("Error in getting weeks", error);
      return [];
    }
  }

  private afterWeeksLoaded() {
    try {
      if (!this.map) return;
      const key = Object.keys(Variables).find(
        (k) => Variables[k].label === this.selectedLayer,
      );
      const firstWeekDate = this.extractAndFormatDate(this.weekList[0]);
      this.selectedWeek = this.weekList[0];
      this.addLayerGroup(key, firstWeekDate);
      this.layersControl["overlays"].addTo(this.map);
      this.updateLegends(key);
    } catch (error) {
      console.error("Error in loading weeks", error);
    }
  }
  private extractAndFormatDate(rangeString) {
    const firstPart = rangeString.split(" - ")[0];
    const [day, month, year] = firstPart.split("/");
    return `${year}-${month}-${day}`;
  }

  private addLayerGroup(key, date) {
    try {
      if (!Layers[key]) {
        throw new Error(`Layer ${key} not found`);
      }
      const terzile1 = this.getTileWms(Layers[key].terzile_1, date).setOpacity(
        0.6,
      );
      const terzile2 = this.getTileWms(Layers[key].terzile_2, date).setOpacity(
        0.6,
      );
      const terzile3 = this.getTileWms(Layers[key].terzile_3, date).setOpacity(
        0.6,
      );
      const quintile1 = this.getTileWms(
        Layers[key].quintile_1,
        date,
      ).setOpacity(0.6);
      const quintile5 = this.getTileWms(
        Layers[key].quintile_5,
        date,
      ).setOpacity(0.6);
      const layerGroup = L.layerGroup([
        terzile1,
        terzile2,
        terzile3,
        quintile1,
        quintile5,
      ]);
      this.layersControl["overlays"] = layerGroup;
    } catch (error) {
      console.error("Error in adding layer group", error);
    }
  }

  private addIBorderLayer(map: L.Map) {
    fetch("./app/custom/assets/images/geoJson/confini_mediterraneo.geojson")
      .then((response) => response.json())
      .then((data) => {
        L.geoJSON(data, {
          style: {
            color: "black",
            weight: 1,
            opacity: 1,
          },
        }).addTo(map);
      });
  }

  private addLegendSvg(svgPath: string) {
    if (!this.map) return;
    if (this.legendControl) this.legendControl.remove();
    this.legendControl = new L.Control({ position: "bottomleft" });
    this.legendControl.onAdd = () => {
      let div = L.DomUtil.create("div");
      div.style.clear = "unset";
      div.innerHTML += `<img class="legenda" src="${svgPath}">`;
      return div;
    };
    this.legendControl.addTo(this.map);
  }

  private updateLegends(layerId: string) {
    const config = legendConfig[layerId];
    if (!config) return;
    this.addLegendSvg(config);
  }

  private addProvinceBullets(map: L.Map) {
    map.createPane("provinceBullets");
    const pane = map.getPane("provinceBullets");

    pane.style.zIndex = "450";
    pane.style.pointerEvents = "none";

    fetch("./app/custom/assets/images/geoJson/province_bullet_expanded.geojson")
      .then((response) => response.json())
      .then((data) => {
        const geoJsonLayer = L.geoJSON(data, {
          pointToLayer: (feature, latlng) => {
            const provinceName = feature.properties.name2
              ? feature.properties.name2
              : feature.properties.name;

            const marker = L.circleMarker(latlng, {
              radius: 3,
              fillColor: "#000",
              color: "#fff",
              weight: 1,
              fillOpacity: 1,
              pane: "provinceBullets",
              interactive: true,
            });

            // Tooltip
            marker.bindTooltip(provinceName, {
              direction: "top",
              offset: L.point(0, -12),
              className: "province-tooltip",
              permanent: false,
              sticky: false,
              interactive: false,
            });

            // Hover tooltip
            marker.on("mouseover", () => marker.openTooltip());
            marker.on("mouseout", () => marker.closeTooltip());
            marker.on("click", () => {
              console.log(this.selectedLayer);
              this.openProvinceReport(
                feature.properties.name,
                marker,
                this.selectedLayer,
              );
            });

            return marker;
          },
        });

        geoJsonLayer.addTo(map);
      })
      .catch((error) =>
        console.error("Errore downloading Province bullet geojson:", error),
      );
  }

  private openProvinceReport(
    prov: string,
    m: L.CircleMarker | null = null,
    layerId: string,
  ) {
    const modalRef = this.modalService.open(ProvinceExpandedReportComponent, {
      size: "xl",
      centered: true,
    });
    if (m instanceof L.CircleMarker) {
      const tooltip = m.getTooltip();
      modalRef.result.finally(() => {
        setTimeout(() => {
          m.bindTooltip(tooltip);
          m.closeTooltip();
        }, 0);
      });
    }
    modalRef.componentInstance.lang = this.lang;
    modalRef.componentInstance.prov = prov;
    modalRef.componentInstance.beforeOpen(this.selectedLayer);
    modalRef.componentInstance.weekList = this.weekList;
  }
}
