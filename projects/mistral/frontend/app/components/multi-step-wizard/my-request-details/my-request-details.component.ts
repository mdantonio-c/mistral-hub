import { Component, Input, OnInit } from "@angular/core";
import {
  FormDataService,
  FormData,
  PP_TIME_RANGES,
} from "@app/services/formData.service";
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

  constructor(
    private formDataService: FormDataService,
    public dataService: DataService,
    private modalService: NgbModal
  ) {}

  ngOnInit(): void {
    this.myRequest = this.formDataService.getFormData();
  }

  emptyName() {
    return !this.myRequest.name || this.myRequest.name.trim().length === 0;
  }

  decodeTimeranges(code) {
    let t = PP_TIME_RANGES.find((x) => x.code === code);
    return t !== undefined ? t.desc : code;
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
}
