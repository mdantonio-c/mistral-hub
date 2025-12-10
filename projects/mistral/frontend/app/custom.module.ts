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

import { DataComponent } from "@app/components/data/data.component";
import { RequestsComponent } from "@app/components/requests/requests.component";
import { SchedulesComponent } from "@app/components/schedules/schedules.component";
import { ArchiveComponent } from "@app/components/archive/archive.component";
import { DashboardComponent } from "@app/components/dashboard/dashboard.component";
import { StorageUsageComponent } from "@app/components/dashboard/storage-usage/storage-usage.component";
import { RequestHourlyReportComponent } from "@app/components/dashboard/request-hourly-report/request-hourly-report.component";
import { NgbTimeStringAdapter } from "@app/adapters/timepicker-adapter";

import { LicenseComponent } from "./components/license/license.component";
import { PrivacyComponent } from "./components/privacy/privacy.component";
import { ParticipateComponent } from "./components/participate/participate.component";
import { DatasetsComponent } from "./components/datasets/datasets.component";
import { DatasetDetailsComponent } from "./components/dataset-details/dataset-details.component";

import { DisableControlDirective } from "./directives/disable-control";
import { ClickStopPropagation } from "./directives/click-stop-propagation";

/* Multi-Step Wizard Components */
import { MultiStepWizardComponent } from "./components/multi-step-wizard/multi-step-wizard.component";
import { MyRequestDetailsComponent } from "./components/multi-step-wizard/my-request-details/my-request-details.component";
import { NavbarComponent } from "./components/multi-step-wizard/navbar/navbar.component";
import { StepComponent } from "./components/multi-step-wizard/step.component";
import { StepDatasetsComponent } from "./components/multi-step-wizard/step-datasets/step-datasets.component";
import { StepFiltersComponent } from "./components/multi-step-wizard/step-filters/step-filters.component";
import { StepPostprocessComponent } from "./components/multi-step-wizard/step-postprocess/step-postprocess.component";
import { StepPostprocessMapComponent } from "./components/multi-step-wizard/step-postprocess/map/step-postprocess-map.component";
import { StepSubmitComponent } from "./components/multi-step-wizard/step-submit/step-submit.component";
import { ReftimeModalContent } from "./components/multi-step-wizard/step-filters/reftime-modal.component";

/* Maps */
import { ForecastMapsBaseComponent } from "@app/components/maps/forecast-maps/forecast-maps-base.component";
import { ForecastMapsComponent } from "@app/components/maps/forecast-maps/forecast-maps.component";
import { FlashFloodMapsComponent } from "@app/components/maps/forecast-maps/flash-flood-maps.component";
import { MapFilterComponent } from "@app/components/maps/forecast-maps/map-filter/map-filter.component";
import { MapFlashFloodFilterComponent } from "@app/components/maps/forecast-maps/map-filter/map-flash-flood-filter.component";
import { MapSliderComponent } from "@app/components/maps/forecast-maps/map-slider/map-slider.component";
import { ObsFilterComponent } from "@app/components/maps/observation-maps/obs-filter/obs-filter.component";
import { ObsDownloadComponent } from "@app/components/maps/observation-maps/obs-download/obs-download.component";
import { ObsNavbarComponent } from "@app/components/maps/observation-maps/obs-navbar/obs-navbar.component";
import { ObsMapComponent } from "@app/components/maps/observation-maps/obs-map/obs-map.component";
import { ObsMeteogramsComponent } from "@app/components/maps/observation-maps/obs-meteograms/obs-meteograms.component";
import { ObsStationReportComponent } from "@app/components/maps/observation-maps/obs-station-report/obs-station-report.component";
import { CustomLineChart } from "@app/components/custom-charts/line-chart-custom.component";
import { CustomBarChart } from "@app/components/custom-charts/bar-chart-custom.component";
import { CustomXAxis } from "@app/components/custom-charts/x-axis-custom.component";
import { CustomXAxisTick } from "@app/components/custom-charts/x-axis-tick-custom.component";
import { MeteoTilesComponent } from "@app/components/maps/meteo-tiles/meteo-tiles.component";
import { SideNavComponent } from "./components/maps/meteo-tiles/side-nav/side-nav.component";
import { BindingsComponent } from "@app/components/bindings/bindings";
import { LivemapComponent } from "./components/maps/livemap/livemap.component";
import { SideNavFilterComponent } from "./components/maps/side-nav/side-nav.component";
import { SeasonalComponent } from "@app/components/maps/seasonal/seasonal.component";
import { SideNavComponentSeasonal } from "./components/maps/seasonal/side-nav/side-nav.component";
import { ProvinceReportComponent } from "./components/maps/seasonal/province-report/province-report.component";
import { MarineComponent } from "./components/maps/marine/marine.component";
import { SideNavComponentMarine } from "./components/maps/marine/side-nav/side-nav.component";
import { RadarComponent } from "./components/maps/radar-observation-maps/radar-observation-maps.component";
import { SideNavComponentRadar } from "./components/maps/radar-observation-maps/side-nav/side-nav.component";
import { FormatDatePipe } from "@app/pipes/format-date.pipe";
import { FormatLabelDatePipe } from "@app/pipes/format-data-label.pipe";
import { ReplacePipe } from "@app/pipes/replace.pipe";
import { WorkflowGuard } from "@app/services/workflow-guard.service";

import { AdminLicgroupsComponent } from "@app/components/admin-licgroups/admin-licgroups";

import { AdminLicensesComponent } from "@app/components/admin-licenses/admin-licenses";
import { AdminAttributionsComponent } from "@app/components/admin-attributions/admin-attributions";
import { AdminDatasetsComponent } from "@app/components/admin-datasets/admin-datasets";
import { TranslatePipe } from "./pipes/translate.pipe";

import { UserGuideComponent } from "./components/user-guide/user-guide.component";
import {
  ComboChartComponent,
  ComboSeriesVerticalComponent,
} from "./components/custom-charts/combo-chart";
import {
  BubbleLineChartComponent,
  ComboBubbleSeriesComponent,
} from "./components/custom-charts/combo-chart-wind";
import {
  DoubleLineChartComponent,
  ComboLineChartComponent,
} from "./components/custom-charts/combo-chart-combined";
import {
  BoxChartComponent,
  ComboLineChartSeasonalComponent,
} from "./components/custom-charts/combo-chart-seasonal";
import { AimObservationMapsComponent } from "./components/maps/aim-observation-maps/aim-observation-maps.component";
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
    component: AimObservationMapsComponent,
    // canActivate: [AuthGuard],
  },
  {
    path: "app/maps/meteotiles",
    component: MeteoTilesComponent,
  },
  {
    path: "app/maps/seasonal",
    component: SeasonalComponent,
  },
  {
    path: "app/maps/marine",
    component: MarineComponent,
  },
  {
    path: "app/maps/radar",
    component: RadarComponent,
  },
  {
    path: "app/maps/livemap",
    component: LivemapComponent,
  },
  {
    path: "app/license",
    component: LicenseComponent,
  },
  {
    path: "app/user-guide",
    component: UserGuideComponent,
  },
  {
    path: "app/admin/bindings",
    component: BindingsComponent,
    canActivate: [AuthGuard],
    runGuardsAndResolvers: "always",
    data: { roles: ["admin_root"] },
  },
  {
    path: "app/admin/group-licenses",
    component: AdminLicgroupsComponent,
    canActivate: [AuthGuard],
    runGuardsAndResolvers: "always",
    data: { roles: ["admin_root"] },
  },
  {
    path: "app/admin/licenses",
    component: AdminLicensesComponent,
    canActivate: [AuthGuard],
    runGuardsAndResolvers: "always",
    data: { roles: ["admin_root"] },
  },
  {
    path: "app/admin/attributions",
    component: AdminAttributionsComponent,
    canActivate: [AuthGuard],
    runGuardsAndResolvers: "always",
    data: { roles: ["admin_root"] },
  },
  {
    path: "app/admin/datasets",
    component: AdminDatasetsComponent,
    canActivate: [AuthGuard],
    runGuardsAndResolvers: "always",
    data: { roles: ["admin_root"] },
  },

  { path: "app/license", component: LicenseComponent },
  { path: "public/privacy", component: PrivacyComponent },
  { path: "public/participate", component: ParticipateComponent },
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
    AdminDatasetsComponent,
    AdminLicensesComponent,
    AdminLicgroupsComponent,
    AdminAttributionsComponent,
    DataComponent,
    ForecastMapsBaseComponent,
    ForecastMapsComponent,
    FlashFloodMapsComponent,
    MapFilterComponent,
    MapFlashFloodFilterComponent,
    MapSliderComponent,
    ObsFilterComponent,
    ObsDownloadComponent,
    ObsNavbarComponent,
    ObsMapComponent,
    ObsMeteogramsComponent,
    ObsStationReportComponent,
    ProvinceReportComponent,
    CustomLineChart,
    CustomBarChart,
    CustomXAxis,
    CustomXAxisTick,
    MeteoTilesComponent,
    SideNavComponent,
    SeasonalComponent,
    SideNavComponentSeasonal,
    MarineComponent,
    SideNavComponentMarine,
    RadarComponent,
    SideNavComponentRadar,
    LivemapComponent,
    SideNavFilterComponent,
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
    RequestHourlyReportComponent,
    RequestsComponent,
    SchedulesComponent,
    ArchiveComponent,
    LicenseComponent,
    PrivacyComponent,
    ParticipateComponent,
    DatasetsComponent,
    DatasetDetailsComponent,
    BindingsComponent,
    ReftimeModalContent,
    FormatDatePipe,
    FormatLabelDatePipe,
    ReplacePipe,
    DisableControlDirective,
    ClickStopPropagation,
    TranslatePipe,
    ComboChartComponent,
    ComboSeriesVerticalComponent,
    BubbleLineChartComponent,
    ComboBubbleSeriesComponent,
    AimObservationMapsComponent,
    DoubleLineChartComponent,
    ComboLineChartComponent,
    BoxChartComponent,
    ComboLineChartSeasonalComponent,
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  providers: [
    DatePipe,
    { provide: NgbTimeAdapter, useClass: NgbTimeStringAdapter },
  ],
  exports: [RouterModule, MapFlashFloodFilterComponent],
  entryComponents: [ReftimeModalContent],
})
export class CustomModule {}
