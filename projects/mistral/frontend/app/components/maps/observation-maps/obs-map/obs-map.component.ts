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
export class ObsMapComponent implements OnChanges {
    @Input() filter: ObsFilter;
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
    // layers = [];

    // Marker cluster stuff
    markerClusterGroup: L.MarkerClusterGroup;
    markerClusterData: L.Marker[] = [];
    markerClusterOptions: L.MarkerClusterGroupOptions;
    map: L.Map;
    /*
    summit = L.marker([45.0, 12.0], {
        icon: L.icon({
            iconSize: [25, 41],
            iconAnchor: [13, 41],
            iconUrl: 'leaflet/marker-icon.png',
            shadowUrl: 'leaflet/marker-shadow.png'
        })
    });
    layers = [ this.summit ];
    // Layers control object with our two base layers and the three overlay layers
    layersControl = {
        baseLayers: {
            'Street Maps': this.streetMaps,
            'Wikimedia Maps': this.wMaps
        },
        overlays: {
            "Summit": this.summit
        }
    };
    */

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
    /*
    ngOnInit() {
        // this.applyFilter({});
        // this.loadMarkers(obsData);
        // console.log('ng init', this.markerClusterData);
    }
     */
    ngOnChanges() {
        this.applyFilter(this.filter);
    }

    onMapReady(map: L.Map) {
        this.map = map;
    }

    markerClusterReady(group: L.MarkerClusterGroup) {
        console.log('markerClusterReady', group);
        this.markerClusterGroup = group;
        /*
        this.map.fitBounds(this.markerClusterGroup.getBounds(), {
            padding: L.point(24, 24),
            maxZoom: 12,
            animate: true
        });
        */
    }

    applyFilter(filter: ObsFilter) {
        // get data
        this.showLayer = false;
        if (this.markerClusterGroup) {
            this.markerClusterGroup.clearLayers();
        }
        setTimeout(() => this.spinner.show(), 0);
        this.meteoService.getStations(filter).subscribe(
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
            // console.log(s);
            const icon = L.icon({
                iconUrl: 'leaflet/marker-icon.png',
                shadowUrl: 'leaflet/marker-shadow.png'
            });
            markers.push(L.marker([s.station.lat, s.station.lon], {icon}));
        })
        this.markerClusterData = markers;
        setTimeout(() => {
            this.map.fitBounds(this.markerClusterGroup.getBounds(), {
                padding: L.point(24, 24),
                maxZoom: 12,
                animate: true
            });
        }, 500)

    }
}
