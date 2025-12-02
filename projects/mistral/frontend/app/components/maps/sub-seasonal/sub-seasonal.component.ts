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
import { TilesService } from "../meteo-tiles/services/tiles.service";
@Component({
  selector: "app-sub-seasonal",
  templateUrl: "./sub-seasonal.component.html",
  styleUrls: ["./sub-seasonal.component.scss"],
})
export class SubSeasonalComponent extends BaseMapComponent implements OnInit {
  wmsPath;
  constructor(injector: Injector, private tileService: TilesService) {
    super(injector);
    this.options["layers"] = [this.LAYER_LIGHTMATTER];
    this.wmsPath = this.tileService.getWMSUrl();
  }

  options = {};

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

  protected centerMap() {}
  protected onMapReady(map: L.Map) {}
  public printDatasetProduct(): string {
    return "";
  }
  protected toggleLayer(obj: Record<string, string | L.Layer>) {}
  public printReferenceDate() {
    return "";
  }
}
