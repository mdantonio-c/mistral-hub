import {Component, OnInit, ViewChild, ElementRef} from "@angular/core";
import {icon, latLng, Map, marker, point, polyline, tileLayer} from 'leaflet';
import {ObsFilter, ObsService} from "./services/obs.service";
import {NotificationService} from '@rapydo/services/notification';
import {NgxSpinnerService} from 'ngx-spinner';

@Component({
    selector: 'app-observation-maps',
    templateUrl: './observation-maps.component.html',
    styleUrls: ['./observation-maps.component.css']
})
export class ObservationMapsComponent implements OnInit {

    // base layers
    streetMaps = tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        detectRetina: true,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
    wMaps = tileLayer('http://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png', {
        detectRetina: true,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });

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

    ngOnInit() {

    }

    onMapReady(map: Map) {
        // When the map is created, the ngx-leaflet directive calls
        // onMapReady passing a reference to the map as an argument
        // TODO
    }

    applyFilter(filter: ObsFilter) {

        // get data
        this.meteoService.getObservations(filter).subscribe(
            response => {

            },
            error => {
                this.notify.showError(error);
            }
        );

    }
}
