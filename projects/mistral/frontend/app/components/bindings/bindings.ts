import { Component, OnInit } from "@angular/core";

// import { BindingsService } from "@app/services/{name}"
import { NgxSpinnerService } from "ngx-spinner";
// import {ApiService} from "@rapydo/services/api";
import { AuthService } from "@rapydo/services/auth";
import { NotificationService } from "@rapydo/services/notification";
import { AdminService } from "../../services/admin.service";
// import { ExchangeBindings } from "@app/types";
import { ExchangeBindings } from "../../types";

enum ColumnMode {
  standard = "standard",
  flex = "flex",
  force = "force",
}

@Component({
  templateUrl: "bindings.html",
})
export class BindingsComponent implements OnInit {
  public data: ExchangeBindings;
  rows = [];
  reorderable = true;
  ColumnMode = ColumnMode;
  outputs: string[] = [];

  constructor(
    private spinner: NgxSpinnerService,
    private adminService: AdminService,
    private auth: AuthService,
    private notify: NotificationService
  ) {}

  ngOnInit() {
    this.getBindings();
  }

  getBindings() {
    this.spinner.show();
    this.adminService
      .getBindings()
      .subscribe(
        (response) => {
          this.data = response;
          // this.rows = this.data.bindings
          let res = new Set<string>();
          for (const [key, value] of Object.entries(this.data.bindings)) {
            let entry = {
              network: key,
            };
            if (value && value.length) {
              const o: string[] = value.map((v) => v.split("-")[0]);
              o.forEach((x) => {
                entry[x] = true;
                res.add(x);
              });
            }
            this.rows.push(entry);
          }
          this.outputs = [...res];
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        this.spinner.hide();
      });
  }

  toggleBinding(user: string, network: string, val: boolean, row) {
    this.spinner.show();
    const action = val ? "deactivate" : "activate";
    console.info(`[user:${user}] - ${action} binding for network '${network}'`);
    if (val) {
      this.adminService
        .disableBinding(user, network)
        .subscribe(
          () => {
            this.notify.showSuccess("Binding disabled");
            row[user] = !val;
          },
          (error) => {
            this.notify.showError(error);
          }
        )
        .add(() => {
          this.spinner.hide();
        });
    } else {
      this.adminService
        .enableBinding(user, network)
        .subscribe(
          () => {
            this.notify.showSuccess("Binding enabled");
            row[user] = !val;
          },
          (error) => {
            this.notify.showError(error);
          }
        )
        .add(() => {
          this.spinner.hide();
        });
    }
  }
}
