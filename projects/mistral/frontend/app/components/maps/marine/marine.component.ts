import { Component, OnInit, Injector } from "@angular/core";
import { BaseMapComponent } from "../base-map.component";
import * as L from "leaflet";
import { TilesService } from "../meteo-tiles/services/tiles.service";
import { MEDITA_BOUNDS, Variables } from "./side-nav/data";
import {
  CARTODB_LICENSE_HREF,
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
  ViewModes,
} from "./../meteo-tiles/meteo-tiles.config";
import { NavigationEnd, Params } from "@angular/router";
import * as moment from "moment";
@Component({
  selector: "app-marine",
  templateUrl: "./marine.component.html",
  styleUrls: ["./marine.component.scss"],
})
export class MarineComponent extends BaseMapComponent implements OnInit {
  private wmsPath: string;
  private timeDimensionControl: any;
  LAYER_OSM = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution: `&copy; ${OSM_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
      maxZoom: this.maxZoom,
      minZoom: this.minZoom,
    },
  );
  LAYER_LIGHTMATTER = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}{r}.png",
    {
      id: "mapbox.light",
      attribution: `&copy; ${CARTODB_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
      maxZoom: this.maxZoom,
      minZoom: this.minZoom,
    },
  );

  // Values to bind to Leaflet Directive
  layersControl = {
    baseLayers: {
      "Carto Map Light": this.LAYER_LIGHTMATTER,
      "Openstreet Map": this.LAYER_OSM,
    },
  };
  bounds = new L.LatLngBounds(
    MEDITA_BOUNDS["southWest"],
    MEDITA_BOUNDS["northEast"],
  );
  options = {
    zoomControl: false,
    minZoom: this.minZoom,
    maxZoom: this.maxZoom - 1,
    //center: L.latLng([46.879966, 11.726909]),
    center: L.latLng([41.3, 12.5]),
    maxBounds: this.bounds,
    maxBoundsViscosity: 1.0,
    timeDimension: true,
    timeDimensionControl: false,
    timeDimensionControlOptions: {
      timeZones: ["utc", "local"],
      timeSteps: 1,
      limitSliders: true,
      speedSlider: true,
      maxSpeed: 2,
      playerOptions: {
        buffer: 0,
        transitionTime: 750,
        loop: true,
      },
    },
  };
  constructor(injector: Injector, private tilesService: TilesService) {
    super(injector);
    // set the initial set of displayed layers
    this.options["layers"] = [this.LAYER_LIGHTMATTER];
    this.wmsPath = this.tilesService.getWMSUrl();
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

  ngOnInit() {
    super.ngOnInit();
    this.route.queryParams.subscribe((params: Params) => {
      const lang = params["lang"];
      if (["it", "en"].includes(lang)) {
        this.lang = lang;
      }
    });
  }

  protected onMapReady(map: L.Map) {
    this.map = map;
    this.map.attributionControl.setPrefix("");
    (window as any).L.Control.TimeDimensionCustom = (
      window as any
    ).L.Control.TimeDimension.extend({
      onAdd: function (map: L.Map) {
        const container = (
          window as any
        ).L.Control.TimeDimension.prototype.onAdd.call(this, map);
        this.timeZoneSelect = container.querySelector(
          ".timecontrol-timezone select",
        );
        return container;
      },

      _getDisplayDateFormat: function (date: Date) {
        const timeZone = this._getCurrentTimeZone().toLowerCase();

        if (timeZone === "utc") {
          return moment.utc(date).format("DD-MM-YYYY HH:mm [UTC]");
        }

        if (timeZone === "local") {
          const offsetHours = moment(date).utcOffset() / 60;
          const sign = offsetHours >= 0 ? "+" : "-";
          return moment(date).format(
            `DD-MM-YYYY HH:mm [UTC${sign}${Math.abs(offsetHours)}]`,
          );
        }
      },
    });

    this.timeDimensionControl = new (
      window as any
    ).L.Control.TimeDimensionCustom({
      timeZones: ["utc", "local"],
      limitSliders: true,
      speedSlider: true,
      maxSpeed: 2,
      playerOptions: {
        buffer: 0,
        transitionTime: 750,
        loop: true,
      },
    });
    this.map.addControl(this.timeDimensionControl);
    this.centerMap();
  }
  protected centerMap() {
    if (this.map) {
      //const mapCenter = super.getMapCenter();
      // map center for ICON
      const mapCenter = L.latLng(41.3, 12.5);

      this.map.setMaxZoom(this.maxZoom - 1);

      this.map.fitBounds(this.bounds);
    }
  }
  public printDatasetProduct(): string {
    return "";
  }
  public printReferenceDate(): string {
    return "";
  }
  protected toggleLayer(obj: Record<string, string | L.Layer>) {}
}
