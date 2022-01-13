import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  Output,
  Renderer2,
  OnInit,
  ChangeDetectorRef,
  SimpleChanges,
} from "@angular/core";
import {
  DatasetProduct as DP,
  DATASETS,
  MultiModelProduct,
  MultiModelProductLabel,
} from "../meteo-tiles.config";
import * as L from "leaflet";
import {
  CLOUD_LEVELS,
  IFF_PERCENTILES,
  IFF_PROBABILITIES,
  PRECIPITATION_HOURS,
  SNOW_HOURS,
  toLayerCode,
  toLayerTitle,
} from "./data";
import { ValueLabel } from "../../../../types";

@Component({
  selector: "map-side-nav",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./side-nav.component.html",
  styleUrls: ["side-nav.component.scss"],
})
export class SideNavComponent implements OnInit {
  @Input() baseLayers: L.Control.LayersObject;
  @Input() dataset: string;
  // Reference to the primary map object
  @Input() map: L.Map;

  private _overlays: L.Control.LayersObject;

  @Input() set overlays(value: L.Control.LayersObject) {
    this._overlays = value;
    if (!value) return;
    // reset selectedMap
    for (const [key, value] of Object.entries(this.selectedMap)) {
      this.selectedMap[key] = null;
    }
    // activate layers
    for (const [key, layer] of Object.entries(this._overlays)) {
      let lCode = toLayerCode(key);
      if (lCode) {
        const el = this.el.nativeElement.querySelector(`.${lCode}`);
        this.renderer.removeClass(el, "attivo");
        if (this.map.hasLayer(layer)) {
          if (Object.keys(this.selectedMap).includes(lCode)) {
            this.selectedMap[lCode] = this.subLevelsMap[lCode][0].value;
          }
          setTimeout(() => {
            this.renderer.addClass(el, "attivo");
          }, 0);
        }
      }
    }
  }

  get overlays(): L.Control.LayersObject {
    return this._overlays;
  }

  @Output() onLayerChange: EventEmitter<Record<string, string | L.Layer>> =
    new EventEmitter<Record<string, string | L.Layer>>();
  @Output() onDatasetChange: EventEmitter<string> = new EventEmitter<string>();

  // Multi Model Ensemble
  @Input() isShowedMultiModel: boolean;
  @Output() onShowMultiModelChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() onMMProductChange: EventEmitter<MultiModelProduct> =
    new EventEmitter<MultiModelProduct>();
  mmProduct: MultiModelProduct = MultiModelProduct.TM;
  mmProductSwitch: boolean = false;
  MultiModelProductLabel = MultiModelProductLabel;
  zLevel: number;

  isCollapsed = false;
  availableDatasets = DATASETS;

  subLevelsMap = {
    prp: PRECIPITATION_HOURS,
    sf: SNOW_HOURS,
    cc: CLOUD_LEVELS,
    tpperc: IFF_PERCENTILES,
    tpprob: IFF_PROBABILITIES,
  };

  selectedMap = {};
  selectedBaseLayer: string;

  constructor(
    private el: ElementRef,
    private renderer: Renderer2,
    private changeDetector: ChangeDetectorRef
  ) {
    Object.keys(this.subLevelsMap).forEach((key) => {
      this.selectedMap[key] = null;
    });
  }

  ngOnInit() {
    this.zLevel = this.map.getZoom();
    const ref = this;
    this.map.on("zoomend", function (event, comp: SideNavComponent = ref) {
      // because we're outside of Angular's zone, this change won't be detected
      comp.zLevel = comp.map.getZoom();
      // need tell Angular to detect changes
      comp.changeDetector.detectChanges();
    });
    // set active base layer
    for (const [key, layer] of Object.entries(this.baseLayers)) {
      if (this.map.hasLayer(layer)) {
        this.selectedBaseLayer = key;
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
    // FIXME can we do better with multi layer products? (i.e. prp)
    const fromActiveState: boolean = (
      event.target as HTMLInputElement
    ).className.includes("attivo");
    const op = fromActiveState ? "remove" : "add";
    if (["prp", "sf", "cc", "tpperc", "tpprob"].includes(layerId)) {
      if (op === "remove") {
        // reset sub-level
        this.selectedMap[layerId] = null;
      } else {
        // default to first value
        this.selectedMap[layerId] = this.subLevelsMap[layerId][0].value;
      }
    }
    for (const [key, layer] of Object.entries(this.overlays)) {
      if (layerId === toLayerCode(key)) {
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

  changeDataset(event, datasetId) {
    event.preventDefault();
    // clear layers
    for (const [key, layer] of Object.entries(this.overlays)) {
      if (this.map.hasLayer(layer)) {
        this.onLayerChange.emit({
          layer: layer,
          name: key,
        });
      }
    }
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
  changeSubLevel(event: Event, target: ValueLabel, layerId: string) {
    console.log(`activate layer ${layerId}, value ${target.value}`);
    for (const [key, layer] of Object.entries(this.overlays)) {
      // need to clean up
      if (layerId === toLayerCode(key) && this.map.hasLayer(layer)) {
        this.onLayerChange.emit({
          layer: layer,
          name: key,
        });
        this.selectedMap[layerId] = null;
      }
    }
    for (const [key, layer] of Object.entries(this.overlays)) {
      if (layerId === toLayerCode(key) && key === target.label) {
        this.onLayerChange.emit({
          layer: layer,
          name: toLayerTitle(layerId, target.value),
        });
        this.selectedMap[layerId] = target.value;
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
      if (layerId === toLayerCode(key) && this.map.hasLayer(layer)) {
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

  /**
   * Switch Multi Model Ensemble from one value to the other.
   */
  switchMMProduct() {
    this.mmProductSwitch = !this.mmProductSwitch;
    this.mmProduct = this.mmProductSwitch
      ? MultiModelProduct.RH
      : MultiModelProduct.TM;
    // console.log(`change Multi Model Ensemble to ${MultiModelProductLabel.get(this.mmProduct)}`);
    this.onMMProductChange.emit(this.mmProduct);
  }

  changeBaseLayer(newVal: string) {
    // console.log(`change base layer to "${newVal}"`);
    this.map.removeLayer(this.baseLayers[this.selectedBaseLayer]);
    this.map.addLayer(this.baseLayers[newVal]);
    this.selectedBaseLayer = newVal;

    for (const [key, layer] of Object.entries(this.overlays)) {
      if (this.map.hasLayer(layer)) {
        (layer as L.TileLayer).bringToFront();
      }
    }
  }
}
