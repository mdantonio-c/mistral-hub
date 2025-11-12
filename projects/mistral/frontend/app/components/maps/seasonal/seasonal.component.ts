import { Component, OnInit, Injector } from "@angular/core";
import { BaseMapComponent } from "../base-map.component";
import * as L from "leaflet";
import {
  CARTODB_LICENSE_HREF,
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
} from "../meteo-tiles/meteo-tiles.config";
import { TilesService } from "../meteo-tiles/services/tiles.service";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { ProvinceReportComponent } from "./province-report/province-report.component";
import { NavigationEnd, Params } from "@angular/router";

const ICON_BOUNDS = {
  southWest: L.latLng(33.69, 2.9875),
  northEast: L.latLng(48.91, 22.0125),
};

const layerMap = {
  "Maximum temperature": [
    "meteohub:seasonal-mean-TM",
    "meteohub:seasonal-ano-max-TM",
  ],
  "Minimum temperature": [
    "meteohub:seasonal-mean-Tm",
    "meteohub:seasonal-ano-min-Tm",
  ],
  "Total precipitation": ["meteohub:seasonal-sum-P", "meteohub:seasonal-ano-P"],
};

@Component({
  selector: "app-seasonal",
  templateUrl: "./seasonal.component.html",
  styleUrls: ["./seasonal.component.scss"],
})
export class SeasonalComponent extends BaseMapComponent implements OnInit {
  maps: Record<"left" | "right", L.Map> = { left: null, right: null };
  bounds = new L.LatLngBounds(
    ICON_BOUNDS["southWest"],
    ICON_BOUNDS["northEast"],
  );
  private legendControl: Record<"left" | "right", L.Control> = {
    left: null,
    right: null,
  };
  private legendConfig = {
    "Maximum temperature": {
      left: [
        "/app/custom/assets/images/legends/seasonal/temperature.svg",
        "/app/custom/assets/images/legends/seasonal/horizontal/temperature.svg",
      ],
      right: [
        "/app/custom/assets/images/legends/seasonal/anomaly-temperature.svg",
        "/app/custom/assets/images/legends/seasonal/horizontal/anomaly-temperature.svg",
      ],
    },
    "Minimum temperature": {
      left: [
        "/app/custom/assets/images/legends/seasonal/temperature.svg",
        "/app/custom/assets/images/legends/seasonal/horizontal/temperature.svg",
      ],
      right: [
        "/app/custom/assets/images/legends/seasonal/anomaly-temperature.svg",
        "/app/custom/assets/images/legends/seasonal/horizontal/anomaly-temperature.svg",
      ],
    },
    "Total precipitation": {
      left: [
        "/app/custom/assets/images/legends/seasonal/precipitations.svg",
        "/app/custom/assets/images/legends/seasonal/horizontal/precipitations.svg",
      ],
      right: [
        "/app/custom/assets/images/legends/seasonal/anomaly-precipitations.svg",
        "/app/custom/assets/images/legends/seasonal/horizontal/anomaly-precipitations.svg",
      ],
    },
  };
  public run;
  private wmsPath: string;
  private mapsPath: string;
  private provinceData: any = null;
  private provinceDataPromise: Promise<any> | null = null;
  public lang = "en";
  private isMobile = false;
  private mediaQuery: MediaQueryList;
  // Leaflet does not allow you to reuse the same TileLayer instance on multiple maps.
  private createLightMatterLayer(): L.TileLayer {
    return L.tileLayer(
      "https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}{r}.png",
      {
        id: "mapbox.light",
        attribution: `&copy; ${CARTODB_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
        maxZoom: this.maxZoom - 4,
        minZoom: this.minZoom,
      },
    );
  }

  public variablesConfigFromChild: any;
  public selectedLayerId: string;
  public varDesc1: string;
  public varDesc2: string;
  private selectedMonth: string;
  public prov: string;
  public runDate: string;
  public maxZoomIn = this.maxZoom - 4;
  layersControl = {
    baseLayers: {
      "Carto Map Light": this.createLightMatterLayer(),
    },
  };

  optionsLeft = {
    zoomControl: false,
    minZoom: this.minZoom,
    maxZoom: this.maxZoom - 4,
    center: L.latLng([41.3, 12.5]),
    maxBounds: this.bounds,
    maxBoundsViscosity: 1.0,
    timeDimension: false,
    timeDimensionControl: false,
    attributionControl: false,
  };
  optionsRight = {
    zoomControl: false,
    minZoom: this.minZoom,
    maxZoom: this.maxZoom - 4,
    center: L.latLng([41.3, 12.5]),
    maxBounds: this.bounds,
    maxBoundsViscosity: 1.0,
    timeDimension: false,
    timeDimensionControl: false,
    attributionControl: false,
  };

  constructor(
    injector: Injector,
    private tilesService: TilesService,
    private modalService: NgbModal,
  ) {
    super(injector);
    this.optionsLeft["layers"] = [this.createLightMatterLayer()];
    this.optionsRight["layers"] = [this.createLightMatterLayer()];
    this.wmsPath = this.tilesService.getWMSUrl();
    this.mapsPath = this.tilesService.getMapsUrl();
    this.router.events.subscribe((s) => {
      if (s instanceof NavigationEnd) {
        const tree = this.router.parseUrl(this.router.url);
        if (tree.fragment) {
          const element = document.querySelector("#" + tree.fragment);
          if (element) {
            element.scrollIntoView(true);
          }
        }
      }
    });
  }

  override ngOnInit(): void {
    this.loadLatestRun();
    super.ngOnInit();

    this.mediaQuery = window.matchMedia("(max-width: 768px)");
    this.isMobile = this.mediaQuery.matches;
    this.mediaQuery.addEventListener("change", (e) => {
      this.isMobile = e.matches;
      this.updateLegends(this.selectedLayerId);
    });

    this.route.queryParams.subscribe((params: Params) => {
      const lang = params["lang"];
      if (["it", "en"].includes(lang)) {
        this.lang = lang;
      }
    });
  }

  protected onMapReady(map: L.Map) {}

  protected onMapReadyLeft(map: L.Map) {
    this.maps.left = map;
    //map.setView([41.3, 12.5], this.minZoom + 1);
    setTimeout(() => this.centerMap(), 200);
    this.layersControl["left_overlays"] = {};
    this.tryLoadWms("left");
    this.addGeojsonLayer(map);
    this.addIconBorderLayer(map);
    this.addProvinceBullets(map);
  }

  protected onMapReadyRight(map: L.Map) {
    //map.setView([41.3, 12.5], this.minZoom + 1);
    this.maps.right = map;
    setTimeout(() => this.centerMap(), 200);
    this.layersControl["right_overlays"] = {};
    this.tryLoadWms("right");
    this.addGeojsonLayer(map);
    this.addIconBorderLayer(map);
    this.addProvinceBullets(map);
  }
  getTileWms(layerId: string, time: string) {
    return L.tileLayer.wms(this.wmsPath, {
      layers: layerId,
      transparent: true,
      format: "image/png",
      tileSize: 1024,
      time: time,
    } as any);
  }
  protected toggleLayer(obj: Record<string, string | L.Layer>) {}
  protected centerMap() {
    const italyCenter = L.latLng(41.3, 12.5);

    if (this.maps.left) {
      this.maps.left.setView(italyCenter, this.minZoom + 0.5, {
        animate: false,
      });
      this.maps.left.invalidateSize({ pan: false, debounceMoveend: true });
    }

    if (this.maps.right) {
      this.maps.right.setView(italyCenter, this.minZoom + 0.5, {
        animate: false,
      });
      this.maps.right.invalidateSize({ pan: false, debounceMoveend: true });
    }
  }

  public printReferenceDate(): string {
    return "2025-10-22";
  }
  public printDatasetProduct(): string {
    return "";
  }
  public printDatasetDescription(): string {
    return "Seasonal";
  }
  public printVarDescSupport(layerId: string): string {
    return this.variablesConfigFromChild[layerId][2];
  }
  public receiveVariablesConfig(config: any) {
    this.variablesConfigFromChild = config;
  }
  public receiveLayerIdSelected(layerId: string) {
    this.selectedLayerId = layerId;
    setTimeout(() => {
      const varDesc = this.printVarDescSupport(layerId);
      const match = varDesc.match(/^(.*?)\s*\([^)]*\)\s*-\s*(.*)$/);
      if (match) {
        this.varDesc1 = match[1].trim();
        this.varDesc2 = match[2].trim();
      } else {
        this.varDesc1 = varDesc;
        this.varDesc2 = "";
      }
    });
    this.updateLegends(layerId);
    this.tryLoadWms("left");
    this.tryLoadWms("right");
  }
  public receiveMonth(monthTimeStamp: string) {
    this.selectedMonth = monthTimeStamp;
    this.tryLoadWms("left");
    this.tryLoadWms("right");
  }

  private tryLoadWms(mapKey: "left" | "right"): void {
    const map = this.maps[mapKey];
    if (!map || !this.selectedMonth || !this.selectedLayerId) {
      return;
    }
    if (this.layersControl[`${mapKey}_overlays`]) {
      map.removeLayer(this.layersControl[`${mapKey}_overlays`]);
    }
    let layer;
    if (mapKey == "left") {
      layer = this.getTileWms(
        layerMap[this.selectedLayerId][0],
        this.selectedMonth,
      )
        .setOpacity(0.6)
        .addTo(map);
      console.log(layerMap[this.selectedLayerId][0], this.selectedMonth);
    } else {
      layer = this.getTileWms(
        layerMap[this.selectedLayerId][1],
        this.selectedMonth,
      )
        .setOpacity(0.6)
        .addTo(map);
      console.log(layerMap[this.selectedLayerId][1], this.selectedMonth);
    }
    this.layersControl[`${mapKey}_overlays`] = layer;
  }

  private async loadGeojsonData(): Promise<void> {
    if (this.provinceData) return;
    if (this.provinceDataPromise) {
      await this.provinceDataPromise;
      return;
    }

    this.provinceDataPromise = fetch(
      "./app/custom/assets/images/geoJson/province.geojson",
    )
      .then((res) => res.json())
      .then((data) => {
        this.provinceData = data;
        this.provinceDataPromise = null;
      });

    await this.provinceDataPromise;
  }
  private async addGeojsonLayer(map: L.Map): Promise<void> {
    await this.loadGeojsonData();

    const layer = L.geoJSON(this.provinceData, {
      style: {
        color: "red",
        weight: 1,
        opacity: 0,
        fillOpacity: 0,
      },
      onEachFeature: (feature, layer) => {
        layer.on("click", (e) => {
          this.prov = feature.properties.DEN_UTS;
          this.openProvinceReport(this.prov);
        });
      },
    });

    layer.addTo(map);
  }
  private addIconBorderLayer(map: L.Map) {
    fetch("./app/custom/assets/images/geoJson/confini_italia.geojson")
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
  private addProvinceBullets(map: L.Map) {
    // Creo un pane per i bullets
    map.createPane("provinceBullets");
    const pane = map.getPane("provinceBullets");

    // Questo pane NON riceve eventi mouse → click passa al layer sottostante
    pane.style.zIndex = "450";
    pane.style.pointerEvents = "none";

    fetch("./app/custom/assets/images/geoJson/province_bullet.geojson")
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
              weight: 2,
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
              this.openProvinceReport(feature.properties.name, marker);
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

  private openProvinceReport(prov: string, m: L.CircleMarker | null = null) {
    const modalRef = this.modalService.open(ProvinceReportComponent, {
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
    modalRef.componentInstance.beforeOpen();
  }

  private async loadLatestRun(): Promise<void> {
    try {
      const response = await fetch(this.mapsPath + `/api/seasonal/latest`);
      const data = await response.json();
      const date = new Date(data.ingestion.last);
      const month = date.getMonth() + 1;
      //this.run = month;
      this.run = 11;
      this.runDate = new Intl.DateTimeFormat("it-IT", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      }).format(date);
    } catch (error) {
      console.error("Error fetch /api/seasonal/latest:", error);
    }
  }

  public onCollapse(isCollapsed: boolean): void {
    setTimeout(() => {
      if (this.maps.left) {
        this.maps.left.invalidateSize();
      }
      if (this.maps.right) {
        this.maps.right.invalidateSize();
      }
    }, 30);
  }

  private addLegendSvg(mapKey: "left" | "right", svgPath: string) {
    const map = this.maps[mapKey];
    if (!map) return;
    const legend = new L.Control({ position: "bottomleft" });
    legend.onAdd = () => {
      let div = L.DomUtil.create("div");
      div.style.clear = "unset";
      div.innerHTML += `<img class="legenda" src="${svgPath}">`;
      return div;
    };
    legend.addTo(map);
    this.legendControl[mapKey] = legend;
  }
  private updateLegends(layerId: string) {
    if (!this.selectedLayerId) return;
    const config = this.legendConfig[layerId];
    if (!config) return;
    if (this.maps.left) {
      this.removeLegend("left");
      if (this.isMobile) {
        this.addLegendSvg("left", config.left[1]);
        console.log("entrato left");
      } else {
        this.addLegendSvg("left", config.left[0]);
      }
    }
    if (this.maps.right) {
      this.removeLegend("right");
      if (this.isMobile) {
        this.addLegendSvg("right", config.right[1]);
        console.log("entrato right");
      } else {
        this.addLegendSvg("right", config.right[0]);
      }
    }
  }
  private removeLegend(mapKey: "left" | "right") {
    if (this.legendControl[mapKey]) {
      this.legendControl[mapKey].remove();
      this.legendControl[mapKey] = null;
    }
  }
}
