import { Component } from "@angular/core";
import { environment } from "@rapydo/../environments/environment";
import * as moment from "moment";
import * as L from "leaflet";
import "leaflet-timedimension/dist/leaflet.timedimension.src.js";
import "leaflet-timedimension/examples/js/extras/leaflet.timedimension.tilelayer.portus.js";
import { TilesService } from "./services/tiles.service";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import { LegendConfig, LEGEND_DATA } from "./services/data";

declare module "leaflet" {
  var timeDimension: any;
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
  TP_PERC1 = "Precipitation percentiles 1%",
  TP_PERC10 = "Precipitation percentile 10%",
  TP_PERC25 = "Precipitation percentile 25%",
  TP_PERC50 = "Precipitation percentile 50%",
  TP_PERC75 = "Precipitation percentile 75%",
  TP_PERC99 = "Precipitation percentile 99%",
  TP_PROB5 = "Precipitation probability 1%",
  TP_PROB10 = "Precipitation probability 10%",
  TP_PROB20 = "Precipitation probability 20%",
  TP_PROB50 = "Precipitation probability 50%";

@Component({
  selector: "app-meteo-tiles",
  templateUrl: "./meteo-tiles.component.html",
  styleUrls: ["./meteo-tiles.component.css"],
})
export class MeteoTilesComponent {
  readonly DEFAULT_PRODUCT = "Temperature at 2 meters";
  readonly DEFAULT_RESOLUTION = "lm5";
  readonly LEGEND_POSITION = "bottomleft";

  map: L.Map;
  resolution: string;
  private refdate: string;
  private run: string;
  private legends: { [key: string]: L.Control } = {};

  LAYER_OSM = L.tileLayer("http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>',
    maxZoom: 8,
    minZoom: 5,
  });
  LAYER_MAPBOX_LIGHT = L.tileLayer(
    "https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw",
    {
      id: "mapbox.light",
      attribution:
        '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>',
      maxZoom: 8,
      minZoom: 5,
    }
  );
  LAYER_DARKMATTER = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png",
    {
      attribution:
        '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a> &copy; <a href="https://creativecommons.org/licenses/by-nd/4.0/legalcode">Work distributed under License CC BY-ND 4.0</a>',
      maxZoom: 8,
      minZoom: 5,
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
    zoom: 5,
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

  constructor(
    private tilesService: TilesService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {
    // set the initial set of displayed layers
    this.options["layers"] = [this.LAYER_MAPBOX_LIGHT];
    this.resolution = this.DEFAULT_RESOLUTION;
  }

  onMapReady(map: L.Map) {
    // console.log('Map ready', map);
    this.map = map;
    this.spinner.show();
    this.tilesService
      .getLastRun("lm5")
      .subscribe(
        (runAvailable) => {
          // runAvailable.reftime : 2020051100
          console.log("Available Run", runAvailable);
          let reftime = runAvailable.reftime;
          this.refdate = reftime.substr(0, 8);
          this.run = reftime.substr(8, 2);

          // set time
          let startTime = moment.utc(reftime, "YYYYMMDDHH").toDate();
          // let startTime = new Date(Date.UTC(2020, 4, 11));
          startTime.setUTCHours(0, 0, 0, 0);
          // let endTime = 'PT72H';
          let endTime = moment
            .utc(reftime, "YYYYMMDDHH")
            .add(3, "days")
            .toDate();
          console.log(endTime);

          // add time dimension
          let newAvailableTimes = (L as any).TimeDimension.Util.explodeTimeRange(
            startTime,
            endTime,
            "PT1H"
          );
          (map as any).timeDimension.setAvailableTimes(
            newAvailableTimes,
            "replace"
          );
          (map as any).timeDimension.setCurrentTime(startTime);

          this.setOverlaysToMap();

          // add default layer
          let tm2m: L.Layer = this.layersControl["overlays"][
            this.DEFAULT_PRODUCT
          ];
          tm2m.addTo(this.map);

          this.initLegends(map);
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        map.invalidateSize();
        this.spinner.hide();
      });
  }

  private setOverlaysToMap() {
    let baseUrl = `${TILES_PATH}/${this.run}-${this.resolution}`;
    if (environment.production) {
      baseUrl += this.resolution === "lm2.2" ? "/Italia" : "/Area_Mediterranea";
    }
    let bounds =
      this.resolution === "lm5"
        ? L.latLngBounds(LM5_BOUNDS["southWest"], LM5_BOUNDS["northEast"])
        : L.latLngBounds(LM2_BOUNDS["southWest"], LM2_BOUNDS["northEast"]);
    let maxZoom = this.resolution === "lm5" ? 7 : 8;
    this.layersControl["overlays"] = {
      // Temperature 2 meters Time Layer
      [TM2]: L.timeDimension.layer.tileLayer.portus(
        L.tileLayer(`${baseUrl}/t2m-t2m/${this.refdate}{h}/{z}/{x}/{y}.png`, {
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
        L.tileLayer(`${baseUrl}/prec3-tp/${this.refdate}{h}/{z}/{x}/{y}.png`, {
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
        L.tileLayer(`${baseUrl}/prec6-tp/${this.refdate}{h}/{z}/{x}/{y}.png`, {
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
        L.tileLayer(
          `${baseUrl}/snow3-snow/${this.refdate}{h}/{z}/{x}/{y}.png`,
          {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }
        ),
        {}
      ),
      // Snowfall 6h Time Layer
      [SF6]: L.timeDimension.layer.tileLayer.portus(
        L.tileLayer(
          `${baseUrl}/snow6-snow/${this.refdate}{h}/{z}/{x}/{y}.png`,
          {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.6,
            bounds: bounds,
          }
        ),
        {}
      ),
      // Relative humidity Time Layer
      [RH]: L.timeDimension.layer.tileLayer.portus(
        L.tileLayer(
          `${baseUrl}/humidity-r/${this.refdate}{h}/{z}/{x}/{y}.png`,
          {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            //opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }
        ),
        {}
      ),
      // High Cloud Time Layer
      [HCC]: L.timeDimension.layer.tileLayer.portus(
        L.tileLayer(
          `${baseUrl}/cloud_hml-hcc/${this.refdate}{h}/{z}/{x}/{y}.png`,
          {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            //opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }
        ),
        {}
      ),
      // Medium Cloud Time Layer
      [MCC]: L.timeDimension.layer.tileLayer.portus(
        L.tileLayer(
          `${baseUrl}/cloud_hml-mcc/${this.refdate}{h}/{z}/{x}/{y}.png`,
          {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            //opacity: 0.6,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }
        ),
        {}
      ),
      // Low Cloud Time Layer
      [LCC]: L.timeDimension.layer.tileLayer.portus(
        L.tileLayer(
          `${baseUrl}/cloud_hml-lcc/${this.refdate}{h}/{z}/{x}/{y}.png`,
          {
            minZoom: 5,
            maxZoom: maxZoom,
            tms: false,
            opacity: 0.9,
            // bounds: [[25.0, -25.0], [50.0, 47.0]],
            bounds: bounds,
          }
        ),
        {}
      ),
      //
[TP_PERC1]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/t2m-t2m/${this.refdate}{h}/{z}/{x}/{y}.png`,
    // `${baseUrl}/tp_percentile-1/${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),
[TP_PERC10]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/tp_percentile-10/${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),
[TP_PERC25]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/tp_percentile-25/${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),
[TP_PERC50]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/tp_percentile-50/${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),
[TP_PERC75]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/tp_percentile-75/${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),
[TP_PERC99]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/tp_percentile-99/${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),

[TP_PROB5]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/tp_probability-5/${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),
[TP_PROB10]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/tp_probability-10${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),
[TP_PROB20]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/tp_probability-20/${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),
[TP_PROB50]: L.timeDimension.layer.tileLayer.portus(
  L.tileLayer(
    `${baseUrl}/tp_probability-50/${this.refdate}{h}/{z}/{x}/{y}.png`,
    {
      minZoom: 5,
      maxZoom: maxZoom,
      tms: false,
      opacity: 0.9,
      // bounds: [[25.0, -25.0], [50.0, 47.0]],
      bounds: bounds,
    }
  ),
  {}
),
    };
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
      [TP_PERC1]: this.createLegendControl("tp_perc"),
      [TP_PERC10]: this.createLegendControl("tp_perc"),
      [TP_PERC25]: this.createLegendControl("tp_perc"),
      [TP_PERC75]: this.createLegendControl("tp_perc"),
      [TP_PERC50]: this.createLegendControl("tp_perc"),
      [TP_PERC99]: this.createLegendControl("tp_perc"),
      [TP_PROB5]: this.createLegendControl("tp_prob"),
      [TP_PROB20]: this.createLegendControl("tp_prob"),
      [TP_PROB10]: this.createLegendControl("tp_prob"),
      [TP_PROB50]: this.createLegendControl("tp_prob"),
    };
    let legends = this.legends;
    map.on("overlayadd", function (event) {
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
      } else if (event["name"] === TP_PERC1 || event["name"] === TP_PERC10 || event["name"] === TP_PERC25 || event["name"] === TP_PERC50 || event["name"] === TP_PERC75 || event["name"] === TP_PERC99)
      {
        legends[TP_PERC1].addTo(this);
      } else if (event["name"] === TP_PROB5 || event["name"] === TP_PROB10 || event["name"] === TP_PROB20 || event["name"] === TP_PROB50)
      {
        legends[TP_PROB5].addTo(this);
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
      } else if (event["name"] === TP_PERC1 && !map.hasLayer(layers[TP_PERC10]) && !map.hasLayer(layers[TP_PERC25])
      && !map.hasLayer(layers[TP_PERC50]) && !map.hasLayer(layers[TP_PERC75]) && !map.hasLayer(layers[TP_PERC99]))
      {
        this.removeControl(legends[TP_PERC1]);
      }
      else if (event["name"] === TP_PROB5 && !map.hasLayer(layers[TP_PROB10])
      && !map.hasLayer(layers[TP_PROB20]) && !map.hasLayer(layers[TP_PROB50]))
      {
        this.removeControl(legends[TP_PROB5]);
      }
    });
    // add default legend to the map
    this.legends[TM2].addTo(map);
  }

  changeRes() {
    let currentRes = this.resolution;
    if (this.resolution === "lm5") {
      this.resolution = "lm2.2";
      // this.map.setZoom(6);
      this.map.setView(MAP_CENTER, 6);
    } else {
      this.resolution = "lm5";
      // this.map.setZoom(5);
      this.map.setView(MAP_CENTER, 5);
    }
    // console.log(`Changed resolution from ${currentRes} to ${this.resolution}`);

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
  }
}
