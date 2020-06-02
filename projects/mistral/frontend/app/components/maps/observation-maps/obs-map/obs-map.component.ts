import {Component, Output, EventEmitter, OnInit} from '@angular/core';
import {ObsFilter, ObsService, Station} from "../services/obs.service";
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
export class ObsMapComponent implements OnInit {

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
    markerClusterOptions: L.MarkerClusterGroupOptions = {
        iconCreateFunction: function (cluster) {
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
            if (childMarkers[0].options['data']) {
                let sum = 0;
                for (const m of childMarkers) {
                    const obj = m.options['data'];
                    const arr: any[] = obj[Object.keys(obj)[0]];
                    sum += arr.map(v => v.value).reduce((a, b) => a + b, 0) / arr.length;
                }
                res = Math.round(sum / childCount);
            }
            return new L.DivIcon({
                html: '<div><span>' + res + '</span></div>',
                className: 'marker-cluster' + c, iconSize: new L.Point(40, 40)
            });
        }
    };
    map: L.Map;

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
    }

    onMapReady(map: L.Map) {
        this.map = map;
    }

    private printHello() {
        console.log('Hello');
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
            data => {
                // console.log(data);
                this.updateCount.emit(data.length);
                this.loadMarkers(data, filter.onlyStations);
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
    private loadMarkers(data, onlyStations = false) {
        const markers: L.Marker[] = [];
        data.forEach((s) => {
            let value: number;
            if (s.data) {
                const obj = s.data;
                const arr: any[] = obj[Object.keys(obj)[0]];
                value = Math.round(arr.map(v => v.value).reduce((a, b) => a + b, 0) / arr.length);
            }
            const icon = (s.data) ? L.divIcon({
                html: `<div class="mstDataIcon"><span>${value}</span></div>`,
                iconSize: [24, 6],
                className: 'leaflet-marker-icon marker-cluster-small'
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
        })

        this.markerClusterData = markers;
        this.markerClusterGroup.addLayers(markers);

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
}
