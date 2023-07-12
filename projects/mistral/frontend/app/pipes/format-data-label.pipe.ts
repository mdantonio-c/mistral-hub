import { Pipe, PipeTransform } from "@angular/core";
import * as moment from "moment";

@Pipe({
  name: "fmtLabelDate",
})
export class FormatLabelDatePipe implements PipeTransform {
  /**
   * Transform ISO date time to specific locale
   * @param dateStr ISO date format
   * @param locale for language translation
   * @param showLocalTime
   */
  transform(
    dateStr: string,
    locale: string = "en",
    showLocalTime: boolean = false,
  ): string {
    if (!dateStr) return;
    const date = showLocalTime
      ? moment.utc(dateStr).local()
      : moment.utc(dateStr);
    return date.locale(locale).format("LLL");
  }
}
