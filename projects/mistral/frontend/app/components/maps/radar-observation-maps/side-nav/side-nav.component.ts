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
import { GenericArg, ValueLabel } from "../../../../types";
import { MOBILE_WIDTH, ViewModes } from "../../meteo-tiles/meteo-tiles.config";
import { SRT_ADJ_HOURS, toLayerCode, Products } from "./data";
interface ValueLabelChecked extends ValueLabel {
  checked?: boolean;
}
@Component({
  selector: "app-side-nav",
  templateUrl: "./side-nav.component.html",
  styleUrls: ["./side-nav.component.scss"],
})
export class SideNavComponentRadar implements OnInit {
  @Input("variables") varConfig: GenericArg;
  @Input("viewMode") mode = ViewModes.adv;
  @Input() baseLayers: L.Control.LayersObject;
  @Input() map: L.Map;
  @Input() lang = "en";
  @Input() set overlays(value: L.Control.LayersObject) {
    this._overlays = value;
    if (!value) return;
    // reset subLevels
    for (const [key, value] of Object.entries(this.subLevels)) {
      this.subLevels[key].forEach((level) => {
        level.checked = false;
      });
    }

    setTimeout(() => {
      // activate layers
      for (const [key, layer] of Object.entries(this._overlays)) {
        let lCode = toLayerCode(key);

        if (lCode) {
          const el = this.el.nativeElement.querySelector(`.${lCode}`);

          if (el) {
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
        }
      }
    }, 0);
  }
  get overlays(): L.Control.LayersObject {
    return this._overlays;
  }
  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() selectedCumulateChange = new EventEmitter<string[]>();
  @Output() onLayerChange: EventEmitter<Record<string, string | L.Layer>> =
    new EventEmitter<Record<string, string | L.Layer>>();

  subLevels: { [key: string]: ValueLabelChecked[] } = {};
  selectedBaseLayer: string;
  selectedCumulate: string[] = ["", ""];
  private _overlays: L.Control.LayersObject;
  modes = ViewModes;
  zLevel: number;
  isCollapsed = false;
  selectedLayers: string = Products.SRI;

  constructor(
    private el: ElementRef,
    private renderer: Renderer2,
    private changeDetector: ChangeDetectorRef,
  ) {}

  changeCollapse() {
    this.isCollapsed = !this.isCollapsed;
    this.onCollapseChange.emit(this.isCollapsed);
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

  ngOnInit(): void {
    this.zLevel = this.map.getZoom();
    const ref = this;
    this.map.on("zoomend", function (event, comp: SideNavComponentRadar = ref) {
      // because we're outside of Angular's zone, this change won't be detected
      comp.zLevel = comp.map.getZoom();
      // need tell Angular to detect changes
      comp.changeDetector.detectChanges();
    });

    for (const [key, layer] of Object.entries(this.baseLayers)) {
      if (this.map.hasLayer(layer)) {
        this.selectedBaseLayer = key;
      }
    }
    let SUB_LEVELS: { [key: string]: ValueLabel[] } = {
      srt_adj: SRT_ADJ_HOURS,
    };

    Object.keys(SUB_LEVELS).forEach((key) => {
      if (Object.keys(this.varConfig).includes(key)) {
        //console.log(key, SUB_LEVELS[key]);
        this.subLevels[key] = SUB_LEVELS[key].filter((obj) => {
          return this.varConfig[key].includes(obj.value);
        });
        this.subLevels[key].forEach((level) => {
          level.checked = false;
        });
      }
    });
    if (window.innerWidth < MOBILE_WIDTH) {
      this.changeCollapse();
    }
  }

  /**
   * Activate / Deactivate a layer with sub-levels
   * @param event
   * @param target
   * @param layerId
   */
  changeSubLevel(event: Event, target: ValueLabel, layerId: string) {
    console.log(`activate layer ${layerId}, value ${target.value}`);
    // force active state to the parent layer element

    let el = this.el.nativeElement.querySelector(`span.${layerId}`);

    const isActive: boolean = el.classList.contains("attivo");
    if (!isActive) {
      this.renderer.addClass(el, "attivo");
    }
  }
  setFirstCumulated(event: Event, value: string, layerId: string) {
    this.selectedCumulate = [layerId, value];
    this.selectedCumulateChange.emit(this.selectedCumulate);
  }
  toggleLayer(event: Event, layerId: string) {
    event.preventDefault();

    for (const key of Object.keys(this.varConfig)) {
      if (key === layerId) continue;

      const el = this.el.nativeElement.querySelector(`span.${key}`);
      if (!el) continue;

      this.renderer.removeClass(el, "attivo");
      if (this.subLevels[key])
        this.subLevels[key].forEach((level) => {
          level.checked = false;
        });
    }

    const clickedEl = this.el.nativeElement.querySelector(`span.${layerId}`);
    if (clickedEl) {
      this.renderer.addClass(clickedEl, "attivo");
    }
    if (this.subLevels[layerId] && this.subLevels[layerId].length) {
      this.subLevels[layerId][0].checked = true;
      this.setFirstCumulated(event, this.subLevels[layerId][0].value, layerId);
    }

    for (const [key, layer] of Object.entries(this.overlays)) {
      if (layerId === toLayerCode(key)) {
        this.onLayerChange.emit({
          layer: layer,
          name: key,
        });
        break;
      }
    }
  }

  changeBaseLayer(newVal: string) {
    if (!this.map || !this.baseLayers) return;

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
