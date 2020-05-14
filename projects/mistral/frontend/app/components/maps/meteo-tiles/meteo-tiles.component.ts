import {Component, OnInit} from '@angular/core';
import {environment} from '@rapydo/../environments/environment';
import * as moment from 'moment';
import * as L from 'leaflet';
import 'leaflet-timedimension/dist/leaflet.timedimension.src.js';
import 'leaflet-timedimension/examples/js/extras/leaflet.timedimension.tilelayer.portus.js';

declare module 'leaflet' {
    var timeDimension: any;
}

const MAP_CENTER = [41.879966, 12.280000];
const TILES_PATH = environment.production ? 'resources/tiles/00-lm5' : 'app/custom/assets/images/tiles/00-lm5';

@Component({
    selector: 'app-meteo-tiles',
    templateUrl: './meteo-tiles.component.html',
    styleUrls: ['./meteo-tiles.component.css']
})
export class MeteoTilesComponent implements OnInit {
    private startDate;
    private endDate;
    options = {};
    layersControl = {};
    map: L.Map;

    // Map layers
    osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 5,
        minZoom: 3
    });

    mlight = L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 5,
        minZoom: 3,
        id: 'mapbox.light'
    });

    darkmatter = L.tileLayer('https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        subdomains: 'abcd',
        maxZoom: 5,
        minZoom: 3
    });

    constructor() {
        this.startDate = moment.utc().format('YYYY-MM-DD');  //"2020-05-11";
        this.endDate = moment.utc().add(3, 'days').format('YYYY-MM-DD');
        // Set the initial set of displayed layers (we could also use the leafletLayers input binding for this)
        this.options = {
            layers: [
                this.mlight
                //this.t2m_time
            ],
            zoom: 5,
            center: L.latLng([46.879966, 11.726909]),
            timeDimension: true,
            timeDimensionOptions: {
                timeInterval: `${this.startDate}/${this.endDate}`,
                period: "PT1H"
            },
            timeDimensionControl: true,
        };
    }

    ngOnInit() {
        // Temperature 2 meters
        let t2m = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/t2m-t2m/{d}{h}/{z}/{x}/{y}.png`, {
                minZoom: 3,
                maxZoom: 5,
                opacity: 0.6,
                // bounds: [[25.0, -25.0], [50.0, 47.0]],
            }), {});
        // Total precipitation 3h
        let prec3tp = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/prec3-tp/{d}{h}/{z}/{x}/{y}.png`, {
                minZoom: 3,
                maxZoom: 5,
                tms: false,
                opacity: 0.6,
                // bounds: [[25.0, -25.0], [50.0, 47.0]],
            }), {});
        // Total precipitation 6h
        let prec6tp = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/prec6-tp/{d}{h}/{z}/{x}/{y}.png`, {
                minZoom: 3,
                maxZoom: 5,
                tms: false,
                opacity: 0.6,
                // bounds: [[25.0, -25.0], [50.0, 47.0]],
            }), {});
        // Snowfall 3h
        let sf3 = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/snow3-snow/{d}{h}/{z}/{x}/{y}.png`, {
                minZoom: 3,
                maxZoom: 5,
                tms: false,
                opacity: 0.6,
                // bounds: [[25.0, -25.0], [50.0, 47.0]],
            }), {});
        // Snowfall 6h
        let sf6 = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/snow6-snow/{d}{h}/{z}/{x}/{y}.png`, {
                minZoom: 3,
                maxZoom: 5,
                tms: false,
                opacity: 0.6,
                // bounds: [[25.0, -25.0], [50.0, 47.0]],
            }), {});
        // Relative humidity
        let rh = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/humidity-r/{d}{h}/{z}/{x}/{y}.png`, {
                minZoom: 3,
                maxZoom: 5,
                tms: false,
                //opacity: 0.6,
                bounds: [[25.0, -25.0], [50.0, 47.0]],
            }), {});
        // Cloud - High
        let hcc = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/cloud_hml-hcc/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 3,
            maxZoom: 5,
            tms: false,
            //opacity: 0.6,
            bounds: [[25.0, -25.0], [50.0, 47.0]],
        }), {});
        // Cloud - Medium
        let mcc = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/cloud_hml-mcc/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 3,
            maxZoom: 5,
            tms: false,
            //opacity: 0.6,
            bounds: [[25.0, -25.0], [50.0, 47.0]],
        }), {});
        // Cloud - Low
        let lcc = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/cloud_hml-lcc/{d}{h}/{z}/{x}/{y}.png`, {
            minZoom: 3,
            maxZoom: 5,
            tms: false,
            opacity: 0.9,
            bounds: [[25.0, -25.0], [50.0, 47.0]],
        }), {});


        this.layersControl = {
            baseLayers: {
                'Openstreet Map': this.osm,
                'Carto Map': this.darkmatter,
                'Mapbox Map': this.mlight
            },
            overlays: {
                'Temperature at 2 meters': t2m,
                'Total Precipitation (3h)': prec3tp,
                'Total Precipitation (6h)': prec6tp,
                'Snowfall (3h)': sf3,
                'Snowfall (6h)': sf6,
                'Relative Humidity': rh,
                'High Cloud': hcc,
                'Medium Cloud': mcc,
                'Low Cloud': lcc
              }
        };
        this.options['layers'].push(t2m);
    }

    onMapReady(map: L.Map) {
        this.map = map;
        console.log('on map ready!');

        const legend_t2m = new L.Control({ position: "bottomright" });
        legend_t2m.onAdd = map => {
          let div = L.DomUtil.create("div", "legend"),
          colors = ["#ffcc00","#ff9900","#ff6600","#ff0000","#cc0000","#990000","#660000","#660066","#990099","#cc00cc","#ff00ff","#bf00ff","#7200ff",
            "#0000ff","#0059ff","#008cff","#00bfff","#00ffff","#00e5cc","#00cc7f","#00b200","#7fcc00","#cce500","#ffff00","#ffcc00","#ff9900",
            "#ff6600","#ff0000","#cc0000","#990000","#660000","#660066","#990099","#cc00cc","#ff00ff","#bf00ff","#7200ff","#ffcc00","#ff9900"],
          labels = [ "-30", " ", "-26", " ", "-22", "", "-18", " ", "-14", " ",
            "-10", " ", "-6", " ", "-2", " ", "2", " ", "6", " ", "10", " ", "14", " ", "18",
            "", "22", " ", "26", " ", "30", " ", "34", " ", "38", " ", "42", " ", "46"];
          div.style.clear ="unset";
          div.innerHTML += "<h6>T [°C]</h6>";
          for (var i = 0; i < labels.length; i++) {
            console.log(i);
            div.innerHTML += '<i style="background:' + colors[i]  + '"></i><span>'+labels[i]+'</span><br>';
          }
          return div;
        };

        const legend_prec3tp = new L.Control({ position: "bottomright" });
        legend_prec3tp.onAdd = map => {
          let div = L.DomUtil.create("div", "legend"),
          colors = ["rgba(0,204,255,0.2)", "rgba(0,255,255,0.25)", "rgba(48, 196, 135, 0.30)", "rgba(128, 255, 0, 0.35)", "rgba(225, 227, 22, 0.40)",
            "rgba(255,255,128, 0.45)", "rgba(255,255,0, 0.5)", "rgba(255,200,0, 0.55)", "rgba(255,185,67, 0.6)", "rgba(255,115,0, 0.65)",
            "rgba(255,0,0, 0.65)", "rgba(204,0,0, 0.7)", "rgba(223,83,121, 0.75)", "rgba(242,166,242,0.8)", "rgba(217,140,217,0.85)",
            "rgba(191,128,217,0.9)", "rgba(153,153,255,0.95)", "rgba(0,153,255,1)"],
            labels = ["1","2","3","4","5","6","8","10","15","20","25","30","40","50","75","100","200","300"];
          div.style.clear ="unset";
          div.innerHTML += "<h6>Prp [mm]</h6>";
          for (var i = 0; i < colors.length; i++) {
            div.innerHTML += '<i style="background:' + colors[i]  + '"></i><span>'+labels[i]+'</span><br>';
          }
          return div;
        };

        const legend_prec6tp = new L.Control({ position: "bottomright" });
        legend_prec6tp.onAdd = map => {
          let div = L.DomUtil.create("div", "legend"),
          colors = ["rgba(0,204,255,0.2)", "rgba(0,255,255,0.25)", "rgba(48, 196, 135, 0.30)", "rgba(128, 255, 0, 0.35)", "rgba(225, 227, 22, 0.40)",
            "rgba(255,255,128, 0.45)", "rgba(255,255,0, 0.5)", "rgba(255,200,0, 0.55)", "rgba(255,185,67, 0.6)", "rgba(255,115,0, 0.65)",
            "rgba(255,0,0, 0.65)", "rgba(204,0,0, 0.7)", "rgba(223,83,121, 0.75)", "rgba(242,166,242,0.8)", "rgba(217,140,217,0.85)",
            "rgba(191,128,217,0.9)", "rgba(153,153,255,0.95)", "rgba(0,153,255,1)"],
          labels = ["0.5", " ", " 2.0", " ", "4.0", " ", "6.0", " ", "10.0", " ",
            "20.0", " ", "30.0", " ", "50.0", " ", "100.0", " ", "300.0"];
          div.style.clear ="unset";
          div.innerHTML += "<h6>Prp [mm]</h6>";
          for (var i = 0; i < colors.length; i++) {
            div.innerHTML += '<i style="background:' + colors[i]  + '"></i><span>'+labels[i]+'</span><br>';
          }
          return div;
        };

        const legend_sf3 = new L.Control({ position: "bottomright" });
        legend_sf3.onAdd = map => {
          let div = L.DomUtil.create("div", "legend"),
          colors = ["rgba(0,204,255,0.2)", "rgba(0,255,255,0.25)", "rgba(48, 196, 135, 0.30)", "rgba(128, 255, 0, 0.35)", "rgba(225, 227, 22, 0.40)", "rgba(255,255,128, 0.45)", "rgba(255,255,0, 0.5)", "rgba(255,200,0, 0.55)", "rgba(255,185,67, 0.6)", "rgba(255,115,0, 0.65)", "rgba(255,0,0, 0.65)", "rgba(204,0,0, 0.7)", "rgba(223,83,121, 0.75)", "rgba(242,166,242,0.8)", "rgba(217,140,217,0.85)", "rgba(191,128,217,0.9)", "rgba(153,153,255,0.95)", "rgba(0,153,255,1)"],
          labels = ["0.1", "0.25", "0.5", "1.0", "1.5", "2.0", "2.5", "3.0", "4.0", "5.0", "7.5", "10.0", "15.0", "20.0", "25.0", "30.0", "40.0", "50.0", "60.0", "80.0"];
          div.style.clear ="unset";
          div.innerHTML += "<h6>Snow [cm]</h6>";
          for (var i = 0; i < colors.length; i++) {
            div.innerHTML += '<i style="background:' + colors[i]  + '"></i><span>'+labels[i]+'</span><br>';
          }
          return div;
        };

        const legend_sf6 = new L.Control({ position: "bottomright" });
        legend_sf6.onAdd = map => {
          let div = L.DomUtil.create("div", "legend"),
          colors = ["rgba(0,204,255,0.2)", "rgba(0,255,255,0.25)", "rgba(48, 196, 135, 0.30)", "rgba(128, 255, 0, 0.35)", "rgba(225, 227, 22, 0.40)", "rgba(255,255,128, 0.45)", "rgba(255,255,0, 0.5)", "rgba(255,200,0, 0.55)", "rgba(255,185,67, 0.6)", "rgba(255,115,0, 0.65)", "rgba(255,0,0, 0.65)", "rgba(204,0,0, 0.7)", "rgba(223,83,121, 0.75)", "rgba(242,166,242,0.8)", "rgba(217,140,217,0.85)", "rgba(191,128,217,0.9)", "rgba(153,153,255,0.95)", "rgba(0,153,255,1)"],
          labels = ["0.1", "0.25", "0.5", "1.0", "1.5", "2.0", "2.5", "3.0", "4.0", "5.0", "7.5", "10.0", "15.0", "20.0", "25.0", "30.0", "40.0", "50.0", "60.0", "80.0"];
          div.style.clear ="unset";
          div.innerHTML += "<h6>Snow [cm]</h6>";
          for (var i = 0; i < colors.length; i++) {
            div.innerHTML += '<i style="background:' + colors[i]  + '"></i><span>'+labels[i]+'</span><br>';
          }
          return div;
        };

        const legend_rh = new L.Control({ position: "bottomright" });
        legend_rh.onAdd = map => {
          let div = L.DomUtil.create("div", "legend"),
          //colors = ["rgba(0,255,255,1)","rgba(51,255,255,0.8)","rgba(102,255,255,0.6)","rgba(153,255,255,0.4)","rgba(204,255,255,0.2)","rgba(255,255,255,0.0)"],
          colors = ["rgba(255,255,255,0.0)","rgba(204,255,255,0.2)","rgba(153,255,255,0.4)","rgba(102,255,255,0.6)","rgba(51,255,255,0.8)","rgba(0,255,255,1)"],
          labels = ["60","70","80","90","100","110"];
          div.style.clear ="unset";
          div.innerHTML += "<h6>RH [%]</h6>";
          for (var i = 0; i < labels.length; i++) {
            div.innerHTML += '<i style="background:' + colors[i]  + '"></i><span>'+labels[i]+'</span><br>';
          }
          return div;
        };

        const legend_hcc = new L.Control({ position: "bottomright" });
        legend_hcc.onAdd = map => {
          let div = L.DomUtil.create("div", "legend"),
          colors = ["rgba(0,188,0,0.0)","rgba(0,188,0,0.08)","rgba(0,188,0,0.16)","rgba(0,188,0,0.24)","rgba(0,188,0,0.32)","rgba(0,188,0,0.4)"],
          labels = ["50", "60", "70", "80", "90", "100"];
          div.style.clear ="unset";
          div.innerHTML += "<h6>Cloud [%]</h6>";
          for (var i = 0; i < colors.length; i++) {
            div.innerHTML += '<i style="background:' + colors[i]  + '"></i><span>'+labels[i]+'</span><br>';
          }
          return div;
        };

        const legend_mcc = new L.Control({ position: "bottomright" });
        legend_mcc.onAdd = map => {
          let div = L.DomUtil.create("div", "legend"),
          colors = ["rgba(0,0,255,0.0)","rgba(0,0,255,0.08)","rgba(0,0,255,0.16)","rgba(0,0,255,0.24)","rgba(0,0,255,0.32)","rgba(0,0,255,0.4)"],
          labels = ["50", "60", "70", "80", "90", "100"];
          div.style.clear ="unset";
          div.innerHTML += "<h6>Cloud [%]</h6>";
          for (var i = 0; i < colors.length; i++) {
            div.innerHTML += '<i style="background:' + colors[i]  + '"></i><span>'+labels[i]+'</span><br>';
          }
          return div;
        };

        const legend_lcc = new L.Control({ position: "bottomright" });
        legend_lcc.onAdd = map => {
          let div = L.DomUtil.create("div", "legend"),
          colors = ["rgba(255,0,0,0.0)","rgba(255,0,0,0.04)","rgba(255,0,0,0.08)","rgba(255,0,0,0.12)","rgba(255,0,0,0.16)","rgba(255,0,0,0.2)"],
          labels = ["50", "60", "70", "80", "90", "100"];
          div.style.clear ="unset";
          div.innerHTML += "<h6>Cloud [%]</h6>";
          for (var i = 0; i < colors.length; i++) {
            div.innerHTML += '<i style="background:' + colors[i]  + '"></i><span>'+labels[i]+'</span><br>';
          }
          return div;
        };
        legend_t2m.addTo(map);

        map.on('overlayadd', function (event) {
            console.log(event['name']);
            if (event['name'] === 'Temperature at 2 meters') {
                legend_t2m.addTo(map);
            } else if (event['name'] === 'Total Precipitation (3h)') {
                legend_prec3tp.addTo(this);
            } else if (event['name'] === 'Total Precipitation (6h)') {
                legend_prec3tp.addTo(this);
            } else if (event['name'] === 'Snowfall (3h)') {
                legend_sf3.addTo(this);
            } else if (event['name'] === 'Snowfall (6h)') {
                legend_sf6.addTo(this);
            } else if (event['name'] === 'Relative Humidity') {
                legend_rh.addTo(this);
            } else if (event['name'] === 'High Cloud') {
                legend_hcc.addTo(this);
            } else if (event['name'] === 'Medium Cloud') {
                legend_mcc.addTo(this);
            } else if (event['name'] === 'Low Cloud') {
                legend_lcc.addTo(this);
            }
        });
        map.on('overlayremove', function (event) {
            if (event['name'] === 'Temperature at 2 meters') {
                this.removeControl(legend_t2m);
            } else if (event['name'] == 'Total Precipitation (3h)') {
                this.removeControl(legend_prec3tp);
            } else if (event['name'] == 'Total Precipitation (6h)') {
                this.removeControl(legend_prec6tp);
            } else if (event['name'] === 'Snowfall (3h)') {
                this.removeControl(legend_sf3);
            } else if (event['name'] === 'Snowfall (6h)') {
                this.removeControl(legend_sf6);
            } else if (event['name'] === 'Relative Humidity') {
                this.removeControl(legend_rh);
            } else if (event['name'] === 'High Cloud') {
                this.removeControl(legend_hcc);
            } else if (event['name'] === 'High Cloud') {
                this.removeControl(legend_mcc);
            } else if (event['name'] === 'High Cloud') {
                this.removeControl(legend_lcc);
            }
        });
        //
        // const legend_t2m = new L.Control({ position: "bottomright" });
        // legend_t2m.onAdd = map => {
        //   let div = L.DomUtil.create("div", "legend_t2m"),
        //   colorz = ["#ffcc00","#ff9900","#ff6600","#ff0000","#cc0000","#990000","#660000","#660066","#990099","#cc00cc","#ff00ff","#bf00ff","#7200ff",
        //     "#0000ff","#0059ff","#008cff","#00bfff","#00ffff","#00e5cc","#00cc7f","#00b200","#7fcc00","#cce500","#ffff00","#ffcc00","#ff9900",
        //     "#ff6600","#ff0000","#cc0000","#990000","#660000","#660066","#990099","#cc00cc","#ff00ff","#bf00ff","#7200ff","#ffcc00","#ff9900"],
        //   labels = [ "-30", " ", " ", " ", " ", "-20", " ", " ", " ", " ",
        //     "-10", " ", " ", " ", " ", "0", " ", " ", " ", " ", "10", " ", " ", " ", " ",
        //     "20", " ", " ", " ", " ", "30", " ", " ", " ", " ", "40", " ", " ", "46"];
        //   div.style.clear ="unset";
        //   div.innerHTML += "<h6>T [°C]</h6>";
        //   for (var i = 0; i < colorz.length; i++) {
        //     div.innerHTML += '<i style="background:' + colorz[i]  + '"></i><span>'+labels[i]+'</span><br>';
        //   }
        //   return div;
        // };
        // legend_t2m.addTo(map)
        //
        //
        // const legend_t2m = new L.Control({ position: "bottomright" });
        // legend_t2m.onAdd = map => {
        //   let div = L.DomUtil.create("div", "legend_t2m"),
        //   colorz = ["#ffcc00","#ff9900","#ff6600","#ff0000","#cc0000","#990000","#660000","#660066","#990099","#cc00cc","#ff00ff","#bf00ff","#7200ff",
        //     "#0000ff","#0059ff","#008cff","#00bfff","#00ffff","#00e5cc","#00cc7f","#00b200","#7fcc00","#cce500","#ffff00","#ffcc00","#ff9900",
        //     "#ff6600","#ff0000","#cc0000","#990000","#660000","#660066","#990099","#cc00cc","#ff00ff","#bf00ff","#7200ff","#ffcc00","#ff9900"],
        //   labels = [ "-30", " ", " ", " ", " ", "-20", " ", " ", " ", " ",
        //     "-10", " ", " ", " ", " ", "0", " ", " ", " ", " ", "10", " ", " ", " ", " ",
        //     "20", " ", " ", " ", " ", "30", " ", " ", " ", " ", "40", " ", " ", "46"];
        //   div.style.clear ="unset";
        //   div.innerHTML += "<h6>T [°C]</h6>";
        //   for (var i = 0; i < colorz.length; i++) {
        //     div.innerHTML += '<i style="background:' + colorz[i]  + '"></i><span>'+labels[i]+'</span><br>';
        //   }
        //   return div;
        // };
        // legend_t2m.addTo(map)
        //
        // const legend_t2m = new L.Control({ position: "bottomright" });
        // legend_t2m.onAdd = map => {
        //   let div = L.DomUtil.create("div", "legend_t2m"),
        //   colorz = ["#ffcc00","#ff9900","#ff6600","#ff0000","#cc0000","#990000","#660000","#660066","#990099","#cc00cc","#ff00ff","#bf00ff","#7200ff",
        //     "#0000ff","#0059ff","#008cff","#00bfff","#00ffff","#00e5cc","#00cc7f","#00b200","#7fcc00","#cce500","#ffff00","#ffcc00","#ff9900",
        //     "#ff6600","#ff0000","#cc0000","#990000","#660000","#660066","#990099","#cc00cc","#ff00ff","#bf00ff","#7200ff","#ffcc00","#ff9900"],
        //   labels = [ "-30", " ", " ", " ", " ", "-20", " ", " ", " ", " ",
        //     "-10", " ", " ", " ", " ", "0", " ", " ", " ", " ", "10", " ", " ", " ", " ",
        //     "20", " ", " ", " ", " ", "30", " ", " ", " ", " ", "40", " ", " ", "46"];
        //   div.style.clear ="unset";
        //   div.innerHTML += "<h6>T [°C]</h6>";
        //   for (var i = 0; i < colorz.length; i++) {
        //     div.innerHTML += '<i style="background:' + colorz[i]  + '"></i><span>'+labels[i]+'</span><br>';
        //   }
        //   return div;
        // };
        // legend_t2m.addTo(map)

    }
}
