import { Component, Injector, Input, OnInit } from "@angular/core";
import { forkJoin } from "rxjs";
import * as moment from "moment";
import * as L from "leaflet";
import * as chroma from "chroma-js";
import "leaflet-timedimension/dist/leaflet.timedimension.src.js";
import { GeoTIFF } from "geotiff";
import "ih-leaflet-canvaslayer-field/dist/leaflet.canvaslayer.field.js";
import { TilesService } from "./services/tiles.service";
import { NavigationEnd, Params } from "@angular/router";
import { Subscription } from "rxjs";

import {
  LEGEND_DATA,
  LegendConfig,
  VARIABLES_CONFIG,
  VARIABLES_CONFIG_BASE,
  COLORSTOPS,
} from "./services/data";
import { CodeDescPair, RunAvailable } from "../../../types";
import {
  CARTODB_LICENSE_HREF,
  DatasetProduct as DP,
  DATASETS,
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
  ViewModes,
} from "./meteo-tiles.config";
import { IffRuns } from "../forecast-maps/services/data";
import { BaseMapComponent } from "../base-map.component";

declare module "leaflet" {
  let timeDimension: any;
  let timeDimensionControl: any;
  let VectorField: any;
  let canvasLayer: any;
  let ScalarField: any;
}

const ICON_BOUNDS = {
  southWest: L.latLng(33.69, 2.9875),
  northEast: L.latLng(48.91, 22.0125),
};

@Component({
  selector: "app-meteo-tiles",
  templateUrl: "./meteo-tiles.component.html",
  styleUrls: ["./meteo-tiles.component.scss"],
})
export class MeteoTilesComponent extends BaseMapComponent implements OnInit {
  readonly LEGEND_POSITION = "bottomleft";
  readonly DEFAULT_DATASET: string = DATASETS[0].code;
  @Input() minZoom: number = 6;
  @Input() maxZoom: number = 9;

  dataset: string;
  private run: string;
  private legends: { [key: string]: L.Control } = {};
  availableDatasets: CodeDescPair[] = DATASETS;
  //bounds = new L.LatLngBounds(new L.LatLng(32, 1), new L.LatLng(51, 24));
  bounds = new L.LatLngBounds(
    ICON_BOUNDS["southWest"],
    ICON_BOUNDS["northEast"],
  );
  tmpStringHourCode: string;

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
  options = {
    zoomControl: false,
    minZoom: this.minZoom,
    maxZoom: this.maxZoom - 1,
    //center: L.latLng([46.879966, 11.726909]),
    center: L.latLng([41.3, 12.5]),
    maxBounds: this.bounds,
    maxBoundsViscosity: 1.0,
    timeDimension: true,
    timeDimensionControl: true,
    timeDimensionControlOptions: {
      timeZones: ["utc"],
      timeSteps: 1,
      limitSliders: true,
      speedSlider: false,
      maxSpeed: 2,
      playerOptions: {
        buffer: 0,
        transitionTime: 2000,
        loop: true,
      },
    },
  };
  public runAvailable: RunAvailable;
  private subscriptions: Subscription[] = [];
  private currentIdx: number = null;
  private timeLoading: boolean = false;
  public onlyWind: boolean = false;
  public onlyPrs: boolean = false;
  private endOffset = 72; // initial setting for ICON
  private observer: MutationObserver;
  private activeSpans;
  private messageShown = false;
  private beginTime;
  private wmsPath: string;

  constructor(injector: Injector, private tilesService: TilesService) {
    super(injector);
    // set the initial set of displayed layers
    this.options["layers"] = [this.LAYER_LIGHTMATTER];
    this.dataset = this.DEFAULT_DATASET;
    // this.wmsPath = "http://localhost:8081/geoserver/meteohub/wms";
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
    this.spinner.show();
    // please do not erase this line, it is useful to import GeoTIFF variable and read geotiff files
    if (false) console.log(GeoTIFF);
    // please do not erase this line, it is useful to import GeoTIFF variable and read geotiff files
    this.startObserving(); // mutation observer on html DOM, useful to know which variable is selected
    this.variablesConfig = VARIABLES_CONFIG;
    this.route.queryParams.subscribe((params: Params) => {
      const view: string = params["view"];
      const lang: string = params["lang"];
      // override if any lang provided
      if (["it", "en"].includes(lang)) {
        this.lang = lang;
      }
      //console.log(`lang: ${this.lang}`);
      if (view) {
        // check for valid view mode
        if (Object.values(ViewModes).includes(view)) {
          this.viewMode = ViewModes[view];
          if (this.viewMode === ViewModes.base) {
            // adapt time dimension options
            this.options.timeDimensionControlOptions.speedSlider = false;
            this.options.timeDimensionControlOptions.timeZones = ["local"];
            // adapt variable configuration
            this.variablesConfig = VARIABLES_CONFIG_BASE;
            // setup default lang
            this.lang = "it";
            // override if any lang provided
            if (["it", "en"].includes(lang)) {
              this.lang = lang;
            }
            console.log(`lang: ${this.lang}`);
          }
        } else {
          console.warn(`Invalid view param: ${view}`);
        }
      }
      if (params["dataset"]) {
        // override the default dataset if given as input
        const found = this.availableDatasets.find(
          (x) => x.code === params["dataset"],
        );
        if (found) {
          this.dataset = found.code;
        } else {
          console.warn(`Invalid dataset param: ${params["dataset"]}`);
        }
      }

      // clean the url from the query parameters
      /*this.router.navigate([], {
                                queryParams: { view: null, dataset: null },
                                queryParamsHandling: "merge",
                              });*/
    });
  }

  ngOnDestroy() {
    super.ngOnDestroy();
    this.subscriptions.forEach((sub) => sub.unsubscribe());
    if (this.observer) {
      this.observer.disconnect();
    }
  }

  onMapReady(map: L.Map) {
    this.map = map;
    this.map.attributionControl.setPrefix("");
    // view mode
    console.log(`view mode: ${ViewModes[this.viewMode]}`);
    // define panes in order to have an overlapping order for cloud fields
    this.map.createPane("low");
    this.map.createPane("medium");
    this.map.createPane("high");
    this.map.getPane("low").style.zIndex = "1000";
    this.map.getPane("medium").style.zIndex = "2000";
    this.map.getPane("high").style.zIndex = "3000";
    this.loadRunAvailable(this.dataset);
    if (this.dataset === "icon") this.addIconBorderLayer();
    this.initLegends(this.map);
    this.centerMap();
    let pane;

    this.map.attributionControl.setPrefix("");
    // pass a reference to this MeteoTilesComponent
    const ref = this;
    // console.log((this.map as any).timeDimensionControl);

    // dict with all available layers
    const layersToUpdate = [
      {
        layer: DP.TM2,
        field: "t2m-t2m",
        variable: "t2m",
        colorStop: COLORSTOPS.t2mColorStops,
      },
      {
        layer: DP.PMSL,
        field: "pressure-pmsl",
        variable: "pmsl",
        colorStop: COLORSTOPS.prsColorStops,
      },
      {
        layer: DP.TCC,
        field: "cloud-tcc",
        variable: "tcc",
        colorStop: COLORSTOPS.tccColorStops,
      },
      {
        layer: DP.RH,
        field: "humidity-r",
        variable: "r",
        colorStop: COLORSTOPS.rhColorStops,
      },
      {
        layer: DP.PREC1P,
        field: "prec1-tp",
        variable: "tp",
        colorStop: COLORSTOPS.prp_1_3_ColorStops,
        offset: 1,
      },
      {
        layer: DP.PREC3P,
        field: "prec3-tp",
        variable: "tp",
        colorStop: COLORSTOPS.prp_1_3_ColorStops,
        offset: 3,
      },
      {
        layer: DP.PREC6P,
        field: "prec6-tp",
        variable: "tp",
        colorStop: COLORSTOPS.prp_6_12_24_ColorStops,
        offset: 6,
      },
      {
        layer: DP.PREC12P,
        field: "prec12-tp",
        variable: "tp",
        colorStop: COLORSTOPS.prp_6_12_24_ColorStops,
        offset: 12,
      },
      {
        layer: DP.PREC24P,
        field: "prec24-tp",
        variable: "tp",
        colorStop: COLORSTOPS.prp_6_12_24_ColorStops,
        offset: 24,
      },
      {
        layer: DP.SF1,
        field: "snow1-snow",
        variable: "snow",
        colorStop: COLORSTOPS.sf_1_3_ColorStops,
        offset: 1,
      },
      {
        layer: DP.SF3,
        field: "snow3-snow",
        variable: "snow",
        colorStop: COLORSTOPS.sf_1_3_ColorStops,
        offset: 3,
      },
      {
        layer: DP.SF6,
        field: "snow6-snow",
        variable: "snow",
        colorStop: COLORSTOPS.sf_6_12_24_ColorStops,
        offset: 6,
      },
      {
        layer: DP.SF12,
        field: "snow12-snow",
        variable: "snow",
        colorStop: COLORSTOPS.sf_6_12_24_ColorStops,
        offset: 12,
      },
      {
        layer: DP.SF24,
        field: "snow24-snow",
        variable: "snow",
        colorStop: COLORSTOPS.sf_6_12_24_ColorStops,
        offset: 24,
      },
      {
        layer: DP.LCC,
        field: "cloud_hml-lcc",
        variable: "lcc",
        colorStop: COLORSTOPS.lccColorStops,
      },
      {
        layer: DP.MCC,
        field: "cloud_hml-mcc",
        variable: "mcc",
        colorStop: COLORSTOPS.mccColorStops,
      },
      {
        layer: DP.HCC,
        field: "cloud_hml-hcc",
        variable: "hcc",
        colorStop: COLORSTOPS.hccColorStops,
      },
      {
        layer: DP.WIND10M,
        field: "wind",
        variable: "10uv",
        colorStop: COLORSTOPS.ws10mColorStops,
      },
    ];
    if (this.viewMode === ViewModes.base) {
      // in base view mode only VARIABLES_CONFIG_BASE
      const layerToRemove = [
        DP.PREC1P,
        DP.HCC,
        DP.MCC,
        DP.LCC,
        DP.SF1,
        DP.SF12,
        DP.SF24,
        DP.PMSL,
        DP.RH,
      ];
      for (let i = layersToUpdate.length - 1; i >= 0; i--) {
        if (layerToRemove.includes(layersToUpdate[i].layer)) {
          layersToUpdate.splice(i, 1);
        }
      }
    }

    //////////////////////////////
    /////// LAYERS DYNAMIC  /////
    /////////////////////////////
    (map as any).timeDimension.on(
      "timeload",
      function (data, comp: MeteoTilesComponent = ref) {
        if (comp.timeLoading) {
          return;
        }
        comp.setHourTimeStamp(map);
        const overlays = comp.layersControl["overlays"];
        if (!overlays) return;
        layersToUpdate.forEach(
          ({ layer, field, variable, colorStop, offset = 0 }) => {
            if (comp.map.hasLayer(overlays[layer])) {
              if (layer === DP.WIND10M) {
                comp
                  .addWindLayer(
                    comp.minZoom,
                    comp.dataset,
                    comp.tmpStringHourCode,
                    comp.onlyWind,
                  )
                  .then((l) => {
                    comp.map.removeLayer(overlays[layer]);
                    l.addTo(comp.map);
                    overlays[layer] = l;
                    if (comp.onlyWind) {
                      if (!comp.legends[layer]) {
                        comp.legends[layer].addTo(comp.map);
                      }
                    } else {
                      comp.map.removeControl(comp.legends[layer]);
                    }
                  });
              } else if (variable === "tp" || variable === "snow") {
                const stringHourToExclude = comp.stringHourToExclude(offset);
                if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
                  comp.map.removeLayer(overlays[layer]);
                  let comp_name = comp.getFileName(
                    variable,
                    comp.tmpStringHourCode,
                  );
                  overlays[layer] = comp.getWMSTileWithOptions(
                    comp.wmsPath,
                    "meteohub:tiff_store_" + comp_name,
                  );
                  overlays[layer].addTo(comp.map);
                } else {
                  comp.map.removeLayer(overlays[layer]);
                  const emptyLayer = L.canvas();
                  overlays[layer] = emptyLayer;
                  emptyLayer.addTo(comp.map);
                }
              } else {
                if (variable === "pmsl") {
                  comp.map.removeLayer(overlays[layer]);
                  let geoJcomp_name = comp.getFileName(
                    variable,
                    comp.tmpStringHourCode,
                  );
                  geoJcomp_name = geoJcomp_name + ".geojson";
                  let comp_name = comp.getFileName(
                    variable,
                    comp.tmpStringHourCode,
                  );
                  if (comp.onlyPrs) {
                    comp.map.removeLayer(overlays[layer]);

                    /*overlays[layer] = comp.getWMSTileWithOptions(
                      comp.wmsPath,
                      "meteohub:tiff_store_" + comp_name,
                    );*/
                    //overlays[layer].addTo(comp.map);
                    if (!comp.legends[layer])
                      comp.legends[layer].addTo(comp.map);
                  }
                  return new Promise((resolve, reject) => {
                    const subscription = comp.tilesService
                      .getGeoJsonComponent(
                        comp.dataset,
                        "pressure-pmsl",
                        geoJcomp_name,
                      )
                      .subscribe({
                        next: (geoJson) => {
                          let isobars = comp.addIsobars(geoJson, comp.map);
                          if (comp.onlyPrs) {
                            overlays[layer] = L.layerGroup([
                              isobars,
                              comp.getWMSTileWithOptions(
                                comp.wmsPath,
                                "meteohub:tiff_store_" + comp_name,
                              ),
                            ]);
                          } else {
                            overlays[layer] = isobars;
                          }
                          //if (comp.legends[layer]) comp.map.removeControl(comp.legends[layer]);
                          overlays[layer].addTo(comp.map);
                        },
                        error: (error) => {
                          console.error(
                            `Error while downloading/processing ${geoJcomp_name} file`,
                            error,
                          );
                          reject(error);
                        },
                      });
                    comp.subscriptions.push(subscription);
                  });
                } else {
                  comp.map.removeLayer(overlays[layer]);
                  let comp_name = comp.getFileName(
                    variable,
                    comp.tmpStringHourCode,
                  );
                  overlays[layer] = comp.getWMSTileWithOptions(
                    comp.wmsPath,
                    "meteohub:tiff_store_" + comp_name,
                  );
                  if (variable === "lcc") pane = "low";
                  if (variable === "mcc") pane = "medium";
                  if (variable === "hcc") pane = "high";
                  if (
                    variable === "lcc" ||
                    variable === "mcc" ||
                    variable === "hcc"
                  ) {
                    overlays[layer].options.pane = pane;
                  }
                  overlays[layer].addTo(comp.map);
                }
              }
            }
          },
        );
      },
    );
    this.spinner.hide();
  }

  addPlayButton() {
    const element = document.querySelector(
      "a.leaflet-control-timecontrol.timecontrol-play.play",
    );
    if (element) {
      (element as HTMLElement).style.display = "block";
    }
  }

  removePlayButton() {
    const element = document.querySelector(
      "a.leaflet-control-timecontrol.timecontrol-play.play",
    );
    if (element) {
      (element as HTMLElement).style.display = "none";
    }
  }

  startObserving() {
    // useful to show/hide play button to prevent animation with multiple layers
    this.observer = new MutationObserver((mutationsList, observer) => {
      mutationsList.forEach((mutation) => {
        if (mutation.type === "childList") {
          // selected layers
          this.activeSpans = document.querySelectorAll('span[class*="attivo"]');
          if (this.activeSpans.length === 1) {
            const onlyActive = this.activeSpans[0];
            if (onlyActive.classList.contains("ws10m")) {
              this.removePlayButton();
            } else {
              this.addPlayButton();
            }
          } else if (this.activeSpans.length > 1) {
            // remove when there will be future improvements with animation
            this.removePlayButton();
          }
          if (this.activeSpans.length === 4 && !this.messageShown) {
            this.notify.showWarning(
              "You reached the maximum number of contemporary layers",
            );
            this.messageShown = true;
          }
          if (this.activeSpans.length != 4) this.messageShown = false;
        }
      });
    });
    // MutationObserver is configured to detect changes in child nodes  and all descendants
    this.observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  setHourTimeStamp(map) {
    // change timestamp based on current time
    const now = moment.utc();
    const current = moment.utc((map as any).timeDimension.getCurrentTime());
    const currentHourFormat = current.format("HH");
    let referenceDate = now;
    if (this.beginTime.date() != now.date()) {
      referenceDate = this.beginTime;
    }
    const diffDays = current
      .startOf("day")
      .diff(referenceDate.startOf("day"), "days");
    let prefix = diffDays.toString().padStart(2, "0");
    this.tmpStringHourCode = prefix + currentHourFormat + "0000";
    console.log(this.tmpStringHourCode);
  }

  private loadRunAvailable(dataset: string) {
    this.timeLoading = true;
    // need to get last run available
    const lastRun$ = this.tilesService.getLastRun(dataset);
    lastRun$
      .subscribe(
        (runAvailable: RunAvailable) => {
          // runAvailable.reftime : 2020051100
          this.runAvailable = runAvailable;
          // console.log(runAvailable);
          //console.log(`Last Available Run [${dataset}]`, runAvailable);
          let reftime = runAvailable.reftime;
          this.run = reftime.substr(8, 2);

          // set time
          let startTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .add(runAvailable.start_offset, "hours")
            .toDate();
          this.beginTime = moment.utc(reftime, "YYYYMMDDHH");
          // console.log(`startTime: ${moment.utc(startTime).format()}`);
          let endTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .add(runAvailable.end_offset, "hours")
            .toDate();
          this.endOffset = runAvailable.end_offset;
          // console.log(`endTime ${moment.utc(endTime).format()}`);

          // add time dimension
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
          // console.log(`today: ${now.format()}`);
          if (now.isBetween(startTime, endTime, "days", "[]")) {
            // console.log(`reftime includes today: set time to ${now.hours()} UTC`);
            currentTime = now.toDate();
          }
          this.timeLoading = false;
          (this.map as any).timeDimension.setCurrentTime(currentTime);
          // initial setting up of layersControl["overlays"]
          this.setOverlaysToMap();

          this.dataset = runAvailable.dataset;

          this.setHourTimeStamp(this.map);

          let componentName = "t2m";
          let comp_name = this.getFileName(
            componentName,
            this.tmpStringHourCode,
          );

          this.layersControl["overlays"][DP.TM2] = this.getWMSTileWithOptions(
            this.wmsPath,
            "meteohub:tiff_store_" + comp_name,
          );
          this.layersControl["overlays"][DP.TM2].addTo(this.map);

          this.legends[DP.TM2].addTo(this.map);
          setTimeout(() => this.spinner.hide(), 800);
          let element = document.querySelectorAll("span.t2m");
          if (element) {
            element[0].classList.add("attivo");
          }
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

  createCustomColorScale(colorStops) {
    const domainValues = colorStops.map((stop) => stop.value);
    const colors = colorStops.map((stop) => stop.color);
    // discrete color scale
    return chroma.scale(colors).domain(domainValues).classes(domainValues);
    // continue color scale
    //return chroma.scale(colors).domain(domainValues);
  }

  getFileName(componentName: string, hour: string | null = null): string {
    let now_ = new Date().getUTCHours().toString();
    if (now_.length === 1) now_ = "0" + now_;
    let s: string = "00" + now_ + "0000";
    if (hour) s = hour;
    const comp_name = `${componentName}_comp_` + s;
    return comp_name;
  }

  addIsobars(geoJson, map) {
    return L.geoJSON(geoJson, {
      style: function () {
        return {
          color: "grey",
          weight: 1,
          opacity: 0.8,
        };
      },
      onEachFeature: function (feature, layer) {
        let invisibleLayer = L.geoJSON(feature, {
          style: function () {
            return {
              color: "transparent",
              weight: 6,
              opacity: 0,
              interactive: true,
            };
          },
        }).addTo(map);

        invisibleLayer.on("mouseover", function (e) {
          layer
            .bindTooltip(feature.properties.label + " hPa", {
              permanent: false,
              direction: "top",
              className: "isobar-label",
              opacity: 1,
              offset: L.point(0, -10),
            })
            .openTooltip(e.latlng);
        });
        invisibleLayer.on("mousemove", function (e) {
          layer.openTooltip(e.latlng);
        });
        invisibleLayer.on("mouseout", function () {
          layer.closeTooltip();
        });
      },
    });
  }
  addIconBorderLayer() {
    // add border layer for ICON model
    fetch("./app/custom/assets/images/geoJson/coastlines_border_lines.geojson")
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

  stringHourToExclude(targetHour: number): string[] {
    // return timestamp until targetHour-1
    if (targetHour < 0 || targetHour > 24) {
      return ["Error: target hour must be between 0 and 24."];
    }
    const strings = [];
    for (let i = 0; i < targetHour; i++) {
      strings.push("00" + i.toString().padStart(2, "0") + "0000");
    }
    return strings;
  }

  generateForecastTimestamp(compName: string) {
    let forecastMap: Record<string, string> = {};
    let index = 0;
    const maxDaysForecasts = this.endOffset / 24;

    for (let D = 0; D <= maxDaysForecasts; D++) {
      for (let HH = 0; HH < 24; HH++) {
        if (index > this.endOffset) break;
        let forecastKey = (index + parseInt(this.run))
          .toString()
          .padStart(2, "0");
        forecastMap[
          forecastKey
        ] = `${compName}_comp_0${D}${HH.toString().padStart(2, "0")}0000.tif`;
        index++;
      }
    }
    return forecastMap;
  }

  traverseDictionary(dict: Record<string, any>, start: number): string[] {
    const keys = Object.keys(dict)
      .map(Number)
      .sort((a, b) => a - b);
    const result: string[] = [];

    for (let i = start; i <= this.endOffset; i++) {
      const key = i.toString().padStart(2, "0");
      if (key in dict) result.push(dict[key]);
    }

    if (start !== 0) {
      for (let i = 0; i < start; i++) {
        const key = i.toString().padStart(2, "0");
        if (key in dict) result.push(dict[key]);
      }
    }

    return result;
  }

  addWindLayer(
    minZoom: number,
    dataset: string,
    hour = "",
    onlyWind = false,
  ): Promise<L.Layer | L.LayerGroup> {
    if (!dataset) {
      return;
    }
    let resLayer: L.Layer;
    let now = new Date().getUTCHours().toString();
    if (now.length === 1) {
      now = "0" + now;
    }
    // initialization useful for the first load of wind layer
    let s: string = "00" + now + "0000";
    if (hour) s = hour;

    const u_name = "10u_comp_" + s + ".tif";
    const v_name = "10v_comp_" + s + ".tif";

    return new Promise((resolve, reject) => {
      //console.time('addwindlayer');
      const subscription = forkJoin({
        u: this.tilesService.getImgComponentCached(dataset, "wind-10u", u_name),
        v: this.tilesService.getImgComponentCached(dataset, "wind-10v", v_name),
      }).subscribe({
        next: ({ u, v }) => {
          let n = (window.innerHeight * window.innerWidth) / 2073600;
          const vf = L.VectorField.fromGeoTIFFs(u, v);
          const sf = vf.getScalarField("magnitude");

          const customColorScale = this.createCustomColorScale(
            COLORSTOPS.ws10mColorStops,
          );
          const magnitude = L.canvasLayer.scalarField(sf, {
            color: customColorScale,
            opacity: 0.4,
          });
          // by construction 5<=zoom<=8, for this reason vectors length is 8
          const vectors = [5e3, 5e3, 5e3, 5e3, 5e3, 5e3, 3e3, 2e3, 1e3];
          let r = vectors[minZoom] * n;
          const layer = L.canvasLayer.vectorFieldAnim(vf, {
            color: "black",
            paths: r,
            fade: 0.92,
            velocityScale: 0.001,
          });

          if (onlyWind) resLayer = L.layerGroup([magnitude, layer]);
          else resLayer = layer;
          resolve(resLayer);
        },
        //complete: ()=> {console.timeEnd('addwindlayer')},
        error: (error) => {
          console.error(
            `Error while downloading/processing ${u_name} or ${v_name} files`,
            error,
          );
          reject(error);
        },
      });
      this.subscriptions.push(subscription);
    });
  }

  updateCumulatedFields(field) {
    // in the case of cumulated field go to the nearest available hour
    if (field[0] === "prp" || field[0] === "sf") {
      const n = parseInt(field[1]);
      const targetHr = parseInt(this.tmpStringHourCode.slice(2, 4));
      const start = moment.utc(
        (this.map as any).timeDimension.getAvailableTimes()[0],
      );
      if (n === 1 && targetHr < n) {
        const newTime = start.add(1, "hour");
        (this.map as any).timeDimension.setCurrentTime(newTime);
      } else if (n === 3 && targetHr < n) {
        const newTime = start.add(3, "hour");
        (this.map as any).timeDimension.setCurrentTime(newTime);
      } else if (n === 6 && targetHr < n) {
        const newTime = start.add(6, "hour");
        (this.map as any).timeDimension.setCurrentTime(newTime);
      } else if (n === 12 && targetHr < n) {
        const newTime = start.add(12, "hour");
        (this.map as any).timeDimension.setCurrentTime(newTime);
      } else if (n === 24 && targetHr < n) {
        const newTime = start.add(24, "hour");
        (this.map as any).timeDimension.setCurrentTime(newTime);
      }
    }
  }

  onCollapse(newValue: boolean) {
    // hide/show scalar field buttons
    if (newValue) {
      const prsSwictch = document.querySelector(
        ".form-switch.prs-switch.justify-content-center.ms-3.d-flex.mb-3",
      );
      if (prsSwictch) {
        (prsSwictch as HTMLElement).setAttribute(
          "style",
          "display: none !important;",
        );
      }
      const windSwittch = document.querySelector(
        ".form-switch.wind-switch.justify-content-center.ms-3.d-flex.mb-3",
      );
      if (windSwittch) {
        (windSwittch as HTMLElement).setAttribute(
          "style",
          "display: none !important;",
        );
      }
    } else {
      const prsSwictch = document.querySelector(
        ".form-switch.prs-switch.justify-content-center.ms-3.d-flex.mb-3",
      );
      if (prsSwictch) {
        (prsSwictch as HTMLElement).setAttribute(
          "style",
          "display: block !important;",
        );
      }
      const windSwittch = document.querySelector(
        ".form-switch.wind-switch.justify-content-center.ms-3.d-flex.mb-3",
      );
      if (windSwittch) {
        (windSwittch as HTMLElement).setAttribute(
          "style",
          "display: block !important;",
        );
      }
    }
  }

  updateScalarWind(newValue: boolean) {
    this.onlyWind = newValue;
    if (
      this.layersControl["overlays"] &&
      this.map.hasLayer(this.layersControl["overlays"][DP.WIND10M])
    ) {
      this.addWindLayer(
        this.minZoom,
        this.dataset,
        this.tmpStringHourCode,
        this.onlyWind,
      ).then((l) => {
        this.map.removeLayer(this.layersControl["overlays"][DP.WIND10M]);
        l.addTo(this.map);
        this.layersControl["overlays"][DP.WIND10M] = l;
        if (this.onlyWind) {
          this.legends[DP.WIND10M].addTo(this.map);
        } else {
          this.map.removeControl(this.legends[DP.WIND10M]);
        }
      });
    }
  }

  updateScalarPrs(newValue: boolean) {
    this.onlyPrs = newValue;
    if (
      this.layersControl["overlays"] &&
      this.map.hasLayer(this.layersControl["overlays"][DP.PMSL])
    ) {
      this.map.removeLayer(this.layersControl["overlays"][DP.PMSL]);
      let geoJcomp_name = this.getFileName("pmsl", this.tmpStringHourCode);
      geoJcomp_name = geoJcomp_name + ".geojson";
      let comp_name = this.getFileName("pmsl", this.tmpStringHourCode);

      if (newValue) {
        this.legends[DP.PMSL].addTo(this.map);
      } else {
        if (this.legends[DP.PMSL])
          this.map.removeControl(this.legends[DP.PMSL]);
        return new Promise((resolve, reject) => {
          const subscription = this.tilesService
            .getGeoJsonComponent(this.dataset, "pressure-pmsl", geoJcomp_name)
            .subscribe({
              next: (geoJson) => {
                this.layersControl["overlays"][DP.PMSL] = this.addIsobars(
                  geoJson,
                  this.map,
                );
                this.layersControl["overlays"][DP.PMSL].addTo(this.map);
              },
              error: (error) => {
                console.error(
                  `Error while downloading/processing ${geoJcomp_name} file`,
                  error,
                );
                reject(error);
              },
            });
          this.subscriptions.push(subscription);
        });
      }
      let comp = this;
      return new Promise((resolve, reject) => {
        const subscription = this.tilesService
          .getGeoJsonComponent(this.dataset, "pressure-pmsl", geoJcomp_name)
          .subscribe({
            next: (geoJson) => {
              let isobars = this.addIsobars(geoJson, comp.map);
              this.layersControl["overlays"][DP.PMSL] = L.layerGroup([
                this.getWMSTileWithOptions(
                  this.wmsPath,
                  "meteohub:tiff_store_" + comp_name,
                ),
                isobars,
              ]);
              this.layersControl["overlays"][DP.PMSL].addTo(this.map);
            },
            error: (error) => {
              console.error(
                `Error while downloading/processing ${geoJcomp_name} file`,
                error,
              );
              reject(error);
            },
          });
        this.subscriptions.push(subscription);
      });
    }
  }

  private setOverlaysToMap() {
    let now = new Date().getUTCHours().toString();
    if (now.length === 1) now = "0" + now;
    const s = "00" + now + "0000";

    this.layersControl["overlays"] = {};

    ////////////////////////////////////
    /////////// TEMPERATURE //////////
    ////////////////////////////////////
    if ("t2m" in this.variablesConfig) {
      let comp_name = this.getFileName("t2m", this.tmpStringHourCode);
      this.layersControl["overlays"][DP.TM2] = L.tileLayer.wms(this.wmsPath, {
        layers: "meteohub:tiff_store_" + comp_name,
      });
    }
    ////////////////////////////////////
    /////////// PRESSURE //////////
    ////////////////////////////////////
    if ("prs" in this.variablesConfig) {
      let comp_name = this.getFileName("pmsl", this.tmpStringHourCode);
      this.layersControl["overlays"][DP.PMSL] = this.getWMSTileWithOptions(
        this.wmsPath,
        "meteohub:tiff_store_" + comp_name,
      );
    }
    ////////////////////////////////////
    /////////// WIND //////////
    ////////////////////////////////////
    if ("ws10m" in this.variablesConfig) {
      this.addWindLayer(this.minZoom, this.dataset).then((l) => {
        this.layersControl["overlays"][DP.WIND10M] = l;
      });
    }
    ////////////////////////////////////
    /////////// RELATIVE HUMIDITY //////////
    ////////////////////////////////////
    if ("rh" in this.variablesConfig) {
      let comp_name = this.getFileName("r", this.tmpStringHourCode);
      this.layersControl["overlays"][DP.RH] = this.getWMSTileWithOptions(
        this.wmsPath,
        "meteohub:tiff_store_" + comp_name,
      );
    }
    ////////////////////////////////////
    /////////// PRECIPITATION //////////
    ////////////////////////////////////
    if ("prp" in this.variablesConfig) {
      if (
        this.variablesConfig["prp"].length &&
        this.variablesConfig["prp"].includes(1)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(1);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("tp");
          this.layersControl["overlays"][DP.PREC1P] =
            this.getWMSTileWithOptions(
              this.wmsPath,
              "meteohub:tiff_store_" + comp_name,
            );
        } else {
          const emptyLayer = L.canvas();
          this.layersControl["overlays"][DP.PREC1P] = emptyLayer;
        }
      }
      if (
        this.variablesConfig["prp"].length &&
        this.variablesConfig["prp"].includes(3)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(3);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("tp");
          this.layersControl["overlays"][DP.PREC3P] =
            this.getWMSTileWithOptions(
              this.wmsPath,
              "meteohub:tiff_store_" + comp_name,
            );
        } else {
          const emptyLayer = L.canvas();
          this.layersControl["overlays"][DP.PREC3P] = emptyLayer;
        }
      }
      if (
        this.variablesConfig["prp"].length &&
        this.variablesConfig["prp"].includes(6)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(6);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("tp");
          this.layersControl["overlays"][DP.PREC6P] =
            this.getWMSTileWithOptions(
              this.wmsPath,
              "meteohub:tiff_store_" + comp_name,
            );
        } else {
          const emptyLayer = L.canvas();
          this.layersControl["overlays"][DP.PREC6P] = emptyLayer;
        }
      }
      if (
        this.variablesConfig["prp"].length &&
        this.variablesConfig["prp"].includes(12)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(12);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("tp");
          this.layersControl["overlays"][DP.PREC12P] =
            this.getWMSTileWithOptions(
              this.wmsPath,
              "meteohub:tiff_store_" + comp_name,
            );
        } else {
          const emptyLayer = L.canvas();
          this.layersControl["overlays"][DP.PREC12P] = emptyLayer;
        }
      }
      if (
        this.variablesConfig["prp"].length &&
        this.variablesConfig["prp"].includes(24)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(24);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("tp");
          this.layersControl["overlays"][DP.PREC24P] =
            this.getWMSTileWithOptions(
              this.wmsPath,
              "meteohub:tiff_store_" + comp_name,
            );
        } else {
          const emptyLayer = L.canvas();
          this.layersControl["overlays"][DP.PREC24P] = emptyLayer;
        }
      }
    }
    ////////////////////////////////////
    ///////////// SNOWFALL /////////////
    ////////////////////////////////////
    if ("sf" in this.variablesConfig) {
      if (
        this.variablesConfig["sf"].length &&
        this.variablesConfig["sf"].includes(1)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(1);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("snow");
          this.layersControl["overlays"][DP.SF1] = this.getWMSTileWithOptions(
            this.wmsPath,
            "meteohub:tiff_store_" + comp_name,
          );
        } else {
          const emptyLayer = L.canvas();
          this.layersControl["overlays"][DP.SF1] = emptyLayer;
        }
      }
      if (
        this.variablesConfig["sf"].length &&
        this.variablesConfig["sf"].includes(3)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(3);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("snow");
          this.layersControl["overlays"][DP.SF3] = this.getWMSTileWithOptions(
            this.wmsPath,
            "meteohub:tiff_store_" + comp_name,
          );
        } else {
          const emptyLayer = L.canvas();
          this.layersControl["overlays"][DP.SF3] = emptyLayer;
        }
      }
      if (
        this.variablesConfig["sf"].length &&
        this.variablesConfig["sf"].includes(6)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(6);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("snow");
          this.layersControl["overlays"][DP.SF6] = this.getWMSTileWithOptions(
            this.wmsPath,
            "meteohub:tiff_store_" + comp_name,
          );
        }
      } else {
        const emptyLayer = L.canvas();
        this.layersControl["overlays"][DP.SF6] = emptyLayer;
      }
      if (
        this.variablesConfig["sf"].length &&
        this.variablesConfig["sf"].includes(12)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(12);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("snow");
          this.layersControl["overlays"][DP.SF12] = this.getWMSTileWithOptions(
            this.wmsPath,
            "meteohub:tiff_store_" + comp_name,
          );
        } else {
          const emptyLayer = L.canvas();
          this.layersControl["overlays"][DP.SF12] = emptyLayer;
        }
      }
      if (
        this.variablesConfig["sf"].length &&
        this.variablesConfig["sf"].includes(24)
      ) {
        const stringHoursToExclude = this.stringHourToExclude(24);
        if (!stringHoursToExclude.includes(s)) {
          let comp_name = this.getFileName("snow");
          this.layersControl["overlays"][DP.SF24] = this.getWMSTileWithOptions(
            this.wmsPath,
            "meteohub:tiff_store_" + comp_name,
          );
        } else {
          const emptyLayer = L.canvas();
          this.layersControl["overlays"][DP.SF24] = emptyLayer;
        }
      }
    }
    ////////////////////////////////////
    //////////// CLOUD COVER ///////////
    ////////////////////////////////////
    if ("cc" in this.variablesConfig) {
      if (
        this.variablesConfig["cc"].length &&
        this.variablesConfig["cc"].includes("low")
      ) {
        let comp_name = this.getFileName("lcc", this.tmpStringHourCode);
        this.layersControl["overlays"][DP.LCC] = this.getWMSTileWithOptions(
          this.wmsPath,
          "meteohub:tiff_store_" + comp_name,
        );
      }
      if (
        this.variablesConfig["cc"].length &&
        this.variablesConfig["cc"].includes("medium")
      ) {
        let comp_name = this.getFileName("mcc", this.tmpStringHourCode);
        this.layersControl["overlays"][DP.MCC] = this.getWMSTileWithOptions(
          this.wmsPath,
          "meteohub:tiff_store_" + comp_name,
        );
      }
      if (
        this.variablesConfig["cc"].length &&
        this.variablesConfig["cc"].includes("high")
      ) {
        let comp_name = this.getFileName("hcc", this.tmpStringHourCode);
        this.layersControl["overlays"][DP.HCC] = this.getWMSTileWithOptions(
          this.wmsPath,
          "meteohub:tiff_store_" + comp_name,
        );
      }

      let comp_name = this.getFileName("tcc", this.tmpStringHourCode);
      this.layersControl["overlays"][DP.TCC] = this.getWMSTileWithOptions(
        this.wmsPath,
        "meteohub:tiff_store_" + comp_name,
      );
    }
  }

  private createLegendControl(id: string): L.Control {
    let idEdited = id.split("_")[0];
    let config: LegendConfig = LEGEND_DATA.find((x) => x.id === idEdited);
    if (!config) {
      console.error(`Legend data NOT found for ID<${id}>`);
      this.notify.showError("Bad legend configuration");
      return;
    }
    const legend = new L.Control({ position: this.LEGEND_POSITION });
    legend.onAdd = () => {
      let div = L.DomUtil.create("div");
      if (id === "psmli") {
        div.style.display = "none";
        return div;
      }
      div.style.clear = "unset";
      div.innerHTML += `<img class="legenda" src="/app/custom/assets/images/${id}.svg">`;
      return div;
    };

    return legend;
  }

  getWMSTileWithOptions(
    url: string,
    layer: string,
    options: Record<string, any> | null = null,
  ) {
    if (options !== null) {
      return L.tileLayer.wms(url, {
        layers: layer,
        ...options,
      });
    } else {
      return L.tileLayer.wms(url, {
        layers: layer,
        transparent: true,
        format: "image/png",
        opacity: 0.6,
      });
    }
  }

  private initLegends(map: L.Map) {
    let layers = this.layersControl["overlays"];
    this.legends = {
      [DP.TM2]: this.createLegendControl("tm2"),
      [DP.PMSL]: this.createLegendControl("pmsl"),
      [DP.WIND10M]: this.createLegendControl("ws10m"),
      [DP.RH]: this.createLegendControl("rh"),

      [DP.PREC1P]: this.createLegendControl("prp_1_3"),
      [DP.PREC3P]: this.createLegendControl("prp_1_3"),
      [DP.PREC6P]: this.createLegendControl("prp_6_12_24"),
      [DP.PREC12P]: this.createLegendControl("prp_6_12_24"),
      [DP.PREC24P]: this.createLegendControl("prp_6_12_24"),

      [DP.SF1]: this.createLegendControl("sf_1_3"),
      [DP.SF3]: this.createLegendControl("sf_1_3"),
      [DP.SF6]: this.createLegendControl("sf_6_12_24"),
      [DP.SF12]: this.createLegendControl("sf_6_12_24"),
      [DP.SF24]: this.createLegendControl("sf_6_12_24"),

      [DP.TCC]: this.createLegendControl("tcc"),
      [DP.HCC]: this.createLegendControl("hcc"),
      [DP.MCC]: this.createLegendControl("mcc"),
      [DP.LCC]: this.createLegendControl("lcc"),
    };

    let legends = this.legends;
    let currentActiveLayers = [];
    let comp = this;
    map.on("overlayadd", function (event) {
      currentActiveLayers.push(event["name"]);
      if (event["name"] === DP.TM2) {
        legends[DP.TM2].addTo(map);
      } else if (event["name"] === DP.PMSL) {
        //legends[DP.PMSL].addTo(map);
      } else if (event["name"] === DP.WIND10M) {
        //legends[DP.WIND10M].addTo(map);
      } else if (event["name"] === DP.RH) {
        legends[DP.RH].addTo(map);
      } else if (event["name"] === DP.PREC1P || event["name"] === DP.PREC3P) {
        legends[DP.PREC1P].addTo(map);
      } else if (
        event["name"] === DP.PREC6P ||
        event["name"] === DP.PREC12P ||
        event["name"] === DP.PREC24P
      ) {
        legends[DP.PREC6P].addTo(map);
      } else if (event["name"] === DP.SF1 || event["name"] === DP.SF3) {
        legends[DP.SF1].addTo(map);
      } else if (
        event["name"] === DP.SF6 ||
        event["name"] === DP.SF12 ||
        event["name"] === DP.SF24
      ) {
        legends[DP.SF6].addTo(map);
      } else if (event["name"] === DP.TCC) {
        legends[DP.TCC].addTo(map);
      } else if (event["name"] === DP.HCC) {
        legends[DP.HCC].addTo(map);
      } else if (event["name"] === DP.MCC) {
        legends[DP.MCC].addTo(map);
      } else if (event["name"] === DP.LCC) {
        legends[DP.LCC].addTo(map);
      }
    });

    map.on("overlayremove", function (event) {
      currentActiveLayers = currentActiveLayers.filter(
        function (value, index, arr) {
          return value != event["name"];
        },
      );
      if (event["name"] === DP.TM2) {
        map.removeControl(legends[DP.TM2]);
      } else if (event["name"] === DP.PMSL) {
        map.removeControl(legends[DP.PMSL]);
      } else if (event["name"] === DP.WIND10M) {
        map.removeControl(legends[DP.WIND10M]);
      } else if (
        // PRECIPITATION
        event["name"] === DP.PREC1P &&
        !currentActiveLayers.includes(DP.PREC3P) &&
        !currentActiveLayers.includes(DP.PREC6P) &&
        !currentActiveLayers.includes(DP.PREC12P) &&
        !currentActiveLayers.includes(DP.PREC24P)
      ) {
        map.removeControl(legends[DP.PREC1P]);
      } else if (
        event["name"] === DP.PREC3P &&
        !currentActiveLayers.includes(DP.PREC1P) &&
        !currentActiveLayers.includes(DP.PREC6P) &&
        !currentActiveLayers.includes(DP.PREC12P) &&
        !currentActiveLayers.includes(DP.PREC24P)
      ) {
        map.removeControl(legends[DP.PREC1P]);
      } else if (
        event["name"] === DP.PREC6P &&
        !currentActiveLayers.includes(DP.PREC1P) &&
        !currentActiveLayers.includes(DP.PREC3P) &&
        !currentActiveLayers.includes(DP.PREC12P) &&
        !currentActiveLayers.includes(DP.PREC24P)
      ) {
        map.removeControl(legends[DP.PREC6P]);
      } else if (
        event["name"] === DP.PREC12P &&
        !currentActiveLayers.includes(DP.PREC1P) &&
        !currentActiveLayers.includes(DP.PREC3P) &&
        !currentActiveLayers.includes(DP.PREC6P) &&
        !currentActiveLayers.includes(DP.PREC24P)
      ) {
        map.removeControl(legends[DP.PREC6P]);
      } else if (
        event["name"] === DP.PREC24P &&
        !currentActiveLayers.includes(DP.PREC1P) &&
        !currentActiveLayers.includes(DP.PREC3P) &&
        !currentActiveLayers.includes(DP.PREC6P) &&
        !currentActiveLayers.includes(DP.PREC12P)
      ) {
        map.removeControl(legends[DP.PREC6P]);
      } else if (
        // SNOWFALL
        event["name"] === DP.SF1 &&
        !currentActiveLayers.includes(DP.SF3) &&
        !currentActiveLayers.includes(DP.SF6) &&
        !currentActiveLayers.includes(DP.SF12) &&
        !currentActiveLayers.includes(DP.SF24)
      ) {
        map.removeControl(legends[DP.SF1]);
      } else if (
        event["name"] === DP.SF3 &&
        !currentActiveLayers.includes(DP.SF1) &&
        !currentActiveLayers.includes(DP.SF6) &&
        !currentActiveLayers.includes(DP.SF12) &&
        !currentActiveLayers.includes(DP.SF24)
      ) {
        map.removeControl(legends[DP.SF1]);
      } else if (
        event["name"] === DP.SF6 &&
        !currentActiveLayers.includes(DP.SF1) &&
        !currentActiveLayers.includes(DP.SF3) &&
        !currentActiveLayers.includes(DP.SF12) &&
        !currentActiveLayers.includes(DP.SF24)
      ) {
        map.removeControl(legends[DP.SF6]);
      } else if (
        event["name"] === DP.SF12 &&
        !currentActiveLayers.includes(DP.SF1) &&
        !currentActiveLayers.includes(DP.SF3) &&
        !currentActiveLayers.includes(DP.SF6) &&
        !currentActiveLayers.includes(DP.SF24)
      ) {
        map.removeControl(legends[DP.SF6]);
      } else if (
        event["name"] === DP.SF24 &&
        !currentActiveLayers.includes(DP.SF1) &&
        !currentActiveLayers.includes(DP.SF3) &&
        !currentActiveLayers.includes(DP.SF6) &&
        !currentActiveLayers.includes(DP.SF12)
      ) {
        map.removeControl(legends[DP.SF6]);
      } else if (event["name"] === DP.RH) {
        map.removeControl(legends[DP.RH]);
      } else if (event["name"] === DP.TCC) {
        map.removeControl(legends[DP.TCC]);
      } else if (event["name"] === DP.HCC) {
        map.removeControl(legends[DP.HCC]);
      } else if (event["name"] === DP.MCC) {
        map.removeControl(legends[DP.MCC]);
      } else if (event["name"] === DP.LCC) {
        map.removeControl(legends[DP.LCC]);
      }
    });
  }

  changeDataset(newDs) {
    // console.log(`change to dataset ${newDs}`);
    // remove all current layers
    let overlays = this.layersControl["overlays"];
    let currentActiveNames = [];
    for (let name in overlays) {
      if (this.map.hasLayer(overlays[name])) {
        currentActiveNames.push(name);
        this.map.removeLayer(overlays[name]);
      }
    }
    this.currentIdx = null;
    this.loadRunAvailable(newDs);
    this.dataset = newDs;
    this.centerMap();
  }

  protected centerMap() {
    if (this.map) {
      //const mapCenter = super.getMapCenter();
      // map center for ICON
      const mapCenter = L.latLng(41.3, 12.5);
      switch (this.dataset) {
        case "icon":
          this.map.setMaxZoom(this.maxZoom - 1);
          //this.map.setView(mapCenter, 6);
          this.map.fitBounds(this.bounds);
          break;
      }
    }
  }

  onMapZoomEnd($event) {
    super.onMapZoomEnd($event);
  }

  toggleLayer(obj: Record<string, string | L.Layer>) {
    console.log("toggleLayer: ", obj);
    let comp = this;
    let layer: L.Layer = obj.layer as L.Layer;
    let numbLayers = [];
    if (this.map.hasLayer(layer)) {
      console.log(`remove layer: ${obj.name}`);
      this.map.fire("overlayremove", obj);
      this.map.removeLayer(layer);
    } else {
      console.log(`add layer : ${obj.name}`);
      this.map.fire("overlayadd", obj);

      if (obj.name === DP.WIND10M) {
        this.addWindLayer(
          this.minZoom,
          this.dataset,
          this.tmpStringHourCode,
          this.onlyWind,
        ).then((l) => {
          l.addTo(this.map);
          this.layersControl["overlays"][DP.WIND10M] = l;
          if (this.onlyWind) this.legends[DP.WIND10M].addTo(this.map);
        });
      } else if (obj.name === DP.PMSL) {
        let geoJcomp_name = this.getFileName("pmsl", this.tmpStringHourCode);
        geoJcomp_name = geoJcomp_name + ".geojson";
        let comp_name = this.getFileName("pmsl", this.tmpStringHourCode);
        if (this.onlyPrs) {
          /*this.layersControl["overlays"][DP.PMSL] = this.getWMSTileWithOptions(
            this.wmsPath,
            "meteohub:tiff_store_" + comp_name,
          );
          this.layersControl["overlays"][DP.PMSL].addTo(this.map);*/
        }

        return new Promise((resolve, reject) => {
          const subscription = this.tilesService
            .getGeoJsonComponent(this.dataset, "pressure-pmsl", geoJcomp_name)
            .subscribe({
              next: (geoJson) => {
                let isobars = this.addIsobars(geoJson, comp.map);
                if (comp.onlyPrs) {
                  this.layersControl["overlays"][DP.PMSL] = L.layerGroup([
                    isobars,
                    this.getWMSTileWithOptions(
                      this.wmsPath,
                      "meteohub:tiff_store_" + comp_name,
                    ),
                  ]);
                  this.legends[DP.PMSL].addTo(this.map);
                } else {
                  this.layersControl["overlays"][DP.PMSL] = isobars;
                  if (this.legends[DP.PMSL])
                    comp.map.removeControl(this.legends[DP.PMSL]);
                }
                //this.layersControl["overlays"][DP.PMSL] = isobars;
                this.layersControl["overlays"][DP.PMSL].addTo(comp.map);
              },
              error: (error) => {
                console.error(
                  `Error while downloading/processing ${geoJcomp_name} file`,
                  error,
                );
                reject(error);
              },
            });
          this.subscriptions.push(subscription);
        });
      } else {
        layer.addTo(this.map);
      }
    }
  }

  printDatasetDescription(): string {
    return this.availableDatasets.find((x) => x.code === this.dataset).desc;
  }

  printDatasetProduct(): string {
    if (!this.runAvailable) {
      return;
    }
    let p = this.runAvailable.reftime.substr(8, 2);
    return this.runAvailable.dataset === "iff"
      ? IffRuns.find((x) => x.key === p).value
      : p;
  }

  printReferenceDate(): string {
    if (!this.runAvailable) {
      return;
    }
    let date = this.runAvailable.reftime.substr(0, 8);
    // console.log(`reftime: ${this.runAvailable.reftime}`);
    return `${date.substr(6, 2)}-${date.substr(4, 2)}-${date.substr(0, 4)}`;
  }
}
