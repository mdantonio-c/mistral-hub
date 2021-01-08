import { Component, Output, EventEmitter, Injector } from "@angular/core";
import { Subscription } from "rxjs";
import { saveAs as importedSaveAs } from "file-saver";
import { BasePaginationComponent } from "@rapydo/components/base.pagination.component";

import { DataService } from "@app/services/data.service";
import { decode, PP_TIME_RANGES } from "@app/services/data";
import { environment } from "@rapydo/../environments/environment";

export interface Request {}

@Component({
  selector: "app-requests",
  templateUrl: "./requests.component.html",
})
export class RequestsComponent extends BasePaginationComponent<Request> {
  expanded: any = {};
  @Output() onLoad: EventEmitter<null> = new EventEmitter<null>();

  PP_TIME_RANGES = PP_TIME_RANGES;
  decode = decode;
  autoSync = false;
  interval: any;
  readonly intervalStep = 20; // seconds

  constructor(protected injector: Injector, public dataService: DataService) {
    super(injector);
    this.init("request", "requests", null);
    this.initPaging(20, true);
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
    this.onLoad.emit();
    return ret;
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

  download(filename) {
    this.dataService.downloadData(filename).subscribe(
      (resp) => {
        const contentType =
          resp.headers["content-type"] || "application/octet-stream";
        const blob = new Blob([resp.body], { type: contentType });
        importedSaveAs(blob, filename);
      },
      (error) => {
        this.notify.showError(`Unable to download file: ${filename}`);
      }
    );
  }

  private getFileURL(filename) {
    const source_url = `${environment.backendURI}/api/data/${filename}`;
    let token = this.auth.getToken();
    return source_url + "?access_token=" + token;
  }

  downloadByUrl(filename) {
    const downloadUrl = this.getFileURL(filename);
    let link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    link.style.visibility = "hidden";
    link.click();
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
