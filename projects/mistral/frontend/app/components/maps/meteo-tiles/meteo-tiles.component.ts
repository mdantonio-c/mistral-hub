import { Component } from "@angular/core";
import { environment } from "@rapydo/../environments/environment";
import { Observable, forkJoin } from "rxjs";
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
  ObservationResponse,
  Station,
  RunAvailable,
} from "../../../types";

declare module "leaflet" {
  let timeDimension: any;
}

const MAP_CENTER = L.latLng(41.879966, 12.28);
/*
"lm2.2": {
  "lat": [34.5, 48.0],
  "lon": [5.0, 21.2]
}
 */
const LM2_BOUNDS = {
  southWest: L.latLng(34.5, 5.0),
  northEast: L.latLng(48.0, 21.2),
};
/*
"lm5":{
  "lat": [25.8, 55.5],
  "lon": [-30.9, 47.0]
}
 */
const LM5_BOUNDS = {
  southWest: L.latLng(25.8, -30.9),
  northEast: L.latLng(55.5, 47.0),
};
const TILES_PATH = environment.production
  ? "resources/tiles"
  : "app/custom/assets/images/tiles";
// Product constants
const TM2 = "Temperature at 2 meters",
  PREC3P = "Total Precipitation (3h)",
  PREC6P = "Total Precipitation (6h)",
  SF3 = "Snowfall (3h)",
  SF6 = "Snowfall (6h)",
  RH = "Relative Humidity",
  HCC = "High Cloud",
  MCC = "Medium Cloud",
  LCC = "Low Cloud",
  TPPERC1 = "Precipitation percentiles 1%",
  TPPERC10 = "Precipitation percentile 10%",
  TPPERC25 = "Precipitation percentile 25%",
  TPPERC50 = "Precipitation percentile 50%",
  TPPERC75 = "Precipitation percentile 75%",
  TPPERC99 = "Precipitation percentile 99%",
  TPPROB5 = "Precipitation probability 5%",
  TPPROB10 = "Precipitation probability 10%",
  TPPROB20 = "Precipitation probability 20%",
  TPPROB50 = "Precipitation probability 50%";

enum MultiModelProduct {
  TM = "B12101",
  RH = "B13003",
}

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
  // readonly DEFAULT_RESOLUTION = "lm5";
  readonly LEGEND_POSITION = "bottomleft";
  readonly DEFAULT_DATASET = "lm5";

  map: L.Map;
  dataset: string;
  private run: string;
  private legends: { [key: string]: L.Control } = {};

  LAYER_OSM = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a href="https://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>',
      maxZoom: 8,
      minZoom: 5,
    }
  );
  LAYER_MAPBOX_LIGHT = L.tileLayer(
    "https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw",
    {
      id: "mapbox.light",
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="https://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>',
      maxZoom: MAX_ZOOM,
      minZoom: MIN_ZOOM,
    }
  );
  LAYER_DARKMATTER = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png",
    {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="https://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>',
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
  private mmProductsData: any[] = new Array(2);

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

    this.getMMProducts();
  }

  private loadRunAvailable(dataset: string) {
    this.spinner.show();
    this.tilesService
      .getLastRun(dataset)
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

          this.setOverlaysToMap();

          // add default layer
          // let tm2m: L.Layer = this.layersControl["overlays"][
          //   this.DEFAULT_PRODUCT_COSMO
          // ];
          // tm2m.addTo(this.map);
          this.dataset = runAvailable.dataset;

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
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        this.map.invalidateSize();
        this.spinner.hide();
      });
  }

  private getMMProducts() {
    console.log("loading multi-model ensemble products");
    let reftime: Date = this.runAvailable
      ? moment(this.runAvailable.reftime.substr(0, 6), "YYYYMMDD").toDate()
      : new Date();
    let filterTM: ObsFilter = {
      product: MultiModelProduct.TM,
      // reftime: new Date(2020, 10, 26),
      reftime: reftime,
      network: "multim-forecast",
      timerange: "254,97200,0",
    };
    let filterRH: ObsFilter = {
      product: MultiModelProduct.RH,
      // reftime: new Date(2020, 10, 26),
      reftime: reftime,
      network: "multim-forecast",
      timerange: "254,97200,0",
    };
    let productTM = this.obsService.getData(filterTM);
    let productRH = this.obsService.getData(filterRH);
    forkJoin([productTM, productRH]).subscribe(
      (results) => {
        this.mmProductsData[0] = results[0].data;
        this.mmProductsData[1] = results[1].data;
        // this.loadMarkers(this.mmProductsData[idx], this.mmProduct);
        this.loadMarkers();
        if (
          this.mmProductsData[0].length === 0 &&
          this.mmProductsData[1].length === 0
        ) {
          this.notify.showWarning("No Multi-Model data found.");
        }
      },
      (error) => {
        this.notify.showError(error);
      }
    );
  }

  private setOverlaysToMap() {
    let baseUrl = `${TILES_PATH}/${this.run}-${this.dataset}`;
    if (environment.production) {
      baseUrl += this.runAvailable.area;
    }
    let bounds =
      this.dataset === "lm5"
        ? L.latLngBounds(LM5_BOUNDS["southWest"], LM5_BOUNDS["northEast"])
        : L.latLngBounds(LM2_BOUNDS["southWest"], LM2_BOUNDS["northEast"]);
    let maxZoom = this.dataset === "lm5" ? 7 : 8;

    if (this.dataset === "iff") {
      this.layersControl["overlays"] = {
        // let overlays = {
        [TPPERC1]: L.timeDimension.layer.tileLayer.portus(
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
        [TPPERC10]: L.timeDimension.layer.tileLayer.portus(
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
        [TPPERC25]: L.timeDimension.layer.tileLayer.portus(
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
        [TPPERC50]: L.timeDimension.layer.tileLayer.portus(
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
        [TPPERC75]: L.timeDimension.layer.tileLayer.portus(
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
        [TPPERC99]: L.timeDimension.layer.tileLayer.portus(
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
        [TPPROB5]: L.timeDimension.layer.tileLayer.portus(
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
        [TPPROB10]: L.timeDimension.layer.tileLayer.portus(
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
        [TPPROB20]: L.timeDimension.layer.tileLayer.portus(
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
        [TPPROB50]: L.timeDimension.layer.tileLayer.portus(
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
        [TM2]: L.timeDimension.layer.tileLayer.portus(
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
        [PREC3P]: L.timeDimension.layer.tileLayer.portus(
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
        [PREC6P]: L.timeDimension.layer.tileLayer.portus(
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
        [SF3]: L.timeDimension.layer.tileLayer.portus(
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
        [SF6]: L.timeDimension.layer.tileLayer.portus(
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
        [RH]: L.timeDimension.layer.tileLayer.portus(
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
        [HCC]: L.timeDimension.layer.tileLayer.portus(
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
        [MCC]: L.timeDimension.layer.tileLayer.portus(
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
        [LCC]: L.timeDimension.layer.tileLayer.portus(
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
      [TM2]: this.createLegendControl("tm2"),
      [PREC3P]: this.createLegendControl("prec3tp"),
      [PREC6P]: this.createLegendControl("prec6tp"),
      [SF3]: this.createLegendControl("sf3"),
      [RH]: this.createLegendControl("rh"),
      [HCC]: this.createLegendControl("hcc"),
      [MCC]: this.createLegendControl("mcc"),
      [LCC]: this.createLegendControl("lcc"),
      [TPPERC1]: this.createLegendControl("tpperc"),
      [TPPERC10]: this.createLegendControl("tpperc"),
      [TPPERC25]: this.createLegendControl("tpperc"),
      [TPPERC75]: this.createLegendControl("tpperc"),
      [TPPERC50]: this.createLegendControl("tpperc"),
      [TPPERC99]: this.createLegendControl("tpperc"),
      [TPPROB5]: this.createLegendControl("tpprob"),
      [TPPROB20]: this.createLegendControl("tpprob"),
      [TPPROB10]: this.createLegendControl("tpprob"),
      [TPPROB50]: this.createLegendControl("tpprob"),
    };

    let legends = this.legends;
    map.on("overlayadd", function (event) {
      console.log(event["name"]);
      if (event["name"] === TM2) {
        legends[TM2].addTo(map);
      } else if (event["name"] === PREC3P) {
        legends[PREC3P].addTo(this);
      } else if (event["name"] === PREC6P) {
        legends[PREC6P].addTo(this);
      } else if (event["name"] === SF3 || event["name"] === SF6) {
        legends[SF3].addTo(this);
      } else if (event["name"] === RH) {
        legends[RH].addTo(this);
      } else if (event["name"] === HCC) {
        legends[HCC].addTo(this);
      } else if (event["name"] === MCC) {
        legends[MCC].addTo(this);
      } else if (event["name"] === LCC) {
        legends[LCC].addTo(this);
      } else if (
        event["name"] === TPPERC1 ||
        event["name"] === TPPERC10 ||
        event["name"] === TPPERC25 ||
        event["name"] === TPPERC50 ||
        event["name"] === TPPERC75 ||
        event["name"] === TPPERC99
      ) {
        legends[TPPERC1].addTo(this);
      } else if (
        event["name"] === TPPROB5 ||
        event["name"] === TPPROB10 ||
        event["name"] === TPPROB20 ||
        event["name"] === TPPROB50
      ) {
        legends[TPPROB5].addTo(this);
      }
    });

    map.on("overlayremove", function (event) {
      if (event["name"] === TM2) {
        this.removeControl(legends[TM2]);
      } else if (event["name"] === PREC3P) {
        this.removeControl(legends[PREC3P]);
      } else if (event["name"] === PREC6P) {
        this.removeControl(legends[PREC6P]);
      } else if (event["name"] === SF3 && !map.hasLayer(layers[SF6])) {
        this.removeControl(legends[SF3]);
      } else if (event["name"] === SF6 && !map.hasLayer(layers[SF3])) {
        this.removeControl(legends[SF3]);
      } else if (event["name"] === RH) {
        this.removeControl(legends[RH]);
      } else if (event["name"] === HCC) {
        this.removeControl(legends[HCC]);
      } else if (event["name"] === MCC) {
        this.removeControl(legends[MCC]);
      } else if (event["name"] === LCC) {
        this.removeControl(legends[LCC]);
      } else if (
        event["name"] === TPPERC1 &&
        !map.hasLayer(layers[TPPERC10]) &&
        !map.hasLayer(layers[TPPERC25]) &&
        !map.hasLayer(layers[TPPERC50]) &&
        !map.hasLayer(layers[TPPERC75]) &&
        !map.hasLayer(layers[TPPERC99])
      ) {
        this.removeControl(legends[TPPERC1]);
      } else if (
        event["name"] === TPPERC10 &&
        !map.hasLayer(layers[TPPERC1]) &&
        !map.hasLayer(layers[TPPERC25]) &&
        !map.hasLayer(layers[TPPERC50]) &&
        !map.hasLayer(layers[TPPERC75]) &&
        !map.hasLayer(layers[TPPERC99])
      ) {
        this.removeControl(legends[TPPERC1]);
      } else if (
        event["name"] === TPPERC25 &&
        !map.hasLayer(layers[TPPERC1]) &&
        !map.hasLayer(layers[TPPERC10]) &&
        !map.hasLayer(layers[TPPERC50]) &&
        !map.hasLayer(layers[TPPERC75]) &&
        !map.hasLayer(layers[TPPERC99])
      ) {
        this.removeControl(legends[TPPERC50]);
      } else if (
        event["name"] === TPPERC50 &&
        !map.hasLayer(layers[TPPERC1]) &&
        !map.hasLayer(layers[TPPERC10]) &&
        !map.hasLayer(layers[TPPERC25]) &&
        !map.hasLayer(layers[TPPERC75]) &&
        !map.hasLayer(layers[TPPERC99])
      ) {
        this.removeControl(legends[TPPERC75]);
      } else if (
        event["name"] === TPPERC75 &&
        !map.hasLayer(layers[TPPERC1]) &&
        !map.hasLayer(layers[TPPERC10]) &&
        !map.hasLayer(layers[TPPERC25]) &&
        !map.hasLayer(layers[TPPERC50]) &&
        !map.hasLayer(layers[TPPERC99])
      ) {
        this.removeControl(legends[TPPERC99]);
      } else if (
        event["name"] === TPPERC99 &&
        !map.hasLayer(layers[TPPERC1]) &&
        !map.hasLayer(layers[TPPERC10]) &&
        !map.hasLayer(layers[TPPERC25]) &&
        !map.hasLayer(layers[TPPERC50]) &&
        !map.hasLayer(layers[TPPERC75])
      ) {
        this.removeControl(legends[TPPERC1]);
      } else if (
        event["name"] === TPPROB5 &&
        !map.hasLayer(layers[TPPROB10]) &&
        !map.hasLayer(layers[TPPROB20]) &&
        !map.hasLayer(layers[TPPROB50])
      ) {
        this.removeControl(legends[TPPROB5]);
      } else if (
        event["name"] === TPPROB10 &&
        !map.hasLayer(layers[TPPROB5]) &&
        !map.hasLayer(layers[TPPROB20]) &&
        !map.hasLayer(layers[TPPROB50])
      ) {
        this.removeControl(legends[TPPROB5]);
      } else if (
        event["name"] === TPPROB20 &&
        !map.hasLayer(layers[TPPROB5]) &&
        !map.hasLayer(layers[TPPROB10]) &&
        !map.hasLayer(layers[TPPROB50])
      ) {
        this.removeControl(legends[TPPROB5]);
      } else if (
        event["name"] === TPPROB50 &&
        !map.hasLayer(layers[TPPROB5]) &&
        !map.hasLayer(layers[TPPROB10]) &&
        !map.hasLayer(layers[TPPROB20])
      ) {
        this.removeControl(legends[TPPROB5]);
      }
    });

    // add default legend to the map
    if (this.dataset === "iff") {
      this.legends[TPPERC1].addTo(map);
    } else {
      this.legends[TM2].addTo(map);
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

    this.loadRunAvailable(newDs);

    this.dataset = newDs;
    if (this.dataset === "lm5") {
      this.map.setView(MAP_CENTER, 5);
    } else if (this.dataset === "lm2.2") {
      this.map.setView(MAP_CENTER, 6);
    } else if (this.dataset === "iff") {
      this.map.setView(MAP_CENTER, 6);
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

  private loadMarkers() {
    this.allMarkers = [];
    let obsData: ObsData;
    const idx = this.mmProduct === MultiModelProduct.TM ? 0 : 1;
    const unit: string =
      this.mmProduct === MultiModelProduct.TM ? "<i>°</i>" : "";
    let min: number, max: number;
    this.mmProductsData[idx].forEach((s) => {
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
    this.mmProductsData[idx].forEach((s) => {
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
}
