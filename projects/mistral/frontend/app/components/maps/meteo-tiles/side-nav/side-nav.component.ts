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
  @Output() onLayerChange: EventEmitter<string> = new EventEmitter<string>();
  @Output() onDatasetChange: EventEmitter<string> = new EventEmitter<string>();

  public isCollapsed = false;

  subscription: Subscription = new Subscription();
  routeDataSubscription!: Subscription;

  constructor(private el: ElementRef, private renderer: Renderer2) {}

  ngOnInit() {}

  ngOnChanges(changes: SimpleChanges): void {
    const isFirstChange = Object.values(changes).some((c) => c.isFirstChange());
    if (isFirstChange) {
      return;
    }
    // activate selected dataset
    const selectorElements = this.el.nativeElement.querySelectorAll(
      ".selettore-dataset > a"
    );
    selectorElements.forEach((el) => {
      this.renderer.removeClass(el, "selected");
    });
    let datasetEl = this.el.nativeElement.querySelector(
      `.selettore-dataset #${this._escapeChars(this.dataset)}`
    );
    if (datasetEl) {
      this.renderer.addClass(datasetEl, "selected");
    }

    // activate layers
    let activeLayers: string[] = [];
    if (this.overlays) {
      for (const [key, layer] of Object.entries(this.overlays)) {
        if (this.map.hasLayer(layer)) {
          activeLayers.push(key);
          let lCode = this._toLayerCode(key);
          if (lCode) {
            let el = this.el.nativeElement.querySelector(`.${lCode}`);
            this.renderer.addClass(el, "attivo");
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
    this.onLayerChange.emit(layerId);
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
      // TODO add the other overlay titles
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
