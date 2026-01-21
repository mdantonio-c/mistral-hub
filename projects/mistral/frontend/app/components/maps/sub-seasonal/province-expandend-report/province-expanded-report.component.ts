import { Component, Input, ChangeDetectorRef } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import { NgxSpinnerService } from "ngx-spinner";
@Component({
  selector: "app-province-expanded-report",
  templateUrl: "./province-expanded-report.component.html",
  styleUrls: ["./province-expanded-report.component.scss"],
})
export class ProvinceExpandedReportComponent {
  constructor(
    public activeModal: NgbActiveModal,
    private spinner: NgxSpinnerService,
    private cdr: ChangeDetectorRef,
  ) {}
}
