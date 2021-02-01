import { Component, ViewChild, TemplateRef, Injector } from "@angular/core";

import { AdminDataset } from "../../types";

import { BasePaginationComponent } from "@rapydo/components/base.pagination.component";

@Component({
  templateUrl: "./admin-datasets.html",
})
export class AdminDatasetsComponent extends BasePaginationComponent<
  AdminDataset
> {
  @ViewChild("controlsCell", { static: false })
  public controlsCell: TemplateRef<any>;
  @ViewChild("emptyHeader", { static: false }) public emptyHeader: TemplateRef<
    any
  >;

  constructor(protected injector: Injector) {
    super(injector);
    this.init("dataset", "admin/datasets", "AdminDataset");
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

  filter(data_filter) {
    return this.unfiltered_data.filter(function (d) {
      if (d.name.toLowerCase().indexOf(data_filter) !== -1) {
        return true;
      }
      return false;
    });
  }
}
