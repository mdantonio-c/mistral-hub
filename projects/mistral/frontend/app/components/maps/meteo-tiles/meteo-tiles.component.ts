import { Component } from "@angular/core";
import { environment } from "@rapydo/../environments/environment";
import { Observable, forkJoin, of, concat, interval } from "rxjs";
import {
  filter,
  scan,
  takeUntil,
  catchError,
  withLatestFrom,
  map,
} from "rxjs/operators";
import * as moment from "moment";
import * as L from "leaflet";
import "leaflet-timedimension/dist/leaflet.timedimension.src.js";
import "@app/../assets/js/leaflet.timedimension.tilelayer.portus.js";
import { TilesService } from "./services/tiles.service";
import { ObsService } from "../observation-maps/services/obs.service";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import { Router, NavigationEnd } from "@angular/router";
import { LegendConfig, LEGEND_DATA } from "./services/data";
import {
  Observation,
  ObsData,
  ObsFilter,
  Station,
  RunAvailable,
} from "../../../types";
import {
  MOCK_MM_TEMP_OBS_RESPONSE,
  MOCK_MM_RH_OBS_RESPONSE,
} from "./data.mock";
import {
  MULTI_MODEL_TIME_RANGES,
  DatasetProduct as DP,
  // MultiModelProduct,
} from "./meteo-tiles.config";

declare module "leaflet" {
  let timeDimension: any;
}

// Product constants
const TM2 = "Temperature at 2 meters",
  PMSL = "Pressure mean sea level",
  WIND10M = "Wind speed at 10 meters",
  RH = "Relative Humidity",
  PREC1P = "Total Precipitation (1h)",
  PREC3P = "Total Precipitation (3h)",
  PREC6P = "Total Precipitation (6h)",
  PREC12P = "Total Precipitation (12h)",
  PREC24P = "Total Precipitation (24h)",
  SF1 = "Snowfall (3h)",
  SF3 = "Snowfall (3h)",
  SF6 = "Snowfall (6h)",
  SF12 = "Snowfall (12h)",
  SF24 = "Snowfall (24h)",
  TCC = "Total Cloud",
  HCC = "High Cloud",
  MCC = "Medium Cloud",
  LCC = "Low Cloud",
  TPPERC1 = "Precipitation percentiles 1%",
  TPPERC10 = "Precipitation percentile 10%",
  TPPERC25 = "Precipitation percentile 25%",
  TPPERC50 = "Precipitation percentile 50%",
  TPPERC70 = "Precipitation percentile 70%",
  TPPERC75 = "Precipitation percentile 75%",
  TPPERC80 = "Precipitation percentile 80%",
  TPPERC90 = "Precipitation percentile 90%",
  TPPERC99 = "Precipitation percentile 99%",
  TPPROB5 = "Precipitation probability 5%",
  TPPROB10 = "Precipitation probability 10%",
  TPPROB20 = "Precipitation probability 20%",
  TPPROB50 = "Precipitation probability 50%";

enum MultiModelProduct {
  RH = "B13003",
  TM = "B12101",
}
const MAP_CENTER = L.latLng(41.879966, 12.28),
  LM2_BOUNDS = {
    southWest: L.latLng(34.5, 5.0),
    northEast: L.latLng(48.0, 21.2),
  },
  LM5_BOUNDS = {
    southWest: L.latLng(25.8, -30.9),
    northEast: L.latLng(55.5, 47.0),
  };

const MAX_ZOOM = 8;
const MIN_ZOOM = 5;

@Component({
  selector: "app-meteo-tiles",
  templateUrl: "./meteo-tiles.component.html",
  styleUrls: ["./meteo-tiles.component.css"],
})
export class MeteoTilesComponent {
  readonly DEFAULT_PRODUCT_COSMO = "Temperature at 2 meters";
  readonly DEFAULT_PRODUCT_IFF = "Precipitation percentiles 1%";
  readonly LEGEND_POSITION = "bottomleft";
  readonly DEFAULT_DATASET = "lm5";
  // readonly license_iff =
  //   '&copy; <a href="http://www.openstreetmap.org/copyright">Open Street Map</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://meteohub.mistralportal.it/app/license">MISTRAL</a>';
  // //'&copy; <a href="http://www.openstreetmap.org/copyright">Open Street Map</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by/4.0/legalcode">Work distributed under License CC BY 4.0</a>';
  // readonly license_cosmo =
  // // '&copy; <a href="http://www.openstreetmap.org/copyright">Open Street Map</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>';
  // '&copy; <a href="http://www.openstreetmap.org/copyright">Open Street Map</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://meteohub.mistralportal.it/app/license">MISTRAL</a>';
  license =
    '&copy; <a href="http://www.openstreetmap.org/copyright" target="_blank">Open Street Map</a> ' +
    '&copy; <a href="http://cartodb.com/attributions" target="_blank">CartoDB</a> | ' +
    '&copy; <a href="./app/license#mistral-products" target="_blank">MISTRAL</a>';

  map: L.Map;
  dataset: string;
  private run: string;
  private legends: { [key: string]: L.Control } = {};
  // license = this.license;
  bounds = new L.LatLngBounds(new L.LatLng(30, -20), new L.LatLng(55, 40));

  LAYER_OSM = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution: this.license,
      //'&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>'+l_iff,
      maxZoom: MAX_ZOOM,
      minZoom: MIN_ZOOM,
    }
  );
  LAYER_LIGHTMATTER = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}{r}.png",
    {
      id: "mapbox.light",
      attribution: this.license,
      maxZoom: MAX_ZOOM,
      minZoom: MIN_ZOOM,
    }
  );
  LAYER_DARKMATTER = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png",
    {
      attribution: this.license,
      maxZoom: MAX_ZOOM,
      minZoom: MIN_ZOOM,
    }
  );

  // Values to bind to Leaflet Directive
  layersControl = {
    baseLayers: {
      "Openstreet Map": this.LAYER_OSM,
      "Carto Map Dark": this.LAYER_DARKMATTER,
      "Carto Map Light": this.LAYER_LIGHTMATTER,
    },
  };
  options = {
    zoom: MIN_ZOOM,
    center: L.latLng([46.879966, 11.726909]),
    timeDimension: true,
    timeDimensionControl: true,
    maxBounds: this.bounds,
    maxBoundsViscosity: 1.0,
    //bounds:
    timeDimensionControlOptions: {
      autoPlay: false,
      loopButton: true,
      timeSteps: 1,
      playReverseButton: true,
      limitSliders: true,
      playerOptions: {
        buffer: 0,
        transitionTime: 500,
        loop: true,
      },
    },
  };
  private runAvailable: RunAvailable;

  public showed: boolean = true;
  public mmProduct = MultiModelProduct.TM;
  public MultiModelProduct = MultiModelProduct;
  private markers: L.Marker[] = [];
  private allMarkers: L.Marker[] = [];
  private markersGroup: any;
  private mmProductsData: any[][] = null;
  private currentIdx: number = null;
  private currentMMReftime: Date = null;
  private timeLoading: boolean = false;

  constructor(
    private tilesService: TilesService,
    private obsService: ObsService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private router: Router
  ) {
    // set the initial set of displayed layers
    this.options["layers"] = [this.LAYER_LIGHTMATTER];
    this.dataset = this.DEFAULT_DATASET;
    router.events.subscribe((s) => {
      if (s instanceof NavigationEnd) {
        const tree = router.parseUrl(router.url);
        if (tree.fragment) {
          const element = document.querySelector("#" + tree.fragment);
          if (element) {
            element.scrollIntoView(true);
          }
        }
      }
    });
  }

  getTilesUrl() {
    let baseUrl = "";
    let production = false;
    if (environment.CUSTOM.TILES_URL !== "") {
      baseUrl = `${environment.CUSTOM.TILES_URL}/tiles/`;
      production = true;
    } else if (
      environment.production ||
      environment.backendURI.startsWith("https")
    ) {
      baseUrl = `${environment.backendURI}/resources/tiles/`;
      production = true;
    } else {
      baseUrl = `${environment.backendURI}/app/custom/assets/images/tiles/`;
      production = false;
    }

    baseUrl += `${this.run}-${this.dataset}`;
    if (production) {
      baseUrl += `/${this.runAvailable.area}`;
    }
    return baseUrl;
  }

  onMapReady(map: L.Map) {
    this.map = map;
    this.map.attributionControl.setPrefix("");
    //console.log(this.bounds);

    this.loadRunAvailable(this.DEFAULT_DATASET);
    this.initLegends(this.map);
    this.map.attributionControl.setPrefix("");
    // pass a reference to this MeteoTilesComponent
    const ref = this;
    (map as any).timeDimension.on(
      "timeload",
      function (data, comp: MeteoTilesComponent = ref) {
        if (comp.timeLoading) {
          return;
        }
        const start = moment.utc(
          (map as any).timeDimension.getAvailableTimes()[0]
        );
        const current = moment.utc((map as any).timeDimension.getCurrentTime());
        // every 3 hour step refresh multi-model markers on the map
        const hour = current.diff(start, "hours");
        const index = Math.floor(hour / 3) - 1 + start.hours() / 3;
        // console.log(`Hour: +${hour} - Index: ${index}`);
        if (index < 0) {
          if (comp.markersGroup) {
            comp.map.removeLayer(comp.markersGroup);
          }
          return;
        }
        if (index === comp.currentIdx && comp.markersGroup) {
          // do nothing
          return;
        }

        // clean up multi-model layer
        if (comp.markersGroup) {
          comp.map.removeLayer(comp.markersGroup);
        }
        if (comp.showed) {
          comp.loadMarkers(index);
        }
      }
    );
  }

  private loadRunAvailable(dataset: string) {
    this.spinner.show();
    this.timeLoading = true;
    // need to get last run available
    const lastRun$ = this.tilesService.getLastRun(dataset);
    // and the download the MultiModel data
    lastRun$
      .subscribe(
        (runAvailable: RunAvailable) => {
          // runAvailable.reftime : 2020051100
          this.runAvailable = runAvailable;
          console.log(`Last Available Run [${dataset}]`, runAvailable);
          let reftime = runAvailable.reftime;
          this.run = reftime.substr(8, 2);

          // set time
          let startTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .add(runAvailable.start_offset, "hours")
            .toDate();
          // console.log(`startTime: ${moment.utc(startTime).format()}`);
          let endTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .add(runAvailable.end_offset, "hours")
            .toDate();
          // console.log(`endTime ${moment.utc(endTime).format()}`);

          // add time dimension
          let newAvailableTimes = (L as any).TimeDimension.Util.explodeTimeRange(
            startTime,
            endTime,
            `PT${runAvailable.step}H`
          );
          (this.map as any).timeDimension.setAvailableTimes(
            newAvailableTimes,
            "replace"
          );
          const today = moment.utc();
          // console.log(`today: ${today.format()}`);
          if (moment.utc(startTime).isSame(today, "day")) {
            // console.log(`reftime today! set hour to ${today.hours()}`);
            startTime.setUTCHours(today.hours());
          }
          this.timeLoading = false;
          (this.map as any).timeDimension.setCurrentTime(startTime);

          this.setOverlaysToMap();

          this.dataset = runAvailable.dataset;

          // add default layer
          if (this.dataset === "iff") {
            let tp1prec: L.Layer = this.layersControl["overlays"][
              this.DEFAULT_PRODUCT_IFF
            ];
            tp1prec.addTo(this.map);
            this.legends[DP.TPPERC1].addTo(this.map);
          } else {
            let tm2m: L.Layer = this.layersControl["overlays"][
              this.DEFAULT_PRODUCT_COSMO
            ];
            tm2m.addTo(this.map);
            this.legends[DP.TM2].addTo(this.map);
          }
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        this.map.invalidateSize();
        this.spinner.hide();
        // get multi-model products
        this.getMMProducts();
      });
  }

  private getMMProducts() {
    let reftime: Date = this.runAvailable
      ? moment
          .utc(this.runAvailable.reftime.substr(0, 8), "YYYYMMDD")
          .subtract(1, "days")
          .toDate()
      : moment
          .utc()
          .set({ hour: 0, minute: 0, second: 0, millisecond: 0 })
          .toDate();
    if (moment(this.currentMMReftime).isSame(reftime, "day")) {
      // do nothing if the reftime does NOT change
      return;
    }
    this.currentMMReftime = reftime;
    console.log(
      `loading multi-model ensemble products [reftime: ${moment
        .utc(reftime)
        .format()}]`
    );

    // reset current data
    this.mmProductsData = [new Array(24), new Array(24)];

    // emit value every 0.05s
    const source = interval(50);
    // keep a running total of the number of even numbers out
    const numberCount = source.pipe(scan((acc, _) => acc + 1, 0));
    // do not emit until 24 numbers have been emitted
    let mm_interval = this.runAvailable.end_offset + 24 || 72;
    let timerange_number = 24;
    if (mm_interval === 72) {
      timerange_number = 16;
    }
    let maxNumbers = numberCount.pipe(filter((val) => val > timerange_number));
    const loadMultipleData$ = source.pipe(
      catchError((error) => {
        // FIXME stop subscription on error
        // console.log('ERROR', error);
        // clearInterval()
        throw error;
      }),
      // catchError(_ => of('no data!')),
      takeUntil(maxNumbers)
    );

    loadMultipleData$.subscribe((val) => {
      let interval = this.runAvailable.end_offset + 24 || 72;
      const timerange = Object.values(MULTI_MODEL_TIME_RANGES)[val];
      // console.log(`timerange: ${timerange} : ${val}`);
      let filterTM: ObsFilter = {
        product: MultiModelProduct.TM,
        reftime: reftime,
        network: "multim-forecast",
        license: "CCBY_COMPLIANT",
        timerange: timerange,
        interval: interval,
      };
      let filterRH: ObsFilter = {
        product: MultiModelProduct.RH,
        reftime: reftime,
        network: "multim-forecast",
        license: "CCBY_COMPLIANT",
        timerange: timerange,
        interval: interval,
      };
      let productTM$ = this.obsService.getData(filterTM, true);
      let productRH$ = this.obsService.getData(filterRH, true);
      forkJoin([productTM$, productRH$]).subscribe(
        (results) => {
          if (results[0].data.length === 0 && results[1].data.length === 0) {
            this.notify.showWarning("No Multi-Model data found.");
            return;
          }
          const offset = parseInt(timerange.toString().split(",")[1]) / 3600;
          const idx = Math.floor((offset - 27) / 3);
          // console.log(`offset: +${offset}h, idx: ${idx}`);

          this.mmProductsData[0][idx] = results[0].data;
          this.mmProductsData[1][idx] = results[1].data;

          const today = moment.utc();
          const current = moment.utc(
            (this.map as any).timeDimension.getCurrentTime()
          );
          if (moment(current).isSame(today, "day")) {
            (this.map as any).timeDimension.fire("timeload", {
              time: current,
            });
            // (this.map as any).timeDimension.setCurrentTime(current);
            // (this.map as any).timeDimension.nextTime();
          }
        },
        (error) => {
          this.notify.showError(error);
          throw error;
        }
      );
    });
  }

  private setOverlaysToMap() {
    const baseUrl = this.getTilesUrl();

    let bounds =
      this.dataset === "lm5"
        ? L.latLngBounds(LM5_BOUNDS["southWest"], LM5_BOUNDS["northEast"])
        : L.latLngBounds(LM2_BOUNDS["southWest"], LM2_BOUNDS["northEast"]);
    let maxZoom = this.dataset === "lm5" ? 7 : 8;

    if (this.dataset === "iff") {
      this.layersControl["overlays"] = {
        // let overlays = {
        [DP.TPPERC1]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/percentile-perc1/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPERC10]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/percentile-perc10/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPERC25]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/percentile-perc25/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPERC50]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/percentile-perc50/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPERC70]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/percentile-perc70/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPERC75]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/percentile-perc75/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPERC80]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/percentile-perc80/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPERC90]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/percentile-perc90/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPERC99]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/percentile-perc99/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPROB5]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/probability-prob5/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPROB10]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/probability-prob10{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPROB20]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/probability-prob20/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        [DP.TPPROB50]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/probability-prob50/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
      };
      let tp1prec: L.Layer = this.layersControl["overlays"][
        this.DEFAULT_PRODUCT_IFF
      ];
      tp1prec.addTo(this.map);
    } else {
      this.layersControl["overlays"] = {
        [DP.TM2]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/t2m-t2m/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        // Pressure at mean sea level
        [DP.PMSL]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/pressure-pmsl/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            bounds: bounds,
          }),
          {}
        ),
        // Wind speed at 10 meters
        [DP.WIND10M]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/wind-vmax_10m/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            bounds: bounds,
          }),
          {}
        ),
        // Relative humidity Time Layer
        [DP.RH]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/humidity-r/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.5,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        ////////////////////////////////////
        /////////// PRECIPITATION //////////
        ////////////////////////////////////

        // Total precipitation 1h Time Layer
        [DP.PREC1P]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/prec1-tp/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        // Total precipitation 3h Time Layer
        [DP.PREC3P]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/prec3-tp/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        // Total precipitation 6h Time Layer
        [DP.PREC6P]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/prec6-tp/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        // Total precipitation 6h Time Layer
        [DP.PREC12P]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/prec12-tp/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        // Total precipitation 3h Time Layer
        [DP.PREC24P]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/prec24-tp/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        ////////////////////////////////////
        ///////////// SNOWFALL /////////////
        ////////////////////////////////////

        // Snowfall 1h Time Layer
        [DP.SF1]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/snow1-snow/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        // Snowfall 3h Time Layer
        [DP.SF3]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/snow3-snow/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        // Snowfall 6h Time Layer
        [DP.SF6]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/snow6-snow/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        // Snowfall 12h Time Layer
        [DP.SF12]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/snow12-snow/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        // Snowfall 24h Time Layer
        [DP.SF24]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/snow24-snow/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }),
          {}
        ),
        ////////////////////////////////////
        //////////// CLOUD COVER ///////////
        ////////////////////////////////////

        // Total Cloud Time Layer
        [DP.TCC]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/cloud-tcc/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            //opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        // High Cloud Time Layer
        [DP.HCC]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/cloud_hml-hcc/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            //opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        // Medium Cloud Time Layer
        [DP.MCC]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/cloud_hml-mcc/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            //opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
        // Low Cloud Time Layer
        [DP.LCC]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/cloud_hml-lcc/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.9,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }),
          {}
        ),
      };
    }
  }

  private createLegendControl(id: string): L.Control {
    let config: LegendConfig = LEGEND_DATA.find((x) => x.id === id);
    if (!config) {
      console.error(`Legend data NOT found for ID<${id}>`);
      this.notify.showError("Bad legend configuration");
      return;
    }

    const legend = new L.Control({ position: this.LEGEND_POSITION });
    legend.onAdd = () => {
      let div = L.DomUtil.create("div", config.legend_type);
      div.style.clear = "unset";
      div.innerHTML += `<h6>${config.title}</h6>`;
      for (let i = 0; i < config.labels.length; i++) {
        div.innerHTML +=
          '<i style="background:' +
          config.colors[i] +
          '"></i><span>' +
          config.labels[i] +
          "</span><br>";
      }
      return div;
    };
    return legend;
  }

  private initLegends(map: L.Map) {
    let layers = this.layersControl["overlays"];
    this.legends = {
      [DP.TM2]: this.createLegendControl("tm2"),
      [DP.PMSL]: this.createLegendControl("pmsl"),
      [DP.WIND10M]: this.createLegendControl("ws10m"),
      [DP.RH]: this.createLegendControl("rh"),

      [DP.PREC1P]: this.createLegendControl("prp"),
      [DP.PREC3P]: this.createLegendControl("prp"),
      [DP.PREC6P]: this.createLegendControl("prp"),
      [DP.PREC12P]: this.createLegendControl("prp"),
      [DP.PREC24P]: this.createLegendControl("prp"),

      [DP.SF1]: this.createLegendControl("sf"),
      [DP.SF3]: this.createLegendControl("sf"),
      [DP.SF6]: this.createLegendControl("sf"),
      [DP.SF12]: this.createLegendControl("sf"),
      [DP.SF24]: this.createLegendControl("sf"),

      [DP.TCC]: this.createLegendControl("tcc"),
      [DP.HCC]: this.createLegendControl("hcc"),
      [DP.MCC]: this.createLegendControl("mcc"),
      [DP.LCC]: this.createLegendControl("lcc"),

      [DP.TPPERC1]: this.createLegendControl("tpperc"),
      [DP.TPPERC10]: this.createLegendControl("tpperc"),
      [DP.TPPERC25]: this.createLegendControl("tpperc"),
      [DP.TPPERC75]: this.createLegendControl("tpperc"),
      [DP.TPPERC50]: this.createLegendControl("tpperc"),
      [DP.TPPERC99]: this.createLegendControl("tpperc"),

      [DP.TPPROB5]: this.createLegendControl("tpprob"),
      [DP.TPPROB20]: this.createLegendControl("tpprob"),
      [DP.TPPROB10]: this.createLegendControl("tpprob"),
      [DP.TPPROB50]: this.createLegendControl("tpprob"),
    };

    let legends = this.legends;
    let currentActiveLayers = [];
    currentActiveLayers.push(DP.TM2);
    currentActiveLayers.push(DP.TPPERC1);

    map.on("overlayadd", function (event) {
      currentActiveLayers.push(event["name"]);
      // console.log(event["name"]);
      if (event["name"] === DP.TM2) {
        legends[DP.TM2].addTo(map);
      } else if (event["name"] === DP.PMSL) {
        legends[DP.PMSL].addTo(map);
      } else if (event["name"] === DP.WIND10M) {
        legends[DP.WIND10M].addTo(map);
      } else if (event["name"] === DP.RH) {
        legends[DP.RH].addTo(map);
      } else if (
        event["name"] === DP.PREC1P ||
        event["name"] === DP.PREC3P ||
        event["name"] === DP.PREC6P ||
        event["name"] === DP.PREC12P ||
        event["name"] === DP.PREC24P
      ) {
        legends[DP.PREC1P].addTo(map);
      } else if (
        event["name"] === DP.SF1 ||
        event["name"] === DP.SF3 ||
        event["name"] === DP.SF6 ||
        event["name"] === DP.SF12 ||
        event["name"] === DP.SF24
      ) {
        legends[DP.SF1].addTo(map);
      } else if (event["name"] === DP.TCC) {
        legends[DP.TCC].addTo(map);
      } else if (event["name"] === DP.HCC) {
        legends[DP.HCC].addTo(map);
      } else if (event["name"] === DP.MCC) {
        legends[DP.MCC].addTo(map);
      } else if (event["name"] === DP.LCC) {
        legends[DP.LCC].addTo(map);
      } else if (
        event["name"] === DP.TPPERC1 ||
        event["name"] === DP.TPPERC10 ||
        event["name"] === DP.TPPERC25 ||
        event["name"] === DP.TPPERC50 ||
        event["name"] === DP.TPPERC70 ||
        event["name"] === DP.TPPERC75 ||
        event["name"] === DP.TPPERC80 ||
        event["name"] === DP.TPPERC90 ||
        event["name"] === DP.TPPERC99
      ) {
        legends[DP.TPPERC1].addTo(map);
      } else if (
        event["name"] === DP.TPPROB5 ||
        event["name"] === DP.TPPROB10 ||
        event["name"] === DP.TPPROB20 ||
        event["name"] === DP.TPPROB50
      ) {
        legends[DP.TPPROB5].addTo(map);
      }
    });

    map.on("overlayremove", function (event) {
      currentActiveLayers = currentActiveLayers.filter(function (
        value,
        index,
        arr
      ) {
        return value != event["name"];
      });
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
        map.removeControl(legends[DP.PREC3P]);
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
        map.removeControl(legends[DP.PREC12P]);
      } else if (
        event["name"] === DP.PREC24P &&
        !currentActiveLayers.includes(DP.PREC1P) &&
        !currentActiveLayers.includes(DP.PREC3P) &&
        !currentActiveLayers.includes(DP.PREC6P) &&
        !currentActiveLayers.includes(DP.PREC12P)
      ) {
        map.removeControl(legends[DP.PREC24P]);
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
        map.removeControl(legends[DP.SF1]);
      } else if (
        event["name"] === DP.SF12 &&
        !currentActiveLayers.includes(DP.SF1) &&
        !currentActiveLayers.includes(DP.SF3) &&
        !currentActiveLayers.includes(DP.SF6) &&
        !currentActiveLayers.includes(DP.SF24)
      ) {
        map.removeControl(legends[DP.SF1]);
      } else if (
        event["name"] === DP.SF24 &&
        !currentActiveLayers.includes(DP.SF1) &&
        !currentActiveLayers.includes(DP.SF3) &&
        !currentActiveLayers.includes(DP.SF6) &&
        !currentActiveLayers.includes(DP.SF12)
      ) {
        map.removeControl(legends[DP.SF1]);
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
      } else if (
        event["name"] === DP.TPPERC1 &&
        !currentActiveLayers.includes(DP.TPPERC10) &&
        !currentActiveLayers.includes(DP.TPPERC25) &&
        !currentActiveLayers.includes(DP.TPPERC50) &&
        !currentActiveLayers.includes(DP.TPPERC70) &&
        !currentActiveLayers.includes(DP.TPPERC75) &&
        !currentActiveLayers.includes(DP.TPPERC80) &&
        !currentActiveLayers.includes(DP.TPPERC90) &&
        !currentActiveLayers.includes(DP.TPPERC99)
      ) {
        map.removeControl(legends[DP.TPPERC1]);
      } else if (
        event["name"] === DP.TPPERC10 &&
        !currentActiveLayers.includes(DP.TPPERC1) &&
        !currentActiveLayers.includes(DP.TPPERC25) &&
        !currentActiveLayers.includes(DP.TPPERC50) &&
        !currentActiveLayers.includes(DP.TPPERC70) &&
        !currentActiveLayers.includes(DP.TPPERC75) &&
        !currentActiveLayers.includes(DP.TPPERC80) &&
        !currentActiveLayers.includes(DP.TPPERC90) &&
        !currentActiveLayers.includes(DP.TPPERC99)
      ) {
        map.removeControl(legends[DP.TPPERC10]);
      } else if (
        event["name"] === DP.TPPERC25 &&
        !currentActiveLayers.includes(DP.TPPERC1) &&
        !currentActiveLayers.includes(DP.TPPERC10) &&
        !currentActiveLayers.includes(DP.TPPERC50) &&
        !currentActiveLayers.includes(DP.TPPERC70) &&
        !currentActiveLayers.includes(DP.TPPERC75) &&
        !currentActiveLayers.includes(DP.TPPERC80) &&
        !currentActiveLayers.includes(DP.TPPERC90) &&
        !currentActiveLayers.includes(DP.TPPERC99)
      ) {
        map.removeControl(legends[DP.TPPERC25]);
      } else if (
        event["name"] === DP.TPPERC50 &&
        !currentActiveLayers.includes(DP.TPPERC1) &&
        !currentActiveLayers.includes(DP.TPPERC10) &&
        !currentActiveLayers.includes(DP.TPPERC25) &&
        !currentActiveLayers.includes(DP.TPPERC70) &&
        !currentActiveLayers.includes(DP.TPPERC75) &&
        !currentActiveLayers.includes(DP.TPPERC80) &&
        !currentActiveLayers.includes(DP.TPPERC90) &&
        !currentActiveLayers.includes(DP.TPPERC99)
      ) {
        map.removeControl(legends[DP.TPPERC50]);
      } else if (
        event["name"] === DP.TPPERC70 &&
        !currentActiveLayers.includes(DP.TPPERC1) &&
        !currentActiveLayers.includes(DP.TPPERC10) &&
        !currentActiveLayers.includes(DP.TPPERC25) &&
        !currentActiveLayers.includes(DP.TPPERC50) &&
        !currentActiveLayers.includes(DP.TPPERC75) &&
        !currentActiveLayers.includes(DP.TPPERC80) &&
        !currentActiveLayers.includes(DP.TPPERC90) &&
        !currentActiveLayers.includes(DP.TPPERC99)
      ) {
        map.removeControl(legends[DP.TPPERC70]);
      } else if (
        event["name"] === DP.TPPERC75 &&
        !currentActiveLayers.includes(DP.TPPERC1) &&
        !currentActiveLayers.includes(DP.TPPERC10) &&
        !currentActiveLayers.includes(DP.TPPERC25) &&
        !currentActiveLayers.includes(DP.TPPERC50) &&
        !currentActiveLayers.includes(DP.TPPERC70) &&
        !currentActiveLayers.includes(DP.TPPERC80) &&
        !currentActiveLayers.includes(DP.TPPERC90) &&
        !currentActiveLayers.includes(DP.TPPERC99)
      ) {
        map.removeControl(legends[DP.TPPERC75]);
      } else if (
        event["name"] === DP.TPPERC80 &&
        !currentActiveLayers.includes(DP.TPPERC1) &&
        !currentActiveLayers.includes(DP.TPPERC10) &&
        !currentActiveLayers.includes(DP.TPPERC25) &&
        !currentActiveLayers.includes(DP.TPPERC50) &&
        !currentActiveLayers.includes(DP.TPPERC70) &&
        !currentActiveLayers.includes(DP.TPPERC75) &&
        !currentActiveLayers.includes(DP.TPPERC90) &&
        !currentActiveLayers.includes(DP.TPPERC99)
      ) {
        map.removeControl(legends[DP.TPPERC80]);
      } else if (
        event["name"] === DP.TPPERC90 &&
        !currentActiveLayers.includes(DP.TPPERC1) &&
        !currentActiveLayers.includes(DP.TPPERC10) &&
        !currentActiveLayers.includes(DP.TPPERC25) &&
        !currentActiveLayers.includes(DP.TPPERC50) &&
        !currentActiveLayers.includes(DP.TPPERC70) &&
        !currentActiveLayers.includes(DP.TPPERC75) &&
        !currentActiveLayers.includes(DP.TPPERC80) &&
        !currentActiveLayers.includes(DP.TPPERC99)
      ) {
        map.removeControl(legends[DP.TPPERC90]);
      } else if (
        event["name"] === DP.TPPERC99 &&
        !currentActiveLayers.includes(DP.TPPERC1) &&
        !currentActiveLayers.includes(DP.TPPERC10) &&
        !currentActiveLayers.includes(DP.TPPERC25) &&
        !currentActiveLayers.includes(DP.TPPERC50) &&
        !currentActiveLayers.includes(DP.TPPERC70) &&
        !currentActiveLayers.includes(DP.TPPERC75) &&
        !currentActiveLayers.includes(DP.TPPERC80) &&
        !currentActiveLayers.includes(DP.TPPERC90)
      ) {
        map.removeControl(legends[DP.TPPERC90]);
      } else if (
        event["name"] === DP.TPPROB5 &&
        !currentActiveLayers.includes(DP.TPPROB10) &&
        !currentActiveLayers.includes(DP.TPPROB20) &&
        !currentActiveLayers.includes(DP.TPPROB50)
      ) {
        map.removeControl(legends[DP.TPPROB5]);
      } else if (
        event["name"] === DP.TPPROB10 &&
        !currentActiveLayers.includes(DP.TPPROB5) &&
        !currentActiveLayers.includes(DP.TPPROB20) &&
        !currentActiveLayers.includes(DP.TPPROB50)
      ) {
        map.removeControl(legends[DP.TPPROB5]);
      } else if (
        event["name"] === DP.TPPROB20 &&
        !currentActiveLayers.includes(DP.TPPROB5) &&
        !currentActiveLayers.includes(DP.TPPROB10) &&
        !currentActiveLayers.includes(DP.TPPROB50)
      ) {
        map.removeControl(legends[DP.TPPROB5]);
      } else if (
        event["name"] === DP.TPPROB50 &&
        !currentActiveLayers.includes(DP.TPPROB5) &&
        !currentActiveLayers.includes(DP.TPPROB10) &&
        !currentActiveLayers.includes(DP.TPPROB20)
      ) {
        map.removeControl(legends[DP.TPPROB5]);
      }
    });

    // add default legend to the map
    if (this.dataset === "iff") {
      this.legends[DP.TPPERC1].addTo(map);
      currentActiveLayers.push(DP.TPPERC1);
    } else {
      this.legends[DP.TM2].addTo(map);
      currentActiveLayers.push(DP.TM2);
    }
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
    // clean up multi-model layer
    if (this.markersGroup) {
      // remove marker layer
      this.cleanupMMLayer();
    }

    this.loadRunAvailable(newDs);

    this.dataset = newDs;
    if (this.dataset === "lm5") {
      this.map.setView(MAP_CENTER, 5);
      // this.map.attributionControl.removeAttribution(this.license);
      // this.map.attributionControl.removeAttribution(this.license_iff);
      // this.map.attributionControl.addAttribution(this.license_cosmo);
    } else if (this.dataset === "lm2.2") {
      this.map.setView(MAP_CENTER, 6);
      // this.map.attributionControl.removeAttribution(this.license);
      // this.map.attributionControl.removeAttribution(this.license_iff);
      // this.map.attributionControl.addAttribution(this.license_cosmo);
    } else if (this.dataset === "iff") {
      this.map.setView(MAP_CENTER, 6);
      // this.map.attributionControl.removeAttribution(this.license);
      // this.map.attributionControl.removeAttribution(this.license_cosmo);
      // this.map.attributionControl.addAttribution(this.license_iff);
    } else {
      console.error(`Unknown dataset ${newDs}`);
    }
  }

  private cleanupMMLayer() {
    if (!this.map) {
      return;
    }
    this.map.removeLayer(this.markersGroup);
    this.allMarkers = [];
    this.markers = [];
  }

  /**
   * Change the Multi-Model product.
   * @param choice
   */
  changeMMProduct(choice: MultiModelProduct) {
    if (choice !== this.mmProduct) {
      this.mmProduct = choice;
      if (this.showed && this.markersGroup) {
        this.map.removeLayer(this.markersGroup);
        this.loadMarkers();
      }
    }
  }

  onMapZoomEnd($event) {
    // console.log(`Map Zoom: ${this.map.getZoom()}`);
    if (this.showed && this.markersGroup) {
      this.map.removeLayer(this.markersGroup);
      this.markers = this.reduceOverlapping(this.allMarkers);
      this.markersGroup = L.layerGroup(this.markers);
      this.markersGroup.addTo(this.map);
    }
  }

  private loadMarkers(timerangeIdx = 0) {
    this.currentIdx = timerangeIdx;
    const idx = this.mmProduct === MultiModelProduct.TM ? 0 : 1;
    if (
      !this.mmProductsData ||
      !this.mmProductsData[idx] ||
      !this.mmProductsData[idx][timerangeIdx]
    ) {
      // console.log("No data to load");
      return;
    }
    // console.log(`load markers. timerange IDX: ${timerangeIdx}`);
    this.allMarkers = [];
    let obsData: ObsData;
    const unit: string =
      this.mmProduct === MultiModelProduct.TM ? "<i>°</i>" : "";
    let min: number, max: number;
    this.mmProductsData[idx][timerangeIdx].forEach((s) => {
      obsData = s.prod.find((x) => x.var === this.mmProduct);
      let localMin = Math.min(...obsData.val.map((v) => v.val));
      if (!min || localMin < min) {
        min = localMin;
      }
      let localMax = Math.max(...obsData.val.map((v) => v.val));
      if (!max || localMax > max) {
        max = localMax;
      }
    });
    this.mmProductsData[idx][timerangeIdx].forEach((s) => {
      obsData = s.prod.find((x) => x.var === this.mmProduct);
      // console.log(obsData);
      if (obsData.val.length !== 0) {
        const val = ObsService.showData(obsData.val[0].val, this.mmProduct);
        let icon = L.divIcon({
          html: `<div class="mstObsIcon"><span>${val}` + unit + "</span></div>",
          iconSize: [24, 6],
          className: `mst-marker-icon
            mst-obs-marker-color-${this.obsService.getColor(
              obsData.val[0].val,
              min,
              max
            )}`,
        });
        const m = new L.Marker([s.stat.lat, s.stat.lon], {
          icon: icon,
        });
        m.options["station"] = s.stat;
        m.options["data"] = obsData;
        m.bindTooltip(
          MeteoTilesComponent.buildTooltipTemplate(
            s.stat,
            obsData.val[0].ref,
            val + unit
          ),
          {
            direction: "top",
            offset: [4, -2],
            opacity: 0.75,
            className: "leaflet-tooltip mst-obs-tooltip",
          }
        );
        this.allMarkers.push(m);
      }
    });
    // reduce overlapping
    this.markers = this.reduceOverlapping(this.allMarkers);
    // console.info(`Number of markers: ${this.markers.length}`);

    this.markersGroup = L.layerGroup(this.markers);
    this.markersGroup.addTo(this.map);
  }

  private static buildTooltipTemplate(
    station: Station,
    reftime?: string,
    val?: string
  ) {
    let ident = station.ident || "";
    let name =
      station.details && station.details.length
        ? station.details.find((e) => e.var === "B01019")
        : undefined;
    const template =
      `<h6 class="mb-1" style="font-size: small;">` +
      (name ? `${name.val}` : "n/a") +
      `<span class="badge badge-secondary ml-2">${val}</span></h6>` +
      `<ul class="p-0 m-0"><li><b>Lat</b>: ${station.lat}</li><li><b>Lon</b>: ${station.lon}</li></ul>` +
      `<hr class="my-1"/>` +
      `<span>` +
      (reftime ? `${moment.utc(reftime).format("MMM Do, HH:mm")}` : "n/a") +
      `</span>`;
    return template;
  }

  private reduceOverlapping(markers: L.Marker[]) {
    let n: L.Marker[] = [];
    if (this.map.getZoom() === MAX_ZOOM) {
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
    // console.log(`number of markers reduced to ${n.length}`);
    return n;
  }

  /**
   *
   */
  showHideMultiModel() {
    this.showed = !this.showed;
    if (!this.showed) {
      this.map.removeLayer(this.markersGroup);
    } else {
      this.markers = this.reduceOverlapping(this.allMarkers);
      this.markersGroup = L.layerGroup(this.markers);
      this.markersGroup.addTo(this.map);
    }
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

  /**
   * Convert data model for observations to GeoJSON.
   * CURRENTLY NOT USED
   * @param data
   * @param product
   * @private
   */
  private toGeoJSON(data: Observation[], product: string, startTime: Date) {
    let features = [];
    data.forEach((obs) => {
      const s = obs.stat;
      let obsData: ObsData[] = obs.prod.filter((x) => x.var === product);
      let f = {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [s.lon, s.lat],
        },
        properties: {
          times: [],
          values: [],
        },
      };
      // console.log(`station: ${s.details[0].val}`);
      const multiTimeRanges: boolean = obsData[0].trange ? true : false;
      if (multiTimeRanges) {
        obsData = obsData
          .filter((x) =>
            (<any>Object).values(MULTI_MODEL_TIME_RANGES).includes(x.trange)
          )
          .sort(
            (a, b) =>
              parseInt(a.trange.split(",")[1]) -
              parseInt(b.trange.split(",")[1])
          );
        let offset = 0;
        obsData.forEach((o) => {
          let t = moment.utc(startTime).add(offset, "hour");
          // console.log(`[timerange: ${o.trange}, reftime: ${t.format()}, value: ${o.val[0].val}`);
          f.properties.times.push(t.toDate());
          f.properties.values.push(o.val[0].val);
          offset += 3;
        });
      } else {
        f.properties.values.push(obsData[0].val[0].val);
      }
      features.push(f);
    });
    return features;
  }
}
