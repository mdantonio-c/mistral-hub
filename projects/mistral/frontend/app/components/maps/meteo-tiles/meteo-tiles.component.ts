import { Component, Injector, Input, OnInit } from "@angular/core";
import { environment } from "@rapydo/../environments/environment";
import { forkJoin, interval } from "rxjs";
import { catchError, filter, scan, takeUntil } from "rxjs/operators";
import * as moment from "moment";
import * as L from "leaflet";
import * as chroma from "chroma-js";
import "leaflet-timedimension/dist/leaflet.timedimension.src.js";
import { GeoTIFF } from "geotiff";
import "ih-leaflet-canvaslayer-field/dist/leaflet.canvaslayer.field.js";
import "@app/../assets/js/leaflet.timedimension.tilelayer.portus.js";
import { TilesService } from "./services/tiles.service";
import { ObsService } from "../observation-maps/services/obs.service";
import { NavigationEnd, Params } from "@angular/router";

import {
  LEGEND_DATA,
  LegendConfig,
  VARIABLES_CONFIG,
  VARIABLES_CONFIG_BASE,
} from "./services/data";
import {
  CodeDescPair,
  ObsData,
  Observation,
  ObsFilter,
  RunAvailable,
} from "../../../types";
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
  let ScalarField: any;
}

const ICON_BOUNDS = {
  southWest: L.latLng(33.69, 2.9875),
  northEast: L.latLng(48.91, 22.0125),
};

const t2mColorStops = [
  { value: -30, color: "#64007f99" },
  { value: -28, color: "#78048d99" },
  { value: -26, color: "#87089899" },
  { value: -24, color: "#b414b999" },
  { value: -22, color: "#d41dd199" },
  { value: -20, color: "#f627eb99" },
  { value: -18, color: "#57007f99" },
  { value: -16, color: "#3e007f99" },
  { value: -14, color: "#00287f99" },
  { value: -12, color: "#003c7f99" },
  { value: -10, color: "#00467f99" },
  { value: -8, color: "#00528f99" },
  { value: -6, color: "#0062af99" },
  { value: -4, color: "#0082ef99" },
  { value: -2, color: "#259aff99" },
  { value: 0, color: "#5bb4ff99" },
  { value: 2, color: "#bbffe299" },
  { value: 4, color: "#9feec899" },
  { value: 6, color: "#87d3ab99" },
  { value: 8, color: "#62af8899" },
  { value: 10, color: "#07a12799" },
  { value: 12, color: "#21bb0e99" },
  { value: 14, color: "#52ca0b99" },
  { value: 16, color: "#9ce10699" },
  { value: 18, color: "#cef00399" },
  { value: 20, color: "#f3fb0199" },
  { value: 22, color: "#f4d90b99" },
  { value: 24, color: "#f4bd0b99" },
  { value: 26, color: "#f4880b99" },
  { value: 28, color: "#f46d0b99" },
  { value: 30, color: "#e8370999" },
  { value: 32, color: "#c41a0a99" },
  { value: 34, color: "#af0f1499" },
  { value: 36, color: "#7c000099" },
  { value: 38, color: "#64000099" },
  { value: 40, color: "#b4646499" },
  { value: 42, color: "#f0a0a099" },
  { value: 44, color: "#ffb4b499" },
  { value: 46, color: "#ffdcdc99" },
];
const tccColorStops = [
  { value: 50, color: "#ecefe9" },
  { value: 60, color: "#dde7dc" },
  { value: 70, color: "#cbded1" },
  { value: 80, color: "#b3d0c7" },
  { value: 90, color: "#9bc4c7" },
  { value: 100, color: "#82a1ba" },
];

const prsColorStops = [
  { value: 98800, color: "#235a95" },
  { value: 99200, color: "#2e6fb8" },
  { value: 99600, color: "#548ece" },
  { value: 100000, color: "#79aade" },
  { value: 100400, color: "#9cc1e7" },
  { value: 100800, color: "#bdd5ef" },
  { value: 101200, color: "#deeaf7" },
  { value: 101600, color: "#F8E8E8" },
  { value: 102000, color: "#ffdcdc" },
  { value: 102400, color: "#ffb4b4" },
  { value: 102800, color: "#f0a0a0" },
  { value: 103200, color: "#ee5a5c" },
  { value: 103600, color: "#da4c4d" },
  { value: 104000, color: "#CB2A2A" },
  { value: 104400, color: "#981F1F" },
  { value: 104800, color: "#661515" },
];
const prp_1_3_ColorStops = [
  { value: 0, color: "#deeaf700" },
  { value: 1, color: "#deeaf7" },
  { value: 2, color: "#bdd5ef" },
  { value: 4, color: "#9cc1e7" },
  { value: 6, color: "#79aade" },
  { value: 8, color: "#548ece" },
  { value: 10, color: "#2e6fb8" },
  { value: 15, color: "#235a95" },
  { value: 20, color: "#173a62" },
  { value: 25, color: "#f7ec31" },
  { value: 30, color: "#e1d52d" },
  { value: 40, color: "#e86411" },
  { value: 50, color: "#e22208" },
  { value: 75, color: "#961405" },
  { value: 100, color: "#6e0e04" },
];
const prp_6_12_24_ColorStops = [
  { value: 0, color: "#deeaf700" },
  { value: 1, color: "#deeaf7" },
  { value: 2, color: "#bdd5ef" },
  { value: 5, color: "#9cc1e7" },
  { value: 10, color: "#79aade" },
  { value: 15, color: "#548ece" },
  { value: 20, color: "#2e6fb8" },
  { value: 25, color: "#235a95" },
  { value: 30, color: "#173a62" },
  { value: 40, color: "#f7ec31" },
  { value: 50, color: "#e1d52d" },
  { value: 75, color: "#e86411" },
  { value: 100, color: "#e22208" },
  { value: 150, color: "#961405" },
  { value: 200, color: "#6e0e04" },
];
const sf_1_3_ColorStops = [
  { value: 0, color: "#90619200" },
  { value: 0.5, color: "#906192" },
  { value: 1, color: "#b67bb9" },
  { value: 2, color: "#b68cbb" },
  { value: 5, color: "#dbc5dd" },
  { value: 10, color: "#e7d8e8" },
  { value: 15, color: "#feedff" },
  { value: 20, color: "#cdcdcd" },
  { value: 25, color: "#dadada" },
  { value: 30, color: "#f2f2f2" },
  { value: 50, color: "#ffffff" },
];
const sf_6_12_24_ColorStops = [
  { value: 0, color: "#90619200" },
  { value: 1, color: "#906192" },
  { value: 2, color: "#b67bb9" },
  { value: 5, color: "#b68cbb" },
  { value: 10, color: "#dbc5dd" },
  { value: 15, color: "#e7d8e8" },
  { value: 20, color: "#feedff" },
  { value: 30, color: "#cdcdcd" },
  { value: 50, color: "#dadada" },
  { value: 75, color: "#f2f2f2" },
  { value: 100, color: "#ffffff" },
];
const hccColorStops = [
  { value: 50, color: "#fafdf900" },
  { value: 60, color: "#ecf7ea" },
  { value: 70, color: "#d6eed4" },
  { value: 80, color: "#c4e6c0" },
  { value: 90, color: "#b0deab" },
  { value: 100, color: "#9dd797" },
];
const mccColorStops = [
  { value: 50, color: "#fafafd00" },
  { value: 60, color: "#ececf7" },
  { value: 70, color: "#d8d7ee" },
  { value: 80, color: "#c4c5e6" },
  { value: 90, color: "#b0b2dd" },
  { value: 100, color: "#9fa1d5" },
];
const lccColorStops = [
  { value: 50, color: "#fffafa00" },
  { value: 60, color: "#fdebeb" },
  { value: 70, color: "#fbd5d6" },
  { value: 80, color: "#f9c1c2" },
  { value: 90, color: "#f6abad" },
  { value: 100, color: "#f49799" },
];

const rhColorStops = [
  { value: 0, color: "#ff000099" },
  { value: 20, color: "#ff8c0099" },
  { value: 40, color: "#ffff0099" },
  { value: 60, color: "#00ff0099" },
  { value: 80, color: "#00ffff99" },
  { value: 100, color: "#0000ff99" },
];
const ws10mColorStops = [
  { value: 1, color: "#8bd8f999" },
  { value: 2, color: "#7070ff99" },
  { value: 5, color: "#4bcf4f99" },
  { value: 10, color: "#ffff0099" },
  { value: 20, color: "#fec60199" },
  { value: 30, color: "#ff333399" },
  { value: 50, color: "#ee82ee99" },
  { value: 70, color: "#ff00c399" },
];

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
    timeDimension: true,
    timeDimensionControl: true,
    maxBounds: this.bounds,
    maxBoundsViscosity: 1.0,
    timeDimensionControlOptions: {
      autoPlay: false,
      timeZones: ["utc"],
      loopButton: true,
      timeSteps: 1,
      playReverseButton: true,
      limitSliders: true,
      playerOptions: {
        buffer: 0,
        transitionTime: 1000,
        loop: true,
      },
      speedSlider: true,
    },
  };
  public runAvailable: RunAvailable;

  private currentIdx: number = null;
  private timeLoading: boolean = false;
  public onlyWind: boolean = false;

  constructor(
    injector: Injector,
    private tilesService: TilesService,
    private obsService: ObsService,
  ) {
    super(injector);
    // set the initial set of displayed layers
    this.options["layers"] = [this.LAYER_LIGHTMATTER];
    this.dataset = this.DEFAULT_DATASET;
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
    // please do not erase this line, it is useful to import GeoTIFF variable and read geotif files
    if (false) console.log(GeoTIFF);
    // please do not erase this line, it is useful to import GeoTIFF variable and read geotif files
    this.variablesConfig = VARIABLES_CONFIG;
    this.route.queryParams.subscribe((params: Params) => {
      const view: string = params["view"];
      const lang: string = params["lang"];
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
    this.addIconBorderLayer();
    this.initLegends(this.map);
    this.centerMap();
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
          (map as any).timeDimension.getAvailableTimes()[0],
        );
        const current = moment.utc((map as any).timeDimension.getCurrentTime());
        const now = moment.utc();
        const nowDay = now.date();
        const currentDay = current.date();
        const currentHourFormat = current.format("HH");
        if (currentDay === nowDay) {
          comp.tmpStringHourCode = "00" + currentHourFormat + "0000";
          console.log(comp.tmpStringHourCode);
        }
        if (currentDay > nowDay) {
          if (currentDay - nowDay === 1) {
            comp.tmpStringHourCode = "01" + currentHourFormat + "0000";
            console.log(comp.tmpStringHourCode);
          }
          if (currentDay - nowDay === 2) {
            comp.tmpStringHourCode = "02" + currentHourFormat + "0000";
            console.log(comp.tmpStringHourCode);
          }
          if (currentDay - nowDay === 3) {
            comp.tmpStringHourCode = "03" + currentHourFormat + "0000";
            console.log(comp.tmpStringHourCode);
          }
        }
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(
            comp.layersControl["overlays"]["Wind speed at 10 meters"],
          )
        ) {
          comp
            .addWindLayer(
              comp.minZoom,
              comp.dataset,
              comp.tmpStringHourCode,
              comp.onlyWind,
            )
            .then((l) => {
              comp.map.removeLayer(
                comp.layersControl["overlays"]["Wind speed at 10 meters"],
              );
              l.addTo(comp.map);
              comp.layersControl["overlays"]["Wind speed at 10 meters"] = l;
              if (comp.onlyWind) {
                comp.legends[DP.WIND10M].addTo(comp.map);
              } else {
                comp.map.removeControl(comp.legends[DP.WIND10M]);
              }
            });
        }
        // temperature
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.TM2])
        ) {
          comp
            .addScalarField(
              comp.minZoom,
              comp.dataset,
              "t2m-t2m",
              "t2m",
              t2mColorStops,
              comp.tmpStringHourCode,
            )
            .then((l) => {
              comp.map.removeLayer(comp.layersControl["overlays"][DP.TM2]);
              l.addTo(comp.map);
              comp.layersControl["overlays"][DP.TM2] = l;
            });
        }
        // total cloud
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.TCC])
        ) {
          comp
            .addScalarField(
              comp.minZoom,
              comp.dataset,
              "cloud-tcc",
              "tcc",
              tccColorStops,
              comp.tmpStringHourCode,
            )
            .then((l) => {
              comp.map.removeLayer(comp.layersControl["overlays"][DP.TCC]);
              l.addTo(comp.map);
              comp.layersControl["overlays"][DP.TCC] = l;
            });
        }

        // rh
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.RH])
        ) {
          comp
            .addScalarField(
              comp.minZoom,
              comp.dataset,
              "humidity-r",
              "r",
              rhColorStops,
              comp.tmpStringHourCode,
            )
            .then((l) => {
              comp.map.removeLayer(comp.layersControl["overlays"][DP.RH]);
              l.addTo(comp.map);
              comp.layersControl["overlays"][DP.RH] = l;
            });
        }

        // prec 1
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.PREC1P])
        ) {
          console.log("prec1");
          const stringHourToExclude = comp.stringHourToExclude(1);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "prec1-tp",
                "tp",
                prp_1_3_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(comp.layersControl["overlays"][DP.PREC1P]);
                comp.layersControl["overlays"][DP.PREC1P] = l;
                l.addTo(comp.map);
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.PREC1P]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.PREC1P] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // prec 3
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.PREC3P])
        ) {
          const stringHourToExclude = comp.stringHourToExclude(3);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "prec3-tp",
                "tp",
                prp_1_3_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(comp.layersControl["overlays"][DP.PREC3P]);
                l.addTo(comp.map);
                comp.layersControl["overlays"][DP.PREC3P] = l;
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.PREC3P]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.PREC3P] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // prec 6
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.PREC6P])
        ) {
          const stringHourToExclude = comp.stringHourToExclude(6);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "prec6-tp",
                "tp",
                prp_6_12_24_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(comp.layersControl["overlays"][DP.PREC6P]);
                l.addTo(comp.map);
                comp.layersControl["overlays"][DP.PREC6P] = l;
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.PREC6P]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.PREC6P] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // prec 12
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.PREC12P])
        ) {
          const stringHourToExclude = comp.stringHourToExclude(12);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "prec12-tp",
                "tp",
                prp_6_12_24_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(
                  comp.layersControl["overlays"][DP.PREC12P],
                );
                l.addTo(comp.map);
                comp.layersControl["overlays"][DP.PREC12P] = l;
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.PREC12P]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.PREC12P] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // prec 24
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.PREC24P])
        ) {
          const stringHourToExclude = comp.stringHourToExclude(24);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "prec24-tp",
                "tp",
                prp_6_12_24_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(
                  comp.layersControl["overlays"][DP.PREC24P],
                );
                l.addTo(comp.map);
                comp.layersControl["overlays"][DP.PREC24P] = l;
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.PREC24P]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.PREC24P] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // snow 1
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.SF1])
        ) {
          const stringHourToExclude = comp.stringHourToExclude(1);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "snow1-snow",
                "snow",
                sf_1_3_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(comp.layersControl["overlays"][DP.SF1]);
                l.addTo(comp.map);
                comp.layersControl["overlays"][DP.SF1] = l;
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.SF1]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.SF1] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // snow 3
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.SF3])
        ) {
          const stringHourToExclude = comp.stringHourToExclude(3);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "snow3-snow",
                "snow",
                sf_1_3_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(comp.layersControl["overlays"][DP.SF3]);
                l.addTo(comp.map);
                comp.layersControl["overlays"][DP.SF3] = l;
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.SF3]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.SF3] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // snow 6
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.SF6])
        ) {
          const stringHourToExclude = comp.stringHourToExclude(6);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "snow6-snow",
                "snow",
                sf_6_12_24_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(comp.layersControl["overlays"][DP.SF6]);
                l.addTo(comp.map);
                comp.layersControl["overlays"][DP.SF6] = l;
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.SF6]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.SF6] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // snow 12
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.SF12])
        ) {
          const stringHourToExclude = comp.stringHourToExclude(12);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "snow12-snow",
                "snow",
                sf_6_12_24_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(comp.layersControl["overlays"][DP.SF12]);
                l.addTo(comp.map);
                comp.layersControl["overlays"][DP.SF12] = l;
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.SF12]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.SF12] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // snow 24
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.SF24])
        ) {
          const stringHourToExclude = comp.stringHourToExclude(24);
          if (!stringHourToExclude.includes(comp.tmpStringHourCode)) {
            comp
              .addScalarField(
                comp.minZoom,
                comp.dataset,
                "snow24-snow",
                "snow",
                sf_6_12_24_ColorStops,
                comp.tmpStringHourCode,
              )
              .then((l) => {
                comp.map.removeLayer(comp.layersControl["overlays"][DP.SF24]);
                l.addTo(comp.map);
                comp.layersControl["overlays"][DP.SF24] = l;
              });
          } else {
            comp.map.removeLayer(comp.layersControl["overlays"][DP.SF24]);
            const emptyLayer = L.canvas();
            comp.layersControl["overlays"][DP.SF24] = emptyLayer;
            emptyLayer.addTo(comp.map);
          }
        }
        // low cloud
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.LCC])
        ) {
          comp
            .addScalarField(
              comp.minZoom,
              comp.dataset,
              "cloud_hml-lcc",
              "lcc",
              lccColorStops,
              comp.tmpStringHourCode,
            )
            .then((l) => {
              comp.map.removeLayer(comp.layersControl["overlays"][DP.LCC]);
              l.addTo(comp.map);
              comp.layersControl["overlays"][DP.LCC] = l;
            });
        }
        // medium cc
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.MCC])
        ) {
          comp
            .addScalarField(
              comp.minZoom,
              comp.dataset,
              "cloud_hml-mcc",
              "mcc",
              mccColorStops,
              comp.tmpStringHourCode,
            )
            .then((l) => {
              comp.map.removeLayer(comp.layersControl["overlays"][DP.MCC]);
              l.addTo(comp.map);
              comp.layersControl["overlays"][DP.MCC] = l;
            });
        }
        // high cc
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.HCC])
        ) {
          comp
            .addScalarField(
              comp.minZoom,
              comp.dataset,
              "cloud_hml-hcc",
              "hcc",
              hccColorStops,
              comp.tmpStringHourCode,
            )
            .then((l) => {
              comp.map.removeLayer(comp.layersControl["overlays"][DP.HCC]);
              l.addTo(comp.map);
              comp.layersControl["overlays"][DP.HCC] = l;
            });
        }

        // pressure
        if (
          comp.layersControl["overlays"] &&
          comp.map.hasLayer(comp.layersControl["overlays"][DP.PMSL])
        ) {
          console.log("pressure");
          comp
            .addScalarField(
              comp.minZoom,
              comp.dataset,
              "pressure-pmsl",
              "pmsl",
              prsColorStops,
              comp.tmpStringHourCode,
            )
            .then((l) => {
              comp.map.removeLayer(comp.layersControl["overlays"][DP.PMSL]);
              l.addTo(comp.map);
              comp.layersControl["overlays"][DP.PMSL] = l;
              comp.legends[DP.PMSL].addTo(comp.map);
            });
          /*comp.addPressureField(comp.dataset, "pressure-pmsl", "pmsl", comp.tmpStringHourCode).then((l) => {
                        comp.map.removeLayer(comp.layersControl["overlays"][DP.PMSL]);
                        //l.addTo(comp.map);
                        //comp.layersControl["overlays"][DP.PMSL] = l;
                        fetch("./app/custom/assets/images/icon/geoJson/isobare.geojson").then(
                        response => response.json()
                    ).then(data => {
                        L.geoJSON(data,{
                            onEachFeature: function (feature,layer){
                                if (feature.properties && feature.properties.label){
/!*                                    layer.bindTooltip(feature.properties.label, {
                                        permanent: true,
                                        direction: 'center',
                                        className : 'isobar-label',
                                        opacity: 1
                                    })*!/
                                }
                            }
                        }).addTo(comp.map);
                    })
                    })*/
        }
      },
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
          console.log(runAvailable);
          //console.log(`Last Available Run [${dataset}]`, runAvailable);
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
          this.setOverlaysToMap();

          this.dataset = runAvailable.dataset;

          // add default layer
          const current = moment.utc(
            (this.map as any).timeDimension.getCurrentTime(),
          );
          const nowDay = now.date();
          const currentDay = current.date();
          const currentHourFormat = current.format("HH");
          let tmpStringHourCode: string;
          if (currentDay === nowDay) {
            tmpStringHourCode = "00" + currentHourFormat + "0000";
          }
          if (currentDay > nowDay) {
            if (currentDay - nowDay === 1) {
              tmpStringHourCode = "01" + currentHourFormat + "0000";
            }
            if (currentDay - nowDay === 2) {
              tmpStringHourCode = "02" + currentHourFormat + "0000";
            }
            if (currentDay - nowDay === 3) {
              tmpStringHourCode = "03" + currentHourFormat + "0000";
            }
          }
          // add default layer and legend, activate t2m span button
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "t2m-t2m",
            "t2m",
            t2mColorStops,
            tmpStringHourCode,
          ).then((l) => {
            this.layersControl["overlays"][DP.TM2] = l;
            l.addTo(this.map);
          });
          this.legends[DP.TM2].addTo(this.map);
          let element = document.querySelectorAll("span.t2m");
          if (element) {
            element[0].classList.add("attivo");
          }
        },
        (error) => {
          this.notify.showError(error);
        },
      )
      .add(() => {
        this.map.invalidateSize();
        this.spinner.hide();
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

  createCustomColorScale(colorStops) {
    const domainValues = colorStops.map((stop) => stop.value);
    const colors = colorStops.map((stop) => stop.color);
    // discrete color scale
    return chroma.scale(colors).domain(domainValues).classes(domainValues);
    // continue color scale
    //return chroma.scale(colors).domain(domainValues);
  }

  async addScalarField(
    minZoom: number,
    dataset: string,
    folderName: string,
    componentName: string,
    colorStop,
    hour: string = "",
  ) {
    let resLayer: L.Layer;
    let pane;
    let now = new Date().getUTCHours().toString();
    if (now.length === 1) now = "0" + now;
    let s: string = "00" + now + "0000";
    if (hour) s = hour;
    const customColorScale = this.createCustomColorScale(colorStop);
    //const ResponseUrl = `./app/custom/assets/images/icon/${folderName}/${componentName}_comp_` + s + ".asc"
    const ResponseUrl =
      `./app/custom/assets/images/icon/${folderName}/${componentName}_comp_` +
      s +
      ".tif";
    const Response = await fetch(ResponseUrl);
    //const variable = await Response.text();
    const variable = await Response.arrayBuffer();
    //const sf = L.ScalarField.fromASCIIGrid(variable);
    const sf = L.ScalarField.fromGeoTIFF(variable);
    const magnitude = L.canvasLayer.scalarField(sf, {
      color: customColorScale,
      opacity: 0.6,
    });
    if (folderName == "cloud_hml-lcc") pane = "low";
    if (folderName == "cloud_hml-mcc") pane = "medium";
    if (folderName == "cloud_hml-hcc") pane = "high";
    if (
      folderName == "cloud_hml-lcc" ||
      folderName == "cloud_hml-mcc" ||
      folderName == "cloud_hml-hcc"
    ) {
      magnitude.options.pane = pane;
    }

    return magnitude;
  }

  addIconBorderLayer() {
    fetch(
      "./app/custom/assets/images/icon/geoJson/coastlines_border_lines.geojson",
    )
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

  stringHourToExclude(targetHour: number) {
    if (targetHour < 0 || targetHour > 24) {
      return "Error: target hour must be between 0 and 24.";
    }
    const strings = [];
    for (let i = 0; i < targetHour; i++) {
      strings.push("00" + i.toString().padStart(2, "0") + "0000");
    }
    return strings;
  }

  async addWindLayer(
    minZoom: number,
    dataset: string,
    hour = "",
    onlyWind = false,
  ) {
    if (!dataset || (dataset != "lm5" && dataset != "lm2.2")) {
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
    try {
      let uResponseUrl, vResponseUrl;

      //uResponseUrl = "./app/custom/assets/images/icon/wind-10u/10u_comp_" + s + ".asc"
      //vResponseUrl = "./app/custom/assets/images/icon/wind-10v/10v_comp_" + s + ".asc"
      uResponseUrl =
        "./app/custom/assets/images/icon/wind-10u/10u_comp_" + s + ".tif";
      vResponseUrl =
        "./app/custom/assets/images/icon/wind-10v/10v_comp_" + s + ".tif";
      const uResponse = await fetch(uResponseUrl);
      const vResponse = await fetch(vResponseUrl);
      // const u = await uResponse.text();
      // const v = await vResponse.text();
      const u = await uResponse.arrayBuffer();
      const v = await vResponse.arrayBuffer();

      //console.log(uResponseUrl, vResponseUrl);
      let n = (window.innerHeight * window.innerWidth) / 2073600;
      //const vf = L.VectorField.fromASCIIGrids(u, v);
      const vf = L.VectorField.fromGeoTIFFs(u, v);
      const sf = vf.getScalarField("magnitude");

      const customColorScale = this.createCustomColorScale(ws10mColorStops);
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
      return resLayer;
    } catch (error) {
      console.error("Error while loading data:", error);
    }
  }

  updateCumulatedFields(field) {
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

  updateScalarWind(newValue: boolean) {
    this.onlyWind = newValue;
    if (
      this.layersControl["overlays"] &&
      this.map.hasLayer(
        this.layersControl["overlays"]["Wind speed at 10 meters"],
      )
    ) {
      this.addWindLayer(
        this.minZoom,
        this.dataset,
        this.tmpStringHourCode,
        this.onlyWind,
      ).then((l) => {
        this.map.removeLayer(
          this.layersControl["overlays"]["Wind speed at 10 meters"],
        );
        l.addTo(this.map);
        this.layersControl["overlays"]["Wind speed at 10 meters"] = l;
        if (this.onlyWind) {
          this.legends[DP.WIND10M].addTo(this.map);
        } else {
          this.map.removeControl(this.legends[DP.WIND10M]);
        }
      });
    }
  }

  private setOverlaysToMap() {
    let now = new Date().getUTCHours().toString();
    if (now.length === 1) now = "0" + now;
    const s = "00" + now + "0000";

    let bounds = L.latLngBounds(
      ICON_BOUNDS["southWest"],
      ICON_BOUNDS["northEast"],
    );

    this.layersControl["overlays"] = {};
    // Temperature at 2 meters
    if ("t2m" in this.variablesConfig) {
      this.addScalarField(
        this.minZoom,
        this.dataset,
        "t2m-t2m",
        "t2m",
        t2mColorStops,
      ).then((l: L.Layer) => {
        this.layersControl["overlays"][DP.TM2] = l;
      });
    }
    // Pressure at mean sea level
    if ("prs" in this.variablesConfig) {
      /*         this.addPressureField(this.dataset,"pressure-pmsl","pmsl").then((l)=>{
                         //this.layersControl["overlays"][DP.PMSL] =l;
                         this.layersControl["overlays"][DP.PMSL]= fetch("./app/custom/assets/images/icon/geoJson/isobare.geojson").then(
                             response => response.json()
                         ).then(data => {
                             L.geoJSON(data,{
                                 onEachFeature: function (feature,layer){
                                     if (feature.properties && feature.properties.label){
                   /!*                      layer.bindTooltip(feature.properties.label, {
                                             permanent: true,
                                             direction: 'center',
                                             className : 'isobar-label'
                                         })*!/
                                     }
                                 }
                             }).addTo(this.map);
                         })
                     })*/
      this.addScalarField(
        this.minZoom,
        this.dataset,
        "pressure-pmsl",
        "pmsl",
        prsColorStops,
      ).then((l) => {
        this.layersControl["overlays"][DP.PMSL] = l;
      });
    }
    // Wind speed at 10 meters
    if ("ws10m" in this.variablesConfig) {
      this.addWindLayer(this.minZoom, this.dataset).then((l) => {
        this.layersControl["overlays"][DP.WIND10M] = l;
      });
    }
    // Relative humidity Time Layer
    if ("rh" in this.variablesConfig) {
      this.addScalarField(
        this.minZoom,
        this.dataset,
        "humidity-r",
        "r",
        rhColorStops,
      ).then((l) => {
        this.layersControl["overlays"][DP.RH] = l;
      });
    }
    ////////////////////////////////////
    /////////// PRECIPITATION //////////
    ////////////////////////////////////
    if ("prp" in this.variablesConfig) {
      if (
        this.variablesConfig["prp"].length &&
        this.variablesConfig["prp"].includes(1)
      ) {
        const stringHoursToExlude = this.stringHourToExclude(1);
        if (!stringHoursToExlude.includes(s)) {
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "prec1-tp",
            "tp",
            prp_1_3_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.PREC1P] = l;
          });
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
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "prec3-tp",
            "tp",
            prp_1_3_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.PREC3P] = l;
          });
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
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "prec6-tp",
            "tp",
            prp_6_12_24_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.PREC6P] = l;
          });
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
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "prec12-tp",
            "tp",
            prp_6_12_24_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.PREC12P] = l;
          });
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
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "prec24-tp",
            "tp",
            prp_6_12_24_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.PREC24P] = l;
          });
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
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "snow1-snow",
            "snow",
            sf_1_3_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.SF1] = l;
          });
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
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "snow3-snow",
            "snow",
            sf_1_3_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.SF3] = l;
          });
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
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "snow6-snow",
            "snow",
            sf_6_12_24_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.SF6] = l;
          });
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
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "snow12-snow",
            "snow",
            sf_6_12_24_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.SF12] = l;
          });
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
          this.addScalarField(
            this.minZoom,
            this.dataset,
            "snow24-snow",
            "snow",
            sf_6_12_24_ColorStops,
          ).then((l) => {
            this.layersControl["overlays"][DP.SF24] = l;
          });
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
        this.addScalarField(
          this.minZoom,
          this.dataset,
          "cloud_hml-lcc",
          "lcc",
          lccColorStops,
        ).then((l) => {
          this.layersControl["overlays"][DP.LCC] = l;
        });
      }
      if (
        this.variablesConfig["cc"].length &&
        this.variablesConfig["cc"].includes("medium")
      ) {
        this.addScalarField(
          this.minZoom,
          this.dataset,
          "cloud_hml-mcc",
          "mcc",
          mccColorStops,
        ).then((l) => {
          this.layersControl["overlays"][DP.MCC] = l;
        });
      }
      if (
        this.variablesConfig["cc"].length &&
        this.variablesConfig["cc"].includes("high")
      ) {
        this.addScalarField(
          this.minZoom,
          this.dataset,
          "cloud_hml-hcc",
          "hcc",
          hccColorStops,
        ).then((l) => {
          this.layersControl["overlays"][DP.HCC] = l;
        });
      }

      this.addScalarField(
        this.minZoom,
        this.dataset,
        "cloud-tcc",
        "tcc",
        tccColorStops,
      ).then((l) => {
        this.layersControl["overlays"][DP.TCC] = l;
      });
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
      div.style.clear = "unset";
      div.innerHTML += `<img class="legenda" src="/app/custom/assets/images/${id}.svg">`;
      return div;
    };

    return legend;
  }

  private initLegends(map: L.Map) {
    let layers = this.layersControl["overlays"];
    this.legends = {
      [DP.TM2]: this.createLegendControl("tm2"),
      [DP.PMSL]: this.createLegendControl("pmsl_1"),
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

    map.on("overlayadd", function (event) {
      currentActiveLayers.push(event["name"]);
      if (event["name"] === DP.TM2) {
        legends[DP.TM2].addTo(map);
      } else if (event["name"] === DP.PMSL) {
        legends[DP.PMSL].addTo(map);
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
      const mapCenter = L.latLng(41.3, 12.5);
      switch (this.dataset) {
        case "lm5":
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
    let layer: L.Layer = obj.layer as L.Layer;
    let numbLayers = [];
    if (this.map.hasLayer(layer)) {
      console.log(`remove layer: ${obj.name}`);
      this.map.fire("overlayremove", obj);
      this.map.removeLayer(layer);
      /*
            // useful to manage new wind layer
            for (const key of Object.keys(this.layersControl["overlays"])) {
                if (this.map.hasLayer(this.layersControl["overlays"][key]))
                    numbLayers.push(key);
            }
            if (
                numbLayers.length === 1 &&
                numbLayers[0] === "Wind speed at 10 meters"
            ) {
                this.addWindLayer(
                    this.minZoom,
                    this.dataset,
                    this.tmpStringHourCode,
                    true,
                ).then((l) => {
                    this.map.removeLayer(
                        this.layersControl["overlays"]["Wind speed at 10 meters"],
                    );
                    l.addTo(this.map);
                    this.layersControl["overlays"]["Wind speed at 10 meters"] = l;
                    this.legends[DP.WIND10M].addTo(this.map);
                });
            }*/
    } else {
      console.log(`add layer : ${obj.name}`);
      this.map.fire("overlayadd", obj);
      // useful to manage new wind layer
      //console.log(this.layersControl["overlays"]["Wind speed at 10 meters"]);
      if (this.layersControl["overlays"]["Wind speed at 10 meters"]) {
        if (this.layersControl["overlays"]["Wind speed at 10 meters"]._layers) {
          const windLayerToRemove = Object.keys(
            this.layersControl["overlays"]["Wind speed at 10 meters"]._layers,
          )[0];
          this.map.removeLayer(
            this.layersControl["overlays"]["Wind speed at 10 meters"]._layers[
              windLayerToRemove
            ],
          );
          this.map.removeControl(this.legends[DP.WIND10M]);
        }
      }
      if (obj.name === "Wind speed at 10 meters") {
        /*       for (const key of Object.keys(this.layersControl["overlays"])) {
                           if (this.map.hasLayer(this.layersControl["overlays"][key]))
                               numbLayers.push(key);
                       }*/
        /*       if (numbLayers.length === 0) {
                           this.addWindLayer(
                               this.minZoom,
                               this.dataset,
                               this.tmpStringHourCode,
                               true,
                           ).then((l) => {
                               l.addTo(this.map);
                               this.layersControl["overlays"]["Wind speed at 10 meters"] = l;
                               this.legends[DP.WIND10M].addTo(this.map);
                           });
                       } */
        this.addWindLayer(
          this.minZoom,
          this.dataset,
          this.tmpStringHourCode,
          this.onlyWind,
        ).then((l) => {
          l.addTo(this.map);
          this.layersControl["overlays"]["Wind speed at 10 meters"] = l;
          if (this.onlyWind) this.legends[DP.WIND10M].addTo(this.map);
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
