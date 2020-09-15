import { Component, ViewChild, ViewEncapsulation } from "@angular/core";
import { ObsFilter } from "./services/obs.service";
import { ObsMapComponent } from "./obs-map/obs-map.component";
import { ObsMeteogramsComponent } from "./obs-meteograms/obs-meteograms.component";

import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { ObsStationReportComponent } from "./obs-station-report/obs-station-report.component";
import { ObsDownloadComponent } from "./obs-download/obs-download.component";

@Component({
  selector: "app-observation-maps",
  templateUrl: "./observation-maps.component.html",
  styleUrls: ["./observation-maps.component.css"],
  encapsulation: ViewEncapsulation.None,
})
export class ObservationMapsComponent {
  totalItems: number = 0;
  currentView: string = "Data";
  filter: ObsFilter;

  constructor(private modalService: NgbModal) {}

  @ViewChild(ObsMapComponent) map: ObsMapComponent;
  @ViewChild(ObsMeteogramsComponent) chart: ObsMeteogramsComponent;

  applyFilter(filter?: ObsFilter, update = false) {
    if (filter) {
      this.filter = filter;
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
