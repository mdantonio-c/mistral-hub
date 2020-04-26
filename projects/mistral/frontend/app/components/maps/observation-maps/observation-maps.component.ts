import {Component, OnInit, ViewChild, ElementRef} from "@angular/core";
import {icon, latLng, Map, marker, point, polyline, tileLayer} from 'leaflet';
import {NgbDateStruct, NgbPanelChangeEvent} from '@ng-bootstrap/ng-bootstrap';

const MAP_CENTER = [41.879966, 12.280000];

@Component({
    selector: 'app-observation-maps',
    templateUrl: './observation-maps.component.html',
    styleUrls: ['./observation-maps.component.css']
})
export class ObservationMapsComponent implements OnInit {

    model: NgbDateStruct;

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
        zoom: 6,
        center: MAP_CENTER
    };

    ngOnInit() {

    }

    onMapReady(map: Map) {
        // When the map is created, the ngx-leaflet directive calls
        // onMapReady passing a reference to the map as an argument
        // TODO
    }
}
