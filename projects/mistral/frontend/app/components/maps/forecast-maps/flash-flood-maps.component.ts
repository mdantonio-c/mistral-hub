import { Component, OnInit } from "@angular/core";
import { ForecastMapsBaseComponent } from "./forecast-maps-base.component";
import { MeteoFilter } from "./services/meteo.service";

@Component({
  selector: "app-flash-flood-maps",
  templateUrl: "./flash-flood-maps.component.html",
})
export class FlashFloodMapsComponent extends ForecastMapsBaseComponent
  implements OnInit {
  loading = false;
  filter: MeteoFilter;
  offsets: string[] = [];
  reftime: string; // YYYYMMDD

  ngOnInit() {
    super.ngOnInit();
  }

  applyFilter(filter: MeteoFilter) {
    this.loading = true;
    this.spinner.show();
    this.filter = filter;
    this.offsets.length = 0;
    //console.log(filter);

    // get data
    this.meteoService
      .getMapset(filter)
      .subscribe(
        (response) => {
          this.offsets = response.offsets;
          this.reftime = response.reftime;
          // always apply platform value from this response
          // this means request maps from that platform
          this.filter.platform = response.platform;
          if (!this.filter.env) {
            this.filter.env = "PROD";
          }
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        this.loading = false;
        this.spinner.hide();
      });
  }
}
