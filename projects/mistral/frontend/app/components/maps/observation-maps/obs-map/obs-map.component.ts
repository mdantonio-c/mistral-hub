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
import {
  COLORS,
  obsData,
  VAR_TABLE,
  COLORS_RH,
  COLORS_WIND,
  COLORS_PREC,
  COLORS_TEMP,
  RANGES_TEMP_LENGEND,
  RANGES_PREC_LEGEND,
  RANGES_WIND_LEGEND,
  RANGES_RH_LEGEND,
} from "../services/data";
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
  // main variables require a fixed colors and legend
  // dictionary={ key=bcode, value=[color vector, routine color, legend text] }
  codeToColorList = {
    B13003: [COLORS_RH, this.setRhColor, RANGES_RH_LEGEND], //relative humidity
    B11002: [COLORS_WIND, this.setWindColor, RANGES_WIND_LEGEND], // wind speed
    B13011: [COLORS_PREC, this.setPrecColor, RANGES_PREC_LEGEND], // total precipitation
    B12101: [COLORS_TEMP, this.setTempColor, RANGES_TEMP_LENGEND], // temperature
  };
  codeToColorListKeys = Object.keys(this.codeToColorList);
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
    const ref = this;
    this.markerClusterOptions = {
      maxClusterRadius: 50,
      iconCreateFunction: function (cluster, srv = obsService) {
        const childCount = cluster.getChildCount();
        const childMarkers: L.Marker[] = cluster.getAllChildMarkers();
        let productCode = childMarkers[0].options["data"]
          ? childMarkers[0].options["data"].var
          : undefined;
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
          let clusterColor: string;
          if (ref.codeToColorListKeys.includes(productCode)) {
            //if(productCode == 'B13003') {clusterColor = ref.setRhColor(val,reliability);}
            clusterColor = ref.codeToColorList[productCode][1](
              val,
              reliability,
            );
          } else {
            clusterColor = srv.getColor(val, srv.min, srv.max, reliability);
          }
          c = " mst-marker-color-" + clusterColor;

          var html = ObsMapComponent.drawTheIcon(
            medians,
            res,
            obsService,
            productCode,
            ref,
          );

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

  static drawTheIcon(data, medianValue, srv, code = undefined, ref): string {
    let colorList = [];
    for (let i = 0; i < data.length; i++) {
      let dataColor: string;

      if (ref.codeToColorListKeys.includes(code)) {
        /*if (code == 'B13003') {
          dataColor = ref.setRhColor(data[i], 1);
        }*/
        dataColor = ref.codeToColorList[code][1](data[i], 1);
      } else {
        dataColor = srv.getColor(data[i], srv.min, srv.max);
      }
      colorList.push(dataColor);
    }

    let totalItems = colorList.length;
    let segments = "";
    let prevPercentage = 0;
    let prevOffset = 0;
    let colorsVectorLenght: number;
    if (ref.codeToColorListKeys.includes(code)) {
      /*if (code == 'B13003') {
        colorsVectorLenght = COLORS_RH.length
      }*/
      colorsVectorLenght = ref.codeToColorList[code][0].length;
    } else {
      colorsVectorLenght = COLORS.length;
    }
    // data preparation to manage very small percentage values
    // and preserve anomaly single values
    let percExact: number[] = new Array(colorsVectorLenght);
    let percEdited: number[] = new Array(colorsVectorLenght);
    let zeroIndices: boolean[] = new Array(colorsVectorLenght).fill(false);
    let normPerc: number[] = new Array(colorsVectorLenght).fill(-1);
    let normPercTrunc: number[] = new Array(colorsVectorLenght).fill(0);
    let finallyPerc: number[] = new Array(colorsVectorLenght).fill(2);

    for (let i = 0; i < colorsVectorLenght; i++) {
      let count: number;
      if (ref.codeToColorListKeys.includes(code)) {
        /*     if (code == 'B13003') {
          count = colorList.filter((x) => x == COLORS_RH[i]).length;
        }*/
        count = colorList.filter(
          (x) => x == ref.codeToColorList[code][0][i],
        ).length;
      } else {
        count = colorList.filter((x) => x == COLORS[i]).length;
      }
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
    for (let i = 0; i < colorsVectorLenght; i++) {
      let count: number;
      if (ref.codeToColorListKeys.includes(code)) {
        /*        if (code == 'B13003') {
          count = colorList.filter((x) => x == COLORS_RH[i]).length;
        }*/
        count = colorList.filter(
          (x) => x == ref.codeToColorList[code][0][i],
        ).length;
      } else {
        count = colorList.filter((x) => x == COLORS[i]).length;
      }
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

    for (let i = 0; i < colorsVectorLenght; i++) {
      if (!zeroIndices[i]) {
        normPerc[i] = (percEdited[i] / totPercExact) * deltaPerc;
      }
    }

    let percReduce = 0;
    for (let j = 0; j < colorsVectorLenght && percReduce <= deltaPerc; j++) {
      for (let i = 0; i < colorsVectorLenght; i++) {
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

    for (let i = 0; i < colorsVectorLenght; i++) {
      if (!zeroIndices[i]) {
        finallyPerc[i] = percEdited[i] - normPercTrunc[i];
        if (finallyPerc[i] == 0) finallyPerc[i] = 1;
      }
    }

    // create the different segments of the donut pie
    for (let i = 0; i < colorsVectorLenght; i++) {
      let count: number;
      if (ref.codeToColorListKeys.includes(code)) {
        /*        if (code == 'B13003') {
          count = colorList.filter((x) => x == COLORS_RH[i]).length;
        }*/
        count = colorList.filter(
          (x) => x == ref.codeToColorList[code][0][i],
        ).length;
      } else {
        count = colorList.filter((x) => x == COLORS[i]).length;
      }
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
        let selectedScaleColor;
        if (ref.codeToColorListKeys.includes(code)) {
          selectedScaleColor = ref.codeToColorList[code][0];
        } else {
          selectedScaleColor = COLORS;
        }
        let newSegment =
          `<circle id=${selectedScaleColor[i]} class="donut-segment" cx="21" cy="21" r="15.91549430918954" fill="transparent" ` +
          //set the segment color
          'stroke="#' +
          selectedScaleColor[i] +
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
    let selectedAMainVariable = this.codeToColorListKeys.includes(product);
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
          let colorClass;
          if (selectedAMainVariable) {
            colorClass = this.codeToColorList[product][1](
              val,
              obsData.val[i].rel,
            );
          } else {
            colorClass = this.obsService.getColor(
              val,
              min,
              max,
              obsData.val[i].rel,
            );
          }
          if (!single_observation) {
            icon = L.divIcon({
              html: `<div class="mstDataIcon"><span>${ObsService.showData(
                val,
                product,
              )}</span></div>`,
              iconSize: [24, 6],
              className: "leaflet-marker-icon mst-marker-color-" + colorClass,
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
                colorClass +
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
    const ref = this;
    this.legend.onAdd = function (map, service = srv) {
      console.log(
        `add legend for product ${product} (${min.toFixed(2)}, ${max.toFixed(
          2,
        )})`,
      );

      let div = L.DomUtil.create("div", "info mst-legend");
      let bcode = VAR_TABLE.find((x) => x.bcode === product);
      let colorVectorLength: number;
      if (ref.codeToColorListKeys.includes(product)) {
        colorVectorLength = ref.codeToColorList[product][0].length;
      } else {
        colorVectorLength = COLORS.length;
      }

      //let halfDelta = (max - min) / (COLORS.length * 2);
      let halfDelta = (max - min) / (colorVectorLength * 2);
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
      if (ref.codeToColorListKeys.includes(product)) {
        let displayValue = "";
        for (let i = 0; i < colorVectorLength; i++) {
          if (product == "B12101") {
            displayValue =
              (ref.codeToColorList[product][2][i][0] + offset).toString() +
              " - " +
              (ref.codeToColorList[product][2][i][1] + offset).toString();
            if (i == 0)
              displayValue =
                "< " +
                (ref.codeToColorList[product][2][i][0] + offset).toString();
            if (i == colorVectorLength - 1)
              displayValue =
                "> " +
                (ref.codeToColorList[product][2][i][0] + offset).toString();
            legendTemp =
              '<i style="background:#' +
              ref.codeToColorList[product][0][i] +
              '"></i><span>' +
              displayValue +
              "</span><br>" +
              legendTemp;
          } else if (product == "B13011") {
            if (i != colorVectorLength - 1) {
              displayValue =
                ref.codeToColorList[product][2][i][0].toString() +
                " - " +
                ref.codeToColorList[product][2][i][1].toString();
            } else {
              displayValue =
                "> " + ref.codeToColorList[product][2][i][0].toString();
            }
            legendTemp =
              '<i style="background:#' +
              ref.codeToColorList[product][0][i] +
              '"></i><span>' +
              displayValue +
              "</span><br>" +
              legendTemp;
          } else if (product == "B11002") {
            if (i != colorVectorLength - 1) {
              displayValue =
                ref.codeToColorList[product][2][i][0].toString() +
                " - " +
                ref.codeToColorList[product][2][i][1].toString();
            } else {
              displayValue =
                "> " + ref.codeToColorList[product][2][i][0].toString();
            }
            legendTemp =
              '<i style="background:#' +
              ref.codeToColorList[product][0][i] +
              '"></i><span>' +
              displayValue +
              "</span><br>" +
              legendTemp;
          } else if (product == "B13003") {
            if (i != colorVectorLength - 1) {
              displayValue =
                ref.codeToColorList[product][2][i][0].toString() +
                " - " +
                ref.codeToColorList[product][2][i][1].toString();
            } else {
              displayValue = ref.codeToColorList[product][2][i][0].toString();
            }
            legendTemp =
              '<i style="background:#' +
              ref.codeToColorList[product][0][i] +
              '"></i><span>' +
              displayValue +
              "</span><br>" +
              legendTemp;
          }
        }
      } else {
        for (let i = 0; i < colorVectorLength; i++) {
          let grade = min + halfDelta * (i * 2 + 1);
          let value = grade * scale + offset;
          let displayValue = ref.getDisplayValue(
            value,
            min,
            max,
            colorVectorLength,
          );

          legendTemp =
            '<i style="background:#' +
            service.getColor(grade, min, max) +
            '"></i><span>' +
            displayValue +
            "</span><br>" +
            legendTemp;
        }
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
      if (val < 263.15) {
        color = "1e4bff";
      } else if (val >= 263.15 && val < 268.15) {
        color = "1e56ff";
      } else if (val >= 268.15 && val < 273.15) {
        color = "1e78ff";
      } else if (val >= 273.15 && val < 275.15) {
        color = "1e9eff";
      } else if (val >= 275.15 && val < 277.15) {
        color = "1ecbff";
      } else if (val >= 277.15 && val < 279.15) {
        color = "1ee1ff";
      } else if (val >= 279.15 && val < 281.15) {
        color = "1effff";
      } else if (val >= 281.15 && val < 283.15) {
        color = "1effce";
      } else if (val >= 283.15 && val < 285.15) {
        color = "1eff9a";
      } else if (val >= 285.15 && val < 287.15) {
        color = "1eff43";
      } else if (val >= 287.15 && val < 289.15) {
        color = "78ff1e";
      } else if (val >= 289.15 && val < 291.15) {
        color = "9eff1e";
      } else if (val >= 291.15 && val < 293.15) {
        color = "d6ff1e";
      } else if (val >= 293.15 && val < 295.15) {
        color = "f4ff1e";
      } else if (val >= 295.15 && val < 297.15) {
        color = "ffec1e";
      } else if (val >= 297.15 && val < 299.15) {
        color = "ffce1e";
      } else if (val >= 299.15 && val < 301.15) {
        color = "ffb01e";
      } else if (val >= 301.15 && val < 303.15) {
        color = "ff9a1e";
      } else if (val >= 303.15 && val < 308.15) {
        color = "ff741e";
      } else if (val >= 308.15 && val < 313.15) {
        color = "ff4d1e";
      } else if (val >= 313.15) {
        color = "ff261e";
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
        color = "4897D9";
      } else if (val >= 200 && val < 300) {
        color = "A2A4D6";
      } else if (val >= 100 && val < 200) {
        color = "B887C0";
      } else if (val >= 75 && val < 100) {
        color = "D6A1CC";
      } else if (val >= 50 && val < 75) {
        color = "E7BDDA";
      } else if (val >= 40 && val < 50) {
        color = "E57D9A";
      } else if (val >= 30 && val < 40) {
        color = "DA4C4D";
      } else if (val >= 25 && val < 30) {
        color = "EE5A5C";
      } else if (val >= 20 && val < 25) {
        color = "F6A15C";
      } else if (val >= 15 && val < 20) {
        color = "FCD48E";
      } else if (val >= 10 && val < 15) {
        color = "FFE073";
      } else if (val >= 8 && val < 10) {
        color = "FDFD81";
      } else if (val >= 6 && val < 8) {
        color = "FFFFC6";
      } else if (val >= 5 && val < 6) {
        color = "F2F2A0";
      } else if (val >= 4 && val < 5) {
        color = "D2EBA3";
      } else if (val >= 3 && val < 4) {
        color = "C2E5D7";
      } else if (val >= 2 && val < 3) {
        color = "C7E7EF";
      } else if (val >= 0 && val < 2) {
        color = "CFEAF6";
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
        color = "1000FD";
      } else if (val >= 80 && val < 100) {
        color = "21FEFF";
      } else if (val >= 60 && val < 80) {
        color = "19FF24";
      } else if (val >= 40 && val < 60) {
        color = "FEFF27";
      } else if (val >= 20 && val < 40) {
        color = "FE8A12";
      } else if (val >= 0 && val < 20) {
        color = "FD1506";
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
        color = "9600FE";
      } else if (val >= 50 && val < 70) {
        color = "EE82EE";
      } else if (val >= 30 && val < 50) {
        color = "FF0000";
      } else if (val >= 20 && val < 30) {
        color = "FFFF00";
      } else if (val >= 10 && val < 20) {
        color = "FFA600";
      } else if (val >= 5 && val < 10) {
        color = "0000FE";
      } else if (val >= 2 && val < 5) {
        color = "54878C";
      } else if (val >= 0 && val < 2) {
        color = "457D00";
      }
      return color;
    }
  }
  getDisplayValue(value, min, max, vectorlen) {
    const range = max - min;
    let decimalPlaces;

    if (range < 0.0001) {
      decimalPlaces = 6;
    } else if (range < 0.001) {
      decimalPlaces = 5;
    } else if (range < 0.01) {
      decimalPlaces = 4;
    } else if (range < 0.1) {
      decimalPlaces = 3;
    } else if (range < 1) {
      decimalPlaces = 2;
    } else {
      if (vectorlen > range) {
        decimalPlaces = 1;
      } else {
        decimalPlaces = 0;
      }
    }

    return value.toFixed(decimalPlaces);
  }
}
