import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
} from "@angular/core";
import { Variables } from "./data";
import * as L from "leaflet";
import { ViewModes, MOBILE_WIDTH } from "../../meteo-tiles/meteo-tiles.config";
import { TilesService } from "../../meteo-tiles/services/tiles.service";
@Component({
  selector: "map-side-nav-marine",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./side-nav.component.html",
  styleUrls: ["side-nav.component.scss"],
})
export class SideNavComponentMarine implements OnInit {
  @Input() lang = "en";
  @Input() baseLayers: L.Control.LayersObject;
  @Input() maxZoomIn: number;
  @Input() minZoom: number;
  @Input() map: L.Map;
  @Input("viewMode") mode = ViewModes.adv;

  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  variablesConfig = Variables;
  isCollapsed = false;
  currentZoom;
  selectedLayers;
  selectedBaseLayer;

  changeBaseLayer(newVal: string) {
    // console.log(`change base layer to "${newVal}"`);
    this.map.removeLayer(this.baseLayers[this.selectedBaseLayer]);
    this.map.addLayer(this.baseLayers[newVal]);
    this.selectedBaseLayer = newVal;
  }
  changeCollapse() {
    this.isCollapsed = !this.isCollapsed;
    this.onCollapseChange.emit(this.isCollapsed);
  }
  toggleLayer(event: Event, layerId: string) {
    console.log(layerId);
    event.preventDefault();
  }

  zoom(event, inOut: string) {}
  ngOnInit(): void {
    // set active base layer
    for (const [key, layer] of Object.entries(this.baseLayers)) {
      if (this.map.hasLayer(layer)) {
        this.selectedBaseLayer = key;
      }
    }

    // setup mobile side-nav
    if (window.innerWidth < MOBILE_WIDTH) {
      this.changeCollapse();
    }
  }

  protected readonly modes = ViewModes;
}
