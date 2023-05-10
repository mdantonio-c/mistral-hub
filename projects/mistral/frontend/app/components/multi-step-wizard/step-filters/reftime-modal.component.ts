import { Component, Input, OnInit } from "@angular/core";
import { NgbActiveModal } from "@ng-bootstrap/ng-bootstrap";
import { FormGroup, FormControl, Validators } from "@angular/forms";
import { NgbDateStruct } from "@ng-bootstrap/ng-bootstrap";
import * as moment from "moment";
import { timeRangeInconsistencyValidator } from "../../../validators/time-range-inconsistency.validator";

@Component({
  selector: "reftime-modal-content",
  templateUrl: "./reftime-modal.component.html",
  styles: [".top-fixed { position: absolute; top: -18px; }"],
})
export class ReftimeModalContent implements OnInit {
  form: FormGroup;

  // @ts-ignore
  @Input() set data(value) {
    this.disabledDp = value.fullDataset;
    this.form = ReftimeModel.getReftime(value);
  }

  fromMaxDate: NgbDateStruct = this.today();
  toMinDate: NgbDateStruct;
  disabledDp = false;

  constructor(public modal: NgbActiveModal) {}

  ngOnInit() {
    // subscribe form value changes
    this.onChanges();
    // enable or disable datepicker
    this.checkRefTimeControls();
  }

  private onChanges(): void {
    this.form.get("fromDate").valueChanges.subscribe((val) => {
      if (!(val instanceof Date)) return;
      this.toMinDate = {
        year: (val as Date).getUTCFullYear(),
        month: (val as Date).getUTCMonth() + 1,
        day: (val as Date).getUTCDate(),
      };
    });
    this.form.get("toDate").valueChanges.subscribe((val) => {
      if (!(val instanceof Date)) return;
      this.fromMaxDate = {
        year: (val as Date).getUTCFullYear(),
        month: (val as Date).getUTCMonth() + 1,
        day: (val as Date).getUTCDate(),
      };
    });
  }

  today(): NgbDateStruct {
    const today = moment.utc();
    return { year: today.year(), month: today.month() + 1, day: today.date() };
  }

  selectToday() {
    let d = moment().utc().toDate();
    (this.form.controls.fromDate as FormControl).setValue(d);
    (this.form.controls.toDate as FormControl).setValue(d);
  }

  toggleFullDataset() {
    this.disabledDp = !this.disabledDp;
    (this.form.controls.fullDataset as FormControl).setValue(this.disabledDp);
    this.checkRefTimeControls();
  }

  private checkRefTimeControls() {
    if (this.disabledDp) {
      (this.form.controls.fromDate as FormControl).disable();
      (this.form.controls.fromTime as FormControl).disable();
      (this.form.controls.toDate as FormControl).disable();
      (this.form.controls.toTime as FormControl).disable();
    } else {
      (this.form.controls.fromDate as FormControl).enable();
      (this.form.controls.fromTime as FormControl).enable();
      (this.form.controls.toDate as FormControl).enable();
      (this.form.controls.toTime as FormControl).enable();
    }
  }
}

export abstract class ReftimeModel {
  public static getReftime = getReftime;
}

function getReftime(value): FormGroup {
  value = value || {
    fromDate: null,
    fromTime: null,
    toDate: null,
    toTime: null,
    fullDataset: false,
  };
  return new FormGroup(
    {
      fromDate: new FormControl(value.fromDate, [Validators.required]),
      fromTime: new FormControl(value.fromTime, [Validators.required]),
      toDate: new FormControl(value.toDate, [Validators.required]),
      toTime: new FormControl(value.toTime, [Validators.required]),
      fullDataset: new FormControl(value.fullDataset),
    },
    {
      validators: [timeRangeInconsistencyValidator],
    },
  );
}
