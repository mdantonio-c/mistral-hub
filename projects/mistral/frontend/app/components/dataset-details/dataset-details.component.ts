import { Component, Input, OnInit } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import { Dataset } from "../../types";

@Component({
  selector: "app-dataset-details",
  templateUrl: "./dataset-details.component.html",
  styleUrls: ["./dataset-details.component.css"],
})
export class DatasetDetailsComponent implements OnInit {
  @Input() dataset: Dataset;
  active = 1;

  constructor(public activeModal: NgbActiveModal) {}

  ngOnInit() {
    console.log(this.dataset);
  }
}
