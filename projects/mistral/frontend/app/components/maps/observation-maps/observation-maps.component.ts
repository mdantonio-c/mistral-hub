import { Component, ViewChild, ViewEncapsulation } from "@angular/core";
import { ObsFilter } from "./services/obs.service";
import { ObsMapComponent } from "./obs-map/obs-map.component";
import { ObsMeteogramsComponent } from "./obs-meteograms/obs-meteograms.component";

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

  @ViewChild(ObsMapComponent) map: ObsMapComponent;
  @ViewChild(ObsMeteogramsComponent) chart: ObsMeteogramsComponent;

  applyFilter(filter?: ObsFilter) {
    if (filter) {
      this.filter = filter;
    }
    if (this.filter) {
      this.filter.onlyStations = this.currentView === "Stations";
      setTimeout(() => {
        this.currentView !== "Meteograms"
          ? this.map.updateMap(this.filter)
          : this.chart.updateChart(this.filter);
      }, 0);
    }
  }

  changeView(view) {
    this.currentView = view;
    this.applyFilter();
  }
}
