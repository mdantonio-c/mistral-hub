import { Component, ElementRef, Injector } from "@angular/core";
import { saveAs as importedSaveAs } from "file-saver";

import { BasePaginationComponent } from "@rapydo/components/base.pagination.component";
import { DataService } from "@app/services/data.service";
import { concatMap, tap } from "rxjs/operators";

export interface Schedule {}

@Component({
  selector: "app-schedules",
  templateUrl: "./schedules.component.html",
})
export class SchedulesComponent extends BasePaginationComponent<Schedule> {
  expanded: any = {};
  loadingLast = false; // it should be bound to the single row!

  constructor(
    protected injector: Injector,
    public dataService: DataService,
    private el: ElementRef
  ) {
    super(injector);
    this.init("schedule", "schedules", null);
    this.initPaging(20, true);
    this.list();
  }

  ngOnInit() {
    // make sure the derived variables have been loaded
    this.dataService.getDerivedVariables().subscribe();
  }

  loadLastSubmission(row) {
    this.loadingLast = true;
    this.spinner.show("last");
    this.dataService
      .getLastScheduledRequest(row.id)
      .subscribe(
        (scheduledRequest) => {
          row.last = scheduledRequest;
          this.dataService.countScheduledRequests(row.id).subscribe((res) => {
            row.requests_count = res.total;
          });
        },
        (error) => {
          if (error.status === 404) {
            // No successful request is available for this schedule yet
            // do nothing
          } else {
            this.notify.showError("Unable to load the last submission");
            // show reason
            this.notify.showError(error);
          }
        }
      )
      .add(() => {
        this.loadingLast = false;
        this.spinner.hide("last");
      });
  }

  toggleExpandRow(row, flag) {
    if (flag === "open") {
      // load last request
      this.loadLastSubmission(row);
    }
    // open or close schedule details
    this.table.rowDetail.toggleExpandRow(row);
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

  toggleActiveState($event: MouseEvent, row) {
    // stop click event and propagation
    $event.stopPropagation();

    const action = !row.enabled ? "Activate" : "Deactivate";
    console.log(
      `${action} schedule [ID:${row.id}]. Current state: ${row.enabled}`
    );
    this.dataService.toggleScheduleActiveState(row.id, !row.enabled).subscribe(
      (response) => {
        row.enabled = response.enabled;
        let toggleBtn = this.el.nativeElement.querySelector(
          "#act-btn-" + row.id
        );
        row.enabled
          ? toggleBtn.classList.add("active")
          : toggleBtn.classList.remove("active");
      },
      (error) => {
        this.notify.showError(error);
      }
    );
  }
}
