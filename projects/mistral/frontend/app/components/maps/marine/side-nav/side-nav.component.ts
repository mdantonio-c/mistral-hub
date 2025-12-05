import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  ElementRef,
  Renderer2,
  ChangeDetectorRef,
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
  // set first variable as default
  selectedLayers = [Object.keys(this.variablesConfig)[0]];
  selectedBaseLayer;
  zLevel: number;

  constructor(
    private el: ElementRef,
    private renderer: Renderer2,
    private changeDetector: ChangeDetectorRef,
  ) {}

  changeCollapse() {
    this.isCollapsed = !this.isCollapsed;
    this.onCollapseChange.emit(this.isCollapsed);
  }
  toggleLayer(event: Event, layerId: string) {
    console.log(layerId);
    event.preventDefault();
    const isSelected = this.selectedLayers.includes(layerId);

    if (isSelected) {
      if (this.selectedLayers.length === 1) {
        return;
      }

      this.selectedLayers = this.selectedLayers.filter((x) => x !== layerId);
      return;
    }

    const hasHs = this.selectedLayers.includes("hs");
    const hasT01 = this.selectedLayers.includes("t01");

    if (layerId === "t01" && hasHs) {
      this.selectedLayers = ["t01"];
      return;
    }

    if (layerId === "hs" && hasT01) {
      this.selectedLayers = ["hs"];
      return;
    }

    if (this.selectedLayers.length >= 2) {
      this.selectedLayers = [layerId];
      return;
    }

    this.selectedLayers.push(layerId);
  }

  zoom(event, inOut: string) {
    event.preventDefault();
    switch (inOut) {
      case "in":
        if (this.map.getZoom() < this.map.getMaxZoom()) {
          this.map.zoomIn();
        }
        break;
      case "out":
        if (this.map.getZoom() > this.map.getMinZoom()) {
          this.map.zoomOut();
        }
        break;
      default:
        console.error(`Invalid zoom param: ${inOut}`);
    }
  }
  ngOnInit(): void {
    this.zLevel = this.map.getZoom();
    const ref = this;
    this.map.on(
      "zoomend",
      function (event, comp: SideNavComponentMarine = ref) {
        // because we're outside of Angular's zone, this change won't be detected
        comp.zLevel = comp.map.getZoom();
        // need tell Angular to detect changes
        comp.changeDetector.detectChanges();
      },
    );

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
