import { Component, Input, OnInit, Output, EventEmitter } from "@angular/core";
import { FormDataService, FormData } from "@app/services/formData.service";
import { decode, PP_TIME_RANGES } from "@app/services/data";
import { DataService } from "@app/services/data.service";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";

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

  constructor(
    private formDataService: FormDataService,
    public dataService: DataService,
    private modalService: NgbModal
  ) {}

  ngOnInit(): void {
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
    this.onCancel.emit();
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
}
