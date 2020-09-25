import { Component, OnInit } from "@angular/core";
import { StorageUsage } from "@app/types";
import { DataService } from "@app/services/data.service";
import { NotificationService } from "@rapydo/services/notification";

@Component({
  selector: "app-storage-usage",
  templateUrl: "./storage-usage.component.html",
})
export class StorageUsageComponent implements OnInit {
  usage: StorageUsage = { quota: 0, used: 0 };
  barValue = 0;

  constructor(
    private dataService: DataService,
    private notify: NotificationService
  ) {}

  ngOnInit() {
    this.load();
  }

  load() {
    this.dataService.getStorageUsage().subscribe(
      (response) => {
        this.usage = response;
        this.barValue = (this.usage.used * 100) / this.usage.quota;
      },
      (error) => {
        this.notify.showError(error);
      }
    );
  }
}
