import { BaseMapComponent } from "../base-map.component";
import { Component, Injector, Input, OnInit } from "@angular/core";
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
import { Variables } from "./side-nav/data";
import { TilesService } from "../meteo-tiles/services/tiles.service";
@Component({
  selector: "app-sub-seasonal",
  templateUrl: "./sub-seasonal.component.html",
  styleUrls: ["./sub-seasonal.component.scss"],
})
export class SubSeasonalComponent extends BaseMapComponent implements OnInit {
  @Input() minZoom: number = 5;
  @Input() maxZoom: number = 9;

  selectedLayer;
  wmsPath;
  run;
  bounds = new L.LatLngBounds(new L.LatLng(30, -20), new L.LatLng(55, 50));
  constructor(injector: Injector, private tileService: TilesService) {
    super(injector);
    this.options["layers"] = [this.LAYER_LIGHTMATTER];
    this.wmsPath = this.tileService.getWMSUrl();
    this.selectedLayer = Variables[Object.keys(Variables)[0]].label;
  }

  options = {
    zoomControl: false,
    center: L.latLng(41.88, 12.28),
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
      const mapCenter = L.latLng(41.3, 12.5);

      this.map.setMaxZoom(this.maxZoom - 1);

      this.map.fitBounds(this.bounds);
    }
  }
  protected onMapReady(map: L.Map) {
    this.map = map;
    this.centerMap();
  }
  public printDatasetProduct(): string {
    return "";
  }
  protected toggleLayer(obj: Record<string, string | L.Layer>) {}
  public printReferenceDate() {
    return "";
  }
  public handleRun(runLabel: string) {
    this.run = runLabel;
  }
}
