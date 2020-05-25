import {Component, Input, OnInit, OnChanges, Output, EventEmitter} from '@angular/core';
import {ObsFilter, ObsService} from "../services/obs.service";
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

    showLayer = false;
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

    markerClusterReady(group: L.MarkerClusterGroup) {
        this.markerClusterGroup = group;
    }

    updateMap(filter: ObsFilter) {
        // get data
        this.showLayer = false;
        if (this.markerClusterGroup) {
            this.markerClusterGroup.clearLayers();
        }
        setTimeout(() => this.spinner.show(), 0);
        this.meteoService.getData(filter).subscribe(
            data => {
                // console.log(data);
                this.updateCount.emit(data.length);
                this.loadMarkers(data);
                if (data.length === 0) {
                    this.notify.showWarning('No results found. Try applying a different filter.');
                }
            },
            error => {
                this.notify.showError(error);
            }
        ).add(() => {
            this.showLayer = true;
            this.spinner.hide();
        });
    }

    private loadMarkers(data) {
        const markers: L.Marker[] = [];
        data.forEach((s) => {
            const icon = L.icon({
                iconUrl: 'leaflet/marker-icon.png',
                shadowUrl: 'leaflet/marker-shadow.png'
            });
            const template = `<ul class="p-1 m-0"><li><b>Network</b>: ${s.station.network}</li>`+
              `<li><b>Lat</b>: ${s.station.lat}</li>`+
              `<li><b>Lon</b>: ${s.station.lon}</li>`+
            `</ul>`;
            markers.push(L.marker([s.station.lat, s.station.lon], {
                icon
            }).bindTooltip(template, {direction: 'top', offset: [12, 0]}));
        })
        this.markerClusterData = markers;
        this.markerClusterGroup.addLayers(markers);
        if (markers.length > 0) {
            this.map.fitBounds(this.markerClusterGroup.getBounds(), {
                    padding: L.point(24, 24),
                    maxZoom: 12,
                    animate: true
                });
        }

    }
}
