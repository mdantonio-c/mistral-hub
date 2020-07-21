import { FormatDatePipe } from "./format-date.pipe";
import { LOCALE_ID } from "@angular/core";
import { DatePipe } from "@angular/common";

describe("FormatDatePipe", () => {
  const datePipe = new DatePipe("en-US");
  const pipe = new FormatDatePipe(datePipe);
  const dateArray = [2019, 6, 23, 12, 0, 0];

  it("create an instance", () => {
    expect(pipe).toBeTruthy();
  });

  it("should transform a date array value", () => {
    expect(pipe.transform(dateArray)).toEqual(`23 Jun 2019 12:00:00 <UTC>`);
  });
});
