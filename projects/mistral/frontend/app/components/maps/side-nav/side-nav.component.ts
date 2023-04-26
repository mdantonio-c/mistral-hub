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
import { KeyValue } from "@angular/common";
import { GenericArg, ValueLabel } from "../../../types";
import { MOBILE_WIDTH, ViewModes } from "../meteo-tiles/meteo-tiles.config";

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
  @Input() baseLayers: L.Control.LayersObject;
  @Input("variables") varConfig: GenericArg;
  @Input("viewMode") mode = ViewModes.adv;
  @Input() overlap: boolean = true;
  // Reference to the primary map object
  @Input() map: L.Map;
  @Input() minZoom: number = 5;
  @Input() maxZoom: number = 12;

  private _overlays: L.Control.LayersObject;
  modes = ViewModes;
  lang = "en";

  isCollapsed = false;
  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() onLayerChange: EventEmitter<Record<string, string | L.Layer>> =
    new EventEmitter<Record<string, string | L.Layer>>();

  zLevel: number;

  @Input() set overlays(value: L.Control.LayersObject) {
    this._overlays = value;
    if (!value) return;
    // activate layers
    let lCode: string;
    if (this._overlays.options["pane"]) {
      const pane = this._overlays.options["pane"];
      for (const [key, value] of Object.entries(this.varConfig)) {
        if (value.code && value.code === pane) {
          lCode = key;
          break;
        }
      }
      const el = this.el.nativeElement.querySelector(`.${lCode}`);
      if (el) {
        this.renderer.removeClass(el, "attivo");
        setTimeout(() => {
          this.renderer.addClass(el, "attivo");
        }, 0);
      }
    }
  }

  get overlays(): L.Control.LayersObject {
    return this._overlays;
  }

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
    // console.log(`toggle "${op}" on layer-id "${layerId}"`);
    if (!this.overlap) {
      if (fromActiveState) {
        // DO NOTHING
        return;
      } else {
        // deactivate links
        let matches = this.el.nativeElement.querySelectorAll("span.attivo");
        matches.forEach((item) => {
          this.renderer.removeClass(item, "attivo");
        });
      }
    }

    this.onLayerChange.emit({
      layer: layerId,
      name: layerId,
    });

    // update active class
    fromActiveState
      ? this.renderer.removeClass(el, "attivo")
      : this.renderer.addClass(el, "attivo");
  }

  // Order by ascending order property value
  valueAscOrder = (
    a: KeyValue<string, any>,
    b: KeyValue<string, any>,
  ): number => {
    return String(a.value.oder).localeCompare(String(b.value.order));
  };
}
