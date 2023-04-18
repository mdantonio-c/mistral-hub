import { Component, OnInit } from "@angular/core";
import * as L from "leaflet";
import { ViewModes } from "./meteo-tiles/meteo-tiles.config";
import { GenericArg } from "../../types";
import { VARIABLES_CONFIG } from "./meteo-tiles/services/data";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";

const MAX_ZOOM = 8;
const MIN_ZOOM = 5;

@Component({
  selector: "mst-base-map",
  template: "",
})
export abstract class BaseMapComponent implements OnInit {
  map: L.Map;
  modes = ViewModes;
  viewMode = ViewModes.adv;
  variablesConfig: GenericArg = VARIABLES_CONFIG;
  lang = "en";
  collapsed: boolean = false;

  protected constructor(
    protected notify: NotificationService,
    protected spinner: NgxSpinnerService,
  ) {}

  ngOnInit(): void {}

  protected abstract onMapReady(map: L.Map);

  protected abstract toggleLayer(obj: Record<string, string | L.Layer>);

  protected reduceOverlapping(markers: L.Marker[]) {
    let n: L.Marker[] = [];
    if (this.map.getZoom() === MAX_ZOOM) {
      return markers;
    }
    const radius = 10 * Math.pow(2, 8 - this.map.getZoom());
    // console.log(`radius: ${radius}`);
    for (let i = 0; i < markers.length; i++) {
      let overlapped: boolean = false;
      if (n.length > 0) {
        let p1 = markers[i].getLatLng();
        for (let j = 0; j < n.length; j++) {
          let p2 = n[j].getLatLng();
          let distance = this.distance(p1.lat, p1.lng, p2.lat, p2.lng, "K");
          if (distance < radius) {
            overlapped = true;
            break;
          }
        }
        if (!overlapped) {
          n.push(markers[i]);
        }
      } else {
        n.push(markers[i]);
      }
    }
    // console.log(`number of markers reduced to ${n.length}`);
    return n;
  }

  /**
   * This routine calculates the distance between two points (given the
   * latitude/longitude of those points).
   *
   * Definitions:
   * South latitudes are negative, east longitudes are positive
   *
   * @param lat1
   *   Latitude of point 1 (in decimal degrees)
   * @param lon1
   *   Longitude of point 1 (in decimal degrees)
   * @param lat2
   *   Latitude of point 2 (in decimal degrees)
   * @param lon2
   *   Longitude of point 2 (in decimal degrees)
   * @param unit
   *    the unit you desire for results. Allowed values:
   *    'M' is statute miles (default)
   *    'K' is kilometers
   *    'N' is nautical miles
   * @private
   */
  private distance(lat1, lon1, lat2, lon2, unit) {
    if (lat1 == lat2 && lon1 == lon2) {
      return 0;
    } else {
      const radlat1 = (Math.PI * lat1) / 180;
      const radlat2 = (Math.PI * lat2) / 180;
      const theta = lon1 - lon2;
      const radtheta = (Math.PI * theta) / 180;
      let dist =
        Math.sin(radlat1) * Math.sin(radlat2) +
        Math.cos(radlat1) * Math.cos(radlat2) * Math.cos(radtheta);
      if (dist > 1) {
        dist = 1;
      }
      dist = Math.acos(dist);
      dist = (dist * 180) / Math.PI;
      dist = dist * 60 * 1.1515;
      if (unit == "K") {
        dist = dist * 1.609344;
      }
      if (unit == "N") {
        dist = dist * 0.8684;
      }
      return dist;
    }
  }

  onCollapse(event: boolean) {
    this.collapsed = event;
  }
}
