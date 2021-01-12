import { AbstractControl, ValidationErrors, ValidatorFn } from "@angular/forms";

/** From time can't be greater than To time */
export const timeRangeInconsistencyValidator: ValidatorFn = (
  control: AbstractControl
): ValidationErrors | null => {
  const fromTime = control.get("fromTime");
  const toTime = control.get("toTime");
  const from = control.get("fromDate");
  const to = control.get("toDate");
  return from &&
    to &&
    fromTime &&
    toTime &&
    datesAreOnSameDay(from.value, to.value) &&
    fromTime.value > toTime.value
    ? { timeRangeInconsistency: true }
    : null;
};

const datesAreOnSameDay = (first, second) =>
  first instanceof Date &&
  second instanceof Date &&
  first.getFullYear() === second.getFullYear() &&
  first.getMonth() === second.getMonth() &&
  first.getDate() === second.getDate();
