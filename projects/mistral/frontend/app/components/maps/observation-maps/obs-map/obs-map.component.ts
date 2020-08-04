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
  ObsService,
  SingleObsData,
  Station,
} from "../services/obs.service";
import { COLORS, obsData, VAR_TABLE } from "../services/data";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";

import * as L from "leaflet";
import "leaflet.markercluster";
import { marker } from "leaflet";

@Component({
  selector: "app-obs-map",
  templateUrl: "./obs-map.component.html",
  styleUrls: ["./obs-map.component.css"],
  encapsulation: ViewEncapsulation.None,
})
export class ObsMapComponent {
  @Output() updateCount: EventEmitter<number> = new EventEmitter<number>();

  // base layers
  streetMaps = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      detectRetina: true,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }
  );
  wMaps = L.tileLayer("http://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png", {
    detectRetina: true,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  });

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
  };

  constructor(
    private obsService: ObsService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {
    // custom cluster options

    this.markerClusterOptions = {
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
          //console.log("costruisco ",childMarkers)
          let mean = 0,
            medians: number[] = [],
            dirtyMedians: number[] = [];
          for (const m of childMarkers) {
            /*const obsData: ObsData = m.options["data"];
                        if (!type) {
                            type = obsData.varcode;
                        }
                        // mean += obsData.values.filter(v => v.is_reliable).map(v => v.value).reduce((a, b) => a + b, 0) / obsData.values.length;
                        let median = ObsService.median(
                            obsData.values.filter((v) => v.is_reliable).map((v) => v.value)
                        );
                        // calculates the median of all values including unreliable ones
                        let dirtyMedian = ObsService.median(
                            obsData.values.map((v) => v.value)
                        );
                        dirtyMedians.push(dirtyMedian);
                        if (Number.isNaN(median)) {
                            // do not consider this median in the cluster median
                            continue;
                        }
                        medians.push(median);*/
            const singleobsData: SingleObsData = m.options["data"];
            if (!type) {
              type = singleobsData.varcode;
            }
            // mean += obsData.values.filter(v => v.is_reliable).map(v => v.value).reduce((a, b) => a + b, 0) / obsData.values.length;
            /* let median = ObsService.median(
                             obsData.values.filter((v) => v.is_reliable).map((v) => v.value)
                         );*/
            //console.log ("here ",singleobsData)
            if (singleobsData.value.is_reliable) {
              let val = singleobsData.value.value;
              medians.push(val);
            } else {
              let dirtyVal = singleobsData.value.value;
              dirtyMedians.push(dirtyVal);
            }
            /*                       // calculates the median of all values including unreliable ones
                                               let dirtyMedian = ObsService.median(
                                                   obsData.values.map((v) => v.value)
                                               );
                                               dirtyMedians.push(dirtyMedian);*/
            /*                        if (Number.isNaN(val)) {
                                                    // do not consider this median in the cluster median
                                                    continue;
                                                }*/
          }
          //console.log(medians)
          // get the median instead of the mean
          // let val = mean/childCount;
          let val =
            medians.length > 0
              ? ObsService.median(medians)
              : ((dirtyCluster = true), ObsService.median(dirtyMedians));
          res = ObsService.showData(val, type, 3);

          // custom background color of cluster
          c = " mst-marker-color-" + srv.getColor(val, srv.min, srv.max);
        }
        let warn = "";
        if (dirtyCluster) {
          warn =
            '<i class="fas fa-exclamation-triangle fa-lg dirty-cluster"></i>';
        }
        /*  L.marker.bindTooltip("singleObsData.value.reftime", {
                              direction: "top",
                              offset: [3, -8],
                          });*/
        //console.log("marker ",marker)

        return new L.DivIcon({
          html: "<div>" + warn + "<span>" + res + "</span></div>",
          className: "marker-cluster" + c,
          iconSize: new L.Point(40, 40),
        });
      },
      spiderLegPolylineOptions: { weight: 1, color: "#ffff", opacity: 0.5 },
      spiderfyDistanceMultiplier: 1.2,
      spiderfyLinear: false,
      spiderfyShapePositions: function (count, centerPt) {
        var distanceFromCenter = 30,
          markerDistance = 45,
          lineLength = markerDistance * (count - 1),
          lineStart = centerPt.y - lineLength / 2,
          res = [],
          i;

        res.length = count;

        for (i = count - 1; i >= 0; i--) {
          res[i] = new L.Point(
            centerPt.x + distanceFromCenter,
            lineStart + markerDistance * i
          );
        }

        return res;
      },
      /*spiderfyShapePositions: function(count, centerPt) {
                console.log("here")
                var distanceFromCenter = 35,
                    markerDistance = 45,
                    lineLength = markerDistance * (count - 1),
                    lineStart = centerPt.y - lineLength / 2,
                    res = [],
                    i;

                res.length = count;

                for (i = count - 1; i >= 0; i--) {
                    res[i] = new L.Point(centerPt.x + distanceFromCenter, lineStart + markerDistance * i);
                }
                console.log("res ",res)
                return res;
            }*/
    };
    console.log("options ", this.markerClusterOptions.spiderfyShapePositions);
  }

  onMapReady(map: L.Map) {
    this.map = map;
  }

  markerClusterReady(group: L.MarkerClusterGroup, obsData: ObsData) {
    this.markerClusterGroup = group;
    /*                        markers.on('clustermouseover', function (a) {
            // a.layer is actually a cluster
            console.log('cluster ' + a.layer.getAllChildMarkers().length);
        });*/
    this.markerClusterGroup.on("clustermouseover", function (a) {
      let childmarkers = a.layer.getAllChildMarkers();

      const obsData = childmarkers[0];
      // a.layer is actually a cluster
      console.log("lenght " + childmarkers.length);
      console.log("data " + obsData.data);
    });
    /*// add a tooltip to the cluster ---> it works!
        this.markerClusterGroup.on('clustermouseover', function(ev) {
        ev.propagatedFrom.bindTooltip('tooltip text', {sticky: true}).openTooltip();
    }).on('clustermouseout', function(ev) {
        ev.propagatedFrom.unbindTooltip();
    });*/

    //console.log("gruppo ",this.markerClusterGroup)
  }

  updateMap(filter: ObsFilter) {
    // get data
    if (this.markerClusterGroup) {
      this.markerClusterGroup.clearLayers();
    }
    setTimeout(() => this.spinner.show(), 0);
    this.obsService
      .getData(filter)
      .subscribe(
        (data: Observation[]) => {
          // console.log(data);
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
        this.spinner.hide();
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
    if (!onlyStations) {
      // min and max needed before data marker creation
      data.forEach((s) => {
        obsData = s.products.find((x) => x.varcode === product);
        let localMin = Math.min(
          ...obsData.values.filter((v) => v.is_reliable).map((v) => v.value)
        );
        if (!min || localMin < min) {
          min = localMin;
        }
        let localMax = Math.max(
          ...obsData.values.filter((v) => v.is_reliable).map((v) => v.value)
        );
        if (!max || localMax > max) {
          max = localMax;
        }
      });
    }
    data.forEach((s) => {
      let icon;
      if (!onlyStations) {
        obsData = s.products.find((x) => x.varcode === product);
        // get the median instead of the mean
        // let val = obsData.values.map(v => v.value).reduce((a, b) => a + b, 0) / obsData.values.length;

        // median of all values
        /*        let val = ObsService.median(
                          obsData.values.filter((v) => v.is_reliable).map((v) => v.value)
                        );
                        if (Number.isNaN(val)) {
                          // at the moment is all the values are unreliable calculate the median and show it anyway
                          // TO BE CHECKED
                          val = ObsService.median(obsData.values.map((v) => v.value));
                        }*/
        for (var i = 0; i < obsData.values.length; i++) {
          //console.log(obsData.values[i].value)
          singleObsData = JSON.parse(JSON.stringify(obsData));
          delete singleObsData["values"];
          singleObsData.value = obsData.values[i];
          //console.log("original ",obsData, " single ",singleObsData)
          let val = singleObsData.value.value;
          icon = L.divIcon({
            html: `<div class="mstDataIcon"><span>${ObsService.showData(
              val,
              product
            )}</span></div>`,
            iconSize: [24, 6],
            className:
              "leaflet-marker-icon mst-marker-color-" +
              this.obsService.getColor(val, min, max),
          });
          const marker = new L.Marker([s.station.lat, s.station.lon], {
            icon: icon,
          });
          marker.options["station"] = s.station;
          if (s.products) {
            marker.options["data"] = singleObsData;
            marker.bindTooltip(
              this.buildDataTooltip(singleObsData.value.reftime),
              {
                direction: "top",
                offset: [3, -8],
              }
            );
          }
          markers.push(marker);
        }
      } else {
        icon = L.divIcon({
          html: '<i class="fa fa-map-marker-alt fa-3x"></i>',
          iconSize: [20, 20],
          className: "mstDivIcon",
        });
        const marker = new L.Marker([s.station.lat, s.station.lon], {
          icon: icon,
        });
        marker.options["station"] = s.station;
        if (s.products) {
          marker.options["data"] = obsData;
        }

        marker.bindTooltip(this.buildTooltipTemplate(s.station), {
          direction: "top",
          offset: [3, -8],
        });
        markers.push(marker);
      }
    });

    if (!onlyStations && data.length > 0) {
      console.log(`min ${min}, max ${max}`);
      this.obsService.min = min;
      this.obsService.max = max;
      this.buildLegend(product, min, max);
    } else {
      this.legend.remove();
    }

    this.markerClusterData = markers;
    this.markerClusterGroup.addLayers(markers);

    this.fitBounds();
  }

  private buildTooltipTemplate(station: Station) {
    let ident = station.ident || "";
    let altitude = station.altitude || "";
    const template =
      `<ul class="p-1 m-0"><li><b>Network</b>: ${station.network}</li>` +
      ident +
      `<li><b>Lat</b>: ${station.lat}</li>` +
      `<li><b>Lon</b>: ${station.lon}</li>` +
      altitude +
      `</ul>`;
    return template;
  }

  private buildDataTooltip(reftime: string) {
    const template =
      `<ul class="p-1 m-0">
                <li>${reftime}</li>` + `</ul>`;
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
      for (let i = 0; i < COLORS.length; i++) {
        let grade = min + halfDelta * (i * 2 + 1);
        div.innerHTML +=
          '<i style="background:#' +
          service.getColor(grade, min, max) +
          '"></i><span>' +
          // (grade*scale+offset).toPrecision(5).replace(/\.?0+$/,"")
          Math.floor(grade * scale + offset) +
          "</span><br>";
      }
      return div;
    };
    this.legend.addTo(this.map);
  }
}
