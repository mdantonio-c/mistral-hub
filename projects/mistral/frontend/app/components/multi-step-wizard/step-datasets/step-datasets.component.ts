import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, FormArray, FormControl, ValidatorFn} from '@angular/forms';
import {FormDataService} from "../../../services/formData.service";
import {NotificationService} from '/rapydo/src/app/services/notification';
import {Dataset} from "../../../services/formData.model";
import {of} from 'rxjs';

@Component({
    selector: 'step-datasets',
    templateUrl: './step-datasets.component.html'
})
export class StepDatasetsComponent implements OnInit {
  title = 'Please select one or more datasets';
  datasets: Dataset[];
  form: FormGroup;

  constructor(private formBuilder: FormBuilder,
              private router: Router,
              private route: ActivatedRoute,
              private formDataService: FormDataService,
              private notify: NotificationService) {
    this.form = this.formBuilder.group({
      datasets: new FormArray([], minSelectedCheckboxes(1))
    });
  }

  ngOnInit() {
    this.formDataService.getDatasets().subscribe(response => {
      this.datasets = response.data;
      if (this.datasets.length === 0) {
        this.notify.showWarning("Unexpected result. The list of datasets is empty.");
      }
      this.datasets.map((o, i) => {
        const control = new FormControl(this.formDataService.isDatasetSelected(o.id));
        (this.form.controls.datasets as FormArray).push(control);
      });
      console.log('Datasets loaded!');
    });
  }

  private save(selectedDatasetsIds: string[]): boolean {
    if (!this.form.valid) {
      return false;
    }

    this.formDataService.setDatasets(selectedDatasetsIds);
    return true;
  }

  goToNext() {
    const selectedDatasetsIds = this.form.value.datasets
      .map((v, i) => v ? this.datasets[i].id : null)
      .filter(v => v !== null);
    console.log(selectedDatasetsIds);
    if (this.save(selectedDatasetsIds)) {
      // Navigate to the filter page
      this.router.navigate(
        ['../', 'filters'], { relativeTo: this.route });
    }
  }

}

function minSelectedCheckboxes(min = 1) {
  const validator: ValidatorFn = (formArray: FormArray) => {
    const totalSelected = formArray.controls
    // get a list of checkbox values (boolean)
      .map(control => control.value)
      // total up the number of checked checkboxes
      .reduce((prev, next) => next ? prev + next : prev, 0);

    // if the total is not greater than the minimum, return the error message
    return totalSelected >= min ? null : {required: true};
  };

  return validator;
}
