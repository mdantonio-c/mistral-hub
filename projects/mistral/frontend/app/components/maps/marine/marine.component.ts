import { Component, OnInit, Injector, Input } from "@angular/core";
import { BaseMapComponent } from "../base-map.component";
import * as L from "leaflet";
import { TilesService } from "../meteo-tiles/services/tiles.service";
import { MEDITA_BOUNDS, Variables, Layers } from "./side-nav/data";
import {
  CARTODB_LICENSE_HREF,
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
  ViewModes,
} from "./../meteo-tiles/meteo-tiles.config";
import { NavigationEnd, Params } from "@angular/router";
import * as moment from "moment";
import { RunAvailable } from "../../../types";
import { legendConfig } from "./side-nav/data";

@Component({
  selector: "app-marine",
  templateUrl: "./marine.component.html",
  styleUrls: ["./marine.component.scss"],
})
export class MarineComponent extends BaseMapComponent implements OnInit {
  @Input() minZoom: number = 5;
  @Input() maxZoom: number = 9;
  ARROW_CONFIG = {
    svgWidth: 32,
    svgHeight: 48,
    tailLength: 13,
    strokeWidth: 2,
    arrowHeadSize: 6,
    arrowHeadStroke: "black",
    arrowHeadStrokeWidth: 0.5,
    backgroundColor: "none",
    opacity: 0.9,
  };
  private wmsPath: string;
  private legendControl;
  private timeDimensionControl: any;
  private beginTime;
  private timeLoading: boolean = false;
  private arrowLayer: L.LayerGroup | null = null;
  private removeArrowLayer = false;
  dataset: string;
  overlaysReady = false;
  public runAvailable: RunAvailable;

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
    maxZoom: this.maxZoom,
    //center: L.latLng([46.879966, 11.726909]),
    center: L.latLng([41.3, 12.5]),
    maxBounds: this.bounds,
    maxBoundsViscosity: 0.3,
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
    this.dataset = "ww3";
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
  private getTilesWms(layer) {
    return L.timeDimension.layer.wms(
      L.tileLayer.wms(this.wmsPath, {
        layers: layer,
        transparent: true,
        format: "image/png",
        tileSize: 1024,
        opacity: 0.6,
      }),
    );
  }
  private setOverlaysToMap() {
    this.layersControl["overlays"] = {};
    Object.keys(Layers).forEach((key) => {
      if (key == "hs") {
        this.layersControl["overlays"][key] = this.getTilesWms(
          Layers[key],
        ).addTo(this.map);
        this.updateLegends(key);
      } else
        this.layersControl["overlays"][key] = this.getTilesWms(Layers[key]);
    });
    // const current=moment.utc((this.map as any).timeDimension.getCurrentTime()).format("DD-MM-YYYY-HH-mm");
    // const geoJsonName = current +".geojson";
    // const vector$=this.tilesService.getGeoJsonVectors(geoJsonName);
    // vector$.subscribe((data)=> {
    //     this.layersControl["overlays"]["dir"]=this.addArrowLayer(data);
    // })
    this.overlaysReady = true;
  }

  private loadRunAvailable(dataset: string) {
    this.timeLoading = true;
    const lastRun$ = this.tilesService.getLastRun(dataset);
    lastRun$
      .subscribe(
        (runAvailable: RunAvailable) => {
          this.runAvailable = runAvailable;
          console.log(this.runAvailable);
          let reftime = this.runAvailable.reftime;
          // set time
          let startTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .add(this.runAvailable.start_offset, "hours")
            .toDate();
          this.beginTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .format("DD-MM-YYYY");
          let endTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .add(this.runAvailable.end_offset, "hours")
            .toDate();

          let newAvailableTimes = (
            L as any
          ).TimeDimension.Util.explodeTimeRange(
            startTime,
            endTime,
            `PT${runAvailable.step}H`,
          );
          (this.map as any).timeDimension.setAvailableTimes(
            newAvailableTimes,
            "replace",
          );
          let currentTime = startTime;
          const now = moment.utc();
          if (now.isBetween(startTime, endTime, "days", "[]")) {
            console.log(
              `reftime includes today: set time to ${now.hours()} UTC`,
            );
            currentTime = now.toDate();
          }
          this.timeLoading = false;
          (this.map as any).timeDimension.setCurrentTime(currentTime);
          this.setOverlaysToMap();
        },
        (error) => {
          this.notify.showError(error);
          this.spinner.hide();
        },
      )
      .add(() => {
        this.map.invalidateSize();
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
    setTimeout(() => this.centerMap(), 200);
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

    this.loadRunAvailable(this.dataset);

    (map as any).timeDimension.on("timeload", (e) => {
      const current = moment
        .utc((this.map as any).timeDimension.getCurrentTime())
        .format("DD-MM-YYYY-HH-mm");
      const geoJsonName = current + ".geojson";
      const vector$ = this.tilesService.getGeoJsonVectors(geoJsonName);
      vector$.subscribe({
        next: (data) => {
          try {
            if (!this.removeArrowLayer) {
              if (this.arrowLayer) {
                this.map.removeLayer(this.arrowLayer);
              }
              this.arrowLayer = this.addArrowLayer(data);
              this.arrowLayer.addTo(this.map);
              this.layersControl["overlays"]["dir"] = this.arrowLayer;
            }
          } catch (error) {
            console.error(" Error adding ", geoJsonName, error);
          }
        },
        error: (error) => {
          console.error(
            " Error retrieving ",
            geoJsonName,
            error?.message || error,
          );
        },
      });
    });
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
    return this.beginTime;
  }
  protected toggleLayer(obj: Record<string, string | L.Layer>) {}
  protected toggleLayer2(layer: string) {
    console.log(layer);
    if (!this.overlaysReady) {
      console.warn("Overlays not ready yet, blocking toggle");
      return;
    }
    const overlays = this.layersControl["overlays"];

    if (this.map.hasLayer(overlays["dir"])) {
      if (
        this.map.hasLayer(overlays["t01"]) ||
        this.map.hasLayer(overlays["hs"])
      ) {
        if (layer == "dir") {
          this.map.removeLayer(overlays["dir"]);
          this.removeArrowLayer = true;
        }
      }
    } else {
      if (
        this.map.hasLayer(overlays["t01"]) ||
        this.map.hasLayer(overlays["hs"])
      ) {
        if (layer == "dir") {
          overlays["dir"].addTo(this.map);
          this.removeArrowLayer = false;
        }
      }
    }
    if (layer == "t01") {
      if (this.map.hasLayer(overlays["t01"])) {
        if (this.map.hasLayer(overlays["dir"])) {
          this.map.removeLayer(overlays["t01"]);
        }
      } else {
        if (this.map.hasLayer(overlays["hs"])) {
          this.map.removeLayer(overlays["hs"]);
        }
        overlays["t01"].addTo(this.map);
      }
    }
    if (layer == "hs") {
      if (this.map.hasLayer(overlays["hs"])) {
        if (this.map.hasLayer(overlays["dir"])) {
          this.map.removeLayer(overlays["hs"]);
        }
      } else {
        if (this.map.hasLayer(overlays["t01"])) {
          this.map.removeLayer(overlays["t01"]);
        }
        overlays["hs"].addTo(this.map);
      }
    }
    this.updateLegends(layer);
  }
  private addArrowLayer(data): L.LayerGroup {
    if (!data || !data.features || !Array.isArray(data.features)) {
      return L.layerGroup([]);
    }
    const markers = data.features
      .map((feature) => {
        try {
          const coords = feature.geometry?.coordinates;
          const lat = coords[0][1];
          const lon = coords[0][0];
          const direction = feature.properties.direction;
          const color = "#000000";
          /*const arrowIcon = L.icon({
              iconUrl: this.createArrowSVG(color, direction),
              iconSize: [20, 20],
              iconAnchor: [10, 10],
              popupAnchor: [0, -10],
              className: "arrow-icon",
            });*/
          const arrowIcon = L.divIcon({
            className: "arrow-icon",
            html: `
    <div style="
      position: relative;
      width: 1px;
      height: 5px;                  /* ridotto */
      background: black;
      transform: rotate(${direction}deg);
      transform-origin: bottom center;
    ">
      <div style="
        position: absolute;
        bottom: 5px;               /* allineato alla nuova altezza */
        left: -3px;                /* ridotto */
        width: 0;
        height: 0;
        border-left: 3px solid transparent;   /* ridotto */
        border-right: 3px solid transparent;  /* ridotto */
        border-bottom: 4px solid black;       /* ridotto */
      "></div>
    </div>
  `,
            iconSize: [10, 10], // ridotto
            iconAnchor: [5, 6], // ridotto
          });

          return L.marker([lat, lon], { icon: arrowIcon });
        } catch (error) {
          console.error("Error adding arrow marker", error, feature);
          return null;
        }
      })
      .filter((marker) => marker != null);
    return L.layerGroup(markers);
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

  private addLegendSvg(svgPath: string) {
    if (!this.map) return;
    if (this.legendControl) {
      this.legendControl.remove();
      if (
        this.map.hasLayer(this.layersControl["overlays"]["dir"]) &&
        !this.map.hasLayer(this.layersControl["overlays"]["hs"]) &&
        !this.map.hasLayer(this.layersControl["overlays"]["t01"])
      ) {
        return;
      }
    }
    this.legendControl = new L.Control({ position: "bottomleft" });
    this.legendControl.onAdd = () => {
      let div = L.DomUtil.create("div");
      div.style.clear = "unset";
      div.innerHTML += `<img class="legenda" src="${svgPath}">`;
      return div;
    };
    this.legendControl.addTo(this.map);
  }

  private updateLegends(layerId: string) {
    const config = legendConfig[layerId];
    if (!config) return;
    this.addLegendSvg(config);
  }
}
