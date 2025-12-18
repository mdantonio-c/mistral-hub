import { Component, ViewChild, TemplateRef, Injector } from "@angular/core";
import { forkJoin, Subject, of } from "rxjs";
import { catchError } from "rxjs/operators";
import { ArcoService } from "../../services/arco.service";

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

  constructor(
    protected injector: Injector,
    private arcoService: ArcoService,
  ) {
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

  public override list(): Subject<boolean> {
    this.loading = true;
    forkJoin({
      attributions: this.api.get<Attribution[]>("/api/admin/attributions"),
      arco: this.arcoService.getArcoDatasets().pipe(catchError(() => of([]))),
    }).subscribe(
      (response) => {
        const attributions = response.attributions;
        const arco = response.arco;

        arco.forEach((ds) => {
          const attribution = attributions.find(
            (a) => a.name === ds.attribution,
          );
          if (attribution) {
            if (!attribution.datasets) {
              attribution.datasets = [];
            }
            attribution.datasets.push({
              id: ds.id,
              name: ds.name,
            });
          }
        });

        this.data = attributions;
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
