import { Component, OnInit } from "@angular/core";
import * as L from "leaflet";
import {
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
} from "../meteo-tiles/meteo-tiles.config";
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
export class LivemapComponent implements OnInit {
  map: L.Map;
  options = {
    layers: [LAYER_OSM],
    zoomControl: false,
    zoom: 6,
    center: L.latLng(41.88, 12.28),
    maxBoundsViscosity: 1.0,
  };

  ngOnInit() {}

  onMapReady(map: L.Map) {
    this.map = map;
    this.map.attributionControl.setPrefix("");
  }

  onMapZoomEnd($event) {
    console.log(`Map Zoom: ${this.map.getZoom()}`);
  }
}
