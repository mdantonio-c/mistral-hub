import { Component, OnInit } from "@angular/core";
import { DataService } from "../../services/data.service";
import { NotificationService } from "@rapydo/services/notification";
import { ColumnMode } from "@swimlane/ngx-datatable";
import { NgxSpinnerService } from "ngx-spinner";

@Component({
  selector: "license",
  templateUrl: "./license.component.html",
})
export class LicenseComponent implements OnInit {
  data;
  maps_data;
  ColumnMode = ColumnMode;

  constructor(
    private dataService: DataService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {}

  ngOnInit() {
    this.spinner.show();

    this.dataService
      .getDatasets(true)
      .subscribe(
        (response) => {
          this.data = response;
          // console.log('Data loaded', this.data);
          if (this.data.length === 0) {
            this.notify.showWarning(
              "Unexpected result. The list of datasets is empty."
            );
          }
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        this.spinner.hide();
      });
    // maps licenses
    this.maps_data = [
      {
        name: "Observations map",
        description:
          "Observation map: graphic representation of the observational data collected in Meteo-Hub platform",
        attribution_description: "Mistral",
        license_description: "CC BY 4.0",
        license_url: "https://creativecommons.org/licenses/by/4.0/legalcode",
      },
      {
        name: "Forecast map",
        description:
          "Forecast map: graphic representation of the forecast data collected in Meteo-Hub platform",
        attribution_description: "Mistral",
        license_description: " CC BY-ND 4.0",
        license_url: "https://creativecommons.org/licenses/by-nd/4.0/legalcode",
      },
      {
        name: "Multi layer Map",
        description:
          "Graphic representation of data collected in Meteo-Hub platform from diffferent models",
        attribution_description: "Mistral",
        license_description: " CC BY-ND 4.0",
        license_url: "https://creativecommons.org/licenses/by-nd/4.0/legalcode",
      },
      {
        name: "IFF",
        description:
          "Graphic representation of forecast model Italy Flash Flood",
        attribution_description: "Mistral",
        license_description: "CC BY 4.0",
        license_url: "https://creativecommons.org/licenses/by/4.0/legalcode",
      },
    ];
  }
}
