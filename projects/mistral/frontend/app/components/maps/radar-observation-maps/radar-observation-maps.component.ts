import { BaseMapComponent } from "../base-map.component";
import { Component, Injector, Input, OnInit } from "@angular/core";
import * as L from "leaflet";
import "leaflet-timedimension/dist/leaflet.timedimension.src.js";
import {
  layerMap,
  Products,
  VARIABLES_CONFIG,
  legendConfig,
} from "./side-nav/data";
import {
  CARTODB_LICENSE_HREF,
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
  DPC_LICENSE_HREF,
  ViewModes,
} from "../meteo-tiles/meteo-tiles.config";
import { Params } from "@angular/router";
import * as moment from "moment";
import { TilesService } from "../meteo-tiles/services/tiles.service";

@Component({
  selector: "app-radar-observation-maps",
  templateUrl: "./radar-observation-maps.component.html",
  styleUrls: ["./radar-observation-maps.component.scss"],
})
export class RadarComponent extends BaseMapComponent implements OnInit {
  readonly LEGEND_POSITION = "bottomleft";
  @Input() minZoom: number = 5;
  @Input() maxZoom: number = 9;

  private legendControl;
  public unit;
  public productName;
  public descr;
  public timelineReferenceDate: string = "";

  private selectedProduct;
  private timeLoading: boolean = false;
  wmsPath;
  bounds = new L.LatLngBounds(new L.LatLng(30, -20), new L.LatLng(55, 50));
  LAYER_OSM = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: this.maxZoom,
      minZoom: this.minZoom,
    },
  );
  LAYER_LIGHTMATTER = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}{r}.png",
    {
      id: "mapbox.light",
      attribution: `&copy; ${CARTODB_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF} | &copy; ${DPC_LICENSE_HREF}`,
      maxZoom: this.maxZoom,
      minZoom: this.minZoom,
    },
  );

  LAYER_DARK = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png",
    {
      id: "mapbox.dark",
      attribution: `&copy; ${CARTODB_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF} | &copy; ${DPC_LICENSE_HREF}`,
      maxZoom: this.maxZoom,
      minZoom: this.minZoom,
    },
  );

  layersControl = {
    baseLayers: {
      "Openstreet Map": this.LAYER_OSM,
      "Carto Map Light": this.LAYER_LIGHTMATTER,
      "Carto Map Dark": this.LAYER_DARK,
    },
  };
  roundedNow = this.roundTo5MinFloor(new Date());
  past = new Date(this.roundedNow.getTime() - 72 * 3600 * 1000);
  timeInterval = `${this.past.toISOString()}/${this.roundedNow.toISOString()}`;
  lastDate: Date;
  options = {
    zoomControl: false,
    center: L.latLng(41.88, 12.28),
    maxBoundsViscosity: 1.0,
    maxBounds: this.bounds,
    minZoom: this.minZoom,
    maxZoom: this.maxZoom,
    timeDimension: true,
    timeDimensionOptions: {
      timeInterval: this.timeInterval,
      period: "PT5M", // ISO8601 duration, step of 5 min
    },
    timeDimensionControl: false,
    timeDimensionControlOptions: {
      autoPlay: false,
      timeZones: ["Local"],
      loopButton: false,
      timeSteps: 1,
      playReverseButton: false,
      limitSliders: true,
      playerOptions: {
        buffer: 0,
        transitionTime: 0,
        loop: true,
        startOver: true,
      },
      speedSlider: false,
      maxSpeed: 5,
    },
  };
  viewMode = ViewModes.adv;
  private timeDimensionControl: any;
  private timelineInterval: any = null;

  constructor(injector: Injector, private tileService: TilesService) {
    super(injector);
    this.options["layers"] = [this.LAYER_LIGHTMATTER];
    this.wmsPath = this.tileService.getWMSUrl();
  }
  ngOnInit(): void {
    super.ngOnInit();
    this.productName = Products.SRI;
    this.unit = "mm/h";
    this.variablesConfig = VARIABLES_CONFIG;
    this.route.queryParams.subscribe((params: Params) => {
      const lang: string = params["lang"];
      const view: string = params["view"];
      if (["it", "en"].includes(lang)) {
        this.lang = lang;
      }

      if (Object.values(ViewModes).includes(view)) {
        this.viewMode = ViewModes[view];
      }
    });
    this.selectedProduct = Products.SRI;
    this.updateTimeLineWithLastDataAvailable();
  }
  protected centerMap() {
    if (this.map) {
      const mapCenter = super.getMapCenter();
      this.map.setView(mapCenter, 6);
    }
  }
  protected onMapReady(map: L.Map) {
    this.map = map;

    setTimeout(() => this.map.setView([41.88, 12.28], 6), 0);
    this.setOverlaysToMap();

    this.addIconBorderLayer();
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
        if (timeZone === "local") {
          const offsetHours = moment().utcOffset() / 60;
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
      autoPlay: false,
      playButton: true,
      timeZones: ["Local"],
      loopButton: false,
      timeSteps: 1,
      playReverseButton: false,
      limitSliders: true,
      playerOptions: {
        buffer: 0,
        transitionTime: 0,
        loop: true,
        startOver: true,
      },
      speedSlider: true,
      maxSpeed: 5,
    });
    this.map.addControl(this.timeDimensionControl);
    let tControl = this.timeDimensionControl;
    if (this.map.hasLayer(this.LAYER_DARK)) {
      this.LAYER_DARK.getContainer().style.filter = "brightness(2.0)";
    }
    this.layersControl["overlays"][Products.SRI].addTo(this.map);
    this.updateLegends(this.selectedProduct);
    (map as any).timeDimension.on("timeload", (e) => {
      this.timelineReferenceDate = this.printTimeLineReferenceDate();
    });
    this.timelineInterval = setInterval(() => {
      this.updateTimeLineWithLastDataAvailable();
    }, 120000);
  }

  private setOverlaysToMap() {
    if (!this.layersControl["overlays"]) {
      this.layersControl["overlays"] = {};
    }
    const overlays = this.layersControl["overlays"];
    if ("sri" in this.variablesConfig) {
      this.addLayer(overlays, Products.SRI);
    }
    if ("srt_adj" in this.variablesConfig) {
      this.addLayer(overlays, Products.SRTADJ1);
    }
  }

  private addLayer(overlays, key: Products) {
    const layer = this.getWmsTiles(this.wmsPath, layerMap[key]);
    layer.on("tileerror", () => {
      console.log(`Errore while downloading ${key}`);
    });
    overlays[key] = layer;
  }
  private getWmsTiles(url, layer) {
    return L.timeDimension.layer.wms(
      L.tileLayer.wms(url, {
        layers: layer,
        transparent: true,
        format: "image/png",
        tileSize: 256,
        opacity: 0.6,
      }),
    );
  }
  protected toggleLayer(obj: Record<string, string | L.Layer>) {
    let Layer = obj.layer as L.Layer;
    let layerName = obj.name as string;
    this.productName = layerName;
    this.selectedProduct = layerName;
    this.unit = this.productName === Products.SRI ? "mm/h" : "mm";
    this.descr =
      this.productName === Products.SRI ? "" : "integrated with rain gauges";
    if (this.map.hasLayer(Layer)) {
      return;
    } else {
      for (const [key, layer] of Object.entries(
        this.layersControl["overlays"],
      )) {
        if (this.map.hasLayer(layer as L.Layer)) {
          this.map.removeLayer(layer as L.Layer);
        }
      }
      this.layersControl["overlays"][layerName].addTo(this.map);
    }
    this.updateLegends(this.selectedProduct);
  }
  public printReferenceDate() {
    return "";
  }

  public printDatasetProduct(): string {
    return "";
  }
  public printDatasetDescription(): string {
    return "";
  }
  private roundTo5MinFloor(date: Date): Date {
    const ms = 1000 * 60 * 5;
    return new Date(Math.floor(date.getTime() / ms) * ms);
  }

  addIconBorderLayer() {
    fetch("./app/custom/assets/images/geoJson/confini_mediterraneo.geojson")
      .then((response) => response.json())
      .then((data) => {
        L.geoJSON(data, {
          style: {
            color: "black",
            weight: 1,
            opacity: 1,
          },
        }).addTo(this.map);
      });
  }

  public updateTimeLineWithLastDataAvailable(reload: boolean = false) {
    this.timeLoading = true;
    const radar_type = this.selectedProduct === Products.SRI ? "sri" : "srt";
    const lastRadarData$ = this.tileService.getLastRadarData(radar_type);
    lastRadarData$.subscribe((data) => {
      const from = new Date(data.from);
      const to = new Date(data.to);
      this.lastDate = to;
      const newAvailableTimes = (L as any).TimeDimension.Util.explodeTimeRange(
        from,
        to,
        this.options.timeDimensionOptions.period,
      );
      const td = (this.map as any)?.timeDimension;
      if (td) {
        td.setAvailableTimes(newAvailableTimes, "replace");
        const current = td.getCurrentTime();
        if (newAvailableTimes.includes(current) && !reload) {
          return;
        }
        td.setCurrentTime(to.getTime());
      }
      if (td && td.getAvailableTimes().length > 0) {
        const currentTimes = td.getAvailableTimes();
        const last = currentTimes[currentTimes.length - 1];
        if (last === to.getTime()) {
          return;
        }
      }
    });
    this.timeLoading = false;
  }
  ngOnDestroy(): void {
    if (this.timelineInterval) {
      clearInterval(this.timelineInterval);
    }
  }

  private addLegendSvg(svgPath: string) {
    if (!this.map) return;
    if (this.legendControl) this.legendControl.remove();
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
    if (!this.selectedProduct) return;
    const config = legendConfig[layerId];
    if (!config) return;
    this.addLegendSvg(config);
  }
  printTimeLineReferenceDate(): string {
    return `${moment
      .utc((this.map as any).timeDimension.getCurrentTime())
      .local()
      .format("DD-MM-YYYY, HH:mm")}`;
  }
  checkUTCShift(): string {
    const now = moment();
    const offsetHours = now.utcOffset() / 60;
    const sign = offsetHours >= 0 ? "+" : "-";
    return `(UTC${sign}${Math.abs(offsetHours)})`;
  }
}
