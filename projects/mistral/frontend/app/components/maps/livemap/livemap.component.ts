import { Component, OnInit, Input } from "@angular/core";
import * as L from "leaflet";
import * as moment from "moment";
import {
  MISTRAL_LICENSE_HREF,
  OSM_LICENSE_HREF,
  ViewModes,
} from "../meteo-tiles/meteo-tiles.config";
import { BaseMapComponent } from "../base-map.component";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import { ActivatedRoute, NavigationEnd, Params, Router } from "@angular/router";
import {
  VARIABLES_CONFIG_OBS,
  LEGEND_DATA,
  LegendConfig,
} from "../meteo-tiles/services/data";
import {
  ObsFilter,
  ObservationResponse,
  ObsData,
  Observation,
  ObsValue,
  Station,
} from "../../../types";
import { ObsService } from "../observation-maps/services/obs.service";
import { ObsStationReportComponent } from "../observation-maps/obs-station-report/obs-station-report.component";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: "app-livemap",
  templateUrl: "./livemap.component.html",
  styleUrls: ["./livemap.component.scss"],
})
export class LivemapComponent extends BaseMapComponent implements OnInit {
  readonly LEGEND_POSITION = "bottomleft";
  @Input() minZoom: number = 5;
  @Input() maxZoom: number = 12;
  bounds = new L.LatLngBounds(new L.LatLng(30, -20), new L.LatLng(55, 50));
  LAYER_OSM = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution: `&copy; ${OSM_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
      maxZoom: this.maxZoom,
      minZoom: this.minZoom,
    },
  );
  layersControl = {
    baseLayers: {
      "Openstreet Map": this.LAYER_OSM,
    },
  };
  options = {
    layers: [this.LAYER_OSM],
    zoomControl: false,
    zoom: 6,
    center: L.latLng(41.88, 12.28),
    maxBoundsViscosity: 1.0,
    maxBounds: this.bounds,
  };
  viewMode = ViewModes.adv;

  private markers: L.Marker[] = [];
  private allMarkers: L.Marker[] = [];
  private markersGroup: L.LayerGroup;
  private legends: { [key: string]: L.Control } = {};
  private currentProduct: string;

  private filter: ObsFilter;

  constructor(
    public notify: NotificationService,
    public spinner: NgxSpinnerService,
    private obsService: ObsService,
    private router: Router,
    private route: ActivatedRoute,
    private modalService: NgbModal,
  ) {
    super(notify, spinner);
  }

  ngOnInit() {
    this.variablesConfig = VARIABLES_CONFIG_OBS;
    this.route.queryParams.subscribe((params: Params) => {
      const lang: string = params["lang"];
      if (["it", "en"].includes(lang)) {
        this.lang = lang;
      }
    });
  }

  onMapReady(map: L.Map) {
    this.map = map;
    this.map.attributionControl.setPrefix("");

    //console.log(`Date: ${Date()} UTC date: ${moment.utc(new Date().getTime())}`)
    // add default layer
    const filter: ObsFilter = {
      // common parameters
      reftime: moment.utc(new Date()).toDate(),
      license: "CCBY_COMPLIANT",
      time: [0, 23],
      onlyStations: false,
      reliabilityCheck: true,
      last: true,

      // temperature
      product: VARIABLES_CONFIG_OBS["t2m"].code,
      timerange: VARIABLES_CONFIG_OBS["t2m"].timerange,
      level: VARIABLES_CONFIG_OBS["t2m"].level,
    };
    this.filter = filter;
    this.loadObservations(filter, true);
    this.centerMap();

    this.legends = {
      t2m: this.createLegendControl("tm2"),
      prs: this.createLegendControl("pmsl"),
      ws10m: this.createLegendControl("ws10m"),
      rh: this.createLegendControl("rh"),
      prp: this.createLegendControl("prp"),
    };

    this.legends["t2m"].addTo(map);
    this.currentProduct = "t2m";
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
      let div = L.DomUtil.create("div");
      div.style.clear = "unset";
      div.innerHTML += `<img class="legenda" src="/app/custom/assets/images/${id}.svg">`;
      // for (let i = 0; i < config.labels.length; i++) {
      //   div.innerHTML +=
      //     '<i style="background:' +
      //     config.colors[i] +
      //     '"></i><span>' +
      //     config.labels[i] +
      //     "</span><br>";
      // }
      return div;
    };
    return legend;
  }

  onMapZoomEnd($event) {
    super.onMapZoomEnd($event);
    if (this.markersGroup) {
      this.map.removeLayer(this.markersGroup);
      this.markers = this.reduceOverlapping(this.allMarkers);
      this.markersGroup = L.layerGroup(this.markers);
      this.markersGroup.addTo(this.map);
    }
  }

  loadObservations(filter: ObsFilter, update = false) {
    const startTime = new Date().getTime();
    this.spinner.show();
    this.obsService
      .getData(filter, update)
      .subscribe(
        (response: ObservationResponse) => {
          console.log(
            `elapsed time for '${filter.product}' data retrieval: ${
              (new Date().getTime() - startTime) / 1000
            }s`,
          );
          let data = response.data;
          this.loadMarkers(data, filter.product);
          if (data.length === 0) {
            this.notify.showWarning("No observations found.");
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

  private loadMarkers(data: Observation[], product: string) {
    this.allMarkers = [];
    let obsData: ObsData;
    let min: number, max: number;
    // min and max needed before data marker creation
    data.forEach((s) => {
      // create a product list to manage cases with multiple products (wind use case)
      const productList: string[] = product
        .split(" or ")
        .map((item: string) => item.trim());
      obsData = s.prod.find((x) => x.var === productList[0]);
      let localMin = Math.min(
        ...obsData.val.filter((v) => v.rel === 1).map((v) => v.val),
      );
      if (!min || localMin < min) {
        min = localMin;
      }
      let localMax = Math.max(
        ...obsData.val.filter((v) => v.rel === 1).map((v) => v.val),
      );
      if (!max || localMax > max) {
        max = localMax;
      }
      // filter the data to get only reliable data
      obsData.val = obsData.val.filter((v) => v.rel === 1);
      if (obsData.val.length > 0) {
        const lastObs: ObsValue = obsData.val.pop();
        const val = ObsService.showData(lastObs.val, productList[0]);
        // console.log(lastObs.val, val, localMin, max);
        if (lastObs.val < max && lastObs.val > min) {
          let htmlIcon = "";
          let color: string = "";
          if (
            "t2m" in this.variablesConfig &&
            this.variablesConfig["t2m"].code.includes(productList[0])
          ) {
            if (lastObs.val >= 319.15) {
              color = "#ff9900";
            } else if (lastObs.val >= 317.15 && lastObs.val < 319.15) {
              color = "#ffcc00";
            } else if (lastObs.val >= 315.15 && lastObs.val < 317.15) {
              color = "#7200ff";
            } else if (lastObs.val >= 313.15 && lastObs.val < 315.15) {
              color = "#bf00ff";
            } else if (lastObs.val >= 311.15 && lastObs.val < 313.15) {
              color = "#ff00ff";
            } else if (lastObs.val >= 309.15 && lastObs.val < 311.15) {
              color = "#cc00cc";
            } else if (lastObs.val >= 307.15 && lastObs.val < 309.15) {
              color = "#990099";
            } else if (lastObs.val >= 305.15 && lastObs.val < 307.15) {
              color = "#660066";
            } else if (lastObs.val >= 303.15 && lastObs.val < 305.15) {
              color = "#660000";
            } else if (lastObs.val >= 301.15 && lastObs.val < 303.15) {
              color = "#990000";
            } else if (lastObs.val >= 299.15 && lastObs.val < 301.15) {
              color = "#cc0000";
            } else if (lastObs.val >= 297.15 && lastObs.val < 299.15) {
              color = "#ff0000";
            } else if (lastObs.val >= 295.15 && lastObs.val < 297.15) {
              color = "#ff6600";
            } else if (lastObs.val >= 293.15 && lastObs.val < 295.15) {
              color = "#ff9900";
            } else if (lastObs.val >= 291.15 && lastObs.val < 293.15) {
              color = "#ffcc00";
            } else if (lastObs.val >= 289.15 && lastObs.val < 291.16) {
              color = "#ffff00";
            } else if (lastObs.val >= 287.15 && lastObs.val < 289.15) {
              color = "#cce500";
            } else if (lastObs.val >= 285.15 && lastObs.val < 287.15) {
              color = "#7fcc00";
            } else if (lastObs.val >= 283.15 && lastObs.val < 285.15) {
              color = "#00b200";
            } else if (lastObs.val >= 281.15 && lastObs.val < 283.15) {
              color = "#00cc7f";
            } else if (lastObs.val >= 279.15 && lastObs.val < 281.15) {
              color = "#00e5cc";
            } else if (lastObs.val >= 277.15 && lastObs.val < 279.15) {
              color = "#00ffff";
            } else if (lastObs.val >= 275.15 && lastObs.val < 277.15) {
              color = "#00bfff";
            } else if (lastObs.val >= 273.15 && lastObs.val < 275.15) {
              color = "#008cff";
            } else if (lastObs.val >= 271.15 && lastObs.val < 273.15) {
              color = "#0059ff";
            } else if (lastObs.val >= 269.15 && lastObs.val < 271.15) {
              color = "#0000ff";
            } else if (lastObs.val >= 267.15 && lastObs.val < 269.15) {
              color = "#7200ff";
            } else if (lastObs.val >= 265.15 && lastObs.val < 267.15) {
              color = "#bf00ff";
            } else if (lastObs.val >= 263.15 && lastObs.val < 265.15) {
              color = "#ff00ff";
            } else if (lastObs.val >= 261.15 && lastObs.val < 263.15) {
              color = "#cc00cc";
            } else if (lastObs.val >= 259.15 && lastObs.val < 261.15) {
              color = "#990099";
            } else if (lastObs.val >= 257.15 && lastObs.val < 259.15) {
              color = "#660066";
            } else if (lastObs.val >= 255.15 && lastObs.val < 257.15) {
              color = "#660000";
            } else if (lastObs.val >= 253.15 && lastObs.val < 255.15) {
              color = "#990000";
            } else if (lastObs.val >= 251.15 && lastObs.val < 253.15) {
              color = "#cc0000";
            } else if (lastObs.val >= 249.15 && lastObs.val < 251.15) {
              color = "#ff0000";
            } else if (lastObs.val >= 247.15 && lastObs.val < 249.15) {
              color = "#ff6600";
            } else if (lastObs.val >= 245.15 && lastObs.val < 247.15) {
              color = "#ff9900";
            } else if (lastObs.val >= 243.15 && lastObs.val < 245.15) {
              color = "#ffcc00";
            }
          }
          if (
            "prp" in this.variablesConfig &&
            this.variablesConfig["prp"].code.includes(productList[0])
          ) {
            if (lastObs.val < max && lastObs.val > min) {
              if (lastObs.val >= 300) {
                color = "#4897D9";
              } else if (lastObs.val >= 200 && lastObs.val < 300) {
                color = "#A2A4D6";
              } else if (lastObs.val >= 100 && lastObs.val < 200) {
                color = "#B887C0";
              } else if (lastObs.val >= 75 && lastObs.val < 100) {
                color = "#D6A1CC";
              } else if (lastObs.val >= 50 && lastObs.val < 75) {
                color = "#E7BDDA";
              } else if (lastObs.val >= 40 && lastObs.val < 50) {
                color = "#E57D9A";
              } else if (lastObs.val >= 30 && lastObs.val < 40) {
                color = "#DA4C4D";
              } else if (lastObs.val >= 25 && lastObs.val < 30) {
                color = "#EE5A5C";
              } else if (lastObs.val >= 20 && lastObs.val < 25) {
                color = "#F6A15C";
              } else if (lastObs.val >= 15 && lastObs.val < 20) {
                color = "#FCD48E";
              } else if (lastObs.val >= 10 && lastObs.val < 15) {
                color = "#FFE073";
              } else if (lastObs.val >= 8 && lastObs.val < 10) {
                color = "#FDFD81";
              } else if (lastObs.val >= 6 && lastObs.val < 8) {
                color = "#FFFFC6";
              } else if (lastObs.val >= 5 && lastObs.val < 6) {
                color = "#F2F2A0";
              } else if (lastObs.val >= 4 && lastObs.val < 5) {
                color = "#D2EBA3";
              } else if (lastObs.val >= 3 && lastObs.val < 4) {
                color = "#C2E5D7";
              } else if (lastObs.val >= 2 && lastObs.val < 3) {
                color = "#C7E7EF";
              } else if (lastObs.val >= 0 && lastObs.val < 2) {
                color = "#CFEAF6";
              }
            }
          }
          if (
            "rh" in this.variablesConfig &&
            this.variablesConfig["rh"].code.includes(productList[0])
          ) {
            if (lastObs.val >= 110) {
              color = "#3F57B0";
            } else if (lastObs.val >= 100 && lastObs.val < 110) {
              color = "#6FC9DC";
            } else if (lastObs.val >= 90 && lastObs.val < 100) {
              color = "#0B7F3F";
            } else if (lastObs.val >= 80 && lastObs.val < 90) {
              color = "#FCFC1E";
            } else if (lastObs.val >= 70 && lastObs.val < 80) {
              color = "#F7A426";
            } else if (lastObs.val >= 60 && lastObs.val < 70) {
              color = "#EC2426";
            }
          }
          if (
            "prs" in this.variablesConfig &&
            this.variablesConfig["prs"].code === product
          ) {
            color = "#7da4eb;";
          }

          if (
            "ws10m" in this.variablesConfig &&
            this.variablesConfig["ws10m"].code.includes(productList[0])
          ) {
            if (lastObs.val >= 70) {
              color = "#9600FE";
            } else if (lastObs.val >= 50 && lastObs.val < 70) {
              color = "#EE82EE";
            } else if (lastObs.val >= 30 && lastObs.val < 50) {
              color = "#FF0000";
            } else if (lastObs.val >= 20 && lastObs.val < 30) {
              color = "#FFFF00";
            } else if (lastObs.val >= 10 && lastObs.val < 20) {
              color = "#FFA600";
            } else if (lastObs.val >= 5 && lastObs.val < 10) {
              color = "#0000FE";
            } else if (lastObs.val >= 2 && lastObs.val < 5) {
              color = "#54878C";
            } else if (lastObs.val >= 0 && lastObs.val < 2) {
              color = "#457D00";
            }
            // get the direction data
            // wind use case
            const secondObsData: ObsData = s.prod.find(
              (x) => x.var === productList[1],
            );
            // filter the data to get only reliable data
            secondObsData.val = secondObsData.val.filter((v) => v.rel === 1);
            let directionWindLastValue: string;
            if (secondObsData.val.length > 0) {
              const directionWindLastObs = secondObsData.val.pop();
              // check that the reference time is the same
              if (directionWindLastObs.ref == directionWindLastObs.ref) {
                directionWindLastValue = ObsService.showData(
                  directionWindLastObs.val,
                  productList[1],
                );
              }
            }
            if (directionWindLastValue) {
              // icon with arrow for the wind direction
              htmlIcon =
                `<div class="mstObsIcon rounded" style="background-color: #fff;" ><span>${val}` +
                `</span>&nbsp<span style="color: ${color};"><i class="fa-solid fa-circle-arrow-up fa-rotate-by" style="--fa-rotate-angle: ${directionWindLastValue}deg;"></i></span></div>`;
            } else {
              // icon ith only wind speed
              htmlIcon = `<div class="mstObsIcon rounded" style="background-color:#fff;" ><span>${val}</span>&nbsp<span style="color: ${color};"><i class="fa-solid fa-circle></i></span></div>`;
            }
          } else {
            htmlIcon =
              `<div class="mstObsIcon rounded" style="background-color: ${color};"><span>${val}` +
              "</span></div>";
          }
          let icon = L.divIcon({
            html: htmlIcon,
            iconSize: [24, 6],
            className: `mst-marker-icon
              mst-obs-marker-color-${color}`,
          });
          const m = new L.Marker([s.stat.lat, s.stat.lon], {
            icon: icon,
          });
          m.options["station"] = s.stat;
          m.options["data"] = obsData;
          const localReferenceTime = moment
            .utc(lastObs.ref, "YYYY-MM-DDTHH:mm")
            .toDate();
          m.bindTooltip(
            BaseMapComponent.buildTooltipTemplate(
              s.stat,
              localReferenceTime.toString(),
              val,
            ),
            {
              direction: "top",
              offset: [4, -2],
              opacity: 0.75,
              className: "leaflet-tooltip mst-obs-tooltip",
            },
          );
          m.on("click", this.openStationReport.bind(this, s.stat));
          this.allMarkers.push(m);
        }
      }
    });
    // console.log(`Total markers: ${this.allMarkers.length}`);

    // reduce overlapping
    this.markers = this.reduceOverlapping(this.allMarkers);
    this.markersGroup = L.layerGroup(this.markers, { pane: product });

    this.layersControl["overlays"] = this.markersGroup;
    this.markersGroup.addTo(this.map);
  }

  private openStationReport(station: Station) {
    const modalRef = this.modalService.open(ObsStationReportComponent, {
      size: "xl",
      centered: true,
    });
    modalRef.componentInstance.station = station;
    // get the query parameters for all the products
    let meteogramProducts: string[] = [];
    let meteogramLevels: string[] = [];
    let meteogramTimeranges: string[] = [];
    for (let key in this.variablesConfig) {
      meteogramProducts.push(this.variablesConfig[key]["code"]);
      meteogramLevels.push(this.variablesConfig[key]["level"]);
      meteogramTimeranges.push(this.variablesConfig[key]["timerange"]);
    }
    // delete duplicates
    meteogramLevels = meteogramLevels.filter(
      (value, index) => meteogramLevels.indexOf(value) === index,
    );
    meteogramTimeranges = meteogramTimeranges.filter(
      (value, index) => meteogramTimeranges.indexOf(value) === index,
    );
    //console.log(`all products : ${meteogramProducts}, all levels : ${meteogramLevels}, all tranges : ${meteogramTimeranges}`)
    // create the filter to get all the livemap products
    let meteogramsFilter: ObsFilter = Object.assign({}, this.filter);
    // delete "last" parameter
    meteogramsFilter.last = false;
    // add the param to insert the product in the query
    meteogramsFilter.allStationProducts = false;
    // update with the query parameters for all the products
    meteogramsFilter.product = meteogramProducts.join(" or ");
    meteogramsFilter.level = meteogramLevels.join(" or ");
    meteogramsFilter.timerange = meteogramTimeranges.join(" or ");
    /*    // TODO deccoment when the grafic of 24h meteogram is fixed
    // get the reftime to and reftime from
    const reftimeTo = moment.utc(new Date().getTime());
    const reftimeFrom = moment
      .utc(new Date().getTime())
      .subtract({ hours: 24 });*/

    const reftimeTo = new Date();
    // get reftime from according to local time
    let reftimeFrom = new Date();
    reftimeFrom.setHours(0);
    reftimeFrom.setMinutes(0);

    meteogramsFilter.dateInterval = [reftimeFrom, reftimeTo];
    //meteogramsFilter.time = [reftimeFrom.hour(),reftimeTo.hour()]
    meteogramsFilter.time = [
      reftimeFrom.getUTCHours(),
      reftimeTo.getUTCHours(),
    ];

    // get the data
    // use product list to cope with wind use case
    const productList: string[] = this.filter.product
      .split(" or ")
      .map((item: string) => item.trim());
    this.filter.product = productList[0];
    modalRef.componentInstance.selectedProduct = this.filter;
    modalRef.componentInstance.filter = meteogramsFilter;
    // get meteograms and label with local time
    modalRef.componentInstance.localTimeData = true;
    // need to trigger resize event
    window.dispatchEvent(new Event("resize"));
  }

  toggleLayer(obj: Record<string, string>) {
    console.log(`toggle layer: ${obj.name}`);

    // clean up layers
    if (this.markersGroup) {
      this.map.removeLayer(this.markersGroup);
      this.allMarkers = [];
      this.markers = [];
    }
    // update the filter
    if (this.variablesConfig[obj.name]) {
      this.filter.product = this.variablesConfig[obj.name].code;
      this.filter.timerange = this.variablesConfig[obj.name].timerange;
      this.filter.level = this.variablesConfig[obj.name].level;
      this.loadObservations(this.filter, true);
    }

    this.map.removeControl(this.legends[this.currentProduct]);
    if (this.legends[obj.name]) {
      //console.log(this.legends[obj.name]);
      this.legends[obj.name].addTo(this.map);
    }

    this.currentProduct = obj.name;
  }

  protected centerMap() {
    if (this.map) {
      const mapCenter = super.getMapCenter();
      this.map.setView(mapCenter, 6);
    }
  }

  printDatasetProduct(): string {
    let product: string;
    for (let key in VARIABLES_CONFIG_OBS) {
      if (this.filter.product.includes(VARIABLES_CONFIG_OBS[key].code)) {
        product = VARIABLES_CONFIG_OBS[key].label;
        break;
      }
    }
    return product || "n/a";
  }

  printDatasetDescription = (): string => {
    let product: string;
    for (let key in VARIABLES_CONFIG_OBS) {
      if (this.filter.product.includes(VARIABLES_CONFIG_OBS[key].code)) {
        product = VARIABLES_CONFIG_OBS[key].desc;
        break;
      }
    }
    return product || "";
  };

  printReferenceDate(): string {
    return `${moment
      .utc(new Date().getTime())
      .local()
      .format("MMM DD, HH:mm")}`;
  }

  reload(): void {
    this.loadObservations(this.filter, true);
  }
}
