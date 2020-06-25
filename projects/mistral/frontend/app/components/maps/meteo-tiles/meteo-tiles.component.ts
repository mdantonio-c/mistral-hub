import {Component} from '@angular/core';
import {environment} from '@rapydo/../environments/environment';
import * as moment from 'moment';
import * as L from 'leaflet';
import 'leaflet-timedimension/dist/leaflet.timedimension.src.js';
import 'leaflet-timedimension/examples/js/extras/leaflet.timedimension.tilelayer.portus.js';
import {TilesService} from "./services/tiles.service";
import {NotificationService} from '@rapydo/services/notification';
import {NgxSpinnerService} from 'ngx-spinner';
import {LegendConfig, LEGEND_DATA} from "./services/data";

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
    readonly LEGEND_POSITION = 'bottomleft';

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

            this.initLegends(map);

        }, error => {
            this.notify.showError(error);
	}).add(() => {
            map.invalidateSize();
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

    private createLegendControl(id: string): L.Control {
        let config: LegendConfig = LEGEND_DATA.find(x => x.id === id);
        if (!config) {
            this.notify.showError('Bad legend configuration');
            return;
        }
        const legend = new L.Control({position: this.LEGEND_POSITION});
        legend.onAdd = () => {
            let div = L.DomUtil.create("div", "legend");
            div.style.clear = "unset";
            div.innerHTML += `<h6>${config.title}</h6>`;
            for (let i = 0; i < config.labels.length; i++) {
                div.innerHTML += '<i style="background:' + config.colors[i] + '"></i><span>' + config.labels[i] + '</span><br>';
            }
            return div;
        };
        return legend;
    }

    private initLegends(map: L.Map) {
        let layers = this.layersControl['overlays'];
        const legend_t2m = this.createLegendControl('tm2'),
            legend_prec3tp = this.createLegendControl('prec3tp'),
            legend_prec6tp = this.createLegendControl('prec6tp'),
            legend_sf = this.createLegendControl('sf3'),
            legend_rh = this.createLegendControl('rh'),
            legend_hcc = this.createLegendControl('hcc'),
            legend_mcc = this.createLegendControl('mcc'),
            legend_lcc = this.createLegendControl('lcc');

        map.on('overlayadd', function (event) {
            if (event['name'] === 'Temperature at 2 meters') {
                legend_t2m.addTo(map);
            } else if (event['name'] === 'Total Precipitation (3h)') {
                legend_prec3tp.addTo(this);
            } else if (event['name'] === 'Total Precipitation (6h)') {
                legend_prec6tp.addTo(this);
            } else if (event['name'] === 'Snowfall (3h)' || event['name'] === 'Snowfall (6h)') {
                legend_sf.addTo(this);
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
            } else if (event['name'] === 'Total Precipitation (3h)') {
                this.removeControl(legend_prec3tp);
            } else if (event['name'] === 'Total Precipitation (6h)') {
                this.removeControl(legend_prec6tp);
            } else if (event['name'] === 'Snowfall (3h)' && !map.hasLayer(layers['Snowfall (6h)'])) {
                this.removeControl(legend_sf);
            } else if (event['name'] === 'Snowfall (6h)' && !map.hasLayer(layers['Snowfall (3h)'])) {
                this.removeControl(legend_sf);
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

        // add default legend to the map
        legend_t2m.addTo(map);
    }
}
