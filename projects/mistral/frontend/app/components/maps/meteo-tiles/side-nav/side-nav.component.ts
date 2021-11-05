import {
  ChangeDetectionStrategy,
  Component,
  Input,
  Output,
  OnDestroy,
  OnInit,
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
export class SideNavComponent implements OnInit, OnDestroy {
  @Input() overlays: L.Control.LayersObject;
  @Input() dataset: string;
  @Input() map: L.Map;

  @Output() onZoomIn: EventEmitter<null> = new EventEmitter<null>();
  @Output() onZoomOut: EventEmitter<null> = new EventEmitter<null>();
  @Output() onLayerChange: EventEmitter<Record<string, string | L.Layer>> =
    new EventEmitter<Record<string, string | L.Layer>>();
  @Output() onDatasetChange: EventEmitter<string> = new EventEmitter<string>();

  public isCollapsed = false;
  public availableDatasets = DATASETS;

  subscription: Subscription = new Subscription();
  routeDataSubscription!: Subscription;

  constructor(private el: ElementRef, private renderer: Renderer2) {}

  ngOnInit() {}

  ngOnChanges(changes: SimpleChanges): void {
    const isFirstChange = Object.values(changes).some((c) => c.isFirstChange());
    if (isFirstChange) {
      return;
    }

    // activate layers
    let activeLayers: string[] = [];
    if (this.overlays) {
      for (const [key, layer] of Object.entries(this.overlays)) {
        let lCode = this._toLayerCode(key);
        if (lCode) {
          let el = this.el.nativeElement.querySelector(`.${lCode}`);
          if (this.map.hasLayer(layer)) {
            activeLayers.push(key);
            this.renderer.addClass(el, "attivo");
          } else {
            this.renderer.removeClass(el, "attivo");
          }
        }
      }
      console.log(`active layers`, activeLayers);
    }
  }

  ngOnDestroy() {
    this.subscription.unsubscribe();
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

  toggleLayer(event, layerId: string) {
    event.preventDefault();
    for (const [key, layer] of Object.entries(this.overlays)) {
      if (layerId === this._toLayerCode(key)) {
        // this.onLayerChange.emit(layer);
        this.onLayerChange.emit({
          layer: layer,
          name: this._toLayerTitle(layerId),
        });
        // activate / deactivate
        let el = this.el.nativeElement.querySelector(`.${layerId}`);
        el.classList.contains("attivo")
          ? this.renderer.removeClass(el, "attivo")
          : this.renderer.addClass(el, "attivo");
        break;
      }
    }
  }

  /**
   * Adds an overlay (checkbox entry) with the given name to the control.
   * @param layer
   * @param name
   */
  addOverlay(layer, name: string) {}

  /**
   * Remove the given layer from the control.
   * @param layer
   */
  removeLayer(layer) {}

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
      case DP.PREC1P || DP.PREC3P || DP.PREC6P || DP.PREC12P || DP.PREC24P:
        return "prp";
      case DP.SF1 || DP.SF3 || DP.SF6 || DP.SF12 || DP.SF24:
        return "sf";
      case DP.LCC || DP.MCC || DP.HCC:
        return "cc";
      default:
        return null;
    }
  }

  private _toLayerTitle(code: string): string | null {
    switch (code) {
      case "t2m":
        return DP.TM2;
      case "prs":
        return DP.PMSL;
      case "rh":
        return DP.RH;
      case "prp":
        return DP.PREC1P;
      case "sf":
        return DP.SF1;
      case "cc":
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
}
