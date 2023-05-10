import { Component, Output, EventEmitter, Injector } from "@angular/core";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { Subject, concat } from "rxjs";
import { saveAs as importedSaveAs } from "file-saver-es";
import { BasePaginationComponent } from "@rapydo/components/base.pagination.component";
import { ConfirmationModals } from "@rapydo/services/confirmation.modals";
import { DataExtractionRequest } from "../../types";
import { ArchiveDeleteModals } from "./delete_archive_modal/archive-delete.modal";

import { DataService } from "@app/services/data.service";
import { decode, PP_TIME_RANGES } from "@app/services/data";
import { environment } from "@rapydo/../environments/environment";
import { Router, NavigationExtras } from "@angular/router";

import { take } from "rxjs/operators";

export interface Request {}

@Component({
  selector: "app-requests",
  templateUrl: "./requests.component.html",
  styleUrls: ["./requests.component.scss"],
})
export class RequestsComponent extends BasePaginationComponent<Request> {
  protected confirmationModals: ConfirmationModals;
  protected modalService: NgbModal;
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
    private router: Router,
  ) {
    super(injector);
    this.init("request", "/api/requests", null);
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

  public list(): Subject<boolean> {
    const subject = super.list();

    subject.pipe(take(1)).subscribe((success: boolean) => {
      this.onLoad.emit();
    });
    return subject;
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
        },
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
      },
    );
  }

  public delete_or_archive(uuid: string) {
    this.modalService.open(ArchiveDeleteModals).result.then(
      (result) => {
        if (result == "archive") {
          this.archive(uuid);
        } else if (result == "delete") {
          this.delete(uuid);
        }
      },
      (reason) => {},
    );
  }

  public archive(
    uuid: string,
    text: string = null,
    title: string = null,
    subText: string = null,
  ): void {
    text = `Are you really sure you want to archive this request?`;
    subText = `
        The file related to this request will be permanently deleted.
        This operation cannot be undone.`;
    let confirmbutton = "Yes, archive";

    this.confirmationModals
      .open({
        text: text,
        title: title,
        subText: subText,
        confirmButton: confirmbutton,
      })
      .then(
        (result) => {
          this.dataService.archiveRequest(uuid).subscribe(
            (response) => {
              this.notify.showSuccess(
                `Confirmation: request successfully archived`,
              );
              this.list();
            },
            (error) => {
              this.notify.showError(error);
            },
          );
        },
        (reason) => {},
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
