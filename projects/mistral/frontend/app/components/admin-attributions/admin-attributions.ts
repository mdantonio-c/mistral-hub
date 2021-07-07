import { Component, ViewChild, TemplateRef, Injector } from "@angular/core";

import { Attribution } from "../../types";

import { BasePaginationComponent } from "@rapydo/components/base.pagination.component";

@Component({
  templateUrl: "./admin-attributions.html",
})
export class AdminAttributionsComponent extends BasePaginationComponent<Attribution> {
  @ViewChild("controlsCell", { static: false })
  public controlsCell: TemplateRef<any>;
  @ViewChild("emptyHeader", { static: false })
  public emptyHeader: TemplateRef<any>;
  @ViewChild("datasetsCell", { static: false })
  public datasetsCell: TemplateRef<any>;

  constructor(protected injector: Injector) {
    super(injector);
    this.init("attribution", "/api/admin/attributions", "Attributions");
    this.initPaging();
    this.list();
  }

  public ngOnInit(): void {}
  public ngAfterViewInit(): void {
    this.columns = [
      { name: "Name", prop: "name", flexGrow: 0.5 },
      {
        name: "Datasets",
        prop: "datasets",
        flexGrow: 0.6,
        cellTemplate: this.datasetsCell,
      },
      { name: "Description", prop: "descr", flexGrow: 1.2 },
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
