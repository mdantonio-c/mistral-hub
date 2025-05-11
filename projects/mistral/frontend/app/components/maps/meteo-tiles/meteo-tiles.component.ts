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
  layerMap,
  layersToUpdate,
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
  let VectorField: any;
  let canvasLayer: any;
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
  private timeDimensionControl: any;

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
    if (this.dataset === "icon") this.addIconBorderLayer();
    this.initLegends(this.map);
    this.centerMap();

    this.map.attributionControl.setPrefix("");
    // pass a reference to this MeteoTilesComponent
    const ref = this;
    // console.log((this.map as any).timeDimensionControl);

    const layersToRemoveInBaseMode = [
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
    const activeLayers =
      this.viewMode === ViewModes.base
        ? layersToUpdate.filter(
            (layer) => !layersToRemoveInBaseMode.includes(layer.layer),
          )
        : layersToUpdate;

    //////////////////////////////
    /////// LAYERS DYNAMIC  /////
    /////////////////////////////
    (map as any).timeDimension.on(
      "timeload",
      async function (data, comp: MeteoTilesComponent = ref) {
        if (comp.timeLoading) {
          return;
        }
        comp.setHourTimeStamp(map);
        let overlays = comp.layersControl["overlays"];
        if (!overlays) return;
        /*activeLayers.forEach(({ layer, field, variable, offset = 0 }) => {
          if (comp.map.hasLayer(overlays[layer])) {
            if (layer === DP.WIND10M) {
                let overlaysWind = overlays[DP.WIND10M];
                comp
                .addWindLayer(
                  comp.minZoom,
                  comp.dataset,
                  comp.tmpStringHourCode,
                )
                .then((l) => {
                  if(comp.onlyWind) {
                    if (!comp.legends[layer]) {
                      comp.legends[layer].addTo(comp.map);
                    }
                    overlaysWind.eachLayer(layer => {
                      // only vector field has color
                      if(layer.options.color){
                        overlaysWind.removeLayer(layer);
                        overlaysWind.addLayer(l);
                      }
                    })
                  }else {
                    overlaysWind.removeLayer(overlaysWind.getLayers()[0]);
                    overlaysWind.addLayer(l);
                  }
                });



            } else if (variable === "pmsl") {
              let overlaysPressure = overlays[DP.PMSL];
                let geoJcomp_name = comp.getFileName(
                  variable,
                  comp.tmpStringHourCode,
                );
                geoJcomp_name = geoJcomp_name + ".geojson";
                new Promise((resolve, reject) => {
                  const subscription = comp.tilesService
                    .getGeoJsonComponent(
                      comp.dataset,
                      "pressure-pmsl",
                      geoJcomp_name,
                    )
                    .subscribe({
                      next: (geoJson) => {
                        overlaysPressure.eachLayer(layer => {
                          // only wms layer has _currentLayer
                          if(!layer._currentLayer){
                            overlaysPressure.removeLayer(layer);
                          }
                          if(!comp.onlyPrs){
                            if(layer._currentLayer){
                   if(layer._currentLayer.options.layers === layerMap[DP.PMSL]){
                     overlaysPressure.removeLayer(layer);
                   }}
                          }
                          overlaysPressure.addLayer(comp.addIsobars(geoJson));

                        })
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

            }
          }
        });*/
        for (const { layer, field, variable, offset = 0 } of activeLayers) {
          if (!comp.map.hasLayer(overlays[layer])) continue;

          if (layer === DP.WIND10M) {
            const overlaysWind = overlays[DP.WIND10M];
            await comp
              .addWindLayer(comp.minZoom, comp.dataset, comp.tmpStringHourCode)
              .then((l) => {
                if (comp.onlyWind) {
                  if (!comp.legends[layer]) {
                    comp.legends[layer].addTo(comp.map);
                  }
                  overlaysWind.eachLayer((existing) => {
                    // options.color is only in canvas vector field
                    if (existing.options.color) {
                      overlaysWind.removeLayer(existing);
                      overlaysWind.addLayer(l);
                    }
                  });
                } else {
                  overlaysWind.clearLayers();
                  overlaysWind.addLayer(l);
                }
              });
            break;
          }

          if (variable === "pmsl") {
            const overlaysPressure = overlays[DP.PMSL];
            let geoJcomp_name =
              comp.getFileName(variable, comp.tmpStringHourCode) + ".geojson";

            const subscription = comp.tilesService
              .getGeoJsonComponent(comp.dataset, "pressure-pmsl", geoJcomp_name)
              .subscribe({
                next: (geoJson) => {
                  overlaysPressure.eachLayer((layer) => {
                    const isWMS = !!layer._currentLayer;
                    if (
                      !isWMS ||
                      (!comp.onlyPrs &&
                        layer._currentLayer.options.layers ===
                          layerMap[DP.PMSL])
                    ) {
                      overlaysPressure.removeLayer(layer);
                    }
                  });
                  overlaysPressure.addLayer(comp.addIsobars(geoJson));
                },
                error: (error) => {
                  console.error(`Error loading ${geoJcomp_name}`, error);
                },
              });

            comp.subscriptions.push(subscription);
            break;
          }
        }
      },
    );

    document
      .querySelector(".leaflet-control-timecontrol.timecontrol-play.play")
      ?.addEventListener("click", (event) => {
        // prevent pointers event on side menu and others buttons while animation
        const button = event.currentTarget as HTMLElement;
        // button.style.pointerEvents = "none";
        const menuDiv = document.querySelector(".map-sidenav-menu");
        if (menuDiv) {
          (menuDiv as HTMLElement).style.pointerEvents = "none";
        }
        const divOverlay = document.getElementById("overlay");
        if (divOverlay) {
          divOverlay.style.display = "block";
        }
        const backwardButton = document.querySelector(
          ".leaflet-control-timecontrol.timecontrol-backward",
        );
        if (backwardButton) {
          (backwardButton as HTMLElement).style.pointerEvents = "none";
        }
        const forwardButton = document.querySelector(
          ".leaflet-control-timecontrol.timecontrol-forward",
        );
        if (forwardButton) {
          (forwardButton as HTMLElement).style.pointerEvents = "none";
        }
        const dateSlider = document.querySelector(
          ".leaflet-control-timecontrol.timecontrol-slider.timecontrol-dateslider",
        );
        if (dateSlider) {
          (dateSlider as HTMLElement).style.pointerEvents = "none";
        }
        //
        if (!button.classList.contains("pause")) {
          (menuDiv as HTMLElement).style.pointerEvents = "auto";
          divOverlay.style.display = "none";
          (backwardButton as HTMLElement).style.pointerEvents = "auto";
          (forwardButton as HTMLElement).style.pointerEvents = "auto";
          (dateSlider as HTMLElement).style.pointerEvents = "auto";
          (button as HTMLElement).style.pointerEvents = "auto";
          return;
        }
      });

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

  fetchSelectedLayers(event) {
    console.log(event);
    if (event.includes("ws10m")) {
      this.timeDimensionControl._player.setTransitionTime(1750);
    } else {
      this.timeDimensionControl._player.setTransitionTime(750);
    }
  }

  setHourTimeStamp(map) {
    // change timestamp based on current time
    const now = moment.utc();
    const current = moment.utc((map as any).timeDimension.getCurrentTime());
    let currentHourFormat = current.format("HH");
    let referenceDate = now;
    if (this.beginTime.date() != now.date()) {
      referenceDate = this.beginTime;
    }
    let diffDays = current
      .startOf("day")
      .diff(referenceDate.startOf("day"), "days");
    let prefix = diffDays.toString().padStart(2, "0");

    if (this.run === "12") {
      let hourNumber = parseInt(currentHourFormat, 10);
      if (hourNumber - 12 < 0) hourNumber = hourNumber - 12 + 24;
      else hourNumber = hourNumber - 12;
      if (diffDays === 1 && hourNumber > 11) {
        diffDays = diffDays - 1;
      }
      if (diffDays === 2 && hourNumber > 11) {
        diffDays = 1;
      }
      if (diffDays === 3 && hourNumber > 11) {
        diffDays = 2;
      }
      prefix = diffDays.toString().padStart(2, "0");
      currentHourFormat = hourNumber.toString().padStart(2, "0");
    }
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
          console.log(`Last Available Run [${dataset}]`, runAvailable);
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
            console.log(
              `reftime includes today: set time to ${now.hours()} UTC`,
            );
            currentTime = now.toDate();
          }
          this.timeLoading = false;
          (this.map as any).timeDimension.setCurrentTime(currentTime);
          // initial setting up of layersControl["overlays"]
          this.setOverlaysToMap();

          this.dataset = runAvailable.dataset;

          this.setHourTimeStamp(this.map);

          this.layersControl["overlays"][DP.TM2] = this.getWMSTileWithOptions(
            this.wmsPath,
            layerMap[DP.TM2],
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

  getFileName(componentName: string, hour: string | null = null): string {
    let now_ = new Date().getUTCHours().toString();
    if (now_.length === 1) now_ = "0" + now_;
    let s: string = "00" + now_ + "0000";
    if (hour) s = hour;
    const comp_name = `${componentName}_comp_` + s;
    return comp_name;
  }

  addIsobars(geoJson) {
    const isobarLayer = L.geoJSON(geoJson, {
      style: function () {
        return {
          color: "transparent",
          weight: 6,
          opacity: 0,
          interactive: true,
        };
      },
      onEachFeature: function (feature, layer) {
        layer.on("mouseover", function (e) {
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

        layer.on("mousemove", function (e) {
          layer.openTooltip(e.latlng);
        });

        layer.on("mouseout", function () {
          layer.closeTooltip();
        });
      },
    });

    return isobarLayer;
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

  /*addWindLayer(
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
          // by construction 5<=zoom<=8, for this reason vectors length is 8
          const vectors = [5e3, 5e3, 5e3, 5e3, 5e3, 5e3, 3e3, 2e3, 1e3];
          let r = vectors[minZoom] * n;
          const layer = L.canvasLayer.vectorFieldAnim(vf, {
            color: "black",
            paths: r,
            fade: 0.92,
            velocityScale: 0.001,
          });

          if (onlyWind) {
            const magnitude = this.getWMSTileWithOptions(
              this.wmsPath,
              layerMap[DP.WIND10M],
            );
            resLayer = L.layerGroup([magnitude, layer]);
          } else resLayer = layer;
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
  }*/

  addWindLayer(
    minZoom: number,
    dataset: string,
    hour = "",
  ): Promise<L.Layer | L.LayerGroup> {
    if (!dataset) {
      return;
    }
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
          // by construction 5<=zoom<=8, for this reason vectors length is 8
          const vectors = [5e3, 5e3, 5e3, 5e3, 5e3, 5e3, 3e3, 2e3, 1e3];
          let r = vectors[minZoom] * n;
          const windVectorField = L.canvasLayer.vectorFieldAnim(vf, {
            color: "black",
            paths: r,
            fade: 0.92,
            velocityScale: 0.001,
          });
          resolve(windVectorField);
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
      let targetHr = parseInt(this.tmpStringHourCode.slice(2, 4));
      const d = parseInt(this.tmpStringHourCode.slice(0, 2));
      if (d > 0) return; // because it means that more than 24h have passed
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
      /*this.addWindLayer(
        this.minZoom,
        this.dataset,
        this.tmpStringHourCode
      ).then((l) => {
        const overlays = this.layersControl["overlays"];
        this.map.removeLayer(overlays[DP.WIND10M]);
        //this.layersControl["overlays"][DP.WIND10M] = l;
        if (this.onlyWind) {
          this.legends[DP.WIND10M].addTo(this.map);
          const scalarLayer = this.getWMSTileWithOptions(
              this.wmsPath,layerMap[DP.WIND10M]
          )
          const scalarVectorialLayer = L.layerGroup([l,scalarLayer]);
          overlays[DP.WIND10M] = scalarVectorialLayer;
          overlays[DP.WIND10M].addTo(this.map);
        } else {
          this.map.removeControl(this.legends[DP.WIND10M]);
          overlays[DP.WIND10M] = l;
          overlays[DP.WIND10M].addTo(this.map);

        }
      });*/
      const overlaysWind = this.layersControl["overlays"][DP.WIND10M];
      if (newValue) {
        this.legends[DP.WIND10M].addTo(this.map);
        const scalarLayer = this.getWMSTileWithOptions(
          this.wmsPath,
          layerMap[DP.WIND10M],
        );
        overlaysWind.addLayer(scalarLayer);
      } else {
        //overlaysWind.removeLayer(overlaysWind.getLayers()[1]);
        overlaysWind.eachLayer((layer) => {
          // only vector field has color
          if (!layer.options.color) {
            overlaysWind.removeLayer(layer);
          }
        });
        this.map.removeControl(this.legends[DP.WIND10M]);
      }
    }
  }

  updateScalarPrs(newValue: boolean) {
    this.onlyPrs = newValue;
    if (
      this.layersControl["overlays"] &&
      this.map.hasLayer(this.layersControl["overlays"][DP.PMSL])
    ) {
      /*  this.map.removeLayer(this.layersControl["overlays"][DP.PMSL]);
      if (newValue) {
        this.legends[DP.PMSL].addTo(this.map);
        this.layersControl["overlays"][DP.PMSL] = L.layerGroup([
          this.getWMSTileWithOptions(this.wmsPath, layerMap[DP.PMSL]),
          this.getWMSTileWithOptions(this.wmsPath, "meteohub:pressure-isob"),
        ]);
        let geoJcomp_name = this.getFileName("pmsl", this.tmpStringHourCode);
        geoJcomp_name = geoJcomp_name + ".geojson";
        new Promise((resolve, reject) => {
          const subscription = this.tilesService
            .getGeoJsonComponent(this.dataset, "pressure-pmsl", geoJcomp_name)
            .subscribe({
              next: (geoJson) => {
                let isobars = this.addIsobars(geoJson);
                this.layersControl["overlays"][DP.PMSL].addLayer(isobars);
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
      } else {
        this.map.removeLayer(this.layersControl["overlays"][DP.PMSL]);
        if (this.legends[DP.PMSL])
          this.map.removeControl(this.legends[DP.PMSL]);
        let geoJcomp_name = this.getFileName("pmsl", this.tmpStringHourCode);
        geoJcomp_name = geoJcomp_name + ".geojson";
        new Promise((resolve, reject) => {
          const subscription = this.tilesService
            .getGeoJsonComponent(this.dataset, "pressure-pmsl", geoJcomp_name)
            .subscribe({
              next: (geoJson) => {
                let isobars = this.addIsobars(geoJson);
                this.layersControl["overlays"][DP.PMSL] = L.layerGroup([
                  this.getWMSTileWithOptions(
                    this.wmsPath,
                    "meteohub:pressure-isob",
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
      }*/
      let overlaysPressure = this.layersControl["overlays"][DP.PMSL];
      let geoJcomp_name = this.getFileName("pmsl", this.tmpStringHourCode);
      geoJcomp_name = geoJcomp_name + ".geojson";
      new Promise((resolve, reject) => {
        const subscription = this.tilesService
          .getGeoJsonComponent(this.dataset, "pressure-pmsl", geoJcomp_name)
          .subscribe({
            next: (geoJson) => {
              if (this.onlyPrs) {
                overlaysPressure.addLayer(
                  this.getWMSTileWithOptions(this.wmsPath, layerMap[DP.PMSL]),
                );
              } else {
                overlaysPressure.eachLayer((layer) => {
                  if (layer._currentLayer) {
                    if (
                      layer._currentLayer.options.layers === layerMap[DP.PMSL]
                    ) {
                      overlaysPressure.removeLayer(layer);
                    }
                  }
                });
              }
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
    const overlays = this.layersControl["overlays"];
    ////////////////////////////////////
    /////////// TEMPERATURE //////////
    ////////////////////////////////////
    if ("t2m" in this.variablesConfig) {
      this.addLayerWithErrorHandling(overlays, DP.TM2);
    }
    ////////////////////////////////////
    /////////// PRESSURE //////////
    ////////////////////////////////////
    if ("prs" in this.variablesConfig) {
      this.addLayerWithErrorHandling(overlays, DP.PMSL);
    }
    ////////////////////////////////////
    /////////// WIND //////////
    ////////////////////////////////////
    if ("ws10m" in this.variablesConfig) {
      this.addWindLayer(this.minZoom, this.dataset)
        .then((l) => {
          this.layersControl["overlays"][DP.WIND10M] = L.layerGroup([l]);
        })
        .catch((error) => {
          console.error("Error while loading layer WIND10M:", error);
          overlays[DP.WIND10M] = L.canvas();
        });
    }
    ////////////////////////////////////
    /////////// RELATIVE HUMIDITY //////////
    ////////////////////////////////////
    if ("rh" in this.variablesConfig) {
      this.addLayerWithErrorHandling(overlays, DP.RH);
    }
    ////////////////////////////////////
    /////////// PRECIPITATION //////////
    ////////////////////////////////////

    if ("prp" in this.variablesConfig) {
      if (this.variablesConfig["prp"].length) {
        this.variablesConfig["prp"].forEach((period) => {
          this.addLayerWithErrorHandling(overlays, DP[`PREC${period}P`]);
        });
      }
    }
    ////////////////////////////////////
    ///////////// SNOWFALL /////////////
    ////////////////////////////////////

    if ("sf" in this.variablesConfig) {
      if (this.variablesConfig["sf"].length) {
        this.variablesConfig["sf"].forEach((period) => {
          this.addLayerWithErrorHandling(overlays, DP[`SF${period}`]);
        });
      }
    }
    ////////////////////////////////////
    //////////// CLOUD COVER ///////////
    ////////////////////////////////////
    if ("cc" in this.variablesConfig) {
      if (this.variablesConfig["cc"].includes("low")) {
        this.addLayerWithErrorHandling(overlays, DP.LCC, 100);
      } else {
        overlays[DP.LCC] = L.canvas(); // Placeholder
      }

      if (this.variablesConfig["cc"].includes("medium")) {
        this.addLayerWithErrorHandling(overlays, DP.MCC, 200);
      } else {
        overlays[DP.MCC] = L.canvas(); // Placeholder
      }

      if (this.variablesConfig["cc"].includes("high")) {
        this.addLayerWithErrorHandling(overlays, DP.HCC, 300);
      } else {
        overlays[DP.HCC] = L.canvas(); // Placeholder
      }

      this.addLayerWithErrorHandling(overlays, DP.TCC);
    }
  }

  addLayerWithErrorHandling(overlays, key: DP, zIndex: number | null = null) {
    try {
      if (layerMap[key].includes("snow")) {
        const layer = this.getWMSTileWithOptions(
          this.wmsPath,
          layerMap[key],
          zIndex,
          1,
        );

        layer.on("tileerror", () => {
          console.error(`Errore while downloading ${key}`);
          overlays[key] = L.canvas();
        });

        overlays[key] = layer;
      } else if (layerMap[key].includes("pressure")) {
        const layer = this.getWMSTileWithOptions(
          this.wmsPath,
          "meteohub:pressure-isob",
          zIndex,
          1,
        );

        layer.on("tileerror", () => {
          console.error(`Errore while downloading ${key}`);
          overlays[key] = L.canvas();
        });

        overlays[key] = L.layerGroup([layer]);
      } else {
        const layer = this.getWMSTileWithOptions(
          this.wmsPath,
          layerMap[key],
          zIndex,
        );

        layer.on("tileerror", () => {
          console.error(`Errore while downloading ${key}`);
          overlays[key] = L.canvas();
        });

        overlays[key] = layer;
      }
    } catch (error) {
      console.error(`Error while creation of layer  ${key}: `, error);
      overlays[key] = L.canvas();
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
    zIndex: number | null = null,
    opacity: number | null = null,
    options: Record<string, any> | null = null,
    tileLayer: L.TileLayer | null = null,
  ) {
    if (options !== null) {
      console.log(layer);
      return L.tileLayer.wms(url, {
        layers: layer,
        ...options,
      });
    } else {
      console.log(layer);
      return L.timeDimension.layer.wms(
        L.tileLayer.wms(url, {
          layers: layer,
          transparent: true,
          format: "image/png",
          tileSize: 1024,
          opacity: opacity ?? 0.6,
          zIndex: zIndex ?? 1,
        }),
      );
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
    let layer: L.Layer = obj.layer as L.Layer;
    let layerName = obj.name as string;

    if (this.map.hasLayer(layer)) {
      console.log(`remove layer: ${obj.name}`);
      this.map.fire("overlayremove", obj);
      this.map.removeLayer(layer);
      return;
    }
    console.log(`add layer : ${obj.name}`);
    this.map.fire("overlayadd", obj);
    const overlays = this.layersControl["overlays"];
    const layersToRemove = [
      DP.PREC1P,
      DP.PREC3P,
      DP.PREC6P,
      DP.PREC12P,
      DP.PREC24P,
      DP.SF1,
      DP.SF3,
      DP.SF6,
      DP.SF12,
      DP.SF24,
      DP.WIND10M,
      DP.PMSL,
    ];
    const baseLayers = Object.fromEntries(
      Object.entries(layerMap).filter(
        ([key]) => !layersToRemove.includes(key as DP),
      ),
    );
    const layerMapByDataset = new Map<
      DP,
      { field: string; variable: string; offset?: number }
    >(
      layersToUpdate.map((item) => [
        item.layer,
        { field: item.field, variable: item.variable, offset: item.offset },
      ]),
    );

    if (baseLayers[layerName]) {
      overlays[layerName] = this.getWMSTileWithOptions(
        this.wmsPath,
        layerMap[layerName],
        layerName === DP.LCC
          ? 100
          : layerName === DP.MCC
          ? 200
          : layerName === DP.HCC
          ? 300
          : null,
      );
      overlays[layerName].addTo(this.map);
      return;
    }
    if (layerName === DP.WIND10M) {
      let overlaysWind = overlays[DP.WIND10M];
      this.addWindLayer(
        this.minZoom,
        this.dataset,
        this.tmpStringHourCode,
      ).then((l) => {
        if (this.onlyWind) {
          this.legends[DP.WIND10M].addTo(this.map);
          const scalarLayer = this.getWMSTileWithOptions(
            this.wmsPath,
            layerMap[DP.WIND10M],
          );
          //this.map.removeLayer(overlaysWind);
          overlaysWind.clearLayers();
          //const scalarVectorialLayer = L.layerGroup([scalarLayer,l]);
          overlaysWind.addLayer(scalarLayer);
          overlaysWind.addLayer(l);
          //overlaysWind = scalarVectorialLayer;
          overlaysWind.addTo(this.map);
        } else {
          overlays[DP.WIND10M] = L.layerGroup([l]);
          overlays[DP.WIND10M].addTo(this.map);
        }
      });

      return;
    }
    if (layerName === DP.PMSL) {
      //this.handlePMSLLayer();
      //return;
      let overlaysPressure = overlays[DP.PMSL];
      this.setHourTimeStamp(this.map);
      let geoJcomp_name = this.getFileName("pmsl", this.tmpStringHourCode);
      geoJcomp_name = geoJcomp_name + ".geojson";

      /*new Promise((resolve, reject) => {
          const subscription = this.tilesService
            .getGeoJsonComponent(this.dataset, "pressure-pmsl", geoJcomp_name)
            .subscribe({
              next: (geoJson) => {
                const layerGroup = L.layerGroup([
                  this.getWMSTileWithOptions(this.wmsPath, layerMap[DP.PMSL]),
                  this.getWMSTileWithOptions(
                    this.wmsPath,
                    "meteohub:pressure-isob",
                    3,
                  ),
                ]);
                this.layersControl["overlays"][DP.PMSL] = layerGroup;
                this.layersControl["overlays"][DP.PMSL].addLayer(
                  this.addIsobars(geoJson),
                );
                this.layersControl["overlays"][DP.PMSL].addTo(this.map);
                this.legends[DP.PMSL].addTo(this.map);
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
        });*/
      new Promise((resolve, reject) => {
        const subscription = this.tilesService
          .getGeoJsonComponent(this.dataset, "pressure-pmsl", geoJcomp_name)
          .subscribe({
            next: (geoJson) => {
              if (this.onlyPrs) {
                this.legends[DP.PMSL].addTo(this.map);
                overlaysPressure.addLayer(
                  this.getWMSTileWithOptions(this.wmsPath, layerMap[DP.PMSL]),
                );
                overlaysPressure.addLayer(this.addIsobars(geoJson));
                overlaysPressure.addTo(this.map);
              } else {
                if (this.legends[DP.PMSL])
                  this.map.removeControl(this.legends[DP.PMSL]);
                overlaysPressure.addLayer(this.addIsobars(geoJson));
                overlaysPressure.addTo(this.map);
              }
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

      /* if (this.map.hasLayer(this.layersControl["overlays"][DP.PMSL]))
          this.map.removeLayer(this.layersControl["overlays"][DP.PMSL]);
        new Promise((resolve, reject) => {
          const subscription = this.tilesService
            .getGeoJsonComponent(this.dataset, "pressure-pmsl", geoJcomp_name)
            .subscribe({
              next: (geoJson) => {
                this.layersControl["overlays"][DP.PMSL] = L.layerGroup([
                  this.getWMSTileWithOptions(
                    this.wmsPath,
                    "meteohub:pressure-isob",
                    3,
                  ),
                  this.addIsobars(geoJson),
                ]);

                this.layersControl["overlays"][DP.PMSL].addTo(this.map);
                if (this.legends[DP.PMSL])
                  this.map.removeControl(this.legends[DP.PMSL]);
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
        });*/
    }
    const precipitationLayers = [
      DP.PREC1P,
      DP.PREC3P,
      DP.PREC6P,
      DP.PREC12P,
      DP.PREC24P,
    ];
    const snowLayers = [DP.SF1, DP.SF3, DP.SF6, DP.SF12, DP.SF24];
    if (precipitationLayers.includes(layerName as DP)) {
      this.handlePrecipitationLayer(layerName, "tp", "meteohub:prec");
      return;
    }
    if (snowLayers.includes(layerName as DP)) {
      this.handlePrecipitationLayer(layerName, "snow", "meteohub:snow");
      return;
    }
  }

  handlePrecipitationLayer(layerName, prefix, basePath) {
    const duration = parseInt(layerName.replace(/\D/g, ""), 10);
    if (prefix != "snow") {
      this.layersControl["overlays"][layerName] = this.getWMSTileWithOptions(
        this.wmsPath,
        `${basePath}${duration}-${prefix}`,
      );
    } else {
      this.layersControl["overlays"][layerName] = this.getWMSTileWithOptions(
        this.wmsPath,
        `${basePath}${duration}-${prefix}`,
        3,
        1,
      );
    }
    this.layersControl["overlays"][layerName].addTo(this.map);
    //console.log(this.layersControl["overlays"][layerName]);
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
