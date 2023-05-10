import { Component } from "@angular/core";

import { ApiService } from "@rapydo/services/api";
import { NotificationService } from "@rapydo/services/notification";

@Component({
  templateUrl: "./data.component.html",
})
export class DataComponent {
  public data_id: string;
  public loading: boolean = false;

  constructor(
    protected api: ApiService,
    protected notify: NotificationService,
  ) {}

  private get_data() {
    let data = {};
    this.api.post("data", data).subscribe(
      (response) => {
        this.data_id = response["data"];
      },
      (error) => {
        this.notify.showError(error);
      },
    );
  }
}
