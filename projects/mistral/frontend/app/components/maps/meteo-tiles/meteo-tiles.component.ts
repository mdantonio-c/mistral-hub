import {Component, OnInit} from '@angular/core';
import {icon, latLng, Map, marker, point, polyline, tileLayer} from 'leaflet';

const MAP_CENTER = [41.879966, 12.280000];

@Component({
    selector: 'app-meteo-tiles',
    templateUrl: './meteo-tiles.component.html',
    styleUrls: ['./meteo-tiles.component.css']
})
export class MeteoTilesComponent implements OnInit {

    // Map layers
    osm = tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 5,
        minZoom: 3
    });

    mlight = tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        maxZoom: 5,
        minZoom: 3,
        id: 'mapbox.light'
    });

    darkmatter = tileLayer('https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://www.mapbox.com/about/maps/"">Mapbox</a> &copy; <a href="http://cartodb.com/attributions">CartoDB</a>',
        subdomains: 'abcd',
        maxZoom: 5,
        minZoom: 3
    });


    options = {
        layers: [
            this.osm, this.mlight, this.darkmatter
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
