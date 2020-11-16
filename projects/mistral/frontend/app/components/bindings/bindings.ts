import { Component } from "@angular/core";

// import { BindingsService } from "@app/services/{name}"

import { NgxSpinnerService } from "ngx-spinner";
import { ApiService } from "@rapydo/services/api";
import { AuthService } from "@rapydo/services/auth";
import { NotificationService } from "@rapydo/services/notification";
import { ExchangeBindings } from "@app/types";

@Component({
  templateUrl: "bindings.html",
})
export class BindingsComponent {
  public data: ExchangeBindings;

  constructor(
    private spinner: NgxSpinnerService,
    private api: ApiService,
    private auth: AuthService,
    private notify: NotificationService
  ) {
    this.get_bindings();
  }

  private get_bindings() {
    this.api
      .get<ExchangeBindings>(
        "outbindings",
        "",
        {},
        { validationSchema: "ExchangeBindings" }
      )
      .subscribe(
        (response) => {
          this.data = response;
        },
        (error) => {
          this.notify.showError(error);
        }
      );
  }

  private enable_binding(user, network) {
    this.api.post(`outbindings/${user}/${network}`).subscribe(
      (response) => {
        this.notify.showSuccess("Binding enabled");
      },
      (error) => {
        this.notify.showError(error);
      }
    );
  }

  private disable_binding(user, network) {
    this.api.delete(`outbindings/${user}/${network}`).subscribe(
      (response) => {
        this.notify.showSuccess("Binding disabled");
      },
      (error) => {
        this.notify.showError(error);
      }
    );
  }
}
