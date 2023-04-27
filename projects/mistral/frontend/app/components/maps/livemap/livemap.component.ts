import { Component, OnInit } from "@angular/core";
import * as L from "leaflet";
import * as moment from "moment";
import {
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
  ViewModes,
} from "../meteo-tiles/meteo-tiles.config";
import { BaseMapComponent } from "../base-map.component";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import { ActivatedRoute, NavigationEnd, Params, Router } from "@angular/router";
import { VARIABLES_CONFIG_OBS } from "../meteo-tiles/services/data";
import {
  ObsFilter,
  ObservationResponse,
  ObsData,
  Observation,
  ObsValue,
} from "../../../types";
import { ObsService } from "../observation-maps/services/obs.service";

const MAX_ZOOM = 12;
const MIN_ZOOM = 5;

const LAYER_OSM = L.tileLayer(
  "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  {
    attribution: `&copy; ${OSM_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
    maxZoom: MAX_ZOOM,
    minZoom: MIN_ZOOM,
  },
);

@Component({
  selector: "app-livemap",
  templateUrl: "./livemap.component.html",
  styleUrls: ["./livemap.component.scss"],
})
export class LivemapComponent extends BaseMapComponent implements OnInit {
  bounds = new L.LatLngBounds(new L.LatLng(30, -20), new L.LatLng(55, 50));
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
    maxBounds: this.bounds,
  };
  viewMode = ViewModes.adv;

  private markers: L.Marker[] = [];
  private allMarkers: L.Marker[] = [];
  private markersGroup: L.LayerGroup;

  private filter: ObsFilter;

  constructor(
    public notify: NotificationService,
    public spinner: NgxSpinnerService,
    private obsService: ObsService,
    private router: Router,
    private route: ActivatedRoute,
  ) {
    super(notify, spinner);
  }

  ngOnInit() {
    this.variablesConfig = VARIABLES_CONFIG_OBS;
    this.route.queryParams.subscribe((params: Params) => {
      const lang: string = params["lang"];
      if (["it", "en"].includes(lang)) {
        this.lang = lang;
      }
    });
  }

  onMapReady(map: L.Map) {
    this.map = map;
    this.map.attributionControl.setPrefix("");

    // add default layer
    const filter: ObsFilter = {
      // common parameters
      reftime: new Date(),
      license: "CCBY_COMPLIANT",
      time: [0, 23],
      onlyStations: false,
      reliabilityCheck: true,

      // temperature
      product: VARIABLES_CONFIG_OBS["t2m"].code,
      timerange: VARIABLES_CONFIG_OBS["t2m"].timerange,
      level: VARIABLES_CONFIG_OBS["t2m"].level,
    };
    this.filter = filter;
    this.loadObservations(filter, true);
    this.centerMap();
  }

  onMapZoomEnd($event) {
    super.onMapZoomEnd($event);
    if (this.markersGroup) {
      this.map.removeLayer(this.markersGroup);
      this.markers = this.reduceOverlapping(this.allMarkers);
      this.markersGroup = L.layerGroup(this.markers);
      this.markersGroup.addTo(this.map);
    }
  }

  loadObservations(filter: ObsFilter, update = false) {
    const startTime = new Date().getTime();
    this.spinner.show();
    this.obsService
      .getData(filter, update)
      .subscribe(
        (response: ObservationResponse) => {
          console.log(
            `elapsed time for '${filter.product}' data retrieval: ${
              (new Date().getTime() - startTime) / 1000
            }s`,
          );
          let data = response.data;
          this.loadMarkers(data, filter.product);
          if (data.length === 0) {
            this.notify.showWarning("No observations found.");
          }
        },
        (error) => {
          this.notify.showError(error);
        },
      )
      .add(() => {
        this.map.invalidateSize();
        this.spinner.hide();
      });
  }

  private loadMarkers(data: Observation[], product: string) {
    this.allMarkers = [];
    let obsData: ObsData;
    let min: number, max: number;
    // min and max needed before data marker creation
    data.forEach((s) => {
      obsData = s.prod.find((x) => x.var === product);
      let localMin = Math.min(
        ...obsData.val.filter((v) => v.rel === 1).map((v) => v.val),
      );
      if (!min || localMin < min) {
        min = localMin;
      }
      let localMax = Math.max(
        ...obsData.val.filter((v) => v.rel === 1).map((v) => v.val),
      );
      if (!max || localMax > max) {
        max = localMax;
      }
    });
    data.forEach((s) => {
      obsData = s.prod.find((x) => x.var === product);
      // get the last value
      const lastObs: ObsValue = obsData.val.pop();
      const val = ObsService.showData(lastObs.val, product);
      let icon = L.divIcon({
        html: `<div class="mstObsIcon"><span>${val}` + "</span></div>",
        iconSize: [24, 6],
        className: `mst-marker-icon
          mst-obs-marker-color-${this.obsService.getColor(
            lastObs.val,
            min,
            max,
          )}`,
      });
      const m = new L.Marker([s.stat.lat, s.stat.lon], {
        icon: icon,
      });
      m.options["station"] = s.stat;
      m.options["data"] = obsData;
      m.bindTooltip(
        BaseMapComponent.buildTooltipTemplate(s.stat, lastObs.ref, val),
        {
          direction: "top",
          offset: [4, -2],
          opacity: 0.75,
          className: "leaflet-tooltip mst-obs-tooltip",
        },
      );
      this.allMarkers.push(m);
    });
    // console.log(`Total markers: ${this.allMarkers.length}`);

    // reduce overlapping
    this.markers = this.reduceOverlapping(this.allMarkers);
    this.markersGroup = L.layerGroup(this.markers, { pane: product });

    this.layersControl["overlays"] = this.markersGroup;
    this.markersGroup.addTo(this.map);
  }

  toggleLayer(obj: Record<string, string>) {
    // console.log(`toggle layer: ${obj.name}`);

    // clean up layers
    if (this.markersGroup) {
      this.map.removeLayer(this.markersGroup);
      this.allMarkers = [];
      this.markers = [];
    }
    // update the filter
    if (this.variablesConfig[obj.name]) {
      this.filter.product = this.variablesConfig[obj.name].code;
      this.filter.timerange = this.variablesConfig[obj.name].timerange;
      this.filter.level = this.variablesConfig[obj.name].level;
      this.loadObservations(this.filter, true);
    }
  }

  protected centerMap() {
    if (this.map) {
      const mapCenter = super.getMapCenter();
      this.map.setView(mapCenter, 6);
    }
  }

  onCollapse(event: boolean) {
    super.onCollapse(event);
    this.centerMap();
  }

  printDatasetProduct(): string {
    let product: string;
    for (let key in VARIABLES_CONFIG_OBS) {
      if (VARIABLES_CONFIG_OBS[key].code === this.filter.product) {
        product = VARIABLES_CONFIG_OBS[key].label;
        break;
      }
    }
    return product || "n/a";
  }

  printReferenceDate(): string {
    return `${moment.utc(new Date().getTime()).format("MMM DD, HH:mm")}`;
  }

  reload(): void {
    this.loadObservations(this.filter, true);
  }
}