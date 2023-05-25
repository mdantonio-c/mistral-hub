import { Component, OnInit, Input, OnDestroy, Injector } from "@angular/core";
import * as L from "leaflet";
import * as moment from "moment";
import { MOBILE_WIDTH, ViewModes } from "./meteo-tiles/meteo-tiles.config";
import { GenericArg, Station } from "../../types";
import { NotificationService } from "@rapydo/services/notification";
import { SharedService } from "@rapydo/services/shared-service";
import { NgxSpinnerService } from "ngx-spinner";
import { ActivatedRoute, Params, Router } from "@angular/router";
import { map } from "rxjs";

const MAP_CENTER = L.latLng(41.879966, 12.28),
  LNG_OFFSET = 2.3;

@Component({
  selector: "mst-base-map",
  template: "",
})
export abstract class BaseMapComponent implements OnInit, OnDestroy {
  map: L.Map;
  modes = ViewModes;
  viewMode = ViewModes.adv;
  iframeMode = false;
  variablesConfig: GenericArg;
  lang = "en";
  collapsed: boolean = false;
  @Input() minZoom: number = 5;
  @Input() maxZoom: number = 12;

  protected notify: NotificationService;
  protected spinner: NgxSpinnerService;
  protected router: Router;
  protected route: ActivatedRoute;
  protected sharedService: SharedService;

  protected constructor(injector: Injector) {
    this.notify = injector.get(NotificationService);
    this.spinner = injector.get(NgxSpinnerService);
    this.router = injector.get(Router);
    this.route = injector.get(ActivatedRoute);
    this.sharedService = injector.get(SharedService);
  }

  ngOnInit(): void {
    this.route.queryParamMap
      .pipe(
        map((params) => {
          const value = params.get("iframe");
          return value ? value.toLocaleLowerCase() === "true" : false;
        }),
      )
      .subscribe((iframe) => {
        if (!iframe) return;
        this.sharedService.emitChange(true);
      });
  }

  ngOnDestroy() {
    if (null != this.map) {
      this.map.remove();
    }
  }

  protected abstract onMapReady(map: L.Map);

  protected onMapZoomEnd($event) {
    // console.log(`Map Zoom: ${this.map.getZoom()}`);
    // DO NOTHING
  }

  protected abstract toggleLayer(obj: Record<string, string | L.Layer>);

  protected reduceOverlapping(markers: L.Marker[]) {
    let n: L.Marker[] = [];
    if (this.map.getZoom() === this.maxZoom) {
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
    console.log(`number of markers reduced to ${n.length}`);
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
    if (this.map && window.innerWidth > MOBILE_WIDTH) {
      const panelWidth = 100;
      let lngOffset = this.collapsed ? panelWidth : -panelWidth;
      this.panToOffset(this.map.getCenter(), [lngOffset, 0], { animate: true });
    }
  }

  protected static buildTooltipTemplate(
    station: Station,
    reftime?: string,
    val?: string,
  ) {
    let ident = station.ident || "";
    let name =
      station.details && station.details.length
        ? station.details.find((e) => e.var === "B01019")
        : undefined;
    const template =
      `<h6 class="mb-1" style="font-size: small;">` +
      (name ? `${name.val}` : "n/a") +
      `<span class="badge bg-secondary ms-2">${val}</span></h6>` +
      `<ul class="p-0 m-0"><li><b>Lat</b>: ${station.lat}</li><li><b>Lon</b>: ${station.lon}</li></ul>` +
      `<hr class="my-1"/>` +
      `<span>` +
      (reftime ? `${moment.utc(reftime).format("MMM Do, HH:mm")}` : "n/a") +
      `</span>`;
    return template;
  }

  protected abstract centerMap();

  protected getMapCenter(): L.LatLng | null {
    let mapCenter: L.LatLng = null;
    if (this.map) {
      let lng =
        this.collapsed || window.innerWidth < MOBILE_WIDTH
          ? MAP_CENTER.lng
          : MAP_CENTER.lng + LNG_OFFSET;
      mapCenter = L.latLng(MAP_CENTER.lat, lng);
    }
    return mapCenter;
  }

  public abstract printReferenceDate(): string;
  public abstract printDatasetProduct(): string;

  public panToOffset(
    latlng: L.LatLng,
    offset,
    options: L.PanOptions,
  ): L.LatLng {
    let x = this.map.latLngToContainerPoint(latlng).x - offset[0];
    let y = this.map.latLngToContainerPoint(latlng).y - offset[1];
    let point = this.map.containerPointToLatLng([x, y]);
    this.map.panTo(point, options);
    return point;
  }
}
