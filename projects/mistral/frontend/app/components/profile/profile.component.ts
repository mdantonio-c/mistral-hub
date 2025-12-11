import { Component, TemplateRef } from "@angular/core";
import { NgxSpinnerService } from "ngx-spinner";
import { NgbModal, NgbModalRef, NgbDateStruct } from "@ng-bootstrap/ng-bootstrap";
import { FormGroup } from "@angular/forms";

import { AuthService } from "@rapydo/services/auth";
import { User } from "@rapydo/types";
import { ApiService } from "@rapydo/services/api";
import { NotificationService } from "@rapydo/services/notification";
import { FormlyService } from "@rapydo/services/formly";
import { Schema } from "@rapydo/types";
import { FormModal } from "@rapydo/components/forms/form.modal";
import { ConfirmationModals } from "@rapydo/services/confirmation.modals";
import { ArcoService } from "@app/services/arco.service";
import { AccessKey } from "@app/types";

@Component({
  templateUrl: "profile.component.html",
})
export class ProfileComponent {
  public user: User;
  public accessKey: AccessKey;
  public expirationDate: NgbDateStruct;

  protected modalRef: NgbModalRef;
  public form;
  public fields;
  public model;

  constructor(
    private spinner: NgxSpinnerService,
    private modalService: NgbModal,
    public notify: NotificationService,
    private api: ApiService,
    private auth: AuthService,
    private formly: FormlyService,
    private confirmationModals: ConfirmationModals,
    private arcoService: ArcoService
  ) {
    this.reloadUser();
    this.loadAccessKey();
  }

  private reloadUser() {
    this.spinner.show();
    this.auth.loadUser().subscribe(
      (response) => {
        this.user = response;
        this.spinner.hide();
      },
      (error) => {
        this.notify.showError(error);
        this.spinner.hide();
      }
    );
  }

  private loadAccessKey() {
    this.arcoService.getAccessKey().subscribe(
      (key) => {
        this.accessKey = key;
      },
      (error) => {
        if (error.status === 404) {
          this.accessKey = null;
        } else {
          this.notify.showError(error);
        }
      }
    );
  }

  public openCreateKeyModal(content: TemplateRef<any>) {
    this.expirationDate = null;
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' }).result.then(
      (result) => {
        if (result === 'create') {
          this.createAccessKey();
        }
      },
      (reason) => {}
    );
  }

  public createAccessKey() {
    let expiration = null;
    const dateInput = this.expirationDate as any;
    if (dateInput) {
        if (dateInput instanceof Date) {
            expiration = dateInput;
        } else if (dateInput.year && dateInput.month && dateInput.day) {
            expiration = new Date(dateInput.year, dateInput.month - 1, dateInput.day);
        }
    }
    this.arcoService.createAccessKey(expiration).subscribe(
      (key) => {
        this.notify.showSuccess("Access key successfully created");
        this.accessKey = key;
      },
      (error) => {
        this.notify.showError(error);
      }
    );
  }

  public openRotateKeyModal(content: TemplateRef<any>) {
    this.expirationDate = null;
    this.modalService.open(content, { ariaLabelledBy: 'modal-basic-title' }).result.then(
      (result) => {
        if (result === 'rotate') {
          this.rotateAccessKey(this.expirationDate);
        }
      },
      (reason) => {}
    );
  }

  public rotateAccessKey(expirationDate: NgbDateStruct) {
    let expiration = null;
    const dateInput = this.expirationDate as any;
    if (dateInput) {
        if (dateInput instanceof Date) {
            expiration = dateInput;
        } else if (dateInput.year && dateInput.month && dateInput.day) {
            expiration = new Date(dateInput.year, dateInput.month - 1, dateInput.day);
        }
    }
    this.arcoService.rotateAccessKey(expiration).subscribe(
      (key) => {
        this.notify.showSuccess("Access key successfully rotated");
        this.accessKey = key;
      },
      (error) => {
        this.notify.showError(error);
      }
    );
  }

  public revokeAccessKey(): void {
    this.confirmationModals.open({
      text: "Are you sure you want to revoke this access key?",
      confirmButton: "Revoke",
      cancelButton: "Cancel"
    }).then(
      (result) => {
        this.arcoService.revokeAccessKey().subscribe(
          (response) => {
            this.notify.showSuccess("Access key successfully revoked");
            this.accessKey = null;
          },
          (error) => {
            this.notify.showError(error);
          }
        );
      },
      (reason) => {}
    );
  }

  public edit_profile(): void {
    this.api.patch<Schema[]>("/auth/profile", { get_schema: true }).subscribe(
      (response) => {
        response.some((value, index) => {
          if (value.key === "privacy_accepted") {
            response.splice(index, 1);
            return true;
          }
        });

        let model = {};
        for (let field of response) {
          model[field.key] = this.user[field.key];
        }

        let data = this.formly.json2Form(response, model);

        this.form = new FormGroup({});
        this.fields = data.fields;
        this.model = data.model;
        this.modalRef = this.modalService.open(FormModal, {
          size: "m",
          backdrop: "static",
        });
        this.modalRef.componentInstance.modalTitle = "Update your profile";
        this.modalRef.componentInstance.updating = false;
        this.modalRef.componentInstance.form = this.form;
        this.modalRef.componentInstance.fields = this.fields;
        this.modalRef.componentInstance.model = this.model;
        this.modalRef.componentInstance.backRef = this;
        this.modalRef.result.then(
          (result) => {},
          (reason) => {}
        );
      },
      (error) => {
        this.notify.showError(error);
      }
    );
  }

  public submit(): void {
    if (this.form.valid) {
      this.spinner.show();
      this.api.patch("/auth/profile", this.model).subscribe(
        (response) => {
          this.modalRef.close("");
          this.notify.showSuccess("Confirmation: Profile successfully updated");
          // spinner hide is included into the reload user method
          this.reloadUser();
        },
        (error) => {
          this.notify.showError(error);
          this.spinner.hide();
        }
      );
    }
  }
}
