import { Component, ViewChild } from "@angular/core";
import { RequestsComponent } from "../requests/requests.component";
import { SchedulesComponent } from "../schedules/schedules.component";
import { ArchiveComponent } from "../archive/archive.component";
import { NgbNavChangeEvent } from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: "app-dashboard",
  templateUrl: "./dashboard.component.html",
  styleUrls: ["./dashboard.component.css"],
})
export class DashboardComponent {
  selectedTabId = "requests";
  @ViewChild("rTab", { static: false }) requests: RequestsComponent;
  @ViewChild("sTab", { static: false }) schedules: SchedulesComponent;
  @ViewChild("sTab", { static: false }) archive: ArchiveComponent;

  onTabChange($event: NgbNavChangeEvent) {
    this.selectedTabId = $event.nextId;
  }

  list() {
    if (this.selectedTabId === "requests") {
      this.requests.list();
    } else if (this.selectedTabId === "archive") {
      this.archive.list();
    } else {
      this.schedules.list();
    }
  }
}
