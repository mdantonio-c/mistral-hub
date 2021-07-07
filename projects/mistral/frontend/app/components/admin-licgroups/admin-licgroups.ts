import { Component, ViewChild, TemplateRef, Injector } from "@angular/core";

import { LicenseGroup } from "../../types";

import { BasePaginationComponent } from "@rapydo/components/base.pagination.component";

@Component({
  templateUrl: "./admin-licgroups.html",
})
export class AdminLicgroupsComponent extends BasePaginationComponent<LicenseGroup> {
  @ViewChild("controlsCell", { static: false })
  public controlsCell: TemplateRef<any>;
  @ViewChild("emptyHeader", { static: false })
  public emptyHeader: TemplateRef<any>;
  @ViewChild("licensesCell", { static: false })
  public licensesCell: TemplateRef<any>;

  constructor(protected injector: Injector) {
    super(injector);
    this.init("license group", "/api/admin/licensegroups", "LicenseGroups");
    this.initPaging();
    this.list();
  }

  public ngOnInit(): void {}
  public ngAfterViewInit(): void {
    this.columns = [
      { name: "Name", prop: "name", flexGrow: 0.5 },
      {
        name: "Licenses",
        prop: "license",
        flexGrow: 0.5,
        cellTemplate: this.licensesCell,
      },
      { name: "Description", prop: "descr", flexGrow: 1.1 },
      { name: "Is open", prop: "is_public", flexGrow: 0.2 },
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
