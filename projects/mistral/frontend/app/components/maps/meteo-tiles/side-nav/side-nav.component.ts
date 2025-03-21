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
} from "@angular/core";
import {
  DatasetProduct as DP,
  DATASETS,
  MOBILE_WIDTH,
  ViewModes,
} from "../meteo-tiles.config";
import * as L from "leaflet";
import {
  CLOUD_LEVELS,
  PRECIPITATION_HOURS,
  SNOW_HOURS,
  toLayerCode,
  toLayerTitle,
} from "./data";
import { GenericArg, ValueLabel } from "../../../../types";

interface ValueLabelChecked extends ValueLabel {
  checked?: boolean;
}

@Component({
  selector: "map-side-nav",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./side-nav.component.html",
  styleUrls: ["side-nav.component.scss"],
})
export class SideNavComponent implements OnInit {
  @Input() baseLayers: L.Control.LayersObject;
  @Input() dataset: string;
  @Input("variables") varConfig: GenericArg;
  @Input("viewMode") mode = ViewModes.adv;
  // Reference to the primary map object
  @Input() map: L.Map;
  @Input() lang = "en";

  private _overlays: L.Control.LayersObject;
  modes = ViewModes;
  datasetTooltip: string = "Dataset";

  @Input() set overlays(value: L.Control.LayersObject) {
    this._overlays = value;
    if (!value) return;
    // reset subLevels
    for (const [key, value] of Object.entries(this.subLevels)) {
      this.subLevels[key].forEach((level) => {
        level.checked = false;
      });
    }
    //console.log(this._overlays);
    // activate layers
    for (const [key, layer] of Object.entries(this._overlays)) {
      let lCode = toLayerCode(key);

      if (lCode) {
        const el = this.el.nativeElement.querySelector(`.${lCode}`);
        this.renderer.removeClass(el, "attivo");
        if (this.map.hasLayer(layer)) {
          if (Object.keys(this.subLevels).includes(lCode)) {
            this.subLevels[lCode][0].checked = true;
          }
          setTimeout(() => {
            this.renderer.addClass(el, "attivo");
          }, 0);
        }
      }
      // work around to force deactivation of the wind icon when changhing dataset
      const fooEl = this.el.nativeElement.querySelector(`.ws10m`);
      this.renderer.removeClass(fooEl, "attivo");
    }
  }

  get overlays(): L.Control.LayersObject {
    return this._overlays;
  }

  @Output() onLayerChange: EventEmitter<Record<string, string | L.Layer>> =
    new EventEmitter<Record<string, string | L.Layer>>();
  @Output() onDatasetChange: EventEmitter<string> = new EventEmitter<string>();

  zLevel: number;

  isCollapsed = false;
  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();

  availableDatasets = DATASETS;

  subLevels: { [key: string]: ValueLabelChecked[] } = {};
  selectedBaseLayer: string;
  showTotalClouds: boolean = false;
  @Output() showScalarWindChange = new EventEmitter<boolean>();
  showScalarWind: boolean = false;
  @Output() showPrsScalarFieldChange = new EventEmitter<boolean>();
  showPrsScalarField: boolean = false;
  selectedLayers: string[] = ["t2m"]; //default layer
  @Output() selectedCumulateChange = new EventEmitter<string[]>();
  selectedCumulate: string[] = ["", ""];
  maxLayers = 4;

  constructor(
    private el: ElementRef,
    private renderer: Renderer2,
    private changeDetector: ChangeDetectorRef,
  ) {}

  changeCollapse() {
    this.isCollapsed = !this.isCollapsed;
    this.onCollapseChange.emit(this.isCollapsed);
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

    const SUB_LEVELS: { [key: string]: ValueLabel[] } = {
      prp: PRECIPITATION_HOURS,
      sf: SNOW_HOURS,
      cc: CLOUD_LEVELS,
    };
    Object.keys(SUB_LEVELS).forEach((key) => {
      if (Object.keys(this.varConfig).includes(key)) {
        this.subLevels[key] = SUB_LEVELS[key].filter((obj) => {
          return this.varConfig[key].includes(obj.value);
        });
        this.subLevels[key].forEach((level) => {
          level.checked = false;
        });
      }
    });
    // setup mobile side-nav
    if (window.innerWidth < MOBILE_WIDTH) {
      this.changeCollapse();
    }
  }

  @HostListener("window:resize", ["$event"])
  onWindowResize(event) {
    if (event.target.innerWidth < MOBILE_WIDTH && !this.isCollapsed) {
      this.changeCollapse();
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

  disableRuleScalarPrsButton() {
    const fooEl = this.el.nativeElement.querySelectorAll("span.prs");
    let bool = true;
    if (fooEl) {
      if (fooEl[0].className === "prs clickable") {
        return bool;
      } else {
        return !bool;
      }
    }
  }
  disabledRuleScalarWindButton() {
    const fooEl = this.el.nativeElement.querySelectorAll("span.ws10m");
    let bool = true;
    if (fooEl) {
      if (fooEl[0].className === "ws10m clickable") {
        return bool;
      } else {
        return !bool;
      }
    }
  }
  max4Layer(layerId) {
    const index = this.selectedLayers.indexOf(layerId);
    if (index > -1) {
      this.selectedLayers.splice(index, 1);
    } else {
      if (this.selectedLayers.length >= this.maxLayers) {
        return true;
      }
      this.selectedLayers.push(layerId);
    }
    return false;
  }

  // force active state to the parent layer element
  toggleLayer(event: Event, layerId: string) {
    event.preventDefault();

    // max 4 fields at time
    if (this.max4Layer(layerId)) return;
    console.log(this.selectedLayers);
    // can we do better with multi layer products? (i.e. prp)
    let el = this.el.nativeElement.querySelector(`span.${layerId}`);
    const fromActiveState: boolean = el.classList.contains("attivo");
    const op = fromActiveState ? "remove" : "add";
    console.log(`toggle "${op}" on layer-id "${layerId}"`);
    if (
      ["prp", "sf", "cc", "tpperc", "tpprob"].includes(layerId) &&
      this.subLevels[layerId].length
    ) {
      // expected sub-levels here
      if (op === "remove") {
        // reset sub-level
        this.subLevels[layerId].forEach((level) => {
          level.checked = false;
        });
        if (layerId === "cc") {
          this.showTotalClouds = false;
        }
      } else {
        // default to first value
        this.subLevels[layerId][0].checked = true;
      }
    }
    // this.changeDetector.detectChanges();
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
    fromActiveState
      ? this.renderer.removeClass(el, "attivo")
      : this.renderer.addClass(el, "attivo");
    //console.log(el);
  }

  changeDataset(event, datasetId) {
    event.preventDefault();
    // clear layers
    /*this.map.eachLayer((l)=>{
      if(this.map.hasLayer(l)) {
        console.log('LAYER ATTIVO',l);
      }
    });*/
    for (const [key, layer] of Object.entries(this.overlays)) {
      if (this.map.hasLayer(layer)) {
        console.log("name", key, "layer", layer);
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

  preventActions(event: Event, target: ValueLabelChecked, layerId: string) {
    if (
      this.showTotalClouds ||
      (target.checked &&
        this.subLevels[layerId].map((x) => x.checked).filter(Boolean).length ===
          1)
    ) {
      event.preventDefault();
    }
  }

  /**
   * Activate / Deactivate a layer with sub-levels
   * @param event
   * @param target
   * @param layerId
   */
  changeSubLevel(
    event: Event,
    target: ValueLabel,
    layerId: string,
    multiSelection = false,
  ) {
    // max 4 fields at time
    if (this.max4Layer(layerId)) return;
    console.log(this.selectedLayers);

    console.log(`activate layer ${layerId}, value ${target.value}`);
    // force active state to the parent layer element

    let el = this.el.nativeElement.querySelector(`span.${layerId}`);

    const isActive: boolean = el.classList.contains("attivo");
    if (!isActive) {
      this.renderer.addClass(el, "attivo");
    }
    for (const [key, layer] of Object.entries(this.overlays)) {
      // need to clean up
      if (
        !multiSelection &&
        layerId === toLayerCode(key) &&
        this.map.hasLayer(layer)
      ) {
        this.onLayerChange.emit({
          layer: layer,
          name: key,
        });
        // this.subLevels[layerId] = null;
        this.subLevels[layerId].forEach((level) => {
          level.checked = false;
        });
      }
    }
    for (const [key, layer] of Object.entries(this.overlays)) {
      if (layerId === toLayerCode(key) && key === target.label) {
        console.log(layerId, toLayerCode(key), target.label, key);
        this.onLayerChange.emit({
          layer: layer,
          name: toLayerTitle(layerId, target.value),
        });
        if (!multiSelection) {
          const idx = this.subLevels[layerId].findIndex(
            (level) => level.value === target.value,
          );
          this.subLevels[layerId][idx].checked =
            !this.subLevels[layerId][idx].checked;
        }
        break;
      }
    }
  }

  setFirstCumulated(event: Event, value: string, layerId: string) {
    this.selectedCumulate = [layerId, value];
    this.selectedCumulateChange.emit(this.selectedCumulate);
  }

  toggleScalarWind() {
    this.showScalarWind = !this.showScalarWind;
    this.showScalarWindChange.emit(this.showScalarWind);
  }

  toggleScalarPrs() {
    this.showPrsScalarField = !this.showPrsScalarField;
    this.showPrsScalarFieldChange.emit(this.showPrsScalarField);
  }

  toggleTotalClouds(layerId: string) {
    // max 4 layers at time
    if (this.max4Layer(layerId)) return;
    console.log(this.selectedLayers);
    // force active state to the parent layer element
    let el = this.el.nativeElement.querySelector("span.cc");
    const isActive: boolean = el.classList.contains("attivo");
    if (!isActive) {
      this.renderer.addClass(el, "attivo");
    }
    this.showTotalClouds = !this.showTotalClouds;
    if (this.showTotalClouds) {
      // remove active layers for cloud sub-levels
      let tccLayer;
      for (const [key, layer] of Object.entries(this.overlays)) {
        if (
          [`${DP.LCC}`, `${DP.MCC}`, `${DP.HCC}`].includes(key) &&
          this.map.hasLayer(layer)
        ) {
          this.onLayerChange.emit({ layer: layer, name: key });
        } else if (key === `${DP.TCC}`) {
          tccLayer = layer;
        }
      }
      // show total clouds
      if (tccLayer) {
        this.onLayerChange.emit({
          layer: tccLayer,
          name: `${DP.TCC}`,
        });
      }
      this.subLevels["cc"].forEach((level) => {
        level.checked = false;
      });
    } else {
      for (const [key, layer] of Object.entries(this.overlays)) {
        if ([`${DP.TCC}`].includes(key) && this.map.hasLayer(layer)) {
          // remove total cloud layer
          this.onLayerChange.emit({ layer: layer, name: key });
        }
      }
      this.subLevels["cc"][0].checked = true;
      this.onLayerChange.emit({
        layer: this.overlays[`${DP.LCC}`],
        name: `${DP.LCC}`,
      });
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

  changeBaseLayer(newVal: string) {
    // console.log(`change base layer to "${newVal}"`);
    this.map.removeLayer(this.baseLayers[this.selectedBaseLayer]);
    this.map.addLayer(this.baseLayers[newVal]);
    this.selectedBaseLayer = newVal;

    for (const [key, layer] of Object.entries(this.overlays)) {
      if (this.map.hasLayer(layer)) {
        (layer as L.TileLayer).bringToFront;
      }
    }
  }
}
