import {Component, Output, EventEmitter} from '@angular/core';
import {Observation, ObsFilter, ObsService, Station} from "../services/obs.service";
import {obsData} from "../services/data";
import {NotificationService} from '@rapydo/services/notification';
import {NgxSpinnerService} from 'ngx-spinner';

import * as L from 'leaflet';
import 'leaflet.markercluster';

@Component({
    selector: 'app-obs-map',
    templateUrl: './obs-map.component.html',
    styleUrls: ['./obs-map.component.css']
})
export class ObsMapComponent {

    @Output() updateCount: EventEmitter<number> = new EventEmitter<number>();

    // base layers
    streetMaps = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        detectRetina: true,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
    wMaps = L.tileLayer('http://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png', {
        detectRetina: true,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });

    // Marker cluster stuff
    markerClusterGroup: L.MarkerClusterGroup;
    markerClusterData: L.Marker[] = [];
    markerClusterOptions: L.MarkerClusterGroupOptions;
    map: L.Map;
    legend = new L.Control({position: "bottomright"});

    // Set the initial set of displayed layers
    options = {
        layers: [
            this.streetMaps
        ],
        zoom: 5,
        center: [45.0, 12.0]
    };

    constructor(private meteoService: ObsService,
                private notify: NotificationService,
                private spinner: NgxSpinnerService) {
        // custom cluster options
        this.markerClusterOptions = {
            iconCreateFunction: function (cluster, service = meteoService) {
                const childCount = cluster.getChildCount();
                const childMarkers: L.Marker[] = cluster.getAllChildMarkers();
                let res: number = childCount;
                let c = ' marker-cluster-';
                if (childCount < 10) {
                    c += 'small';
                } else if (childCount < 100) {
                    c += 'medium';
                } else {
                    c += 'large';
                }
                let type: string;
                if (childMarkers[0].options['data']) {
                    let sum = 0;
                    for (const m of childMarkers) {
                        const obj = m.options['data'];
                        const arr: any[] = obj[Object.keys(obj)[0]];
                        if (!type) {
                            type = Object.keys(obj)[0];
                        }
                        sum += arr.map(v => v.value).reduce((a, b) => a + b, 0) / arr.length;
                    }
                    res = sum / childCount;
                    if (type === 'B12101') {
                        // convert temperatures from Kelvin to Celsius
                        res -= 273.15;
                    }
                    res = Math.round(res);
                    // custom background color of cluster
                    c = ' mst-marker-color-' + service.getColor(res);
                }
                return new L.DivIcon({
                    html: '<div><span>' + res + '</span></div>',
                    className: 'marker-cluster' + c, iconSize: new L.Point(40, 40)
                });
            }
        }
    }

    onMapReady(map: L.Map) {
        this.map = map;
    }

    markerClusterReady(group: L.MarkerClusterGroup) {
        this.markerClusterGroup = group;
    }

    updateMap(filter: ObsFilter) {
        // get data
        if (this.markerClusterGroup) {
            this.markerClusterGroup.clearLayers();
        }
        setTimeout(() => this.spinner.show(), 0);
        this.meteoService.getData(filter).subscribe(
            (data: Observation[]) => {
                // console.log(data);
                this.updateCount.emit(data.length);
                this.loadMarkers(data, filter.product, filter.onlyStations);
                if (data.length === 0) {
                    this.notify.showWarning('No results found. Try applying a different filter.');
                }
            },
            error => {
                this.notify.showError(error);
            }
        ).add(() => {
            this.spinner.hide();
        });
    }

    fitBounds() {
        if (this.markerClusterData.length > 0) {
            this.map.fitBounds(this.markerClusterGroup.getBounds(), {
                padding: L.point(24, 24),
                maxZoom: 12,
                animate: true
            });
        }
    }

    /**
     *
     * @param data
     */
    private loadMarkers(data: Observation[], product: string, onlyStations = false) {
        const markers: L.Marker[] = [];
        let min: number, max: number;
        data.forEach((s) => {
            let value: number;
            if (s.data) {
                const obj = s.data;
                const arr: any[] = obj[Object.keys(obj)[0]];
                // value = Math.round(arr.map(v => v.value).reduce((a, b) => a + b, 0) / arr.length);
                value = arr.map(v => v.value).reduce((a, b) => a + b, 0) / arr.length;
                if (product === 'B12101') {
                    value -= 273.15;    // convert temperatures from Kelvin to Celsius
                }
                let localMin = Math.min(...arr.map(v => v.value));
                if (!min || localMin < min) {
                    min = localMin;
                }
                let localMax = Math.max(...arr.map(v => v.value));
                if (!max || localMax > max) {
                    max = localMax;
                }
            }
            const icon = (s.data) ? L.divIcon({
                html: `<div class="mstDataIcon"><span>${value.toFixed(2)}</span></div>`,
                iconSize: [24, 6],
                className: 'leaflet-marker-icon mst-marker-color-' + this.meteoService.getColor(value)
            }) : L.divIcon({
                html: '<i class="fa fa-map-marker-alt fa-3x"></i>',
                iconSize: [20, 20],
                className: 'mstDivIcon'
            });
            const marker = new L.Marker([s.station.lat, s.station.lon], {
                icon: icon
            });
            marker.options['station'] = s.station;
            if (s.data) {
                marker.options['data'] = s.data;
            }

            marker.bindTooltip(this.buildTooltipTemplate(s.station),
                {direction: 'top', offset: [3, -8]});
            markers.push(marker);
        });

        this.markerClusterData = markers;
        this.markerClusterGroup.addLayers(markers);

        if (!onlyStations && data.length > 0) {
            console.log(`min ${min}, max ${max}`);
            if (product === 'B12101') {
                // convert min and max temperatures from Kelvin to Celsius
                min -= 273.15;
                max -= 273.15;
            }
            this.buildLegend(product, min, max);
        } else {
            this.legend.remove();
        }

        this.fitBounds();
    }

    private buildTooltipTemplate(station: Station) {
        let ident = station.ident || '';
        let altitude = station.altitude || '';
        const template = `<ul class="p-1 m-0"><li><b>Network</b>: ${station.network}</li>` +
            ident +
            `<li><b>Lat</b>: ${station.lat}</li>` +
            `<li><b>Lon</b>: ${station.lon}</li>` +
            altitude +
            `</ul>`;
        return template;
    }

    private buildLegend(product: string, min: number, max: number) {
        this.legend.onAdd = function (map) {
            console.log(`add legend for product ${product} (${min.toFixed(2)}, ${max.toFixed(2)})`);
            let div = L.DomUtil.create('div', 'info legend');
            const colors = ["#ffcc00", "#ff9900", "#ff6600", "#ff0000", "#cc0000", "#990000", "#660000", "#660066", "#990099", "#cc00cc", "#ff00ff", "#bf00ff", "#7200ff",
                    "#0000ff", "#0059ff", "#008cff", "#00bfff", "#00ffff", "#00e5cc", "#00cc7f", "#00b200", "#7fcc00", "#cce500", "#ffff00", "#ffcc00", "#ff9900",
                    "#ff6600", "#ff0000", "#cc0000", "#990000", "#660000", "#660066", "#990099", "#cc00cc", "#ff00ff", "#bf00ff", "#7200ff", "#ffcc00", "#ff9900"],
            labels = ["-30", " ", "-26", " ", "-22", "", "-18", " ", "-14", " ",
                "-10", " ", "-6", " ", "-2", " ", "2", " ", "6", " ", "10", " ", "14", " ", "18",
                "", "22", " ", "26", " ", "30", " ", "34", " ", "38", " ", "42", " ", "46"];
            let title = "Temp [°C]";
            div.style.clear = "unset";
            div.innerHTML += `<h6 style="font-size: small;">${title}</h6>`;
            for (let i = 0; i < labels.length; i++) {
                div.innerHTML += '<i style="background:' + colors[i] + '"></i><span>' + labels[i] + '</span><br>';
            }
            return div;
        };
        this.legend.addTo(this.map);
    }
}
