import { Component, Input } from '@angular/core';
import { FormGroup, FormControl } from '@angular/forms';

import * as L from 'leaflet';

@Component({
	selector: 'step-postprocess-map',
	templateUrl: './step-postprocess-map.component.html'
})
export class StepPostprocessMapComponent {

	@Input() formGroup: FormGroup;
	// ilon, ilat, flon, flat
	@Input() ilonControl: FormControl;
	@Input() ilatControl: FormControl;
	@Input() flonControl: FormControl;
	@Input() flatControl: FormControl;

	layerList = [];
	formControls;
	mapView;
	drawControl;

	options = {
		layers: [
			L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, attribution: 'Open Street Map' })
		],
		zoom: 5,
		center: L.latLng({ lat: 41.879966, lng: 12.280000 })
	};

	drawOptions = {
		position: 'topright',
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
				showArea: false
			},
		}
	};

	onMapReady(map) {
		this.mapView = map;
		map.on(L.Draw.Event.DRAWSTART, (e) => {
			this.resetAll()
		});

		map.on(L.Draw.Event.DELETED, (e) => {
			this.resetAll()
		});

		this.formControls = [
			this.ilonControl,
			this.ilatControl,
			this.flonControl,
			this.flatControl
		];
		// Form-changes event listener
		this.formControls.forEach(control =>
			control.valueChanges.subscribe(val => {
				this.updateRectangle();
			}));
	}

	onDrawReady(drawControl: L.Control.Draw) {
		this.drawControl = drawControl;
	}

	public clearAll() {
		this.layerList.forEach((layer) => { this.mapView.removeLayer(layer); });
		this.layerList = [];
		this.drawControl.options.edit.featureGroup.clearLayers();
	}

	public resetAll() {
		this.layerList.forEach((layer) => { this.mapView.removeLayer(layer); });
		this.ilonControl.reset();
		this.ilatControl.reset();
		this.flonControl.reset();
		this.flatControl.reset();
	}

	public updateRectangle() {
		this.clearAll()
		const poly = new L.Rectangle([
			L.latLng(this.ilatControl.value, this.ilonControl.value),
			L.latLng(this.flatControl.value, this.flonControl.value)
		]);

		this.drawControl.options.edit.featureGroup.addLayer(poly);
		this.mapView.addLayer(poly);
		this.layerList.push(poly);
	}

	public onDrawCreated(e: any) {
		const type = (e as any).layerType;
		const layer = (e as any).layer;
		if (type === 'rectangle') {
			const objll = layer._latlngs;
			this.ilonControl.setValue(objll[0][0].lng, {emitEvent:false});
			this.ilatControl.setValue(objll[0][0].lat, {emitEvent:false});
			this.flonControl.setValue(objll[0][2].lng, {emitEvent:false});
			this.flatControl.setValue(objll[0][2].lat, {emitEvent:false});
			this.layerList.push(layer);
			// console.log(this.layerList);
		}
	}

	public onEditStop(e: any) {
		this.layerList.forEach((layer) => {
			const objll = layer._latlngs;
			this.ilonControl.setValue(objll[0][0].lng, {emitEvent:false});
			this.ilatControl.setValue(objll[0][0].lat, {emitEvent:false});
			this.flonControl.setValue(objll[0][2].lng, {emitEvent:false});
			this.flatControl.setValue(objll[0][2].lat, {emitEvent:false});
		});
	}

	public onDrawStart(e: any) {
		// tslint:disable-next-line:no-console
	}

}
