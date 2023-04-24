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
import { GenericArg, ValueLabel } from "../../../types";
import { MOBILE_WIDTH, ViewModes } from "../meteo-tiles/meteo-tiles.config";
import { toLayerCode } from "../meteo-tiles/side-nav/data";

interface ValueLabelChecked extends ValueLabel {
  checked?: boolean;
}

@Component({
  selector: "side-nav-filter",
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: "./side-nav.component.html",
  styleUrls: ["side-nav.component.scss"],
})
export class SideNavFilterComponent implements OnInit {
  //@Input() baseLayers: L.Control.LayersObject;
  @Input("variables") varConfig: GenericArg;
  @Input("viewMode") mode = ViewModes.adv;
  // Reference to the primary map object
  @Input() map: L.Map;

  private _overlays: L.Control.LayersObject;
  modes = ViewModes;
  lang = "en";

  isCollapsed = false;
  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() onLayerChange: EventEmitter<Record<string, string | L.Layer>> =
    new EventEmitter<Record<string, string | L.Layer>>();

  zLevel: number;

  /*@Input() set overlays(value: L.Control.LayersObject) {
    this._overlays = value;
    if (!value) return;
    // reset subLevels
    for (const [key, value] of Object.entries(this.subLevels)) {
      this.subLevels[key].forEach((level) => {
        level.checked = false;
      });
    }
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
    }
  }

  get overlays(): L.Control.LayersObject {
    return this._overlays;
  }*/

  constructor(
    private el: ElementRef,
    private renderer: Renderer2,
    private changeDetector: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.zLevel = this.map.getZoom();
    const ref = this;
    this.map.on(
      "zoomend",
      function (event, comp: SideNavFilterComponent = ref) {
        // because we're outside of Angular's zone, this change won't be detected
        comp.zLevel = comp.map.getZoom();
        // need tell Angular to detect changes
        comp.changeDetector.detectChanges();
      },
    );
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

  changeCollapse() {
    this.isCollapsed = !this.isCollapsed;
    this.onCollapseChange.emit(this.isCollapsed);
  }

  toggleLayer(event: Event, layerId: string) {
    event.preventDefault();
    let el = this.el.nativeElement.querySelector(`span.${layerId}`);
    const fromActiveState: boolean = el.classList.contains("attivo");
    const op = fromActiveState ? "remove" : "add";
    console.log(`toggle "${op}" on layer-id "${layerId}"`);

    this.onLayerChange.emit({
      layer: layerId,
      name: layerId,
    });

    // update active class
    fromActiveState
      ? this.renderer.removeClass(el, "attivo")
      : this.renderer.addClass(el, "attivo");
  }
}
