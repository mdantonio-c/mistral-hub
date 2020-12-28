import { Component, OnInit } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import {
  FormBuilder,
  FormGroup,
  FormArray,
  FormControl,
  ValidatorFn,
} from "@angular/forms";
import { NotificationService } from "@rapydo/services/notification";
import { FormDataService } from "@app/services/formData.service";
import { Dataset } from "@app/types";
import { NgxSpinnerService } from "ngx-spinner";
import { StepComponent } from "../step.component";

@Component({
  selector: "step-datasets",
  templateUrl: "./step-datasets.component.html",
  styleUrls: ["./step-datasets.component.css"],
})
export class StepDatasetsComponent extends StepComponent implements OnInit {
  title = "Please select one or more datasets";
  datasets: Dataset[];
  form: FormGroup;
  selectedCategories: string[] = [];

  constructor(
    private formBuilder: FormBuilder,
    protected router: Router,
    protected route: ActivatedRoute,
    protected formDataService: FormDataService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService
  ) {
    super(formDataService, router, route);
    this.form = this.formBuilder.group({
      datasets: new FormArray([], minSelectedCheckboxes(1)),
    });
  }

  ngOnInit() {
    this.spinner.show();
    this.formDataService
      .getDatasets()
      .subscribe(
        (response) => {
          this.datasets = response;
          // console.log('Dataset(s) loaded', this.datasets);
          if (this.datasets.length === 0) {
            this.notify.showWarning(
              "Unexpected result. The list of datasets is empty."
            );
          }
          this.datasets.map((o, i) => {
            const control = new FormControl(
              this.formDataService.isDatasetSelected(o.id)
            );
            (this.form.controls.datasets as FormArray).push(control);
          });
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        this.spinner.hide();
      });

    this.onChanges();
  }

  private onChanges(): void {
    this.form.get("datasets").valueChanges.subscribe((val) => {
      let categories = val
        .map((v, i) => (v ? this.datasets[i].category : null))
        .filter((v) => v !== null);
      this.selectedCategories = categories.filter(
        (v, i) => categories.indexOf(v) === i
      );
      if (this.selectedCategories.length > 1) {
        this.notify
          .showWarning(`It is not currently possible to mix different types of datasets.
                Please select datasets under the same category.`);
      }
      let selected_datasets = val
        .map((v, i) => (v ? this.datasets[i].id : null))
        .filter((v) => v !== null);
      if (
        selected_datasets.includes("multim-forecast") &&
        selected_datasets.length > 1
      ) {
        this.notify.showWarning(
          `The selection of multiple datasets is not supported if Multi-Model Ensemble is included.`
        );
      }
    });
  }

  private save(selectedDatasetsIds: string[]): boolean {
    if (!this.form.valid) {
      return false;
    }

    this.formDataService.setDatasets(
      this.datasets.filter((x) => selectedDatasetsIds.includes(x.id))
    );
    return true;
  }

  goToNext() {
    const selectedDatasetsIds = this.form.value.datasets
      .map((v, i) => (v ? this.datasets[i].id : null))
      .filter((v) => v !== null);
    console.log(selectedDatasetsIds);
    if (this.save(selectedDatasetsIds)) {
      // Navigate to the filter page
      this.router.navigate(["../", "filters"], { relativeTo: this.route });
    }
  }
}

function minSelectedCheckboxes(min = 1) {
  const validator: ValidatorFn = (formArray: FormArray) => {
    const totalSelected = formArray.controls
      // get a list of checkbox values (boolean)
      .map((control) => control.value)
      // total up the number of checked checkboxes
      .reduce((prev, next) => (next ? prev + next : prev), 0);

    // if the total is not greater than the minimum, return the error message
    return totalSelected >= min ? null : { required: true };
  };

  return validator;
}
