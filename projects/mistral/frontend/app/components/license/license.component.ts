import { Component, OnInit } from "@angular/core";
import { DataService } from "../../services/data.service";
import { NotificationService } from "@rapydo/services/notification";
import { ColumnMode } from "@swimlane/ngx-datatable";
import { NgxSpinnerService } from "ngx-spinner";
import { Router, Scroll } from "@angular/router";

@Component({
  selector: "license",
  templateUrl: "./license.component.html",
})
export class LicenseComponent implements OnInit {
  data;
  mistral_products;
  ColumnMode = ColumnMode;
  loading: boolean = false;

  constructor(
    private dataService: DataService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private router: Router,
  ) {
    this.router.events.subscribe((event: any) => {
      if (event instanceof Scroll && event.anchor) {
        setTimeout(() => {
          this.scroll("#" + event.anchor);
        }, 500);
      }
    });
  }

  private scroll(query: string) {
    const targetElement = document.querySelector(query);
    if (!targetElement) {
      window.scrollTo(0, 0);
    } else if (!this.isInViewport(targetElement)) {
      targetElement.scrollIntoView();
    }
  }

  private isInViewport = (elem: any) => {
    const bounding = elem.getBoundingClientRect();
    return (
      bounding.top >= 0 &&
      bounding.left >= 0 &&
      bounding.bottom <=
        (window.innerHeight || document.documentElement.clientHeight) &&
      bounding.right <=
        (window.innerWidth || document.documentElement.clientWidth)
    );
  };

  ngOnInit() {
    this.spinner.show();
    this.loading = true;
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
              "Unexpected result. The list of datasets is empty.",
            );
          }
          let attr_description = null;
          let attr_url = null;
          if (iff_dataset) {
            attr_description = iff_dataset.attribution_description;
            attr_url = iff_dataset.attribution_url;
          } else {
            attr_description = "Mistral";
            attr_url = "https://www.mistralportal.it";
          }
          // mistral products licenses
          this.mistral_products = [
            {
              name: "Observed data map",
              description:
                "Graphical visualization of the observational data collected in MeteoHub platform",
              attribution_description: "Agenzia ItaliaMeteo - CINECA",
              //attribution_url: attr_url,
              license_description: "CC BY 4.0",
              license_url:
                "https://creativecommons.org/licenses/by/4.0/legalcode",
            },
            {
              name: "Static map",
              description:
                "Graphical visualization of the forecast data collected in MeteoHub platform",
              attribution_description: "CINECA",
              //attribution_url: attr_url,
              license_description: " CC BY-ND 4.0",
              license_url:
                "https://creativecommons.org/licenses/by-nd/4.0/legalcode",
            },
            {
              name: "Multi-layer map",
              description:
                "Interactive graphical visualization of forecast data from the MeteoHub platform, supporting the simultaneous display of multiple variable layers",
              attribution_description: "Agenzia ItaliaMeteo - CINECA",
              //attribution_url: attr_url,
              license_description: " CC BY-ND 4.0",
              license_url:
                "https://creativecommons.org/licenses/by-nd/4.0/legalcode",
            },
            {
              name: "Monthly forecast map",
              description:
                "Graphical visualization of Seasonal Forecast (0.1° downscaling)",
              attribution_description: "Agenzia ItaliaMeteo - CINECA",
              //attribution_url: "https://cds.climate.copernicus.eu/",
              license_description: "CC BY 4.0",
              license_url:
                "https://creativecommons.org/licenses/by/4.0/legalcode",
            },
            {
              name: "Weekly forecast map",
              description:
                "Graphical visualization of ECMWF Subseasonal Forecast",
              attribution_description: "Agenzia ItaliaMeteo - CINECA",
              license_description: "CC BY 4.0",
              license_url:
                "https://creativecommons.org/licenses/by/4.0/legalcode",
            },
            {
              name: "Marine forecast map",
              description:
                "Interactive graphical visualization of forecast data from WW3 marine model with overlapping variable layers",
              attribution_description: "Agenzia ItaliaMeteo - CINECA",
              license_description: "CC BY 4.0",
              license_url:
                "https://creativecommons.org/licenses/by/4.0/legalcode",
            },
            {
              name: "Radar map",
              description:
                "Graphical visualization of SRI and SRT1 products from the Civil Protection Department national radar network",
              attribution_description: "Agenzia ItaliaMeteo - CINECA",
              license_description: "CCBY SA 4.0",
              license_url:
                "https://creativecommons.org/licenses/by-sa/4.0/legalcode",
            },
          ];
          // append iff dataset in mistral products
          //this.mistral_products.push(iff_dataset);
          // append multimodel dataset in mistral products
          //this.mistral_products.push(multim_dataset);
        },
        (error) => {
          this.notify.showError(error);
        },
      )
      .add(() => {
        this.spinner.hide();
        this.loading = false;
      });
  }
}
