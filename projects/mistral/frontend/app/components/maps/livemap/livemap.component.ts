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
import {
  VARIABLES_CONFIG_BASE,
  VARIABLES_CONFIG_OBS,
} from "../meteo-tiles/services/data";
import {
  ObsFilter,
  ObservationResponse,
  ObsData,
  Observation,
  ObsValue,
} from "../../../types";
import { ObsService } from "../observation-maps/services/obs.service";

const MAX_ZOOM = 8;
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
  ) {
    super(notify, spinner);
  }

  ngOnInit() {
    this.variablesConfig = VARIABLES_CONFIG_OBS;
  }

  onMapReady(map: L.Map) {
    this.map = map;
    this.map.attributionControl.setPrefix("");

    /*
      temperature B12101
      rainfall    B13011
      humidity    B13003
      pressure    B10004
      wind        B11001 (direction)
                  B11002 (speed)
     */
    const filter: ObsFilter = {
      // common parameters
      reftime: new Date(),
      license: "CCBY_COMPLIANT",
      time: [0, 23],
      onlyStations: false,
      reliabilityCheck: true,

      // temperature
      product: "B12101",
      timerange: "254,0,0",
      level: "103,2000,0,0",
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
            `---Getting Data elapsed time: ${
              (new Date().getTime() - startTime) / 1000
            }s`,
          );
          let data = response.data;
          this.loadMarkers(data, "B12101");
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
        // setTimeout(() => this.spinner.hide(), 0);
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

    // reduce overlapping
    this.markers = this.reduceOverlapping(this.allMarkers);
    console.info(`Number of markers: ${this.markers.length}`);

    this.markersGroup = L.layerGroup(this.markers);
    this.markersGroup.addTo(this.map);
  }

  toggleLayer(obj: Record<string, string | L.Layer>) {
    console.log(`toggle layer: `, obj);
    let counter: number = 0;
    this.map.eachLayer((layer: L.Layer) => {
      //console.log(layer);
      counter++;
    });
    console.log(`number of layers: ${counter}`);
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
    Object.keys(VARIABLES_CONFIG_OBS).every((key) => {
      if (VARIABLES_CONFIG_OBS[key].code === this.filter.product) {
        product = VARIABLES_CONFIG_OBS[key].label;
        return false;
      }
    });
    return product || "n/a";
  }

  printReferenceDate(): string {
    return `${moment.utc(new Date().getTime()).format("MMM DD, HH:mm")}`;
  }

  reload(): void {
    this.loadObservations(this.filter, true);
  }
}
