import { Component, Input, OnInit, Output, EventEmitter } from "@angular/core";
import { FormDataService, FormData } from "@app/services/formData.service";
import { decode, PP_TIME_RANGES } from "@app/services/data";
import { DataService } from "@app/services/data.service";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { AuthService } from "@rapydo/services/auth";
import { ConfirmationModals } from "@rapydo/services/confirmation.modals";
import { User, ConfirmationModalOptions } from "@rapydo/types";

@Component({
  selector: "mst-my-request-details",
  templateUrl: "./my-request-details.component.html",
  styleUrls: ["./my-request-details.component.css"],
})
export class MyRequestDetailsComponent implements OnInit {
  myRequest: FormData;
  @Input() onSubmitStep = false;
  @Output() onCancel: EventEmitter<null> = new EventEmitter<null>();

  PP_TIME_RANGES = PP_TIME_RANGES;
  decode = decode;
  user: User;

  constructor(
    private formDataService: FormDataService,
    public dataService: DataService,
    private modalService: NgbModal,
    private confirmationModals: ConfirmationModals,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.user = this.authService.getUser();
    this.myRequest = this.formDataService.getFormData();
  }

  emptyName() {
    return (
      !this.myRequest.request_name ||
      this.myRequest.request_name.trim().length === 0
    );
  }

  open(content) {
    this.modalService.open(content).result.then(
      (result) => {
        console.log("open license content");
      },
      (reason) => {
        // do nothing
      }
    );
  }

  cancel() {
    const options: ConfirmationModalOptions = {
      title: "Cancel this request",
      text: "Are you really sure you want to cancel this request?",
      subText:
        "This operation cannot be undone. This takes you back to the initial step for selecting a new dataset.",
      cancelButton: "Undo",
      confirmButton: "Confirm",
    };

    this.confirmationModals.open(options).then(
      (result) => {
        this.onCancel.emit();
      },
      (reason) => {}
    );
  }

  getConfirmation(name) {
    return {
      title: "Confirmation required",
      message:
        `<div class='card text-center'>
          <div class='card-body'>
          <h4 class='card-title'>Are you really sure you want to cancel this ` +
        name +
        `?</h4>
          <p class='card-text'>This operation cannot be undone. This takes you back to the initial step for selecting a new dataset.</p>
          </div>
          </div>`,
    };
  }

  toggleDataPush() {
    this.myRequest.push = !this.myRequest.push;
  }
  getFileName(path) {
    let filepath = path.split("/");
    return filepath[filepath.length - 1];
  }
}
