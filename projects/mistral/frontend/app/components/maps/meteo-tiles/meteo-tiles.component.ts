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
const TILES_PATH = environment.production ? 'resources/tiles' : 'app/custom/assets/images/tiles';

@Component({
    selector: 'app-meteo-tiles',
    templateUrl: './meteo-tiles.component.html',
    styleUrls: ['./meteo-tiles.component.css']
})
export class MeteoTilesComponent {

    readonly DEFAULT_PRODUCT = 'Temperature at 2 meters';
    readonly DEFAULT_RESOLUTION = 'lm5'
    readonly LEGEND_POSITION = 'bottomleft';

    map: L.Map;
    resolution: string ;
    private refdate: string;
    private run: string;

    LAYER_OSM = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 7,
        minZoom: 5
    });
    LAYER_MAPBOX_LIGHT = L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
        id: 'mapbox.light',
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 7,
        minZoom: 5
    });
    LAYER_DARKMATTER = L.tileLayer('https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 7,
        minZoom: 5
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
        this.resolution = this.DEFAULT_RESOLUTION;
    }

    onMapReady(map: L.Map) {
        // console.log('Map ready', map);
        this.map = map;
        this.spinner.show();
        this.tilesService.getLastRun('lm5', '00').subscribe(runAvailable => {
            // runAvailable.reftime : 2020051100
            console.log('Available Run', runAvailable);
            let reftime = runAvailable.reftime;
            this.refdate = reftime.substr(0, 8);
            this.run = reftime.substr(8, 2);

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

            this.setOverlaysToMap();

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

    private setOverlaysToMap() {
        let baseUrl = `${TILES_PATH}/${this.run}-${this.resolution}`
        // Temperature 2 meters Time Layer
        let t2m = L.timeDimension.layer.tileLayer.portus(
            L.tileLayer(`${baseUrl}/t2m-t2m/${this.refdate}{h}/{z}/{x}/{y}.png`, {
                minZoom: 5,
                maxZoom: 7,
                tms: false,
                opacity: 0.6,
                // bounds: [[25.0, -25.0], [50.0, 47.0]],
            }), {}),
            // Total precipitation 3h Time Layer
            prec3tp = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${baseUrl}/prec3-tp/${this.refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 5,
                    maxZoom: 7,
                    tms: false,
                    opacity: 0.6,
                    // bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Total precipitation 6h Time Layer
            prec6tp = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${baseUrl}/prec6-tp/${this.refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 5,
                    maxZoom: 7,
                    tms: false,
                    opacity: 0.6,
                    // bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Snowfall 3h Time Layer
            sf3 = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${baseUrl}/snow3-snow/${this.refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 5,
                    maxZoom: 7,
                    tms: false,
                    opacity: 0.6,
                    // bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Snowfall 6h Time Layer
            sf6 = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${baseUrl}/snow6-snow/${this.refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 5,
                    maxZoom: 7,
                    tms: false,
                    opacity: 0.6,
                    // bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Relative humidity Time Layer
            rh = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${baseUrl}/humidity-r/${this.refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 5,
                    maxZoom: 7,
                    tms: false,
                    //opacity: 0.6,
                    bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // High Cloud Time Layer
            hcc = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${baseUrl}/cloud_hml-hcc/${this.refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 5,
                    maxZoom: 7,
                    tms: false,
                    //opacity: 0.6,
                    bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Medium Cloud Time Layer
            mcc = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${baseUrl}/cloud_hml-mcc/${this.refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 5,
                    maxZoom: 7,
                    tms: false,
                    //opacity: 0.6,
                    bounds: [[25.0, -25.0], [50.0, 47.0]],
                }), {}),
            // Low Cloud Time Layer
            lcc = L.timeDimension.layer.tileLayer.portus(
                L.tileLayer(`${baseUrl}/cloud_hml-lcc/${this.refdate}{h}/{z}/{x}/{y}.png`, {
                    minZoom: 5,
                    maxZoom: 7,
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
            let div = L.DomUtil.create("div", config.legend_type);
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

    changeRes() {
        let currentRes = this.resolution;
        (this.resolution === 'lm5') ? this.resolution = 'lm2.2' : this.resolution = 'lm5'
        console.log(`Changed resolution from ${currentRes} to ${this.resolution}`);

        // remove all current layers
        let overlays = this.layersControl['overlays'];
        let currentActiveNames = [];
        for (let name in overlays) {
            if (this.map.hasLayer(overlays[name])) {
                currentActiveNames.push(name);
                this.map.removeLayer(overlays[name]);
            }
        }
        this.setOverlaysToMap();

        // reload the new list of layers
        overlays = this.layersControl['overlays'];

        // apply the same list to the map
        for (let name in overlays) {
            if (currentActiveNames.includes(name)) {
                console.log('qui');
                let tileLayer: L.Layer = overlays[name];
                tileLayer.addTo(this.map);
            }
        }
    }
}
