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

  private wmsPath: string;
  private legendControl;
  private timeDimensionControl: any;
  private beginTime;
  private timeLoading: boolean = false;
  private arrowLayer: L.Layer | null = null;
  private arrowCanvasLayer: any = null;
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
      maxSpeed: 1.3,
      playerOptions: {
        buffer: 0,
        transitionTime: 1000,
        loop: true,
      },
    });
    this.map.addControl(this.timeDimensionControl);
    this.loadRunAvailable(this.dataset);
    (map as any).timeDimension.on("timeload", (e) => {
      this.loadArrowsForCurrentState();
    });
    this.map.on("zoomend", () => {
      this.loadArrowsForCurrentState();
    });
  }

  private loadArrowsForCurrentState() {
    const current = moment
      .utc((this.map as any).timeDimension.getCurrentTime())
      .format("DD-MM-YYYY-HH-mm");
    const zoom = this.map.getZoom() ?? 5;
    const geoJsonName = current + ".geojson";
    const geoJsonPath = `${zoom}/${geoJsonName}`;
    const vector$ = this.tilesService.getGeoJsonVectors(geoJsonPath);

    vector$.subscribe({
      next: (data) => {
        try {
          if (!this.removeArrowLayer) {
            if (!this.arrowCanvasLayer) {
              this.arrowCanvasLayer = this.createArrowCanvasLayer(data);
              this.arrowLayer = this.arrowCanvasLayer;
              this.arrowLayer.addTo(this.map);
              this.layersControl["overlays"]["dir"] = this.arrowLayer;
            } else {
              this.arrowCanvasLayer.updateData(data);
            }
          }
        } catch (error) {
          console.error("Error adding", geoJsonName, error);
        }
      },
      error: (error) => {
        console.error("Error retrieving", geoJsonName, error?.message || error);
      },
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
          if (this.arrowCanvasLayer) this.arrowCanvasLayer = null;
        }
      }
    } else {
      if (
        this.map.hasLayer(overlays["t01"]) ||
        this.map.hasLayer(overlays["hs"])
      ) {
        if (layer == "dir") {
          //overlays["dir"].addTo(this.map);
          this.removeArrowLayer = false;
          this.loadArrowsForCurrentState();
          return;
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

  private createArrowCanvasLayer(data: any): any {
    const ArrowCanvasLayer = (L as any).CanvasLayer.extend({
      initialize: function (geojson) {
        this._data = geojson;
      },

      updateData: function (newData) {
        this._data = newData;
        // Forza il ridisegno chiamando direttamente onDrawLayer
        if (this._map && this._canvas) {
          this.onDrawLayer({
            canvas: this._canvas,
            bounds: this._map.getBounds(),
            size: this._map.getSize(),
            zoom: this._map.getZoom(),
            center: this._map.getCenter(),
          });
        }
      },

      onAdd: function (map) {
        (L as any).CanvasLayer.prototype.onAdd.call(this, map);

        if (!this._canvas) {
          const container = map.getPanes().overlayPane;
          const canvases = container.getElementsByTagName("canvas");
          if (canvases.length > 0) {
            this._canvas = canvases[canvases.length - 1];
          }
        }

        map.on("moveend", this._redraw, this);
        map.on("zoomend", this._redraw, this);
        map.on("viewreset", this._redraw, this);
        map.on("resize", this._redraw, this);
      },

      onRemove: function (map) {
        // Rimuovi i listener quando il layer viene rimosso
        map.off("moveend", this._redraw, this);
        map.off("zoomend", this._redraw, this);
        map.off("viewreset", this._redraw, this);
        map.off("resize", this._redraw, this);

        (L as any).CanvasLayer.prototype.onRemove.call(this, map);
      },

      _redraw: function () {
        if (this.needRedraw) {
          this.needRedraw();
        } else if (this._canvas && this._map) {
          this.onDrawLayer({
            canvas: this._canvas,
            bounds: this._map.getBounds(),
            size: this._map.getSize(),
            zoom: this._map.getZoom(),
            center: this._map.getCenter(),
          });
        }
      },

      onDrawLayer: function (info) {
        const map = this._map;
        if (!map || !map.getSize) return;

        const ctx = info.canvas.getContext("2d");
        if (!ctx) return;

        if (!this._canvas) {
          this._canvas = info.canvas;
        }

        ctx.clearRect(0, 0, info.canvas.width, info.canvas.height);

        ctx.strokeStyle = "black";
        ctx.fillStyle = "black";
        ctx.lineWidth = 1;

        if (!this._data || !this._data.features) return;

        for (const f of this._data.features) {
          const coords = f.geometry?.coordinates;
          if (!coords) continue;

          const lat = coords[0][1];
          const lon = coords[0][0];
          const dir = f.properties?.direction;
          if (dir == null || dir < 0) continue;

          const p = map.latLngToContainerPoint([lat, lon]);

          if (
            p.x < 0 ||
            p.y < 0 ||
            p.x > info.canvas.width ||
            p.y > info.canvas.height
          ) {
            continue;
          }

          ctx.save();
          ctx.translate(p.x, p.y);
          ctx.rotate((dir * Math.PI) / 180);

          ctx.beginPath();
          ctx.moveTo(0, 6);
          ctx.lineTo(0, -6);
          ctx.stroke();

          ctx.beginPath();
          ctx.moveTo(-3, -3);
          ctx.lineTo(0, -6);
          ctx.lineTo(3, -3);
          ctx.fill();

          ctx.restore();
        }
      },
    });

    return new ArrowCanvasLayer(data);
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
