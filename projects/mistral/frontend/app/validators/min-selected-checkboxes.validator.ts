import { FormArray, AbstractControl, ValidatorFn } from "@angular/forms";

export function minSelectedCheckboxes(min = 1): ValidatorFn {
  return (formArray: AbstractControl): { [key: string]: boolean } | null => {
    const totalSelected = (formArray as FormArray).controls
      // get a list of checkbox values (boolean)
      .map((control) => control.value)
      // total up the number of checked checkboxes
      .reduce((prev, next) => (next ? prev + next : prev), 0);

    // if the total is not greater than the minimum, return the error message
    return totalSelected >= min ? null : { required: true };
  };
}
