import { Component } from "@angular/core";
import { environment } from "@rapydo/../environments/environment";
import { Observable, forkJoin, of, concat, interval } from "rxjs";
import { filter, scan, takeUntil, withLatestFrom, map } from "rxjs/operators";
import * as moment from "moment";
import * as L from "leaflet";
import "leaflet-timedimension/dist/leaflet.timedimension.src.js";
import "@app/../assets/js/leaflet.timedimension.tilelayer.portus.js";
import { TilesService } from "./services/tiles.service";
import { ObsService } from "../observation-maps/services/obs.service";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
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
  MultiModelProduct,
} from "./meteo-tiles.config";

declare module "leaflet" {
  let timeDimension: any;
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

const TILES_PATH = environment.production
  ? "resources/tiles"
  : "app/custom/assets/images/tiles";

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
  readonly license_iff =
    '&copy; <a href="http://www.openstreetmap.org/copyright">Open Street Map</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by/4.0/legalcode">Work distributed under License CC BY 4.0</a>';
  readonly license_cosmo =
    '&copy; <a href="http://www.openstreetmap.org/copyright">Open Street Map</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>';
  readonly license =
    '&copy; <a href="http://www.openstreetmap.org/copyright">Open Street Map</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>';

  map: L.Map;
  dataset: string;
  private run: string;
  private legends: { [key: string]: L.Control } = {};
  // license = this.license;

  LAYER_OSM = L.tileLayer("http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: this.license,
    //'&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>'+l_iff,
    maxZoom: MAX_ZOOM,
    minZoom: MIN_ZOOM,
  });
  LAYER_MAPBOX_LIGHT = L.tileLayer(
    "https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw",
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
      "Carto Map": this.LAYER_DARKMATTER,
      "Mapbox Map": this.LAYER_MAPBOX_LIGHT,
    },
  };
  options = {
    zoom: MIN_ZOOM,
    center: L.latLng([46.879966, 11.726909]),
    timeDimension: true,
    timeDimensionControl: true,
    timeDimensionControlOptions: {
      autoPlay: false,
      loopButton: true,
      timeSteps: 1,
      playReverseButton: true,
      limitSliders: true,
      playerOptions: {
        buffer: 0,
        transitionTime: 250,
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
  private mmProductsData: any[][] = [new Array(24), new Array(24)];

  constructor(
    private tilesService: TilesService,
    private obsService: ObsService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {
    // set the initial set of displayed layers
    this.options["layers"] = [this.LAYER_MAPBOX_LIGHT];
    this.dataset = this.DEFAULT_DATASET;
  }

  onMapReady(map: L.Map) {
    this.map = map;
    this.loadRunAvailable(this.DEFAULT_DATASET);
    this.initLegends(this.map);
    // pass a reference to this MeteoTilesComponent
    const ref = this;
    (map as any).timeDimension.on("timeload", function (
      data,
      comp: MeteoTilesComponent = ref
    ) {
      let date = new Date((map as any).timeDimension.getCurrentTime());
      // every 3 hour step refresh multi-model markers on the map
      // TODO
      console.log(moment.utc(date).format());
      // clean up multi-model layer
      if (comp.markersGroup) {
        comp.map.removeLayer(comp.markersGroup);
      }
      if (comp.showed) {
        comp.loadMarkers(Math.floor(Math.random() * 23));
      }
    });
  }

  private loadRunAvailable(dataset: string) {
    this.spinner.show();
    // need to get last run available
    const lastRun$ = this.tilesService.getLastRun(dataset);
    // and the download the MultiModel data
    lastRun$
      .subscribe(
        (runAvailable: RunAvailable) => {
          // runAvailable.reftime : 2020051100
          this.runAvailable = runAvailable;
          console.log("Available Run", runAvailable);
          let reftime = runAvailable.reftime;
          console.log("reftime", reftime);
          this.run = reftime.substr(8, 2);

          // set time
          let startTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .add(runAvailable.start_offset, "hours")
            .toDate();
          console.log(`startTime: ${startTime}`);
          // let startTime = new Date(Date.UTC(2020, 4, 11));
          // startTime.setUTCHours(0, 0, 0, 0);
          // let endTime = 'PT72H';
          let endTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .add(runAvailable.end_offset, "hours")
            .toDate();
          console.log(`endTime ${endTime}`);

          // add time dimension
          /*
          let newAvailableTimes = (L as any).TimeDimension.Util.explodeTimeRange(
            startTime,
            endTime,
            `PT${runAvailable.step}H`
          );
          (this.map as any).timeDimension.setAvailableTimes(
            newAvailableTimes,
            "replace"
          );
          (this.map as any).timeDimension.setCurrentTime(startTime);
           */

          this.setOverlaysToMap();

          // let tm2m: L.Layer = this.layersControl["overlays"][
          //   this.DEFAULT_PRODUCT_COSMO
          // ];
          // tm2m.addTo(this.map);
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
        // use rxjs operator to concat this
        this.getMMProducts();
      });
  }

  private getMMProducts(timerange = MULTI_MODEL_TIME_RANGES._1D3H) {
    console.log("loading multi-model ensemble products");
    // reset current data
    this.mmProductsData = [new Array(24), new Array(24)];

    // let reftime: Date = this.runAvailable
    //   ? moment(this.runAvailable.reftime.substr(0, 6), "YYYYMMDD").toDate()
    //   : moment
    //       .utc()
    //       .set({ hour: 0, minute: 0, second: 0, millisecond: 0 })
    //       .toDate();
    const reftime = moment.utc("2020-12-10 00:00:00").toDate();
    console.log(
      `reftime: ${moment
        .utc(reftime)
        .format()}, timerange ${timerange.toString()}`
    );

    // added
    let startTime = moment.utc(reftime, "YYYYMMDDHH").add(27, "hours").toDate();
    console.log(`startTime: ${startTime}`);
    // let startTime = new Date(Date.UTC(2020, 4, 11));
    // startTime.setUTCHours(0, 0, 0, 0);
    // let endTime = 'PT72H';
    let endTime = moment.utc(reftime, "YYYYMMDDHH").add(96, "hours").toDate();
    console.log(`endTime ${endTime}`);
    let newAvailableTimes = (L as any).TimeDimension.Util.explodeTimeRange(
      startTime,
      endTime,
      `PT3H`
    );
    (this.map as any).timeDimension.setAvailableTimes(
      newAvailableTimes,
      "replace"
    );
    (this.map as any).timeDimension.setCurrentTime(startTime);
    // end

    // emit value every 0.5s
    const source = interval(500);
    // keep a running total of the number of even numbers out
    const numberCount = source.pipe(scan((acc, _) => acc + 1, 0));
    // do not emit until 24 numbers have been emitted
    const maxNumbers = numberCount.pipe(filter((val) => val > 24));
    const example = source.pipe(
      // map(val => `number (timerange: ${Object.values(MULTI_MODEL_TIME_RANGES)[val]}) : ${val}`),
      takeUntil(maxNumbers)
    );
    // const subscribe = example.subscribe(val => console.log(val));

    // console.log(`MULTI_MODEL_TIME_RANGES[0] ${Object.values(MULTI_MODEL_TIME_RANGES)[0]}`);

    const subscribe = example.subscribe((val) => {
      const timerange = Object.values(MULTI_MODEL_TIME_RANGES)[val];
      console.log(`timerange: ${timerange} : ${val}`);
      let filterTM: ObsFilter = {
        product: MultiModelProduct.TM,
        reftime: reftime,
        network: "multim-forecast",
        timerange: timerange,
      };
      let filterRH: ObsFilter = {
        product: MultiModelProduct.RH,
        reftime: reftime,
        network: "multim-forecast",
        timerange: timerange,
      };
      let productTM$ = this.obsService.getData(filterTM, true);
      let productRH$ = this.obsService.getData(filterRH, true);
      // let productTM = of(MOCK_MM_TEMP_OBS_RESPONSE);
      // let productRH = of(MOCK_MM_RH_OBS_RESPONSE);
      forkJoin([productTM$, productRH$]).subscribe(
        (results) => {
          if (results[0].data.length === 0 && results[1].data.length === 0) {
            this.notify.showWarning("No Multi-Model data found.");
            return;
          }
          const offset = parseInt(timerange.toString().split(",")[1]) / 3600;
          const idx = Math.floor((offset - 27) / 3);
          console.log(`offset: +${offset}h, idx: ${idx}`);
          // set time
          let startTime = moment.utc(reftime).add(27, "hours").toDate();
          console.log(`startTime: ${moment.utc(startTime).format()}`);

          this.mmProductsData[0][idx] = results[0].data;
          this.mmProductsData[1][idx] = results[1].data;

          // if (this.markersGroup) {
          //   this.map.removeLayer(this.markersGroup);
          // }
          // if (this.showed) {
          //   this.loadMarkers();
          // }
        },
        (error) => {
          this.notify.showError(error);
        }
      );
    });
  }

  private setOverlaysToMap() {
    let baseUrl = `${TILES_PATH}/${this.run}-${this.dataset}`;
    if (environment.production) {
      baseUrl += `/${this.runAvailable.area}`;
    }
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
            opacity: 0.9,
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
            opacity: 0.9,
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
            opacity: 0.9,
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
            opacity: 0.9,
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
            opacity: 0.9,
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
            opacity: 0.9,
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
            opacity: 0.9,
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
            opacity: 0.9,
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
            opacity: 0.9,
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
            opacity: 0.9,
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
        // Relative humidity Time Layer
        [DP.RH]: L.timeDimension.layer.tileLayer.portus(
          L.tileLayer(`${baseUrl}/humidity-r/{d}{h}/{z}/{x}/{y}.png`, {
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
      [DP.PREC3P]: this.createLegendControl("prec3tp"),
      [DP.PREC6P]: this.createLegendControl("prec6tp"),
      [DP.SF3]: this.createLegendControl("sf3"),
      [DP.RH]: this.createLegendControl("rh"),
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
    map.on("overlayadd", function (event) {
      // console.log(event["name"]);
      if (event["name"] === DP.TM2) {
        legends[DP.TM2].addTo(map);
      } else if (event["name"] === DP.PREC3P) {
        legends[DP.PREC3P].addTo(this);
      } else if (event["name"] === DP.PREC6P) {
        legends[DP.PREC6P].addTo(this);
      } else if (event["name"] === DP.SF3 || event["name"] === DP.SF6) {
        legends[DP.SF3].addTo(this);
      } else if (event["name"] === DP.RH) {
        legends[DP.RH].addTo(this);
      } else if (event["name"] === DP.HCC) {
        legends[DP.HCC].addTo(this);
      } else if (event["name"] === DP.MCC) {
        legends[DP.MCC].addTo(this);
      } else if (event["name"] === DP.LCC) {
        legends[DP.LCC].addTo(this);
      } else if (
        event["name"] === DP.TPPERC1 ||
        event["name"] === DP.TPPERC10 ||
        event["name"] === DP.TPPERC25 ||
        event["name"] === DP.TPPERC50 ||
        event["name"] === DP.TPPERC75 ||
        event["name"] === DP.TPPERC99
      ) {
        legends[DP.TPPERC1].addTo(this);
      } else if (
        event["name"] === DP.TPPROB5 ||
        event["name"] === DP.TPPROB10 ||
        event["name"] === DP.TPPROB20 ||
        event["name"] === DP.TPPROB50
      ) {
        legends[DP.TPPROB5].addTo(this);
      }
    });

    map.on("overlayremove", function (event) {
      if (event["name"] === DP.TM2) {
        this.removeControl(legends[DP.TM2]);
      } else if (event["name"] === DP.PREC3P) {
        this.removeControl(legends[DP.PREC3P]);
      } else if (event["name"] === DP.PREC6P) {
        this.removeControl(legends[DP.PREC6P]);
      } else if (event["name"] === DP.SF3 && !map.hasLayer(layers[DP.SF6])) {
        this.removeControl(legends[DP.SF3]);
      } else if (event["name"] === DP.SF6 && !map.hasLayer(layers[DP.SF3])) {
        this.removeControl(legends[DP.SF3]);
      } else if (event["name"] === DP.RH) {
        this.removeControl(legends[DP.RH]);
      } else if (event["name"] === DP.HCC) {
        this.removeControl(legends[DP.HCC]);
      } else if (event["name"] === DP.MCC) {
        this.removeControl(legends[DP.MCC]);
      } else if (event["name"] === DP.LCC) {
        this.removeControl(legends[DP.LCC]);
      } else if (
        event["name"] === DP.TPPERC1 &&
        !map.hasLayer(layers[DP.TPPERC10]) &&
        !map.hasLayer(layers[DP.TPPERC25]) &&
        !map.hasLayer(layers[DP.TPPERC50]) &&
        !map.hasLayer(layers[DP.TPPERC75]) &&
        !map.hasLayer(layers[DP.TPPERC99])
      ) {
        this.removeControl(legends[DP.TPPERC1]);
      } else if (
        event["name"] === DP.TPPERC10 &&
        !map.hasLayer(layers[DP.TPPERC1]) &&
        !map.hasLayer(layers[DP.TPPERC25]) &&
        !map.hasLayer(layers[DP.TPPERC50]) &&
        !map.hasLayer(layers[DP.TPPERC75]) &&
        !map.hasLayer(layers[DP.TPPERC99])
      ) {
        this.removeControl(legends[DP.TPPERC1]);
      } else if (
        event["name"] === DP.TPPERC25 &&
        !map.hasLayer(layers[DP.TPPERC1]) &&
        !map.hasLayer(layers[DP.TPPERC10]) &&
        !map.hasLayer(layers[DP.TPPERC50]) &&
        !map.hasLayer(layers[DP.TPPERC75]) &&
        !map.hasLayer(layers[DP.TPPERC99])
      ) {
        this.removeControl(legends[DP.TPPERC50]);
      } else if (
        event["name"] === DP.TPPERC50 &&
        !map.hasLayer(layers[DP.TPPERC1]) &&
        !map.hasLayer(layers[DP.TPPERC10]) &&
        !map.hasLayer(layers[DP.TPPERC25]) &&
        !map.hasLayer(layers[DP.TPPERC75]) &&
        !map.hasLayer(layers[DP.TPPERC99])
      ) {
        this.removeControl(legends[DP.TPPERC75]);
      } else if (
        event["name"] === DP.TPPERC75 &&
        !map.hasLayer(layers[DP.TPPERC1]) &&
        !map.hasLayer(layers[DP.TPPERC10]) &&
        !map.hasLayer(layers[DP.TPPERC25]) &&
        !map.hasLayer(layers[DP.TPPERC50]) &&
        !map.hasLayer(layers[DP.TPPERC99])
      ) {
        this.removeControl(legends[DP.TPPERC99]);
      } else if (
        event["name"] === DP.TPPERC99 &&
        !map.hasLayer(layers[DP.TPPERC1]) &&
        !map.hasLayer(layers[DP.TPPERC10]) &&
        !map.hasLayer(layers[DP.TPPERC25]) &&
        !map.hasLayer(layers[DP.TPPERC50]) &&
        !map.hasLayer(layers[DP.TPPERC75])
      ) {
        this.removeControl(legends[DP.TPPERC1]);
      } else if (
        event["name"] === DP.TPPROB5 &&
        !map.hasLayer(layers[DP.TPPROB10]) &&
        !map.hasLayer(layers[DP.TPPROB20]) &&
        !map.hasLayer(layers[DP.TPPROB50])
      ) {
        this.removeControl(legends[DP.TPPROB5]);
      } else if (
        event["name"] === DP.TPPROB10 &&
        !map.hasLayer(layers[DP.TPPROB5]) &&
        !map.hasLayer(layers[DP.TPPROB20]) &&
        !map.hasLayer(layers[DP.TPPROB50])
      ) {
        this.removeControl(legends[DP.TPPROB5]);
      } else if (
        event["name"] === DP.TPPROB20 &&
        !map.hasLayer(layers[DP.TPPROB5]) &&
        !map.hasLayer(layers[DP.TPPROB10]) &&
        !map.hasLayer(layers[DP.TPPROB50])
      ) {
        this.removeControl(legends[DP.TPPROB5]);
      } else if (
        event["name"] === DP.TPPROB50 &&
        !map.hasLayer(layers[DP.TPPROB5]) &&
        !map.hasLayer(layers[DP.TPPROB10]) &&
        !map.hasLayer(layers[DP.TPPROB20])
      ) {
        this.removeControl(legends[DP.TPPROB5]);
      }
    });

    // add default legend to the map
    if (this.dataset === "iff") {
      this.legends[DP.TPPERC1].addTo(map);
    } else {
      this.legends[DP.TM2].addTo(map);
    }
  }

  changeDataset(newDs) {
    // remove all current layers
    let overlays = this.layersControl["overlays"];
    let currentActiveNames = [];
    for (let name in overlays) {
      if (this.map.hasLayer(overlays[name])) {
        currentActiveNames.push(name);
        this.map.removeLayer(overlays[name]);
      }
    }

    this.loadRunAvailable(newDs); //removeAttribution

    this.dataset = newDs;
    if (this.dataset === "lm5") {
      this.map.setView(MAP_CENTER, 5);
      this.map.attributionControl.removeAttribution(this.license);
      this.map.attributionControl.removeAttribution(this.license_iff);
      this.map.attributionControl.addAttribution(this.license_cosmo);
    } else if (this.dataset === "lm2.2") {
      this.map.setView(MAP_CENTER, 6);
      this.map.attributionControl.removeAttribution(this.license);
      this.map.attributionControl.removeAttribution(this.license_iff);
      this.map.attributionControl.addAttribution(this.license_cosmo);
    } else if (this.dataset === "iff") {
      this.map.setView(MAP_CENTER, 6);
      this.map.attributionControl.removeAttribution(this.license);
      this.map.attributionControl.removeAttribution(this.license_cosmo);
      this.map.attributionControl.addAttribution(this.license_iff);
    } else {
      console.error(`Unknown dataset ${newDs}`);
    }

    /*
    // remove all current layers
    let overlays = this.layersControl["overlays"];
    let currentActiveNames = [];
    for (let name in overlays) {
      if (this.map.hasLayer(overlays[name])) {
        currentActiveNames.push(name);
        this.map.removeLayer(overlays[name]);
      }
    }
    this.setOverlaysToMap();

    // reload the new list of layers
    overlays = this.layersControl["overlays"];

    // apply the same list to the map
    for (let name in overlays) {
      if (currentActiveNames.includes(name)) {
        let tileLayer: L.Layer = overlays[name];
        tileLayer.addTo(this.map);
        this.legends[name].addTo(this.map);
      }
    }
    if (this.dataset === "iff") {
      let tp1prec: L.Layer = this.layersControl["overlays"][
        this.DEFAULT_PRODUCT_IFF
      ];
      tp1prec.addTo(this.map);
      this.legends[TPPERC1].addTo(this.map);
    } else {
      let tm2m: L.Layer = this.layersControl["overlays"][
        this.DEFAULT_PRODUCT_COSMO
      ];
      tm2m.addTo(this.map);
      this.legends[TM2].addTo(this.map);
    }
     */
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
    console.log(`loading markers`);
    this.allMarkers = [];
    let obsData: ObsData;
    const idx = this.mmProduct === MultiModelProduct.TM ? 0 : 1;
    const unit: string =
      this.mmProduct === MultiModelProduct.TM ? "<i>°</i>" : "";
    let min: number, max: number;
    this.mmProductsData[idx][timerangeIdx].forEach((s) => {
      obsData = s.prod.find((x) => x.var === this.mmProduct);
      let localMin = Math.min(
        ...obsData.val.filter((v) => v.rel === 1).map((v) => v.val)
      );
      if (!min || localMin < min) {
        min = localMin;
      }
      let localMax = Math.max(
        ...obsData.val.filter((v) => v.rel === 1).map((v) => v.val)
      );
      if (!max || localMax > max) {
        max = localMax;
      }
    });
    this.mmProductsData[idx][timerangeIdx].forEach((s) => {
      obsData = s.prod.find((x) => x.var === this.mmProduct);
      // console.log(obsData);
      if (obsData.val.length !== 0) {
        let icon = L.divIcon({
          html:
            `<div class="mstObsIcon"><span>${ObsService.showData(
              obsData.val[0].val,
              this.mmProduct
            )}` +
            unit +
            "</span></div>",
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
          MeteoTilesComponent.buildTooltipTemplate(s.stat, obsData.val[0].ref),
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

  private static buildTooltipTemplate(station: Station, reftime?: string) {
    let ident = station.ident || "";
    let name =
      station.details && station.details.length
        ? station.details.find((e) => e.var === "B01019")
        : undefined;
    const template =
      `<ul class="p-1 m-0"><li>` +
      (name ? `<b>${name.val}</b>` : "n/a") +
      `</li><li><b>Lat</b>: ${station.lat}, <b>Lon</b>: ${station.lon}</li>` +
      `<hr class="m-1"/><li>` +
      (reftime ? `${reftime}` : "n/a") +
      `</li></ul>`;
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
