import {
  Component,
  Output,
  EventEmitter,
  ViewEncapsulation,
} from "@angular/core";
import {
  ObsData,
  Observation,
  ObsFilter,
  SingleObsData,
  Station,
  ObservationResponse,
  StationDetail,
} from "@app/types";
import { ObsService } from "../services/obs.service";
import { ObsStationReportComponent } from "../obs-station-report/obs-station-report.component";
import { COLORS, obsData, VAR_TABLE } from "../services/data";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";

import * as L from "leaflet";
import "leaflet.markercluster";

@Component({
  selector: "app-obs-map",
  templateUrl: "./obs-map.component.html",
  styleUrls: ["./obs-map.component.css"],
  encapsulation: ViewEncapsulation.None,
})
export class ObsMapComponent {
  @Output() updateCount: EventEmitter<number> = new EventEmitter<number>();

  // base layer
  streetMaps = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      detectRetina: true,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> | ' +
        '&copy; <a href="/app/license#mistral-contributors" target="_blank" rel="noopener noreferrer">MISTRAL data contributor</a>',
    },
  );

  // Marker cluster stuff
  markerClusterGroup: L.MarkerClusterGroup;
  markerClusterData: L.Marker[] = [];
  markerClusterOptions: L.MarkerClusterGroupOptions;
  map: L.Map;
  legend = new L.Control({ position: "bottomright" });

  // Set the initial set of displayed layers
  options = {
    layers: [this.streetMaps],
    zoom: 5,
    center: [45.0, 12.0],
    preferCanvas: true,
  };

  private filter: ObsFilter;
  hourFrom: number;
  hourTo: number;
  // useful to set the standard view when loading the page
  resetView: boolean = false;

  constructor(
    private obsService: ObsService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private modalService: NgbModal,
  ) {
    // custom cluster options
    let usefuldata: number[] = new Array(8).fill(0);
    this.markerClusterOptions = {
      maxClusterRadius: 50,
      iconCreateFunction: function (cluster, srv = obsService) {
        const childCount = cluster.getChildCount();
        const childMarkers: L.Marker[] = cluster.getAllChildMarkers();
        let res: string = "" + childCount;
        let c = " marker-cluster-";
        let dirtyCluster = false;
        if (childCount < 10) {
          c += "small";
        } else if (childCount < 100) {
          c += "medium";
        } else {
          c += "large";
        }
        let type: string;
        if (childMarkers[0].options["data"]) {
          let mean = 0,
            medians: number[] = [],
            dirtyMedians: number[] = [];
          for (const m of childMarkers) {
            const singleObsData: SingleObsData = m.options["data"];
            if (!type) {
              type = singleObsData.var;
            }
            singleObsData.val.rel === 1
              ? medians.push(singleObsData.val.val)
              : dirtyMedians.push(singleObsData.val.val);
          }
          //console.log(medians)
          // get the median instead of the mean
          // let val = mean/childCount;
          let val =
            medians.length > 0
              ? ObsService.median(medians)
              : ((dirtyCluster = true), ObsService.median(dirtyMedians));
          //res = ObsService.showData(val, type, 3);
          res = ObsService.showData(val, type); // default precision is 5
          // custom background color of cluster
          let reliability = 1;
          if (dirtyCluster) {
            reliability = 0;
          }
          let clusterColor = srv.getColor(val, srv.min, srv.max, reliability);
          c = " mst-marker-color-" + clusterColor;

          var html = ObsMapComponent.drawTheIcon(medians, res, obsService);

          // if the cluster contains data for a single station, bind a tooltip
          let is_single_station = false;
          let station_lng = null;
          let station_lat = null;
          for (let i = 0; i < childMarkers.length; i++) {
            let latlng = childMarkers[i].getLatLng();
            if (!station_lng) {
              station_lat = latlng.lat;
              station_lng = latlng.lng;
              is_single_station = true;
            } else if (
              latlng.lat !== station_lat &&
              latlng.lng !== station_lng
            ) {
              is_single_station = false;
              break;
            }
          }
          if (is_single_station) {
            cluster.bindTooltip(
              ObsMapComponent.buildTooltipTemplate(
                childMarkers[0].options["station"],
              ),
              {
                direction: "top",
                offset: [3, -8],
              },
            );
          }
        } else {
          // case of stations icons
          html = "<div> <span>" + res + "</span></div>";
        }
        let warn = "";
        if (dirtyCluster) {
          // re-draw the html without the donut pie and with the warning sign on it
          html =
            "<div> " +
            '<i class="fas fa-exclamation-triangle fa-lg dirty-cluster"></i>' +
            "<span>" +
            res +
            "</span></div>";
        }
        //console.log("marker ",marker)

        return new L.DivIcon({
          html: html,
          className: "marker-cluster" + c,
          iconSize: new L.Point(40, 40),
        });
      },
      spiderLegPolylineOptions: {
        weight: 1,
        color: "#222",
        opacity: 0.5,
        dashArray: "10 10",
      },
      spiderfyDistanceMultiplier: 1.2,
    };
  }

  static drawTheIcon(data, medianValue, srv): string {
    let colorList = [];
    for (let i = 0; i < data.length; i++) {
      let dataColor = srv.getColor(data[i], srv.min, srv.max);
      colorList.push(dataColor);
    }
    let totalItems = colorList.length;

    let segments = "";
    let prevPercentage = 0;
    let prevOffset = 0;

    // data preparation to manage very small percentage values
    // and preserve anomaly single values
    let percExact: number[] = new Array(COLORS.length);
    let percEdited: number[] = new Array(COLORS.length);
    let zeroIndices: boolean[] = new Array(COLORS.length).fill(false);
    let normPerc: number[] = new Array(COLORS.length).fill(-1);
    let normPercTrunc: number[] = new Array(COLORS.length).fill(0);
    let finallyPerc: number[] = new Array(COLORS.length).fill(2);

    for (let i = 0; i < COLORS.length; i++) {
      let count = colorList.filter((x) => x == COLORS[i]).length;
      if (count > 0) {
        let percentage = Math.round((count / totalItems) * 100);
        if (percentage === 0) zeroIndices[i] = true;
        percExact[i] = percentage;
      }
    }
    const totPercExact = percExact.reduce(
      (accumulator, currentValue) => accumulator + currentValue,
      0,
    );
    for (let i = 0; i < COLORS.length; i++) {
      let count = colorList.filter((x) => x == COLORS[i]).length;
      if (count > 0) {
        let percentage = Math.round((count / totalItems) * 100);
        if (percentage === 0) percentage = 2;
        percEdited[i] = percentage;
      }
    }
    const totPercEdited = percEdited.reduce(
      (accumulator, currentValue) => accumulator + currentValue,
      0,
    );
    const deltaPerc = totPercEdited - totPercExact;

    for (let i = 0; i < COLORS.length; i++) {
      if (!zeroIndices[i]) {
        normPerc[i] = (percEdited[i] / totPercExact) * deltaPerc;
      }
    }

    let percReduce = 0;
    for (let j = 0; j < COLORS.length && percReduce <= deltaPerc; j++) {
      for (let i = 0; i < COLORS.length; i++) {
        if (!zeroIndices[i]) {
          if (j < i) {
            normPercTrunc[i] = Math.ceil(normPerc[i]);
          } else {
            normPercTrunc[i] = Math.floor(normPerc[i]);
          }
        }
      }
      percReduce = normPercTrunc.reduce(
        (accumulator, currentValue) => accumulator + currentValue,
        0,
      );
    }

    for (let i = 0; i < COLORS.length; i++) {
      if (!zeroIndices[i]) {
        finallyPerc[i] = percEdited[i] - normPercTrunc[i];
      }
    }

    // create the different segments of the donut pie
    for (let i = 0; i < COLORS.length; i++) {
      let count = colorList.filter((x) => x == COLORS[i]).length;
      if (count > 0) {
        let percentage = finallyPerc[i];

        // remove the number of pixel needed for the donut slice border
        let percentageWBorder = percentage - 1;
        let strokeDasharray =
          percentageWBorder + " " + (100 - percentageWBorder);

        let strokeDashoffset = 0;
        if (prevOffset == 0) {
          strokeDashoffset = 25;
          // update the previous offset
          prevOffset = 25;
        } else {
          strokeDashoffset = 100 - prevPercentage + prevOffset;
          prevOffset = strokeDashoffset;
        }
        // update the previous percentage
        prevPercentage = percentage;
        //create the segment

        let newSegment =
          `<circle id=${COLORS[i]} class="donut-segment" cx="21" cy="21" r="15.91549430918954" fill="transparent" ` +
          //set the segment color
          'stroke="#' +
          COLORS[i] +
          '" ' +
          'stroke-width="3" ' +
          //set the dasharray
          'stroke-dasharray=" ' +
          strokeDasharray +
          '" ' +
          // set the dashoffset
          'stroke-dashoffset="' +
          strokeDashoffset +
          '"></circle>';
        segments += newSegment;
      }
    }
    let iconHtml =
      '<div class="wrapper"> <svg width="50px" height="50px" viewBox="0 0 42 42" class="donut"> ' +
      '<circle class="donut-hole" cx="21" cy="21" r="15.91549430918954" fill="transparent"></circle> ' +
      '<circle class="donut-ring" cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#fdfdfd ' +
      'stroke-width="3"></circle> ' +
      segments +
      "</svg>" +
      "<span>" +
      medianValue +
      "</span>" +
      "</div>";

    return iconHtml;
  }

  onMapReady(map: L.Map) {
    this.map = map;
    this.map.attributionControl.setPrefix("");
    this.addResetView(this.map);
    this.resetView = true;
  }

  markerClusterReady(group: L.MarkerClusterGroup) {
    this.markerClusterGroup = group;
  }

  updateMap(filter: ObsFilter, update = false) {
    // const startTime = new Date().getTime();
    this.filter = filter;
    this.hourFrom = filter.time[0];
    this.hourTo = filter.time[1];
    // get data
    if (this.markerClusterGroup) {
      this.markerClusterGroup.clearLayers();
    }
    setTimeout(() => this.spinner.show(), 0);
    this.obsService
      .getData(filter, update)
      .subscribe(
        (response: ObservationResponse) => {
          // console.log(`---Getting Data elapsed time: ${(new Date().getTime() - startTime)/1000}s`);
          let data = response.data;
          this.updateCount.emit(data.length);
          this.loadMarkers(data, filter.product, filter.onlyStations);
          if (data.length === 0) {
            this.notify.showWarning(
              "No results found. Try applying a different filter.",
            );
          }
        },
        (error) => {
          this.notify.showError(error);
        },
      )
      .add(() => {
        setTimeout(() => this.spinner.hide(), 0);
        // console.log(`Total Elapsed time: ${(new Date().getTime() - startTime)/1000}s`);
      });
  }

  fitBounds() {
    if (this.markerClusterData.length > 0) {
      this.map.fitBounds(this.markerClusterGroup.getBounds(), {
        padding: L.point(24, 24),
        maxZoom: 12,
        animate: true,
      });
    }
  }

  /**
   *
   * @param data
   */
  private loadMarkers(
    data: Observation[],
    product: string,
    onlyStations = false,
  ) {
    const markers: L.Marker[] = [];
    let min: number, max: number;
    let obsData: ObsData;
    let singleObsData: SingleObsData;
    // const startTime_1 = new Date().getTime();
    if (!onlyStations) {
      // min and max needed before data marker creation
      data.forEach((s) => {
        obsData = s.prod.find((x) => x.var === product);
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
      });
    }
    // console.log(`---Min/Max elapsed time: ${(new Date().getTime() - startTime_1)/1000}s`);
    // const startTime_2 = new Date().getTime();
    data.forEach((s) => {
      let icon;
      if (!onlyStations) {
        obsData = s.prod.find((x) => x.var === product);
        let single_observation = false;
        let count = obsData.val.length;
        if (count === 1) {
          single_observation = true;
        }

        for (let i = 0; i < obsData.val.length; i++) {
          // create an object for each value of obsData
          singleObsData = {
            var: product,
            val: obsData.val[i],
          };
          const val = singleObsData.val.val;
          if (!single_observation) {
            icon = L.divIcon({
              html: `<div class="mstDataIcon"><span>${ObsService.showData(
                val,
                product,
              )}</span></div>`,
              iconSize: [24, 6],
              className:
                "leaflet-marker-icon mst-marker-color-" +
                this.obsService.getColor(val, min, max, obsData.val[i].rel),
            });
          } else {
            icon = L.divIcon({
              html: `<div style="width:31px;height:31px"><span>${ObsService.showData(
                val,
                product,
              )}</span></div>`,
              iconSize: [40, 40],
              className:
                "leaflet-marker-icon mst-marker-color-" +
                this.obsService.getColor(val, min, max, obsData.val[i].rel) +
                " marker-cluster",
            });
          }
          const marker = new L.Marker([s.stat.lat, s.stat.lon], {
            icon: icon,
          });
          marker.options["station"] = s.stat;
          if (s.prod) {
            marker.options["data"] = singleObsData;
            marker.bindTooltip(
              !single_observation
                ? ObsMapComponent.buildDataTooltip(
                    singleObsData.val.ref,
                    // singleObsData.value.level_desc,
                    // singleObsData.value.timerange_desc
                  )
                : ObsMapComponent.buildTooltipTemplate(
                    s.stat,
                    singleObsData.val.ref,
                    // singleObsData.value.level_desc,
                    // singleObsData.value.timerange_desc
                  ),
              {
                direction: "top",
                offset: [3, -8],
              },
            );
            marker.on("click", this.openStationReport.bind(this, s.stat));
          }
          markers.push(marker);
        }
      } else {
        icon = L.divIcon({
          html: '<i class="fa fa-map-marker-alt fa-3x"></i>',
          iconSize: [20, 20],
          className: "mstDivIcon",
        });
        const marker = new L.Marker([s.stat.lat, s.stat.lon], {
          icon: icon,
        });
        marker.options["station"] = s.stat;
        if (s.prod) {
          marker.options["data"] = obsData;
        }

        marker.bindTooltip(ObsMapComponent.buildTooltipTemplate(s.stat), {
          direction: "top",
          offset: [3, -8],
        });
        markers.push(marker);
      }
    });
    // console.log(`---Markers creation elapsed time: ${(new Date().getTime() - startTime_2)/1000}s`);

    if (!onlyStations && data.length > 0) {
      const startTime_3 = new Date().getTime();
      console.log(`min ${min}, max ${max}`);
      this.obsService.min = min;
      this.obsService.max = max;
      this.buildLegend(product, min, max);
    } else {
      this.legend.remove();
    }

    this.markerClusterData = markers;
    this.markerClusterGroup.addLayers(markers);

    // need to trigger resize event
    window.dispatchEvent(new Event("resize"));
    // need to remain in the previously selected map area
    if (this.resetView) {
      setTimeout(() => {
        this.fitBounds();
      }, 0);
      this.resetView = false;
    }
  }

  private openStationReport(station: Station) {
    const modalRef = this.modalService.open(ObsStationReportComponent, {
      size: "xl",
      centered: true,
    });
    modalRef.componentInstance.station = station;
    modalRef.componentInstance.filter = this.filter;
    // need to trigger resize event
    window.dispatchEvent(new Event("resize"));
  }

  private static buildTooltipTemplate(
    station: Station,
    reftime?: string,
    level?: string,
    timerange?: string,
  ) {
    let ident = station.ident || "";
    let name =
      station.details && station.details.length
        ? station.details.find((e) => e.var === "B01019")
        : undefined;
    const template =
      `<ul class="p-1 m-0">` +
      `<li><b><u>Station</u></b></li>` +
      (name ? `<li><b>Name</b>: ${name.val}</li>` : "") +
      `<li><b>Network</b>: ${station.net}</li>` +
      (ident !== "" ? `<li><b>Ident</b>: ` + ident + `</li>` : "") +
      `<li><b>Lat</b>: ${station.lat}</li>` +
      `<li><b>Lon</b>: ${station.lon}</li>` +
      (reftime
        ? `<br><li><b><u>Data</u></b></li><li><b>Reftime</b>: ` +
          reftime +
          `</li>`
        : "") +
      (level ? `<li><b>Level</b>: ` + level + `</li>` : "") +
      (timerange ? `<li><b>Timerange</b>: ` + timerange + `</li>` : "") +
      `</ul>`;
    return template;
  }
  /*private static buildStationTooltip(station_details: StationDetail[]) {
    let detail_list = "";
    station_details.forEach(function (d) {
      detail_list +=
        `<li><b>` +
        d.description
          .replace(/\w\S*!/g, function (txt) {
            return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
          })
          .replace(/ *\([^)]*\) *!/g, "") +
        `</b>: ` +
        d.value +
        `</li>`;
    });
    const template = `<ul class="p-1 m-0">` + detail_list + `</ul>`;
    return template;
  }*/

  private static buildDataTooltip(
    reftime: string,
    level?: string,
    timerange?: string,
  ) {
    const template =
      `<ul class="p-1 m-0">
                <!--<li><b><u>Data</u></b></li>--><li><b>Reftime: </b>${reftime}</li>` +
      /*        (level ? `<li><b>Level</b>${level}</li>` : "") +
        (timerange ? `<li><b>Timerange: </b>${timerange}</li>`:"") +*/
      `</ul>`;
    return template;
  }

  private buildLegend(product: string, min: number, max: number) {
    let srv = this.obsService;
    this.legend.onAdd = function (map, service = srv) {
      console.log(
        `add legend for product ${product} (${min.toFixed(2)}, ${max.toFixed(
          2,
        )})`,
      );
      let div = L.DomUtil.create("div", "info mst-legend");
      let halfDelta = (max - min) / (COLORS.length * 2);
      let bcode = VAR_TABLE.find((x) => x.bcode === product);
      let title = product,
        scale = 1,
        offset = 0,
        userunit = "n/a";
      if (bcode) {
        title = bcode.short || bcode.description;
        userunit = bcode.userunit;
        (scale = bcode.scale), (offset = bcode.offset);
      } else {
        title = srv.getProductDescr(product);
        userunit = srv.getUnit(product);
      }

      div.innerHTML += `<h6>${title} [${userunit}]</h6>`;
      let legendTemp = "";
      for (let i = 0; i < COLORS.length; i++) {
        let grade = min + halfDelta * (i * 2 + 1);
        legendTemp =
          '<i style="background:#' +
          service.getColor(grade, min, max) +
          '"></i><span>' +
          // (grade*scale+offset).toPrecision(5).replace(/\.?0+$/,"")
          Math.floor(grade * scale + offset) +
          "</span><br>" +
          legendTemp;
      }
      div.innerHTML += legendTemp;
      return div;
    };
    this.legend.addTo(this.map);
  }
  addResetView(map: L.Map) {
    this.map = map;
    var self = this;
    var button = L.Control.extend({
      onAdd: function (map: L.Map) {
        var container = L.DomUtil.create("div", "leaflet-bar leaflet-control");
        var resetButton = L.DomUtil.create(
          "a",
          "leaflet-control-button",
          container,
        );

        resetButton.innerHTML = '<i class="fa-solid fa-rotate-right"></i>';
        resetButton.title = "Reset view";
        L.DomEvent.disableClickPropagation(resetButton);
        L.DomEvent.on(resetButton, "click", () => {
          self.fitBounds();
        });

        return container;
      },
    });

    var buttonOpt = function (opts: L.ControlOptions | undefined) {
      return new button(opts);
    };
    let buttonItem = buttonOpt({
      position: "topleft",
    });
    buttonItem.addTo(map);
    return buttonItem;
  }
  setTempColor(val, rel) {
    // code B12101
    let color;
    if (rel == 0) {
      return "undefined";
    } else {
      if (val >= 319.15) {
        color = "#ff9900";
      } else if (val >= 317.15 && val < 319.15) {
        color = "#ffcc00";
      } else if (val >= 315.15 && val < 317.15) {
        color = "#7200ff";
      } else if (val >= 313.15 && val < 315.15) {
        color = "#bf00ff";
      } else if (val >= 311.15 && val < 313.15) {
        color = "#ff00ff";
      } else if (val >= 309.15 && val < 311.15) {
        color = "#cc00cc";
      } else if (val >= 307.15 && val < 309.15) {
        color = "#990099";
      } else if (val >= 305.15 && val < 307.15) {
        color = "#660066";
      } else if (val >= 303.15 && val < 305.15) {
        color = "#660000";
      } else if (val >= 301.15 && val < 303.15) {
        color = "#990000";
      } else if (val >= 299.15 && val < 301.15) {
        color = "#cc0000";
      } else if (val >= 297.15 && val < 299.15) {
        color = "#ff0000";
      } else if (val >= 295.15 && val < 297.15) {
        color = "#ff6600";
      } else if (val >= 293.15 && val < 295.15) {
        color = "#ff9900";
      } else if (val >= 291.15 && val < 293.15) {
        color = "#ffcc00";
      } else if (val >= 289.15 && val < 291.16) {
        color = "#ffff00";
      } else if (val >= 287.15 && val < 289.15) {
        color = "#cce500";
      } else if (val >= 285.15 && val < 287.15) {
        color = "#7fcc00";
      } else if (val >= 283.15 && val < 285.15) {
        color = "#00b200";
      } else if (val >= 281.15 && val < 283.15) {
        color = "#00cc7f";
      } else if (val >= 279.15 && val < 281.15) {
        color = "#00e5cc";
      } else if (val >= 277.15 && val < 279.15) {
        color = "#00ffff";
      } else if (val >= 275.15 && val < 277.15) {
        color = "#00bfff";
      } else if (val >= 273.15 && val < 275.15) {
        color = "#008cff";
      } else if (val >= 271.15 && val < 273.15) {
        color = "#0059ff";
      } else if (val >= 269.15 && val < 271.15) {
        color = "#0000ff";
      } else if (val >= 267.15 && val < 269.15) {
        color = "#7200ff";
      } else if (val >= 265.15 && val < 267.15) {
        color = "#bf00ff";
      } else if (val >= 263.15 && val < 265.15) {
        color = "#ff00ff";
      } else if (val >= 261.15 && val < 263.15) {
        color = "#cc00cc";
      } else if (val >= 259.15 && val < 261.15) {
        color = "#990099";
      } else if (val >= 257.15 && val < 259.15) {
        color = "#660066";
      } else if (val >= 255.15 && val < 257.15) {
        color = "#660000";
      } else if (val >= 253.15 && val < 255.15) {
        color = "#990000";
      } else if (val >= 251.15 && val < 253.15) {
        color = "#cc0000";
      } else if (val >= 249.15 && val < 251.15) {
        color = "#ff0000";
      } else if (val >= 247.15 && val < 249.15) {
        color = "#ff6600";
      } else if (val >= 245.15 && val < 247.15) {
        color = "#ff9900";
      } else if (val >= 243.15 && val < 245.15) {
        color = "#ffcc00";
      }
      return color;
    }
  }
  setPrecColor(val, rel) {
    let color;
    if (rel == 0) {
      return "undefined";
    } else {
      if (val >= 300) {
        color = "#4897D9";
      } else if (val >= 200 && val < 300) {
        color = "#A2A4D6";
      } else if (val >= 100 && val < 200) {
        color = "#B887C0";
      } else if (val >= 75 && val < 100) {
        color = "#D6A1CC";
      } else if (val >= 50 && val < 75) {
        color = "#E7BDDA";
      } else if (val >= 40 && val < 50) {
        color = "#E57D9A";
      } else if (val >= 30 && val < 40) {
        color = "#DA4C4D";
      } else if (val >= 25 && val < 30) {
        color = "#EE5A5C";
      } else if (val >= 20 && val < 25) {
        color = "#F6A15C";
      } else if (val >= 15 && val < 20) {
        color = "#FCD48E";
      } else if (val >= 10 && val < 15) {
        color = "#FFE073";
      } else if (val >= 8 && val < 10) {
        color = "#FDFD81";
      } else if (val >= 6 && val < 8) {
        color = "#FFFFC6";
      } else if (val >= 5 && val < 6) {
        color = "#F2F2A0";
      } else if (val >= 4 && val < 5) {
        color = "#D2EBA3";
      } else if (val >= 3 && val < 4) {
        color = "#C2E5D7";
      } else if (val >= 2 && val < 3) {
        color = "#C7E7EF";
      } else if (val >= 0 && val < 2) {
        color = "#CFEAF6";
      }
      return color;
    }
  }
  setRhColor(val, rel) {
    let color;
    if (rel == 0) {
      return "undefined";
    } else {
      if (val >= 100) {
        color = "#1000FD";
      } else if (val >= 80 && val < 100) {
        color = "#21FEFF";
      } else if (val >= 60 && val < 80) {
        color = "#19FF24";
      } else if (val >= 40 && val < 60) {
        color = "#FEFF27";
      } else if (val >= 20 && val < 40) {
        color = "#FE8A12";
      } else if (val >= 0 && val < 20) {
        color = "#FD1506";
      }
      return color;
    }
  }
  setWindColor(val, rel) {
    let color;
    if (rel == 0) {
      return "undefined";
    } else {
      if (val >= 70) {
        color = "#9600FE";
      } else if (val >= 50 && val < 70) {
        color = "#EE82EE";
      } else if (val >= 30 && val < 50) {
        color = "#FF0000";
      } else if (val >= 20 && val < 30) {
        color = "#FFFF00";
      } else if (val >= 10 && val < 20) {
        color = "#FFA600";
      } else if (val >= 5 && val < 10) {
        color = "#0000FE";
      } else if (val >= 2 && val < 5) {
        color = "#54878C";
      } else if (val >= 0 && val < 2) {
        color = "#457D00";
      }
      return color;
    }
  }
}
