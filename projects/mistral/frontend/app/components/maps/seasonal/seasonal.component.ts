import { Component, OnInit, Injector } from "@angular/core";
import { BaseMapComponent } from "../base-map.component";
import * as L from "leaflet";
import {
  CARTODB_LICENSE_HREF,
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
} from "../meteo-tiles/meteo-tiles.config";
import { TilesService } from "../meteo-tiles/services/tiles.service";

const ICON_BOUNDS = {
  southWest: L.latLng(33.69, 2.9875),
  northEast: L.latLng(48.91, 22.0125),
};

const layerMap = {
  "Maximum temperature": ["meteo-hub:mean_TM", "meteo-hub:ano_max_TM"],
  "Minimum temperature": ["meteo-hub:mean_Tm", "meteo-hub:ano_min_Tm"],
  "Total monthly precipitation": ["meteo-hub:sum_P", "meteo-hub:ano_P"],
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
  // Leaflet does not allow you to reuse the same TileLayer instance on multiple maps.
  private createLightMatterLayer(): L.TileLayer {
    return L.tileLayer(
      "https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}{r}.png",
      {
        id: "mapbox.light",
        attribution: `&copy; ${CARTODB_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
        maxZoom: this.maxZoom,
        minZoom: this.minZoom,
      },
    );
  }

  public variablesConfigFromChild: any;
  public selectedLayerId: string;
  public varDesc;
  private selectedMonth: string;

  layersControl = {
    baseLayers: {
      "Carto Map Light": this.createLightMatterLayer(),
    },
  };

  optionsLeft = {
    zoomControl: false,
    minZoom: this.minZoom,
    maxZoom: this.maxZoom - 1,
    center: L.latLng([41.3, 12.5]),
    maxBounds: this.bounds,
    maxBoundsViscosity: 1.0,
    timeDimension: false,
    timeDimensionControl: false,
  };
  optionsRight = {
    zoomControl: false,
    minZoom: this.minZoom,
    maxZoom: this.maxZoom - 1,
    center: L.latLng([41.3, 12.5]),
    maxBounds: this.bounds,
    maxBoundsViscosity: 1.0,
    timeDimension: false,
    timeDimensionControl: false,
  };

  constructor(injector: Injector, private tilesService: TilesService) {
    super(injector);
    this.optionsLeft["layers"] = [this.createLightMatterLayer()];
    this.optionsRight["layers"] = [this.createLightMatterLayer()];
    this.wmsPath = this.tilesService.getWMSUrl();
  }

  override ngOnInit(): void {
    super.ngOnInit();
    this.run = 10;
  }

  protected onMapReady(map: L.Map) {}
  protected onMapReadyLeft(map: L.Map) {
    this.maps.left = map;
    map.setView([41.3, 12.5], this.minZoom + 1);
    this.layersControl["left_overlays"] = {};
    this.tryLoadWms("left");
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

  protected onMapReadyRight(map: L.Map) {
    this.maps.right = map;
    map.setView([41.3, 12.5], this.minZoom + 1);
    this.layersControl["right_overlays"] = {};
    this.tryLoadWms("right");
  }
  protected toggleLayer(obj: Record<string, string | L.Layer>) {}
  protected centerMap() {
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
  }

  public printReferenceDate(): string {
    return "2025-10-22";
  }
  public printDatasetProduct(): string {
    return "01/10/2025";
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
    this.varDesc = this.printVarDescSupport(layerId);
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
}
