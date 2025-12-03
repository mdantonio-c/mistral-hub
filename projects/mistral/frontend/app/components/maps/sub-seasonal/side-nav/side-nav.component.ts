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

  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() onSelectedWeekChange = new EventEmitter<string>();
  @Output() run = new EventEmitter<string>();

  variablesConfig = Variables;
  weeksMapping = ["Week 1", "Week 2", "Week 3", "Week 4"];
  weeksRanges;
  selectedWeek = "Week 1";
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
    console.log(layerId);
    event.preventDefault();
    this.selectedLayers = [layerId];
  }

  ngOnInit() {
    this.zLevel = this.map.getZoom();
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
    this.updateWithLastDataAvailable();
  }
  public updateWithLastDataAvailable(reload: boolean = false) {
    const readyFileName = "READY.json";
    fetch(`./app/custom/assets/readySubSeasonal/${readyFileName}`)
      .then((response) => response.json())
      .then((data) => {
        const from = new Date(data.from);
        const to = new Date(data.to);
        this.run.emit(data.from);
        const weeks = this.getWeeksBetween(from, to);
        console.log(weeks);
        this.weeksRanges = weeks;
      });
  }
  toggleWeek(event: Event, weekId: string) {
    this.selectedWeek = weekId;
    const found = this.weeksMapping.find((item) => item[0] === weekId);
    this.onSelectedWeekChange.emit(found[1]);
  }
  private getWeeksBetween(from: Date, to: Date): string[] {
    const format = (d: Date) =>
      `${String(d.getDate()).padStart(2, "0")}/${String(
        d.getMonth() + 1,
      ).padStart(2, "0")}/${d.getFullYear()}`;

    const weeks: string[] = [];

    let current = new Date(from);

    while (current <= to) {
      const start = new Date(current);
      const end = new Date(current);
      end.setDate(end.getDate() + 6);

      weeks.push(`${format(start)} - ${format(end)}`);
      current.setDate(current.getDate() + 7);
    }

    return weeks;
  }
}
