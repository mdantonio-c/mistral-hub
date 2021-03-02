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
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> | &copy; <a href="https://meteohub.hpc.cineca.it/app/license">MISTRAL data contributor</a>',
    }
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

  constructor(
    private obsService: ObsService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private modalService: NgbModal
  ) {
    // custom cluster options
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
          c =
            " mst-marker-color-" +
            srv.getColor(val, srv.min, srv.max, reliability);

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
                childMarkers[0].options["station"]
              ),
              {
                direction: "top",
                offset: [3, -8],
              }
            );
          }
        }
        let warn = "";
        if (dirtyCluster) {
          warn =
            '<i class="fas fa-exclamation-triangle fa-lg dirty-cluster"></i>';
        }
        //console.log("marker ",marker)

        return new L.DivIcon({
          html: "<div>" + warn + "<span>" + res + "</span></div>",
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
              "No results found. Try applying a different filter."
            );
          }
        },
        (error) => {
          this.notify.showError(error);
        }
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
    onlyStations = false
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
                product
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
                product
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
                    singleObsData.val.ref
                    // singleObsData.value.level_desc,
                    // singleObsData.value.timerange_desc
                  )
                : ObsMapComponent.buildTooltipTemplate(
                    s.stat,
                    singleObsData.val.ref
                    // singleObsData.value.level_desc,
                    // singleObsData.value.timerange_desc
                  ),
              {
                direction: "top",
                offset: [3, -8],
              }
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
    setTimeout(() => {
      this.fitBounds();
    }, 0);
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
    timerange?: string
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
    timerange?: string
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
          2
        )})`
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
}
