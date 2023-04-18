import { Component, OnInit } from "@angular/core";
import * as L from "leaflet";
import {
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
  ViewModes,
} from "../meteo-tiles/meteo-tiles.config";
import { BaseMapComponent } from "../base-map.component";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";

const LAYER_OSM = L.tileLayer(
  "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  {
    attribution: `&copy; ${OSM_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
  },
);

@Component({
  selector: "app-livemap",
  templateUrl: "./livemap.component.html",
  styleUrls: ["./livemap.component.scss"],
})
export class LivemapComponent extends BaseMapComponent implements OnInit {
  layersControl = {
    baseLayers: {
      "Openstreet Map": LAYER_OSM,
    },
  };
  options = {
    layers: [LAYER_OSM],
    zoomControl: false,
    zoom: 6,
    center: L.latLng(41.88, 12.28),
    maxBoundsViscosity: 1.0,
  };
  viewMode = ViewModes.adv;

  constructor(
    public notify: NotificationService,
    public spinner: NgxSpinnerService,
  ) {
    super(notify, spinner);
  }

  ngOnInit() {}

  onMapReady(map: L.Map) {
    this.map = map;
    this.map.attributionControl.setPrefix("");
  }

  onMapZoomEnd($event) {
    console.log(`Map Zoom: ${this.map.getZoom()}`);
  }

  toggleLayer(obj: Record<string, string | L.Layer>) {
    console.log("toggle layer");
  }
}
