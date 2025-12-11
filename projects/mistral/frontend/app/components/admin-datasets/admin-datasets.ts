import { Component, ViewChild, TemplateRef, Injector } from "@angular/core";
import { forkJoin, Subject } from "rxjs";
import { ArcoService } from "../../services/arco.service";

import { AdminDataset } from "../../types";

import { BasePaginationComponent } from "@rapydo/components/base.pagination.component";

@Component({
  templateUrl: "./admin-datasets.html",
})
export class AdminDatasetsComponent extends BasePaginationComponent<AdminDataset> {
  @ViewChild("controlsCell", { static: false })
  public controlsCell: TemplateRef<any>;
  @ViewChild("emptyHeader", { static: false })
  public emptyHeader: TemplateRef<any>;

  constructor(
    protected injector: Injector,
    private arcoService: ArcoService,
  ) {
    super(injector);
    this.init("dataset", "/api/admin/datasets", "AdminDatasets");
    this.initPaging();
    this.list();
  }

  public ngOnInit(): void {}
  public ngAfterViewInit(): void {
    this.columns = [
      { name: "Name", prop: "name", flexGrow: 0.4 },

      { name: "Description", prop: "description", flexGrow: 1 },
      { name: "License", prop: "license.name", flexGrow: 0.2 },
      { name: "Attribution", prop: "attribution.name", flexGrow: 0.2 },
      { name: "Sort Index", prop: "sort_index", flexGrow: 0.2 },
      {
        name: "controls",
        prop: "controls",
        cellTemplate: this.controlsCell,
        headerTemplate: this.emptyHeader,
        sortable: false,
        flexGrow: 0.2,
        minWidth: 60,
      },
    ];
  }

  public override list(): Subject<boolean> {
    this.loading = true;
    forkJoin({
      datasets: this.api.get<AdminDataset[]>("/api/admin/datasets"),
      arco: this.arcoService.getArcoDatasets(),
    }).subscribe(
      (response) => {
        const datasets = response.datasets;
        const arco = response.arco;

        const arcoDatasets: AdminDataset[] = arco.map((ds) => {
          return {
            id: ds.id,
            arkimet_id: ds.id,
            name: ds.name,
            description: ds.description,
            category: ds.category,
            fileformat: ds.format,
            bounding: "",
            sort_index: 0,
            license: {
              id: "",
              name: ds.license,
              descr: "",
              url: "",
            },
            attribution: {
              id: "",
              name: ds.attribution,
              descr: "",
            },
          } as AdminDataset;
        });

        this.data = [...datasets, ...arcoDatasets];
        this.unfiltered_data = this.data;

        this.paging.dataLength = this.data.length;
        this.paging.numPages = Math.ceil(
          this.data.length / this.paging.itemsPerPage,
        );

        this.loading = false;
        this.list_subject.next(true);
      },
      (error) => {
        this.notify.showError(error);
        this.loading = false;
        this.list_subject.next(false);
      },
    );
    return this.list_subject;
  }

  filter(data_filter) {
    return this.unfiltered_data.filter(function (d) {
      if (d.name.toLowerCase().indexOf(data_filter) !== -1) {
        return true;
      }
      return false;
    });
  }
}
