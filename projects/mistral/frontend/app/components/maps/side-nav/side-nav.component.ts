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
import { GenericArg, ValueLabel, ObsFilter } from "../../../types";
import { MOBILE_WIDTH, ViewModes } from "../meteo-tiles/meteo-tiles.config";
import {
  NETWORK_NAMES,
  NETWORKS,
  sharedSideNav,
} from "../meteo-tiles/services/data";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { ObsDownloadComponent } from "../observation-maps/obs-download/obs-download.component";

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
  @Input() lang = "en";
  @Input() overlap: boolean = true;
  // Reference to the primary map object
  @Input() map: L.Map;
  @Input() minZoom: number = 5;
  @Input() maxZoom: number = 12;
  @Input() mode_1!: sharedSideNav;

  private _overlays: L.Control.LayersObject;
  private network: string = "";

  modes = ViewModes;
  //lang = "en";

  isCollapsed = false;
  @Output() onCollapseChange: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() onLayerChange: EventEmitter<Record<string, string | L.Layer>> =
    new EventEmitter<Record<string, string | L.Layer>>();
  @Output() onWindConvert: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() onQualityControlFilter: EventEmitter<boolean> =
    new EventEmitter<boolean>();
  @Output() onNetworkChangeEmitter: EventEmitter<string> =
    new EventEmitter<string>();
  @Output() filterDownload: EventEmitter<ObsFilter | ObsFilter[]> =
    new EventEmitter<ObsFilter | ObsFilter[]>();
  windShow = false;
  windConvert = false;
  zLevel: number;
  dropdownOptions: string[] = NETWORK_NAMES;
  selectedOption: string = "All";
  selectedQuality = false;
  showObsFilter = false;

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
    private modalService: NgbModal,
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
    this.selectedQuality = false;
    if (this.mode_1 === sharedSideNav.livemapComp) {
      this.showObsFilter = false;
      console.log(this.showObsFilter);
    } else {
      this.showObsFilter = true;
      console.log(this.showObsFilter);
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

  onNetworkChange(value: string) {
    console.log("Network selezionato:", value);
    if (value === "All") this.network = "";
    else this.network = value;
    this.onNetworkChangeEmitter.emit(value);
  }
  onQualitySelected(event) {
    const isChecked = (event.target as HTMLInputElement).checked;
    this.onQualityControlFilter.emit(isChecked);
    this.selectedQuality = isChecked;
  }
  download() {
    this.filterDownload.emit(this.toObsFilter());
  }
  changeCollapse() {
    this.isCollapsed = !this.isCollapsed;
    this.onCollapseChange.emit(this.isCollapsed);
  }

  private toObsFilter(): ObsFilter | ObsFilter[] {
    console.log(this.network);
    let filter: ObsFilter = {
      product: this._overlays.options["pane"],
      reftime: new Date(),
      time: [0, 23],
      license: "CCBY_COMPLIANT",
      network: this.network
        ? NETWORKS.find((n) => n.name === this.network).network
        : "",
    };

    if (this._overlays.options["pane"] === "B13011") {
      filter.timerange = "1,0,3600";
      filter.level = "1,0,0,0";
    } else if (
      ["B12101", "B10004", "B13003", "B13013"].includes(
        this._overlays.options["pane"],
      )
    ) {
      filter.timerange = "254,0,0"; //temp:B12101,pressure:B10004,rh:"B13003",snow:"B13013"
      if (
        this._overlays.options["pane"] === "B10004" ||
        this._overlays.options["pane"] === "B13013"
      )
        filter.level = "1,0,0,0";
      else filter.level = "103,2000,0,0";
    } else if (this._overlays.options["pane"] === "B11002 or B11001") {
      let filter2 = { ...filter };
      filter.product = "B11001";
      filter.timerange = "254,0,0";
      filter.level = "103,10000,0,0";
      filter.reliabilityCheck = true;
      filter2.product = "B11002";
      filter2.timerange = filter.timerange;
      filter2.level = filter.level;
      filter2.reliabilityCheck = true;
      this.openDownload([filter, filter2]);
      return [filter, filter2];
    }

    filter.reliabilityCheck = true;
    // da continuare quando applico il contro filter
    /*if (form.reliabilityCheck) {
      filter.reliabilityCheck = true;
    }*/
    this.openDownload(filter);
    return filter;
  }
  openDownload(filter: ObsFilter | ObsFilter[]) {
    const modalRef = this.modalService.open(ObsDownloadComponent, {
      backdrop: "static",
      keyboard: false,
    });
    modalRef.componentInstance.filter = filter;
  }

  toggleWindConvert() {
    this.windConvert = !this.windConvert;
    this.onWindConvert.emit(this.windConvert);
  }

  toggleLayer(event: Event, layerId: string) {
    event.preventDefault();
    let el = this.el.nativeElement.querySelector(`span.${layerId}`);
    const fromActiveState: boolean = el.classList.contains("attivo");
    const op = fromActiveState ? "remove" : "add";
    if (layerId === "ws10m" && op == "add") {
      this.windShow = true;
    } else this.windShow = false;

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
    return String(a.value.order).localeCompare(String(b.value.order));
  };
}
