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
  public run;
  private wmsPath: string;
  private mapsPath: string;
  private provinceData: any = null;
  private provinceDataPromise: Promise<any> | null = null;
  public lang = "en";
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
  }

  protected onMapReadyRight(map: L.Map) {
    //map.setView([41.3, 12.5], this.minZoom + 1);
    this.maps.right = map;
    setTimeout(() => this.centerMap(), 200);
    this.layersControl["right_overlays"] = {};
    this.tryLoadWms("right");
    this.addGeojsonLayer(map);
    this.addIconBorderLayer(map);
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
  /*  protected centerMap() {
    if (this.maps.left) {
      const mapCenter = L.latLng(41.3, 12.5);
      this.maps.left.setMaxZoom(this.maxZoom - 1);
      this.maps.left.fitBounds(this.bounds);
    }
    if (this.maps.right) {
      const mapCenter = L.latLng(41.3, 12.5);
      this.maps.right.setMaxZoom(this.maxZoom - 1);
      this.maps.right.fitBounds(this.bounds);
    }
  }*/
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
  private openProvinceReport(prov: string) {
    const modalRef = this.modalService.open(ProvinceReportComponent, {
      size: "xl",
      centered: true,
    });
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
      this.run = month;
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
}
