import {
  Component,
  OnInit,
  Input,
  Injector,
  ChangeDetectorRef,
} from "@angular/core";
import * as L from "leaflet";
import "leaflet-timedimension/dist/leaflet.timedimension.src.js";
import "@app/../assets/js/leaflet.timedimension.tilelayer.portus.js";
import * as moment from "moment";
import {
  CARTODB_LICENSE_HREF,
  MISTRAL_LICENSE_HREF,
  STADIA_LICENSE_HREF,
  OSM_LICENSE_HREF,
  ViewModes,
} from "../meteo-tiles/meteo-tiles.config";
import { COLOR_RANGES } from "./data";
import { BaseMapComponent } from "../base-map.component";
import { Params } from "@angular/router";
import {
  VARIABLES_CONFIG_OBS,
  LEGEND_DATA,
  LegendConfig,
  NETWORKS,
  sharedSideNav,
} from "../meteo-tiles/services/data";
import {
  ObsFilter,
  ObservationResponse,
  ObsData,
  Observation,
  ObsValue,
  Station,
} from "@app/types";
import { ObsService } from "../observation-maps/services/obs.service";
import { ObsStationReportComponent } from "../observation-maps/obs-station-report/obs-station-report.component";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: "app-aim-observation-maps",
  templateUrl: "./aim-observation-maps.component.html",
  styleUrls: ["./aim-observation-maps.component.scss"],
})
export class AimObservationMapsComponent
  extends BaseMapComponent
  implements OnInit
{
  readonly LEGEND_POSITION = "bottomleft";
  @Input() minZoom: number = 5;
  @Input() maxZoom: number = 12;
  lastResponse = null; // to track last response from the server
  bounds = new L.LatLngBounds(new L.LatLng(30, -20), new L.LatLng(55, 50));
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
  LAYER_STADIA_SMOOTH = L.tileLayer(
    "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png",
    {
      id: "stadia.alidade.smooth",
      attribution: `&copy; ${STADIA_LICENSE_HREF} | &copy; ${MISTRAL_LICENSE_HREF}`,
      maxZoom: this.maxZoom,
      minZoom: this.minZoom,
    },
  );
  layersControl = {
    baseLayers: {
      "Openstreet Map": this.LAYER_OSM,
      "Carto Map Light": this.LAYER_LIGHTMATTER,
      "Stadia Alidade Smooth": this.LAYER_STADIA_SMOOTH,
    },
  };
  options = {
    layers: [this.LAYER_LIGHTMATTER],
    zoomControl: false,
    zoom: 6,
    center: L.latLng(41.88, 12.28),
    zoomSnap: 0.1,
    maxBoundsViscosity: 1.0,
    maxBounds: this.bounds,
    timeDimension: true,
    timeDimensionOptions: {
      timeInterval: this.timeIntervalTimeLine(),
      period: "PT60M", // ISO8601 duration, step of 60 min
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
    },
  };
  viewMode = ViewModes.adv;

  private markers: L.Marker[] = [];
  private allMarkers: L.Marker[] = [];
  private markersGroup: L.LayerGroup;
  private legends: { [key: string]: L.Control } = {};
  private currentProduct: string;
  private now: number; // to track time when layer changes
  private myNow: Date; // now date for timeline
  private myRefTime: Date; // to allow when changing layer to set to previous selected time
  private myTime: number[]; // to allow when changing layer to set to previous selected hour
  private refTimeToTimeLine: Date | null = null; // to track time selected on the timebar
  private playControl: boolean = false; // to deactivate spinner when animation starts
  private fromDate: Date;
  private filter: ObsFilter;
  private windConvert = false;
  private intervalId: any;
  private timeDimensionControl: any;
  private ITAversion = false;
  private visibilityHandler: () => void;

  selectedNetwork = "";
  timelineReferenceDate: string = "";
  qualityContolFilter = false;
  sharedSideNav = sharedSideNav;
  constructor(
    injector: Injector,
    private obsService: ObsService,
    private modalService: NgbModal,
    private cdr: ChangeDetectorRef,
  ) {
    super(injector);
  }

  ngOnInit() {
    super.ngOnInit();
    this.variablesConfig = VARIABLES_CONFIG_OBS;
    this.route.queryParams.subscribe((params: Params) => {
      const lang: string = params["lang"];
      const view: string = params["view"];
      if (["it", "en"].includes(lang)) {
        this.lang = lang;
      }
      if (this.lang === "it") {
        // TODO
        this.ITAversion = true;
      }
      if (Object.values(ViewModes).includes(view)) {
        this.viewMode = ViewModes[view];
      }
    });
    setTimeout(() => {
      this.intervalId = setInterval(
        () => {
          const availableTimes = (
            this.map as any
          ).timeDimension.getAvailableTimes();
          const currentTime = (this.map as any).timeDimension.getCurrentTime();
          if (availableTimes[availableTimes.length - 1] === currentTime) {
            this.toggleLayer();
          }
        },
        10 * 60 * 1000,
      );
    }, 0);

    this.visibilityHandler = () => {
      if (!document.hidden) {
        this.toggleLayer();
        this.updateTimelineRange();
      }
    };
    document.addEventListener("visibilitychange", this.visibilityHandler);
  }
  ngOnDestroy() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    if (this.visibilityHandler) {
      document.removeEventListener("visibilitychange", this.visibilityHandler);
    }
  }

  onMapReady(map: L.Map) {
    this.map = map;
    setTimeout(() => this.map.setView([41.88, 12.28], 5.8), 0);
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
      autoPlay: false,
      playButton: false,
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
    });
    this.map.addControl(this.timeDimensionControl);
    let tControl = this.timeDimensionControl;
    let beforeOneHour: Date = new Date();
    beforeOneHour.setUTCHours(beforeOneHour.getUTCHours());
    beforeOneHour.setUTCMinutes(0);
    beforeOneHour.setUTCSeconds(0);
    beforeOneHour.setUTCMilliseconds(0);
    this.myNow = beforeOneHour;
    //console.log(`Date: ${Date()} UTC date: ${moment.utc(new Date().getTime())}`)
    //console.log(`Date: ${Date()} UTC date: ${moment.utc(new Date().getTime())}`)
    // default product: temperature
    const defaultProduct: string = "t2m";
    // add default layer and filter
    const filter: ObsFilter = {
      reftime: beforeOneHour,
      license: "CCBY_COMPLIANT",
      time: [beforeOneHour.getUTCHours() - 1, beforeOneHour.getUTCHours()],
      onlyStations: false,
      reliabilityCheck: true,
      last: true,
      product: VARIABLES_CONFIG_OBS[defaultProduct].code,
      timerange: VARIABLES_CONFIG_OBS[defaultProduct].timerange,
      level: VARIABLES_CONFIG_OBS[defaultProduct].level,
    };
    this.filter = filter;
    this.spinner.show();
    this.loadObservations(filter, true);

    (map as any).timeDimension.setCurrentTime(beforeOneHour);
    this.centerMap();
    //this.timelineReferenceDate = this.printTimeLineReferenceDate();

    /* catch event timeloloadObad on the timebar, a timeload event is any injection of time in the timebar */
    (map as any).timeDimension.on("timeload", () => {
      //fire the action if the timeload event is fired by the
      if (!tControl._player.isPlaying()) this.spinner.show();
      // in order to sync with load observation
      tControl._player.pause();
      let isMidNight: boolean = false;
      const selectedDateUTC = new Date(
        (map as any).timeDimension.getCurrentTime(),
      );

      this.refTimeToTimeLine = selectedDateUTC;
      let startDate = new Date(selectedDateUTC);
      startDate.setHours(selectedDateUTC.getHours() - 1);
      /* For data that refer to the previous day */
      if (startDate.getUTCDate() != selectedDateUTC.getUTCDate()) {
        isMidNight = true;
      }
      const filter: ObsFilter = {
        reftime: !isMidNight ? selectedDateUTC : startDate,
        time: [
          startDate.getUTCHours(),
          isMidNight
            ? selectedDateUTC.getUTCHours()
            : startDate.getUTCHours() + 1,
        ],
        license: this.filter.license,
        onlyStations: false,
        reliabilityCheck: true,
        last: true,
        product: this.filter.product,
        timerange: this.filter.timerange,
        level: this.filter.level,
      };
      this.myRefTime = filter["reftime"];
      this.myTime = filter["time"];
      if (this.qualityContolFilter) filter["reliabilityCheck"] = true;
      if (this.selectedNetwork) filter["network"] = this.selectedNetwork;
      this.loadObservations(filter, true, isMidNight);
      this.timelineReferenceDate = this.printTimeLineReferenceDate();
      this.cdr.detectChanges();
    });

    this.legends = {
      t2m: this.createLegendControl("tm2"),
      prs: this.createLegendControl("pmsl"),
      ws10m: this.createLegendControl("ws10m"),
      rh: this.createLegendControl("rh"),
      prp: this.createLegendControl("prp"),
      snow: this.createLegendControl("snow"),
    };

    this.legends[defaultProduct].addTo(map);
    this.currentProduct = defaultProduct;
    // hourly update of the timeline
    this.startHourlyTimelineUpdater();
  }

  /*
   * Define time interval of timeline following ISO standard
   * dayToSubtract defines the start date
   */

  private timeIntervalTimeLine() {
    const dayToSubtract: number = 2;
    const now = new Date();
    now.setUTCMinutes(0, 0, 0);
    const nowIsoDate: string = now.toISOString();
    let behindDate = new Date(now);
    behindDate.setUTCDate(now.getUTCDate() - dayToSubtract);
    behindDate.setUTCHours(0, 0, 0, 0);
    this.fromDate = behindDate;
    const behindIsoDate: string = behindDate.toISOString();
    //console.log(behindIsoDate, nowIsoDate);
    return `${behindIsoDate}/${nowIsoDate}`;
  }

  private startHourlyTimelineUpdater() {
    // Calculates the delay until the next hour
    const now = new Date();
    const millisUntilNextHour =
      (60 - now.getUTCMinutes()) * 60 * 1000 -
      now.getUTCSeconds() * 1000 -
      now.getUTCMilliseconds();

    // First timeout until the hour
    setTimeout(() => {
      this.updateTimelineRange(); // First update at the turn of the hour

      // Then update every hour
      setInterval(
        () => {
          this.updateTimelineRange();
        },
        60 * 60 * 1000,
      );
    }, millisUntilNextHour);
  }
  private updateTimelineRange() {
    const dayToSubtract = 2;
    const now = new Date();
    now.setUTCMinutes(0, 0, 0);

    const nowIso = now.toISOString();

    const behindDate = new Date(now);
    behindDate.setUTCDate(now.getUTCDate() - dayToSubtract);
    behindDate.setUTCHours(0, 0, 0, 0);
    const behindIso = behindDate.toISOString();

    const timeSteps = [];
    const stepMillis = 60 * 60 * 1000;
    for (let t = behindDate.getTime(); t <= now.getTime(); t += stepMillis) {
      timeSteps.push(new Date(t).toISOString());
    }

    const td = (this.map as any).timeDimension;
    td.setAvailableTimes(timeSteps.join(","), "replace");

    // always go back to the last available time
    td.setCurrentTimeIndex(timeSteps.length - 1);
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
      div.innerHTML += `<img class="legenda" alt="legend" src="/app/custom/assets/images/legends/${id}.svg">`;

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
  loadObservations(filter: ObsFilter, update = false, midNight = null) {
    this.obsService
      .getData(filter, update, midNight)
      .subscribe(
        (response: ObservationResponse) => {
          /*console.log(
            `elapsed time for '${filter.product}' data retrieval: ${
              (new Date().getTime() - startTime) / 1000
            }s`,
          );*/
          // to avoid markers overlapping
          if (this.markersGroup) {
            this.map.removeLayer(this.markersGroup);
            this.markers = [];
            this.allMarkers = [];
          }
          let data = response.data;
          this.loadMarkers(data, filter.product);
          if (this.currentProduct === "ws10m") {
            if (this.windConvert) this.updateWindMarkers();
          }
          // in order to sync with the end of marker update
          this.timeDimensionControl._player.release();
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
  loadWindMarkersHandle(event) {
    if (this.currentProduct !== "ws10m") return;
    let oldWindConvert = this.windConvert;
    if (event) {
      this.windConvert = true;
      const legend = new L.Control({ position: this.LEGEND_POSITION });
      legend.onAdd = () => {
        let div = L.DomUtil.create("div");
        div.style.clear = "unset";
        div.innerHTML += `<img class="legenda" alt="legend" src="/app/custom/assets/images/legends/vkm.svg">`;
        return div;
      };
      this.map.removeControl(this.legends[this.currentProduct]);
      if (legend) {
        legend.addTo(this.map);
      }
      this.legends["ws10m"] = legend;
    }
    if (!event) {
      this.windConvert = false;
      this.map.removeControl(this.legends[this.currentProduct]);
      const legend = this.createLegendControl("ws10m");
      legend.addTo(this.map);
      this.legends["ws10m"] = legend;
    }
    this.updateWindMarkers(oldWindConvert);
  }

  handleQualityChange(event) {
    this.qualityContolFilter = !!event;
    console.log(this.qualityContolFilter);
  }

  loadNetwork(event) {
    if (event === "All") {
      this.selectedNetwork = "";
      this.filter.network = "";
      this.toggleLayer();
      return;
    }

    const selected = NETWORKS.find((n) => n.name === event);
    if (!selected) {
      console.error("Network not found for ", event);
      return;
    }
    const network = selected.network;

    this.filter.network = network;
    this.filter.reftime = this.filter.reftime ?? this.myRefTime;
    this.filter.time = this.filter.time ?? this.myTime;
    if (this.qualityContolFilter) this.filter.reliabilityCheck = true;
    this.loadObservations(this.filter, true);
    this.selectedNetwork = network;
  }

  updateWindMarkers(oldWindConvert?: boolean) {
    if (oldWindConvert !== undefined && oldWindConvert === this.windConvert) {
      return;
    }
    if (this.currentProduct !== "ws10m") {
      return;
    }
    this.allMarkers.forEach((m) => {
      const currentIcon = m.getIcon() as L.DivIcon;
      const html = currentIcon.options.html;
      const tmpDiv = document.createElement("div");
      (tmpDiv.innerHTML as any) = html;
      const span = tmpDiv.querySelector("span");
      let updatedValue: string | null = null;

      if (span) {
        if (this.windConvert) {
          updatedValue = (parseFloat(span.textContent) * 3.6).toFixed(1);
        } else {
          updatedValue = (parseFloat(span.textContent) * 0.28).toFixed(1);
        }
        span.textContent = updatedValue;
      }
      const updatedIcon = L.divIcon({
        ...currentIcon.options,
        html: tmpDiv.innerHTML,
      });
      m.setIcon(updatedIcon);

      // update the value in the marker tooltip
      const tooltipContent = m.getTooltip().getContent() as string;
      const parser = new DOMParser();
      const tooltipDOM = parser.parseFromString(tooltipContent, "text/html");
      const tooltipSpan = tooltipDOM.querySelector("span.badge");
      if (tooltipSpan) {
        tooltipSpan.textContent = updatedValue;
      }
      const updatedTooltipContent = tooltipDOM.body.innerHTML;
      m.getTooltip().setContent(updatedTooltipContent);
    });
  }

  getMarkersColor(value, variableName) {
    let color: string = "";
    let textColor: string = "#453822";
    for (const range of COLOR_RANGES[variableName]) {
      if (value >= range.min) {
        color = range.color;
        if (textColor) {
          textColor = range.textColor;
        }
        break;
      }
    }
    return [color, textColor];
  }

  private loadMarkers(data: Observation[], product: string) {
    this.allMarkers = [];
    let obsData: ObsData;
    let min: number, max: number;
    let lastTimeObsValues = [];
    // min and max needed before data marker creation
    data.forEach((s) => {
      // create a product list to manage cases with multiple products (wind use case)
      const productList: string[] = product
        .split(" or ")
        .map((item: string) => item.trim());
      obsData = s.prod.find((x) => x.var === productList[0]);
      if (!obsData) {
        //console.log(s.stat)
        return;
      }
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
        lastTimeObsValues.push(lastObs);
        let val = ObsService.showData(lastObs.val, productList[0]);
        // all values with one decimal digit, only for hr no decimal digit
        let numericVal = parseFloat(val);
        val = isNaN(numericVal) ? val : numericVal.toFixed(1);
        if (this.variablesConfig["rh"].code === productList[0]) {
          val = isNaN(numericVal) ? val : Math.round(numericVal).toString();
        }

        // console.log(lastObs.val, val, localMin, max);
        if (lastObs.val >= min && lastObs.val <= max) {
          let htmlIcon = "";
          let color: string = "";
          let textColor: string = "#453822";

          if (
            "snow" in this.variablesConfig &&
            this.variablesConfig["snow"].code === productList[0]
          ) {
            [color, textColor] = this.getMarkersColor(lastObs.val, "snow");
          }
          if (
            "t2m" in this.variablesConfig &&
            this.variablesConfig["t2m"].code === productList[0]
          ) {
            [color, textColor] = this.getMarkersColor(lastObs.val, "t2m");
          }
          if (
            "prp" in this.variablesConfig &&
            this.variablesConfig["prp"].code === productList[0]
          ) {
            [color, textColor] = this.getMarkersColor(lastObs.val, "prp");
          }
          if (
            "rh" in this.variablesConfig &&
            this.variablesConfig["rh"].code === productList[0]
          ) {
            [color, textColor] = this.getMarkersColor(lastObs.val, "rh");
          }
          if (
            "prs" in this.variablesConfig &&
            this.variablesConfig["prs"].code === product
          ) {
            color = "#7da4eb;";
          }
          htmlIcon =
            `<div class="mstObsIcon rounded" style="background-color: ${color};"><span style="color: ${textColor} !important;">${val}` +
            "</span></div>";
          //  for the wind we expect two variables configured in "code"
          if (
            "ws10m" in this.variablesConfig &&
            this.variablesConfig["ws10m"].code.includes(productList[0])
          ) {
            [color, textColor] = this.getMarkersColor(lastObs.val, "ws10m");
            // get the direction data
            // wind use case
            const secondObsData: ObsData = s.prod.find(
              (x) => x.var === productList[1],
            );
            // filter the data to get only reliable data
            let directionWindLastValue: string;
            if (secondObsData) {
              secondObsData.val = secondObsData.val.filter((v) => v.rel === 1);
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
            }
            if (directionWindLastValue) {
              const directionWindLastValueConvention =
                parseInt(directionWindLastValue) + 180;
              // icon with arrow for the wind direction
              htmlIcon =
                `<div class="mstObsIcon rounded" style="background-color: #fff;" ><span>${val}` +
                `</span>&nbsp<span style="color: ${color};"><i class="fa-solid fa-circle-arrow-up fa-rotate-by" style="--fa-rotate-angle: ${directionWindLastValueConvention.toString()}deg;"></i></span></div>`;
            } else {
              // icon with only wind speed
              htmlIcon = `<div class="mstObsIcon rounded" style="background-color:#fff;" ><span>${val}</span>&nbsp<span style="color: ${color};"><i class="fa-solid fa-circle></i></span></div>`;
            }
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
          const language = this.lang;
          m.bindTooltip(
            BaseMapComponent.buildTooltipTemplate(
              s.stat,
              localReferenceTime.toString(),
              val,
              language,
            ),
            {
              direction: "top",
              offset: [4, -2],
              opacity: 0.75,
              className: "leaflet-tooltip mst-obs-tooltip",
            },
          );
          m.on("click", this.openStationReport.bind(this, s.stat, m));
          this.allMarkers.push(m);
        }
      }
    });
    // console.log(`Total markers: ${this.allMarkers.length}`);

    // set visualized time coming from last observation
    lastTimeObsValues.sort((a, b) => {
      return new Date(b.ref).getTime() - new Date(a.ref).getTime();
    });
    let lastTimeValue = lastTimeObsValues[0].ref + "Z";
    const availableTimes = (this.map as any).timeDimension.getAvailableTimes();
    const currentTime = (this.map as any).timeDimension.getCurrentTime();
    if (availableTimes[availableTimes.length - 1] === currentTime) {
      this.timelineReferenceDate =
        this.printTimeLineLastReferenceDate(lastTimeValue);
    } else {
      this.timelineReferenceDate = this.printTimeLineReferenceDate();
    }
    // reduce overlapping
    this.markers = this.reduceOverlapping(this.allMarkers);
    this.markersGroup = L.layerGroup(this.markers, { pane: product });

    this.layersControl["overlays"] = this.markersGroup;
    this.markersGroup.addTo(this.map);
  }
  checkUTCShift(): string {
    const now = moment();
    const offsetHours = now.utcOffset() / 60;
    const sign = offsetHours >= 0 ? "+" : "-";
    return `(UTC${sign}${Math.abs(offsetHours)})`;
  }
  private openStationReport(station: Station, m: L.Marker | null = null) {
    const modalRef = this.modalService.open(ObsStationReportComponent, {
      size: "xl",
      centered: true,
    });
    if (m instanceof L.Marker) {
      const tooltip = m.getTooltip();
      // forces the tooltip to not reopen after the modal is closed
      modalRef.result.finally(() => {
        setTimeout(() => {
          m.bindTooltip(tooltip);
          m.closeTooltip();
        }, 0);
      });
    }
    // pass the requested language
    modalRef.componentInstance.lang = this.lang;
    // clear the timerange and level details in the visualization
    modalRef.componentInstance.extendedVisualization = false;
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
    // get the reftime to and reftime from
    const reftimeTo = new Date();
    let reftimeFrom: Date = this.fromDate;
    const timeZoneOffset = reftimeFrom.getTimezoneOffset();
    // refTimeFrom must represent local midnight
    reftimeFrom = new Date(reftimeFrom.getTime() + timeZoneOffset * 60 * 1000);
    // set reftime from one hour before the time selected on the timebar
    // if (this.refTimeToTimeLine) {
    //   this.refTimeToTimeLine.setHours(this.refTimeToTimeLine.getHours() - 1);
    //   reftimeFrom = this.refTimeToTimeLine;
    // } else {
    //   reftimeFrom = reftimeTo;
    //   reftimeFrom.setHours(reftimeFrom.getHours() - 2);
    // }
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

  toggleLayer(obj?: Record<string, string>) {
    if (!obj && !this.currentProduct) {
      this.notify.showError("No product selected");
      return;
    }

    // get fresh current time
    const currentUtcNow = new Date();
    currentUtcNow.setUTCMinutes(0, 0, 0);
    // flag useful to discern between automatic refresh/reload button/all-network and user choice
    let loadObs = false;
    // when reload button
    if (!obj) {
      obj = {
        name: this.currentProduct,
        layer: this.currentProduct,
      };
      // update the myNow variable with fresh time
      this.myNow = currentUtcNow;
      loadObs = true;
    }
    // console.log(`toggle layer: ${obj.name}`);
    // update the filter
    if (this.variablesConfig[obj.name]) {
      this.filter.product = this.variablesConfig[obj.name].code;
      this.filter.timerange = this.variablesConfig[obj.name].timerange;
      this.filter.level = this.variablesConfig[obj.name].level;

      // refresh the time filter with fresh date
      let isMidNight: boolean = false;
      let startDate = new Date(currentUtcNow);
      startDate.setHours(currentUtcNow.getHours() - 1);
      // For data that refer to the previous day
      if (startDate.getUTCDate() != currentUtcNow.getUTCDate()) {
        isMidNight = true;
      }
      let newReftime = !isMidNight ? currentUtcNow : startDate;
      let newTime = [
        startDate.getUTCHours(),
        isMidNight ? currentUtcNow.getUTCHours() : startDate.getUTCHours() + 1,
      ];
      this.filter.reftime = newReftime;
      this.filter.time = newTime;
      // update variables with fresh data
      this.myRefTime = newReftime;
      this.myTime = newTime;
      if (this.selectedNetwork) this.filter.network = this.selectedNetwork;
      if (this.qualityContolFilter) this.filter.reliabilityCheck = true;
      if (!loadObs) {
        this.loadObservations(this.filter, true, isMidNight);
      } else {
        (this.map as any).timeDimension.setCurrentTime(currentUtcNow);
      }
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
      if (VARIABLES_CONFIG_OBS[key].code.includes(this.filter.product)) {
        product = VARIABLES_CONFIG_OBS[key].label;
        break;
      }
    }
    return product || "n/a";
  }

  printDatasetDescription = (): string => {
    let product: string;
    for (let key in VARIABLES_CONFIG_OBS) {
      if (
        VARIABLES_CONFIG_OBS[key].code.includes(this.filter.product) &&
        VARIABLES_CONFIG_OBS[key].code != "B11002 or B11001"
      ) {
        product = VARIABLES_CONFIG_OBS[key].desc;
        if (VARIABLES_CONFIG_OBS[key].code === "B12101" && this.ITAversion)
          product = "(°C)";
        if (VARIABLES_CONFIG_OBS[key].code === "B10004" && this.ITAversion)
          product = "(hPa)";
        break;
      } else if (VARIABLES_CONFIG_OBS[key].code.includes(this.filter.product)) {
        product = !this.windConvert
          ? VARIABLES_CONFIG_OBS[key].desc
          : "speed and direction near surface (km/h)";
        break;
      }
    }
    return product || "";
  };
  printHoursDescription = (): string => {
    return "local time";
  };
  printReferenceDate(): string {
    const now: number = new Date().getTime();
    this.now = now;
    return `${moment
      .utc(new Date().getTime())
      .local()
      .format("DD-MM-YYYY, HH:mm")}`;
  }

  printTimeLineReferenceDate(): string {
    return `${moment
      .utc((this.map as any).timeDimension.getCurrentTime())
      .local()
      .format("DD-MM-YYYY, HH:mm")}`;
  }
  printTimeLineLastReferenceDate(timeStamp) {
    const lastTime = new Date(timeStamp);
    const day = lastTime.getDate().toString().padStart(2, "0");
    const month = (lastTime.getMonth() + 1).toString().padStart(2, "0");
    const year = lastTime.getFullYear();
    const hours = lastTime.getHours().toString().padStart(2, "0");
    const minutes = lastTime.getMinutes().toString().padStart(2, "0");
    return `${day}-${month}-${year}, ${hours}:${minutes}`;
  }
}
