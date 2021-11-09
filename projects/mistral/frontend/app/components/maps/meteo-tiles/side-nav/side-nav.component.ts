import {
  ChangeDetectionStrategy,
  Component,
  Input,
  Output,
  OnChanges,
  HostListener,
  EventEmitter,
  ElementRef,
  Renderer2,
  SimpleChanges,
} from "@angular/core";
import {
  DatasetProduct as DP,
  DATASETS,
  // MultiModelProduct,
} from "../meteo-tiles.config";
import { Subscription } from "rxjs";
import * as L from "leaflet";

@Component({
  selector: "map-side-nav",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./side-nav.component.html",
  styleUrls: ["side-nav.component.scss"],
})
export class SideNavComponent implements OnChanges {
  @Input() overlays: L.Control.LayersObject;
  @Input() dataset: string;
  // Reference to the primary map object
  @Input() map: L.Map;

  // Change zoom level of the map
  @Output() onZoomIn: EventEmitter<null> = new EventEmitter<null>();
  @Output() onZoomOut: EventEmitter<null> = new EventEmitter<null>();

  @Output() onLayerChange: EventEmitter<Record<string, string | L.Layer>> =
    new EventEmitter<Record<string, string | L.Layer>>();
  @Output() onDatasetChange: EventEmitter<string> = new EventEmitter<string>();

  // Multi Model Ensemble
  @Input() isShowedMultiModel: boolean;
  @Output() onShowMultiModelChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() onMMProductChange: EventEmitter<string> =
    new EventEmitter<string>();

  isCollapsed = false;
  availableDatasets = DATASETS;
  readonly PRECIPITATION_HOURS: any = [
    { value: 1, selected: false, regex: "(1h)" },
    { value: 3, selected: false, regex: "(3h)" },
    { value: 6, selected: false, regex: "(6h)" },
    { value: 12, selected: false, regex: "(12h)" },
    { value: 24, selected: false, regex: "(24h)" },
  ];
  readonly SNOW_HOURS: any = [
    { value: 1, selected: false, regex: "(1h)" },
    { value: 3, selected: false, regex: "(3h)" },
    { value: 6, selected: false, regex: "(6h)" },
    { value: 12, selected: false, regex: "(12h)" },
    { value: 24, selected: false, regex: "(24h)" },
  ];
  readonly CLOUD_LEVELS: any = [
    { value: "low", selected: false, regex: "Low" },
    { value: "medium", selected: false, regex: "Medium" },
    { value: "high", selected: false, regex: "High" },
    { value: "total", selected: false, regex: "Total" },
  ];
  private hoursMap = {
    prp: this.PRECIPITATION_HOURS,
    sf: this.SNOW_HOURS,
    cc: this.CLOUD_LEVELS,
  };

  constructor(private el: ElementRef, private renderer: Renderer2) {}

  ngOnChanges(changes: SimpleChanges): void {
    const isFirstChange = Object.values(changes).some((c) => c.isFirstChange());
    if (isFirstChange) {
      return;
    }

    // activate layers
    // let activeLayers: string[] = [];
    if (this.overlays) {
      for (const [key, layer] of Object.entries(this.overlays)) {
        let lCode = this._toLayerCode(key);
        if (lCode) {
          let el = this.el.nativeElement.querySelector(`.${lCode}`);
          if (this.map.hasLayer(layer)) {
            // activeLayers.push(key);
            this.renderer.addClass(el, "attivo");
          } else {
            this.renderer.removeClass(el, "attivo");
          }
        }
      }
    }
  }

  @HostListener("dblclick", ["$event"])
  @HostListener("click", ["$event"])
  @HostListener("mousedown", ["$event"])
  @HostListener("wheel", ["$event"])
  public onClick(event: any): void {
    event.stopPropagation();
  }

  zoom(event, inOut: string) {
    event.preventDefault();
    switch (inOut) {
      case "in":
        this.onZoomIn.emit();
        break;
      case "out":
        this.onZoomOut.emit();
        break;
      default:
        console.error(`Invalid zoom param: ${inOut}`);
    }
  }

  toggleLayer(event: Event, layerId: string) {
    event.preventDefault();
    // FIXME can we do better with multi layer products? (i.e. prp)
    const fromActiveState: boolean = (
      event.target as HTMLInputElement
    ).className.includes("attivo");
    const op = fromActiveState ? "remove" : "add";
    if (["prp", "sf", "cc"].includes(layerId)) {
      if (op === "remove") {
        // reset hours
        this.hoursMap[layerId].forEach((e) => (e.selected = false));
      } else {
        const found = this.hoursMap[layerId].find((e) => e.selected);
        if (!found) {
          // select default
          this.hoursMap[layerId][0].selected = true;
        }
      }
    }
    for (const [key, layer] of Object.entries(this.overlays)) {
      if (layerId === this._toLayerCode(key)) {
        // let op = (this.map.hasLayer(layer)) ? 'remove' : 'add';
        if (this.map.hasLayer(layer) && op === "remove") {
          this.onLayerChange.emit({
            layer: layer,
            name: key,
          });
        }
        if (op === "add") {
          this.onLayerChange.emit({
            layer: layer,
            name: key,
          });
          break;
        }
      }
    }
    // update active class
    let el = this.el.nativeElement.querySelector(`.${layerId}`);
    el.classList.contains("attivo")
      ? this.renderer.removeClass(el, "attivo")
      : this.renderer.addClass(el, "attivo");
  }

  /**
   * Custom mapper for overlay titles into component codes
   * @param title
   * @private
   */
  private _toLayerCode(title: string): string | null {
    switch (title) {
      case DP.TM2:
        return "t2m";
      case DP.PMSL:
        return "prs";
      case DP.RH:
        return "rh";
      case DP.PREC1P:
      case DP.PREC3P:
      case DP.PREC6P:
      case DP.PREC12P:
      case DP.PREC24P:
        return "prp";
      case DP.SF1:
      case DP.SF3:
      case DP.SF6:
      case DP.SF12:
      case DP.SF24:
        return "sf";
      case DP.LCC:
      case DP.MCC:
      case DP.HCC:
      case DP.TCC:
        return "cc";
      default:
        return null;
    }
  }

  private _toLayerTitle(
    code: string,
    lvl: string | number | null = null
  ): string | null {
    if (lvl) {
      lvl = `${lvl}`;
    }
    switch (code) {
      case "t2m":
        return DP.TM2;
      case "prs":
        return DP.PMSL;
      case "rh":
        return DP.RH;
      case "prp":
        switch (lvl) {
          case "1":
            return DP.PREC1P;
          case "3":
            return DP.PREC3P;
          case "6":
            return DP.PREC6P;
          case "12":
            return DP.PREC12P;
          case "24":
            return DP.PREC24P;
        }
        return DP.PREC1P;
      case "sf":
        switch (lvl) {
          case "1":
            return DP.SF1;
          case "3":
            return DP.SF3;
          case "6":
            return DP.SF6;
          case "12":
            return DP.SF12;
          case "24":
            return DP.SF24;
        }
        return DP.SF1;
      case "cc":
        switch (lvl) {
          case "low":
            return DP.LCC;
          case "medium":
            return DP.MCC;
          case "high":
            return DP.HCC;
          case "total":
            return DP.TCC;
        }
        return DP.LCC;
      default:
        return null;
    }
  }

  changeDataset(event, datasetId) {
    event.preventDefault();
    this.onDatasetChange.emit(datasetId);
  }

  private _escapeChars(input: string): string {
    return input.replace(/\./g, "\\.");
  }

  /**
   * Activate / Deactivate a layer with sub levels
   * @param event
   * @param target
   * @param layerId
   */
  changeHour(event: Event, target, layerId: string) {
    target.selected = !target.selected;
    let activeHoursCount = this.hoursMap[layerId]
      .filter((h) => h.selected)
      .reduce((accumulator) => {
        return accumulator + 1;
      }, 0);
    if (activeHoursCount === 0) {
      // prevent unchecking last active hour
      target.selected = !target.selected;
      (event.target as HTMLInputElement).checked = true;
      // do nothing
      return;
    }
    // console.log(`activate layer ${layerId}, value ${target.value}`);
    for (const [key, layer] of Object.entries(this.overlays)) {
      if (
        layerId === this._toLayerCode(key) &&
        key.includes(`${target.regex}`)
      ) {
        this.onLayerChange.emit({
          layer: layer,
          name: this._toLayerTitle(layerId, target.value),
        });
        break;
      }
    }
  }

  /**
   *
   * @param layerId
   */
  isLayerActive(layerId: string): boolean {
    if (!this.overlays) return false;
    let active = false;
    for (const [key, layer] of Object.entries(this.overlays)) {
      if (layerId === this._toLayerCode(key) && this.map.hasLayer(layer)) {
        active = true;
      }
    }
    return active;
  }

  toggleMultiModel() {
    /*const op = this.isShowedMultiModel ? 'off' : 'on';
    console.log(`Turn ${op} Multi Model Ensemble`);*/
    this.onShowMultiModelChange.emit(this.isShowedMultiModel);
  }

  changeMMProduct(product: string) {
    this.onMMProductChange.emit(product);
  }
}
