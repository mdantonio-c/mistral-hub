import { Component, Input } from "@angular/core";
import { FormGroup, FormControl } from "@angular/forms";

import * as L from "leaflet";

@Component({
  selector: "step-postprocess-map",
  templateUrl: "./step-postprocess-map.component.html",
})
export class StepPostprocessMapComponent {
  @Input() formGroup: FormGroup;
  // ilon, ilat, flon, flat
  @Input() ilonControl: FormControl;
  @Input() ilatControl: FormControl;
  @Input() flonControl: FormControl;
  @Input() flatControl: FormControl;

  drawnItems: L.FeatureGroup = L.featureGroup();

  options = {
    layers: [
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: "Open Street Map",
      }),
    ],
    zoom: 5,
    center: L.latLng({ lat: 41.879966, lng: 12.28 }),
  };

  drawOptions = {
    position: "topright",
    draw: {
      polygon: false,
      circlemarker: false,
      circle: false,
      marker: false,
      polyline: false,
      // "showArea:false" 	solves a leafler-draw bug. An alternative is to add
      // "noImplicitUseStrict": true
      // under the compilerOptions property in tsconfig.json and tsconfig.app.json
      rectangle: {
        showArea: false,
      },
    },
    edit: {
      featureGroup: this.drawnItems,
    },
  };

  onMapReady(map) {
    map.on(L.Draw.Event.DRAWSTART, (e) => {
      this.resetAll();
    });

    map.on(L.Draw.Event.DELETED, (e) => {
      this.resetAll();
    });

    const formControls = [
      this.ilonControl,
      this.ilatControl,
      this.flonControl,
      this.flatControl,
    ];
    // Form-changes event listener
    formControls.forEach((control) =>
      control.valueChanges.subscribe((val) => {
        this.updateRectangle();
      }),
    );
    let poly = this.updateRectangle();
    if (poly) {
      map.fitBounds((poly as L.Rectangle).getLatLngs(), { padding: [50, 50] });
    }
  }

  public clearAll() {
    this.drawnItems.clearLayers();
  }

  public resetAll() {
    this.drawnItems.clearLayers();
    this.ilonControl.reset();
    this.ilatControl.reset();
    this.flonControl.reset();
    this.flatControl.reset();
  }

  public updateRectangle() {
    this.clearAll();
    if (
      this.ilatControl.value &&
      this.ilonControl.value &&
      this.flatControl.value &&
      this.flonControl.value
    ) {
      const poly = new L.Rectangle(
        L.latLngBounds(
          L.latLng(this.ilatControl.value, this.ilonControl.value),
          L.latLng(this.flatControl.value, this.flonControl.value),
        ),
      );
      // this.drawControl.options.edit.featureGroup.addLayer(poly);
      // this.mapView.addLayer(poly);
      // this.layerList.push(poly);
      this.drawnItems.addLayer(poly);
      return poly;
    }
  }

  public onDrawCreated(e: any) {
    const type = (e as L.DrawEvents.Created).layerType,
      layer = (e as L.DrawEvents.Created).layer;
    if (type === "rectangle") {
      const coords = (layer as L.Rectangle).getLatLngs();
      this.ilonControl.setValue(coords[0][0].lng, { emitEvent: false });
      this.ilatControl.setValue(coords[0][0].lat, { emitEvent: false });
      this.flonControl.setValue(coords[0][2].lng, { emitEvent: false });
      this.flatControl.setValue(coords[0][2].lat, { emitEvent: false });
      this.drawnItems.addLayer(layer);
    }
  }

  onDrawEdited(e: L.DrawEvents.Edited) {
    const ref = this;
    e.layers.eachLayer(function (
      layer,
      comp: StepPostprocessMapComponent = ref,
    ) {
      if (layer instanceof L.Rectangle) {
        const coords = (layer as L.Rectangle).getLatLngs();
        comp.ilonControl.setValue(coords[0][0].lng, { emitEvent: false });
        comp.ilatControl.setValue(coords[0][0].lat, { emitEvent: false });
        comp.flonControl.setValue(coords[0][2].lng, { emitEvent: false });
        comp.flatControl.setValue(coords[0][2].lat, { emitEvent: false });
      }
    });
  }
}
