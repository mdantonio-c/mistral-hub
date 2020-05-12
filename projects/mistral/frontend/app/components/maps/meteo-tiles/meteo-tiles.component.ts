import {Component, OnInit} from '@angular/core';
import * as moment from 'moment';
import * as L from 'leaflet';
import 'leaflet-timedimension/dist/leaflet.timedimension.src.js';
import 'leaflet-timedimension/examples/js/extras/leaflet.timedimension.tilelayer.portus.js';

declare module 'leaflet' {
    var timeDimension: any;
}

const MAP_CENTER = [41.879966, 12.280000];
const TILES_PATH = 'resources/tiles/00-lm5/t2m-t2m';

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
        maxZoom: 10,
        minZoom: 3
    });

    mlight = L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 10,
        minZoom: 3,
        id: 'mapbox.light'
    });

    darkmatter = L.tileLayer('https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        subdomains: 'abcd',
        maxZoom: 10,
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
            L.tileLayer(`${TILES_PATH}/{d}{h}/{z}/{x}/{y}.png`, {
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
    }
}
