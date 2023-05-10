import {
  Component,
  OnInit,
  Output,
  ViewChild,
  ViewEncapsulation,
  EventEmitter,
} from "@angular/core";
import { ActivatedRoute, Router, Params } from "@angular/router";
import { ObsFilter } from "../../../types";
import { ObsMapComponent } from "./obs-map/obs-map.component";
import { ObsMeteogramsComponent } from "./obs-meteograms/obs-meteograms.component";

import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { ObsStationReportComponent } from "./obs-station-report/obs-station-report.component";
import { ObsDownloadComponent } from "./obs-download/obs-download.component";

@Component({
  selector: "app-observation-maps",
  templateUrl: "./observation-maps.component.html",
  styleUrls: ["./observation-maps.component.scss"],
  encapsulation: ViewEncapsulation.None,
})
export class ObservationMapsComponent implements OnInit {
  totalItems: number = 0;
  currentView: string = "Data";
  filter: ObsFilter;

  /** keep network preset value on init */
  // @Output() preset: EventEmitter<string> = new EventEmitter<string>();
  preset: string;

  constructor(
    private modalService: NgbModal,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  @ViewChild(ObsMapComponent) map: ObsMapComponent;
  @ViewChild(ObsMeteogramsComponent) chart: ObsMeteogramsComponent;

  ngOnInit() {
    this.route.queryParams.subscribe((params: Params) => {
      if (params["network"]) {
        // console.log(`apply network ${params["network"]} to the filter`);
        // this.preset.emit(params["network"]);
        this.preset = params["network"];
        // clean the url from the query parameter
        this.router.navigate([], {
          queryParams: { network: null },
          queryParamsHandling: "merge",
        });
      }
    });
  }

  applyFilter(filter?: ObsFilter, update = false) {
    if (filter) {
      this.filter = filter;
      // if (this.preset) {
      //   this.filter.network = this.preset;
      //   this.preset = null;
      // }
    }
    if (this.filter) {
      this.filter.onlyStations = this.currentView === "Stations";
      setTimeout(() => {
        this.currentView !== "Meteograms"
          ? this.map.updateMap(this.filter, update)
          : this.chart.updateChart(this.filter, update);
      }, 0);
    }
  }

  openDownload(filter: ObsFilter) {
    const modalRef = this.modalService.open(ObsDownloadComponent, {
      backdrop: "static",
      keyboard: false,
    });
    modalRef.componentInstance.filter = filter;
  }

  changeView(view) {
    this.currentView = view;
    this.applyFilter();
  }
}
