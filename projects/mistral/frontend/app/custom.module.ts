import {
  NgModule,
  CUSTOM_ELEMENTS_SCHEMA,
  ModuleWithProviders,
} from "@angular/core";
import { NgbTimeAdapter } from "@ng-bootstrap/ng-bootstrap";
import { RouterModule, Routes } from "@angular/router";
import { DatePipe } from "@angular/common";

import { SharedModule } from "@rapydo/shared.module";
import { AuthGuard } from "@rapydo/app.auth.guard";

import { NgxBootstrapSliderModule } from "ngx-bootstrap-slider";
import { LeafletModule } from "@asymmetrik/ngx-leaflet";
import { LeafletDrawModule } from "@asymmetrik/ngx-leaflet-draw";
import { LeafletMarkerClusterModule } from "@asymmetrik/ngx-leaflet-markercluster";
import { NgxChartsModule } from "@swimlane/ngx-charts";

import { HomeComponent } from "@app/custom.home";
import { DataComponent } from "@app/components/data/data.component";
import { RequestsComponent } from "@app/components/requests/requests.component";
import { SchedulesComponent } from "@app/components/schedules/schedules.component";
import { DashboardComponent } from "@app/components/dashboard/dashboard.component";
import { StorageUsageComponent } from "@app/components/dashboard/storage-usage/storage-usage.component";
import { NgbTimeStringAdapter } from "@app/adapters/timepicker-adapter";

import { LicenseComponent } from "@app/components/license/license.component";
import { PrivacyComponent } from "@app/components/privacy/privacy.component";
import { DatasetsComponent } from "./components/datasets/datasets.component";
import { DatasetDetailsComponent } from "./components/dataset-details/dataset-details.component";

import { DisableControlDirective } from "@app/directives/disable-control";

/* Multi-Step Wizard Components */
import { MultiStepWizardComponent } from "@app/components/multi-step-wizard/multi-step-wizard.component";
import { MyRequestDetailsComponent } from "@app/components/multi-step-wizard/my-request-details/my-request-details.component";
import { NavbarComponent } from "@app/components/multi-step-wizard/navbar/navbar.component";
import { StepComponent } from "@app/components/multi-step-wizard/step.component";
import { StepDatasetsComponent } from "@app/components/multi-step-wizard/step-datasets/step-datasets.component";
import { StepFiltersComponent } from "@app/components/multi-step-wizard/step-filters/step-filters.component";
import { StepPostprocessComponent } from "@app/components/multi-step-wizard/step-postprocess/step-postprocess.component";
import { StepPostprocessMapComponent } from "@app/components/multi-step-wizard/step-postprocess/map/step-postprocess-map.component";
import { StepSubmitComponent } from "@app/components/multi-step-wizard/step-submit/step-submit.component";

/* Maps */
import { ForecastMapsBaseComponent } from "@app/components/maps/forecast-maps/forecast-maps-base.component";
import { ForecastMapsComponent } from "@app/components/maps/forecast-maps/forecast-maps.component";
import { FlashFloodMapsComponent } from "@app/components/maps/forecast-maps/flash-flood-maps.component";
import { MapFilterComponent } from "@app/components/maps/forecast-maps/map-filter/map-filter.component";
import { MapFlashFloodFilterComponent } from "@app/components/maps/forecast-maps/map-filter/map-flash-flood-filter.component";
import { MapSliderComponent } from "@app/components/maps/forecast-maps/map-slider/map-slider.component";
import { ObservationMapsComponent } from "@app/components/maps/observation-maps/observation-maps.component";
import { ObsFilterComponent } from "@app/components/maps/observation-maps/obs-filter/obs-filter.component";
import { ObsDownloadComponent } from "@app/components/maps/observation-maps/obs-download/obs-download.component";
import { ObsNavbarComponent } from "@app/components/maps/observation-maps/obs-navbar/obs-navbar.component";
import { ObsMapComponent } from "@app/components/maps/observation-maps/obs-map/obs-map.component";
import { ObsMeteogramsComponent } from "@app/components/maps/observation-maps/obs-meteograms/obs-meteograms.component";
import { ObsStationReportComponent } from "@app/components/maps/observation-maps/obs-station-report/obs-station-report.component";
import { MeteoTilesComponent } from "@app/components/maps/meteo-tiles/meteo-tiles.component";
import { BindingsComponent } from "@app/components/bindings/bindings";

import { FormatDatePipe } from "@app/pipes/format-date.pipe";
import { ReplacePipe } from "@app/pipes/replace.pipe";
import { WorkflowGuard } from "@app/services/workflow-guard.service";

const appRoutes: Routes = [
  {
    path: "app/data",
    component: DataComponent,
    canActivate: [AuthGuard],
    runGuardsAndResolvers: "always",
    children: [
      { path: "", redirectTo: "datasets", pathMatch: "full" },
      { path: "datasets", component: StepDatasetsComponent },
      {
        path: "filters",
        component: StepFiltersComponent,
        canActivate: [WorkflowGuard],
      },
      {
        path: "postprocess",
        component: StepPostprocessComponent,
        canActivate: [WorkflowGuard],
      },
      {
        path: "submit",
        component: StepSubmitComponent,
        canActivate: [WorkflowGuard],
      },
    ],
  },
  { path: "app/datasets", component: DatasetsComponent },
  { path: "app/maps/forecasts", component: ForecastMapsComponent },
  { path: "app/maps/flashflood", component: FlashFloodMapsComponent },
  {
    path: "app/requests",
    component: DashboardComponent,
    canActivate: [AuthGuard],
  },
  {
    path: "app/maps/observations",
    component: ObservationMapsComponent,
    // canActivate: [AuthGuard],
  },
  {
    path: "app/maps/meteotiles",
    component: MeteoTilesComponent,
  },
  {
    path: "app/license",
    component: LicenseComponent,
    canActivate: [AuthGuard],
  },
  {
    path: "app/admin/bindings",
    component: BindingsComponent,
    canActivate: [AuthGuard],
    runGuardsAndResolvers: "always",
    data: { roles: ["admin_root"] },
  },

  { path: "public/privacy", component: PrivacyComponent },
  { path: "app", redirectTo: "/app/datasets", pathMatch: "full" },
  { path: "", redirectTo: "/app/datasets", pathMatch: "full" },
];

@NgModule({
  imports: [
    SharedModule,
    RouterModule.forChild(appRoutes),
    NgxBootstrapSliderModule,
    LeafletModule,
    LeafletDrawModule,
    LeafletMarkerClusterModule,
    NgxChartsModule,
  ],
  declarations: [
    HomeComponent,
    DataComponent,
    ForecastMapsBaseComponent,
    ForecastMapsComponent,
    FlashFloodMapsComponent,
    MapFilterComponent,
    MapFlashFloodFilterComponent,
    MapSliderComponent,
    ObservationMapsComponent,
    ObsFilterComponent,
    ObsDownloadComponent,
    ObsNavbarComponent,
    ObsMapComponent,
    ObsMeteogramsComponent,
    ObsStationReportComponent,
    MeteoTilesComponent,
    MultiStepWizardComponent,
    MyRequestDetailsComponent,
    NavbarComponent,
    StepComponent,
    StepDatasetsComponent,
    StepFiltersComponent,
    StepPostprocessComponent,
    StepPostprocessMapComponent,
    StepSubmitComponent,
    DashboardComponent,
    StorageUsageComponent,
    RequestsComponent,
    SchedulesComponent,
    LicenseComponent,
    PrivacyComponent,
    DatasetsComponent,
    DatasetDetailsComponent,
    BindingsComponent,
    FormatDatePipe,
    ReplacePipe,
    DisableControlDirective,
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  providers: [
    DatePipe,
    { provide: NgbTimeAdapter, useClass: NgbTimeStringAdapter },
  ],
  exports: [RouterModule, MapFlashFloodFilterComponent],
})
export class CustomModule {}
