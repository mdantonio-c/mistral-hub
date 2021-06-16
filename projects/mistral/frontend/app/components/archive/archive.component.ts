import { Component, Output, EventEmitter, Injector } from "@angular/core";
import { Subscription, concat } from "rxjs";
import { saveAs as importedSaveAs } from "file-saver-es";
import { BasePaginationComponent } from "@rapydo/components/base.pagination.component";

import { DataService } from "@app/services/data.service";
import { decode, PP_TIME_RANGES } from "@app/services/data";
import { environment } from "@rapydo/../environments/environment";
import { Router, NavigationExtras } from "@angular/router";

export interface Archive {}

@Component({
  selector: "app-archive",
  templateUrl: "./archive.component.html",
})
export class ArchiveComponent extends BasePaginationComponent<Request> {
  expanded: any = {};
  @Output() onLoad: EventEmitter<null> = new EventEmitter<null>();

  PP_TIME_RANGES = PP_TIME_RANGES;
  decode = decode;
  autoSync = false;
  interval: any;
  readonly intervalStep = 20; // seconds

  constructor(
    protected injector: Injector,
    public dataService: DataService,
    private router: Router
  ) {
    super(injector);
    this.init("request", "/api/requests", null);
    this.initPaging(20, true);
    this.setServerSideFiltering();
    this.data_filters = { archived: true };
    this.list();
  }

  ngOnInit() {
    // make sure the derived variables have been loaded
    this.dataService.getDerivedVariables().subscribe();

    this.activateAutoSync();
  }

  ngOnDestroy() {
    clearInterval(this.interval);
  }

  list_and_clear() {
    // reset timer
    clearInterval(this.interval);
    this.activateAutoSync();
    this.list();
  }

  list(): Subscription {
    const ret = super.list();
    ret.add((response) => {
      this.onLoad.emit();
    });
    return ret;
  }

  cloneAsNew(request) {
    this.spinner.show();
    // query clone API to retrieve the query model
    this.dataService
      .cloneRequest(request.id)
      .subscribe(
        (data) => {
          let objToSend: NavigationExtras = data;
          this.router.navigate(["/app/data/submit"], {
            state: objToSend,
          });
        },
        (error) => {
          this.notify.showError(`Unable to clone request: ${request.id}`);
        }
      )
      .add(() => {
        this.spinner.hide();
      });
  }

  copiedToClipboard($event) {
    if ($event["isSuccess"]) {
      this.notify.showSuccess("Copied to Clipboard");
    }
  }

  downloadJSON(jsonBody) {
    const blob = new Blob([jsonBody], { type: "text/plain" });
    importedSaveAs(blob, "query.json");
  }

  toggleExpandRow(row) {
    this.table.rowDetail.toggleExpandRow(row);
  }

  toggleAutoSync() {
    this.autoSync = !this.autoSync;
  }

  private activateAutoSync() {
    this.interval = setInterval(() => {
      if (this.autoSync) {
        this.list();
      }
    }, this.intervalStep * 1000);
  }

  getFileName(path) {
    let filepath = path.split("/");
    return filepath[filepath.length - 1];
  }
}
