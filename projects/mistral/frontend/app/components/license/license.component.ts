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
  mistral_products;
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
          this.data = response
            .filter((x) => x.name !== "COSMO-2Ipp_ecPoint")
            .filter((x) => x.name !== "multim-forecast");
          let iff_dataset =
            response.find((x) => x.name === "COSMO-2Ipp_ecPoint") || null;
          let multim_dataset =
            response.find((x) => x.name === "multim-forecast") || null;
          // console.log('Data loaded', this.data);
          if (this.data.length === 0) {
            this.notify.showWarning(
              "Unexpected result. The list of datasets is empty."
            );
          }
          // mistral products licenses
          this.mistral_products = [
            {
              name: "Observations map",
              description:
                "Observation map: graphic representation of the observational data collected in Meteo-Hub platform",
              attribution_description: "Mistral",
              license_description: "CC BY 4.0",
              license_url:
                "https://creativecommons.org/licenses/by/4.0/legalcode",
            },
            {
              name: "Forecast map",
              description:
                "Forecast map: graphic representation of the forecast data collected in Meteo-Hub platform",
              attribution_description: "Mistral",
              license_description: " CC BY-ND 4.0",
              license_url:
                "https://creativecommons.org/licenses/by-nd/4.0/legalcode",
            },
            {
              name: "Multi layer Map",
              description:
                "Graphic representation of data collected in Meteo-Hub platform from diffferent models",
              attribution_description: "Mistral",
              license_description: " CC BY-ND 4.0",
              license_url:
                "https://creativecommons.org/licenses/by-nd/4.0/legalcode",
            },
            {
              name: "IFF Map",
              description:
                "Graphic representation of forecast model Italy Flash Flood",
              attribution_description: "Mistral",
              license_description: "CC BY 4.0",
              license_url:
                "https://creativecommons.org/licenses/by/4.0/legalcode",
            },
          ];
          // append iff dataset in mistral products
          this.mistral_products.push(iff_dataset);
          // append multimodel dataset in mistral products
          this.mistral_products.push(multim_dataset);
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        this.spinner.hide();
      });
  }
}
