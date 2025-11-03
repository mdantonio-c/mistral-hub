import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Output,
  Input,
  EventEmitter,
  OnChanges,
  SimpleChanges,
} from "@angular/core";
import { ViewModes } from "../../meteo-tiles/meteo-tiles.config";
import * as L from "leaflet";

@Component({
  selector: "map-side-nav-seasonal",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./side-nav.component.html",
  styleUrls: ["side-nav.component.scss"],
})
export class SideNavComponentSeasonal implements OnInit {
  @Input() lang = "en";
  @Input() maps: Record<"left" | "right", L.Map>;
  @Input() baseLayers: L.Control.LayersObject;
  @Input() run: number;

  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() onVariableConfig = new EventEmitter<any>();
  @Output() onSelectedLayerChange = new EventEmitter<string>();
  @Output() onSelectedMonthChange = new EventEmitter<string>();

  selectedBaseLayer: string;
  selectedLayers: string;
  selectedMonths: string;
  isCollapsed = false;
  monthsNumber = 4;
  monthsMapping = [];
  zLevel: number;

  public VariablesConfig = {
    "Maximum temperature": [
      "Monthly average of daily maximum temperatures",
      "t2mplus clickable",
      "Max temperature (°C) - monthly median values",
    ],
    "Minimum temperature": [
      "Monthly average of daily minimum temperatures",
      "t2mminus clickable",
      "Min temperature (°C) - monthly median values",
    ],
    "Total precipitation": [
      "Accumulated",
      "prp clickable",
      "Monthly total precipitation (mm)",
    ],
  };

  ngOnInit(): void {
    this.onVariableConfig.emit(this.VariablesConfig);
    // set active base layer
    for (const [key, layer] of Object.entries(this.baseLayers)) {
      if (this.maps.left?.hasLayer(layer)) {
        this.selectedBaseLayer = key;
      }
    }
    // set default layer
    this.selectedLayers = Object.keys(this.VariablesConfig)[0];
    this.onSelectedLayerChange.emit(this.selectedLayers);
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.run && this.run) {
      this.updateMonths();
    }
  }

  private updateMonths() {
    this.monthsMapping = [];
    const months = this.getNextFourMonths(this.run);
    const timeStamps = this.genTimestampMonth();

    months.forEach((month, index) => {
      this.monthsMapping.push([month, timeStamps[index]]);
    });

    this.selectedMonths = this.monthsMapping[0][0];
    this.onSelectedMonthChange.emit(this.monthsMapping[0][1]);
  }

  private genTimestampMonth(): string[] {
    const timeStamps: string[] = [];
    const year = new Date().getFullYear();
    const monthIndex = this.run - 1;
    const initialDate = new Date(Date.UTC(year, monthIndex, 1, 0));
    for (let i = 0; i < this.monthsNumber; i++) {
      const date = new Date(initialDate.getTime());
      date.setUTCMonth(date.getUTCMonth() + i);
      timeStamps.push(date.toISOString());
    }
    return timeStamps;
  }
  private getNextFourMonths(startMonth: number): string[] {
    const months: string[] = [];
    const year = 2000;
    const formatter = new Intl.DateTimeFormat("en-US", { month: "long" });

    for (let i = 0; i < 4; i++) {
      const monthIndex = (startMonth - 1 + i) % 12; // 0-based
      const date = new Date(year, monthIndex, 1);
      months.push(formatter.format(date));
    }

    return months;
  }
  toggleLayer(event: Event, layerId: string) {
    console.log(layerId);
    event.preventDefault();
    this.selectedLayers = layerId;
    this.onSelectedLayerChange.emit(layerId);
  }
  toggleMonth(event: Event, monthId: string) {
    this.selectedMonths = monthId;
    const found = this.monthsMapping.find((item) => item[0] === monthId);
    this.onSelectedMonthChange.emit(found[1]);
  }
  changeCollapse() {
    this.isCollapsed = !this.isCollapsed;
    this.onCollapseChange.emit(this.isCollapsed);
  }

  protected readonly modes = ViewModes;
  zoom(event, inOut: string) {
    /*event.preventDefault();
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
  }*/
    event.preventDefault();
    Object.values(this.maps).forEach((map) => {
      if (!map) return;
      switch (inOut) {
        case "in":
          if (map.getZoom() < map.getMaxZoom()) map.zoomIn();
          break;
        case "out":
          if (map.getZoom() > map.getMinZoom()) map.zoomOut();
          break;
      }
    });
  }
}
