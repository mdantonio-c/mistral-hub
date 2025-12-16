import {
  Component,
  OnInit,
  Input,
  ElementRef,
  Renderer2,
  ChangeDetectorRef,
  Output,
  EventEmitter,
  HostListener,
} from "@angular/core";
import * as L from "leaflet";
import { Variables } from "./data";
import { ViewModes, MOBILE_WIDTH } from "../../meteo-tiles/meteo-tiles.config";
import { environment } from "@rapydo/../environments/environment";
@Component({
  selector: "map-side-nav-subseasonal",
  templateUrl: "./side-nav.component.html",
  styleUrls: ["./side-nav.component.scss"],
})
export class SideNavComponentSubseasonal implements OnInit {
  @Input() lang = "en";
  @Input() baseLayers: L.Control.LayersObject;
  @Input() maxZoomIn: number;
  @Input() minZoom: number;
  @Input() map: L.Map;
  @Input("viewMode") mode = ViewModes.adv;
  @Input() weekRanges: string[];
  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() onSelectedWeekChange = new EventEmitter<string>();
  @Output() onLayerChange = new EventEmitter<string>();
  variablesConfig = Variables;

  infoHome: string = environment.CUSTOM.INFO_HOME;
  aboutPage: string = environment.CUSTOM.INFO_HOME + "/about?lang=en";
  selectedWeek;
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
  toggleLayer(event: Event, layerId: string) {
    event.preventDefault();
    this.selectedLayers = [layerId];
    this.onLayerChange.emit(layerId);
  }

  ngOnChanges() {
    if (this.weekRanges && this.weekRanges.length > 0) {
      this.selectedWeek = this.weekRanges[0];
    }
  }
  ngOnInit() {
    this.zLevel = this.map.getZoom();
    this.selectedWeek = this.weekRanges[0];
    const ref = this;
    this.map.on(
      "zoomend",
      function (event, comp: SideNavComponentSubseasonal = ref) {
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

  toggleWeek(event: Event, weekId: string) {
    this.selectedWeek = weekId;
    this.onSelectedWeekChange.emit(this.selectedWeek);
  }
}
