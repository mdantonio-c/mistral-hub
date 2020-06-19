import {Component} from '@angular/core';
import {environment} from '@rapydo/../environments/environment';
import * as moment from 'moment';
import * as L from 'leaflet';
import 'leaflet-timedimension/dist/leaflet.timedimension.src.js';
import 'leaflet-timedimension/examples/js/extras/leaflet.timedimension.tilelayer.portus.js';
import {TilesService} from "./services/tiles.service";
import {NotificationService} from '@rapydo/services/notification';
import {NgxSpinnerService} from 'ngx-spinner';

declare module 'leaflet' {
    var timeDimension: any;
}

// const MAP_CENTER = [41.879966, 12.280000];
const TILES_PATH = environment.production ? 'resources/tiles/00-lm5' : 'app/custom/assets/images/tiles/00-lm5';

@Component({
    selector: 'app-meteo-tiles',
    templateUrl: './meteo-tiles.component.html',
    styleUrls: ['./meteo-tiles.component.css']
})
export class MeteoTilesComponent {

    readonly DEFAULT_PRODUCT = 'Temperature at 2 meters';

    map: L.Map;

    LAYER_OSM = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 5,
        minZoom: 3
    });
    LAYER_MAPBOX_LIGHT = L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
        id: 'mapbox.light',
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 5,
        minZoom: 3
    });
    LAYER_DARKMATTER = L.tileLayer('https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 5,
        minZoom: 3
    });

    // Values to bind to Leaflet Directive
    layersControl = {
        baseLayers: {
            'Openstreet Map': this.LAYER_OSM,
            'Carto Map': this.LAYER_DARKMATTER,
            'Mapbox Map': this.LAYER_MAPBOX_LIGHT
        }
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
            }
        }
    };

    constructor(private tilesService: TilesService,
                private notify: NotificationService,
                private spinner: NgxSpinnerService) {

        // set the initial set of displayed layers
        this.options['layers'] = [this.LAYER_MAPBOX_LIGHT];
    }

    onMapReady(map: L.Map) {
        // console.log('Map ready', map);
        this.map = map;
        this.initLegends(map);
        this.spinner.show();
        this.tilesService.getLastRun('lm5', '00').subscribe(runAvailable => {
            // runAvailable.reftime : 2020051100
            console.log('Available Run', runAvailable);
            let reftime = runAvailable.reftime;
            let refdate = reftime.substr(0, 8);

            // set time
            let startTime = moment.utc(reftime, "YYYYMMDDHH").toDate();
            // let startTime = new Date(Date.UTC(2020, 4, 11));
            startTime.setUTCHours(0, 0, 0, 0);
            // let endTime = 'PT72H';
            let endTime = moment.utc(reftime, "YYYYMMDDHH").add(3, 'days').toDate();
            console.log(endTime);

            // add time dimension
            let newAvailableTimes = (L as any).TimeDimension.Util.explodeTimeRange(startTime, endTime, 'PT1H');
            (map as any).timeDimension.setAvailableTimes(newAvailableTimes, 'replace');
            (map as any).timeDimension.setCurrentTime(startTime);

            this.setOverlaysToMap(refdate);

            // add default layer
            let tm2m: L.Layer = this.layersControl['overlays'][this.DEFAULT_PRODUCT];
            tm2m.addTo(this.map);

            // TODO trigger event to add proper legend
            //legend_t2m.addTo(map);
            // new Event('overlayadd', {name: 'Temperature at 2 meters'});
            //new CustomEvent('overlayadd', {name: DEFAULT_PRODUCT});

        }, error => {
            this.notify.showError(error);
        }).add(() => {
            this.spinner.hide();
        });
    }

    private setOverlaysToMap(refdate: string) {
        // Temperature 2 meters Time Layer
        let t2m = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${TILES_PATH}/t2m-t2m/${refdate}{h}/{z}/{x}/{y}.png`, {
                minZoom: 3,
                maxZoom: 5,
                tms: false,
                opacity: 0.6,
                // bounds: [[25.0, -25.0], [50.0, 47.0]],
            }), {}),
            // Total precipitation 3h Time Layer
            prec3tp = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${TILES_PATH}/prec3-tp/${refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 3,
                    maxZoom: 5,
                    tms: false,
                    opacity: 0.6,
                    // bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Total precipitation 6h Time Layer
            prec6tp = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${TILES_PATH}/prec6-tp/${refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 3,
                    maxZoom: 5,
                    tms: false,
                    opacity: 0.6,
                    // bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Snowfall 3h Time Layer
            sf3 = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${TILES_PATH}/snow3-snow/${refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 3,
                    maxZoom: 5,
                    tms: false,
                    opacity: 0.6,
                    // bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Snowfall 6h Time Layer
            sf6 = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${TILES_PATH}/snow6-snow/${refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 3,
                    maxZoom: 5,
                    tms: false,
                    opacity: 0.6,
                    // bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Relative humidity Time Layer
            rh = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${TILES_PATH}/humidity-r/${refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 3,
                    maxZoom: 5,
                    tms: false,
                    //opacity: 0.6,
                    bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // High Cloud Time Layer
            hcc = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${TILES_PATH}/cloud_hml-hcc/${refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 3,
                    maxZoom: 5,
                    tms: false,
                    //opacity: 0.6,
                    bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Medium Cloud Time Layer
            mcc = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${TILES_PATH}/cloud_hml-mcc/${refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 3,
                    maxZoom: 5,
                    tms: false,
                    //opacity: 0.6,
                    bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Low Cloud Time Layer
            lcc = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${TILES_PATH}/cloud_hml-lcc/${refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 3,
                    maxZoom: 5,
                    tms: false,
                    opacity: 0.9,
                    bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {});

        this.layersControl['overlays'] = {
            'Temperature at 2 meters': t2m,
            'Total Precipitation (3h)': prec3tp,
            'Total Precipitation (6h)': prec6tp,
            'Snowfall (3h)': sf3,
            'Snowfall (6h)': sf6,
            'Relative Humidity': rh,
            'High Cloud': hcc,
            'Medium Cloud': mcc,
            'Low Cloud': lcc
        };
    }

    private static createLegend(title: string, colors: string[], labels: string[]) {
        let div = L.DomUtil.create("div", "legend");
        div.style.clear = "unset";
        div.innerHTML += `<h6>${title}</h6>`;
        for (let i = 0; i < labels.length; i++) {
            div.innerHTML += '<i style="background:' + colors[i] + '"></i><span>' + labels[i] + '</span><br>';
        }
        return div;
    }

    private initLegends(map: L.Map) {
        const legend_t2m = new L.Control({position: "bottomleft"});
        legend_t2m.onAdd = () => {
            let colors = ["#ffcc00", "#ff9900", "#ff6600", "#ff0000", "#cc0000", "#990000", "#660000", "#660066", "#990099", "#cc00cc", "#ff00ff", "#bf00ff", "#7200ff",
                    "#0000ff", "#0059ff", "#008cff", "#00bfff", "#00ffff", "#00e5cc", "#00cc7f", "#00b200", "#7fcc00", "#cce500", "#ffff00", "#ffcc00", "#ff9900",
                    "#ff6600", "#ff0000", "#cc0000", "#990000", "#660000", "#660066", "#990099", "#cc00cc", "#ff00ff", "#bf00ff", "#7200ff", "#ffcc00", "#ff9900"],
                labels = ["-30", " ", "-26", " ", "-22", "", "-18", " ", "-14", " ",
                    "-10", " ", "-6", " ", "-2", " ", "2", " ", "6", " ", "10", " ", "14", " ", "18",
                    "", "22", " ", "26", " ", "30", " ", "34", " ", "38", " ", "42", " ", "46"];
            return MeteoTilesComponent.createLegend('T [°C]', colors, labels);
        };

        const legend_prec3tp = new L.Control({position: "bottomright"});
        legend_prec3tp.onAdd = () => {
            let colors = ["rgba(0,204,255,0.2)", "rgba(0,255,255,0.25)", "rgba(48, 196, 135, 0.30)", "rgba(128, 255, 0, 0.35)", "rgba(225, 227, 22, 0.40)",
                    "rgba(255,255,128, 0.45)", "rgba(255,255,0, 0.5)", "rgba(255,200,0, 0.55)", "rgba(255,185,67, 0.6)", "rgba(255,115,0, 0.65)",
                    "rgba(255,0,0, 0.65)", "rgba(204,0,0, 0.7)", "rgba(223,83,121, 0.75)", "rgba(242,166,242,0.8)", "rgba(217,140,217,0.85)",
                    "rgba(191,128,217,0.9)", "rgba(153,153,255,0.95)", "rgba(0,153,255,1)"],
                labels = ["1", "2", "3", "4", "5", "6", "8", "10", "15", "20", "25", "30", "40", "50", "75", "100", "200", "300"];
            return MeteoTilesComponent.createLegend('Prp [mm]', colors, labels);
        };

        const legend_prec6tp = new L.Control({position: "bottomright"});
        legend_prec6tp.onAdd = () => {
            let colors = ["rgba(0,204,255,0.2)", "rgba(0,255,255,0.25)", "rgba(48, 196, 135, 0.30)", "rgba(128, 255, 0, 0.35)", "rgba(225, 227, 22, 0.40)",
                    "rgba(255,255,128, 0.45)", "rgba(255,255,0, 0.5)", "rgba(255,200,0, 0.55)", "rgba(255,185,67, 0.6)", "rgba(255,115,0, 0.65)",
                    "rgba(255,0,0, 0.65)", "rgba(204,0,0, 0.7)", "rgba(223,83,121, 0.75)", "rgba(242,166,242,0.8)", "rgba(217,140,217,0.85)",
                    "rgba(191,128,217,0.9)", "rgba(153,153,255,0.95)", "rgba(0,153,255,1)"],
                labels = ["0.5", " ", " 2.0", " ", "4.0", " ", "6.0", " ", "10.0", " ",
                    "20.0", " ", "30.0", " ", "50.0", " ", "100.0", " ", "300.0"];
            return MeteoTilesComponent.createLegend('Prp [mm]', colors, labels);
        };

        const legend_sf3 = new L.Control({position: "bottomright"});
        legend_sf3.onAdd = () => {
            let colors = ["rgba(0,204,255,0.2)", "rgba(0,255,255,0.25)", "rgba(48, 196, 135, 0.30)", "rgba(128, 255, 0, 0.35)", "rgba(225, 227, 22, 0.40)", "rgba(255,255,128, 0.45)", "rgba(255,255,0, 0.5)", "rgba(255,200,0, 0.55)", "rgba(255,185,67, 0.6)", "rgba(255,115,0, 0.65)", "rgba(255,0,0, 0.65)", "rgba(204,0,0, 0.7)", "rgba(223,83,121, 0.75)", "rgba(242,166,242,0.8)", "rgba(217,140,217,0.85)", "rgba(191,128,217,0.9)", "rgba(153,153,255,0.95)", "rgba(0,153,255,1)"],
                labels = ["0.1", "0.25", "0.5", "1.0", "1.5", "2.0", "2.5", "3.0", "4.0", "5.0", "7.5", "10.0", "15.0", "20.0", "25.0", "30.0", "40.0", "50.0", "60.0", "80.0"];
            return MeteoTilesComponent.createLegend('Snow [cm]', colors, labels);
        };

        const legend_sf6 = legend_sf3;

        const legend_rh = new L.Control({position: "bottomright"});
        legend_rh.onAdd = () => {
            let //colors = ["rgba(0,255,255,1)","rgba(51,255,255,0.8)","rgba(102,255,255,0.6)","rgba(153,255,255,0.4)","rgba(204,255,255,0.2)","rgba(255,255,255,0.0)"],
                colors = ["rgba(255,255,255,0.0)", "rgba(204,255,255,0.2)", "rgba(153,255,255,0.4)", "rgba(102,255,255,0.6)", "rgba(51,255,255,0.8)", "rgba(0,255,255,1)"],
                labels = ["60", "70", "80", "90", "100", "110"];
            return MeteoTilesComponent.createLegend('RH [%]', colors, labels);
        };

        const legend_hcc = new L.Control({position: "bottomright"});
        legend_hcc.onAdd = () => {
            let colors = ["rgba(0,188,0,0.0)", "rgba(0,188,0,0.08)", "rgba(0,188,0,0.16)", "rgba(0,188,0,0.24)", "rgba(0,188,0,0.32)", "rgba(0,188,0,0.4)"],
                labels = ["50", "60", "70", "80", "90", "100"];
            return MeteoTilesComponent.createLegend('Cloud [%]', colors, labels);
        };

        const legend_mcc = new L.Control({position: "bottomright"});
        legend_mcc.onAdd = () => {
            let colors = ["rgba(0,0,255,0.0)", "rgba(0,0,255,0.08)", "rgba(0,0,255,0.16)", "rgba(0,0,255,0.24)", "rgba(0,0,255,0.32)", "rgba(0,0,255,0.4)"],
                labels = ["50", "60", "70", "80", "90", "100"];
            return MeteoTilesComponent.createLegend('Cloud [%]', colors, labels);
        };

        const legend_lcc = new L.Control({position: "bottomright"});
        legend_lcc.onAdd = () => {
            let colors = ["rgba(255,0,0,0.0)", "rgba(255,0,0,0.04)", "rgba(255,0,0,0.08)", "rgba(255,0,0,0.12)", "rgba(255,0,0,0.16)", "rgba(255,0,0,0.2)"],
                labels = ["50", "60", "70", "80", "90", "100"];
            return MeteoTilesComponent.createLegend('Cloud [%]', colors, labels);
        };

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
            } else if (event['name'] === 'Medium Cloud') {
                this.removeControl(legend_mcc);
            } else if (event['name'] === 'Low Cloud') {
                this.removeControl(legend_lcc);
            }
        });
    }
}
