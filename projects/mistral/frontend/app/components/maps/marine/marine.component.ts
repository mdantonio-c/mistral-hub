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
  ARROW_CONFIG = {
    // Dimensioni SVG (aumenta per frecce più grandi)
    svgWidth: 32,
    svgHeight: 48,

    // Lunghezza della coda (in pixel interni SVG)
    // Aumenta per frecce più lunghe
    tailLength: 13,

    // Spessore della linea della coda
    strokeWidth: 2,

    // Dimensione della punta della freccia
    arrowHeadSize: 6,

    // Colore bordo punta (lascia 'black' o cambia)
    arrowHeadStroke: "black",
    arrowHeadStrokeWidth: 0.5,

    // Colore di sfondo (lascia 'none' per trasparente)
    backgroundColor: "none",

    // Opacità delle frecce (0-1)
    opacity: 0.9,
  };
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
    //this.addArrowLayer(this.map);
    //this.getTileWms('meteohub:wave_height_17').addTo(this.map);
    // this.getTileWms('meteohub:t01_17').addTo(this.map);
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
  private addArrowLayer(map: L.Map) {
    fetch("./app/custom/assets/readyRadar/wave_arrows_17.geojson")
      .then((response) => response.json())
      .then((data) => {
        data.features.forEach((feature) => {
          const coords = feature.geometry.coordinates;
          const lat = coords[0][1];
          const lon = coords[0][0];
          const direction = feature.properties.direction;
          const color = "#000000";
          const arrowIcon = L.icon({
            iconUrl: this.createArrowSVG(color, direction),
            iconSize: [20, 20],
            iconAnchor: [10, 10],
            popupAnchor: [0, -10],
            className: "arrow-icon",
          });
          const marker = L.marker([lat, lon], { icon: arrowIcon }).addTo(map);
        });
      });
  }
  createArrowSVG(color, direction) {
    const cfg = this.ARROW_CONFIG;
    const centerX = cfg.svgWidth / 2;
    const centerY = cfg.svgHeight / 2;
    const tailStart = centerY - cfg.tailLength;

    const svg = `
                <svg width="${cfg.svgWidth}" height="${
                  cfg.svgHeight
                }" viewBox="0 0 ${cfg.svgWidth} ${
                  cfg.svgHeight
                }" xmlns="http://www.w3.org/2000/svg">
                    <g transform="translate(${centerX}, ${centerY}) rotate(${direction})" opacity="${
                      cfg.opacity
                    }">
                        <!-- Coda (linea verticale) -->
                        <line x1="0" y1="${cfg.tailLength}" x2="0" y2="-${
                          cfg.tailLength
                        }" stroke="${color}" stroke-width="${cfg.strokeWidth}"/>
                        <!-- Punta della freccia -->
                        <polygon points="0,-${cfg.tailLength} -${
                          cfg.arrowHeadSize
                        },-${cfg.tailLength - cfg.arrowHeadSize} 0,-${
                          cfg.tailLength - cfg.arrowHeadSize
                        } ${cfg.arrowHeadSize},-${
                          cfg.tailLength - cfg.arrowHeadSize
                        }" fill="${color}" stroke="${
                          cfg.arrowHeadStroke
                        }" stroke-width="${cfg.arrowHeadStrokeWidth}"/>
                    </g>
                </svg>
            `;
    return "data:image/svg+xml;base64," + btoa(svg);
  }

  getTileWms(layerId: string) {
    return L.tileLayer.wms(this.wmsPath, {
      layers: layerId,
      transparent: true,
      format: "image/png",
      tileSize: 1024,
      opacity: 0.6,
    } as any);
  }
}
