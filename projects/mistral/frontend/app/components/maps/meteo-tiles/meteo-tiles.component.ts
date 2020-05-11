import {Component, OnInit} from '@angular/core';
import * as L from 'leaflet';
import 'leaflet-timedimension/dist/leaflet.timedimension.src.js';
import 'leaflet-timedimension/examples/js/extras/leaflet.timedimension.tilelayer.portus.js';
declare module 'leaflet' {
   var timeDimension: any;
}

const MAP_CENTER = [41.879966, 12.280000];

@Component({
    selector: 'app-meteo-tiles',
    templateUrl: './meteo-tiles.component.html',
    styleUrls: ['./meteo-tiles.component.css']
})
export class MeteoTilesComponent implements OnInit {
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

  temperature2m =	L.tileLayer('app/custom/assets/images/t2m-t2m/2020030200/{z}/{x}/{y}.png', {
    minZoom: 3,
    maxZoom: 5,
    opacity: 0.6,
    // bounds: [[25.0, -25.0], [50.0, 47.0]],
  });
  t2m_time = L.timeDimension.layer.tileLayer.portus(this.temperature2m, {});

  totalPrecipitation = L.tileLayer("app/custom/assets/images/tp/2020030200/{z}/{x}/{y}.png", {
    minZoom: 3,
    maxZoom: 5,
    tms: false,
    opacity: 0.6,
    // bounds: [[25.0, -25.0], [50.0, 47.0]],
  });
  // tp_time = L.timeDimension.layer.tileLayer.portus(tp, {});

  snowfall = L.tileLayer("app/custom/assets/images/snow3-snow/2020030200/{z}/{x}/{y}.png", {
    minZoom: 3,
    maxZoom: 5,
    tms: false,
    opacity: 0.6,
    // bounds: [[25.0, -25.0], [50.0, 47.0]],
  });
  // var sf_time = L.timeDimension.layer.tileLayer.portus(sf, {});

  press = L.tileLayer("app/custom/assets/images/press/2020030200/{z}/{x}/{y}.png", {
    minZoom: 3,
    maxZoom: 5,
    tms: false,
    //opacity: 0.6,
    // bounds: [[25.0, -25.0], [50.0, 47.0]],
  });

  relativeHumidity = L.tileLayer("app/custom/assets/images/humidity-r/2020030200/{z}/{x}/{y}.png", {
    minZoom: 3,
    maxZoom: 5,
    tms: false,
    //opacity: 0.6,
    bounds: [[25.0, -25.0], [50.0, 47.0]],
  });
  // var sh_time = L.timeDimension.layer.tileLayer.portus(sh,  {});

  tcc = L.tileLayer("app/custom/assets/images/tcc/2020030200/{z}/{x}/{y}.png", {
    minZoom: 3,
    maxZoom: 5,
    tms: false,
    //opacity: 0.6,
    bounds: [[25.0, -25.0], [50.0, 47.0]],
  });
  // var tcc_time = L.timeDimension.layer.tileLayer.portus(tcc, {});

  hcc = L.tileLayer("app/custom/assets/images/cloud_hml-hcc/2020030200/{z}/{x}/{y}.png", {
    minZoom: 3,
    maxZoom: 5,
    tms: false,
    //opacity: 0.6,
    bounds: [[25.0, -25.0], [50.0, 47.0]],
  });
  // var hcc_time = L.timeDimension.layer.tileLayer.portus(hcc, {});

  mcc = L.tileLayer("app/custom/assets/images/cloud_hml-mcc/2020030200/{z}/{x}/{y}.png", {
    minZoom: 3,
    maxZoom: 5,
    tms: false,
    opacity: 0.9,
    bounds: [[25.0, -25.0], [50.0, 47.0]],
  });
  // var mcc_time = L.timeDimension.layer.tileLayer.portus(mcc, {});

  lcc = L.tileLayer("app/custom/assets/images/cloud_hml-lcc/2020030200/{z}/{x}/{y}.png", {
    minZoom: 3,
    maxZoom: 5,
    tms: false,
    //opacity: 0.6,
    bounds: [[25.0, -25.0], [50.0, 47.0]],
  });

  layersControl = {
    baseLayers: {
      'Openstreet Map': this.osm,
      'Carto Map': this.darkmatter,
      'Mapbox Map': this.mlight
    },
    overlays: {
      'Temperatura 2 metri': this.temperature2m,
      'Precipitazione': this.totalPrecipitation,
      'Neve': this.snowfall,
      'Umidità relativa': this.relativeHumidity,
      'Nubi alte': this.hcc,
      'Nubi medie': this.mcc,
      'Nubi basse': this.lcc
    }
  };
  // Set the initial set of displayed layers (we could also use the leafletLayers input binding for this)
  options = {
    layers: [
      this.osm,
      this.darkmatter,
      this.mlight,
      this.temperature2m
    ],
    zoom: 5,
    center: L.latLng([ 46.879966, 11.726909 ]),
    timeDimension: true,
    timeDimensionControl: true
  };
  ngOnInit() {

  }
  onMapReady(map: L.Map) {

  }
}
