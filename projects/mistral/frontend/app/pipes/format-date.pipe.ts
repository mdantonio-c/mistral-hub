import {Pipe, PipeTransform} from '@angular/core';
import {DatePipe} from '@angular/common';

@Pipe({
    name: 'fmtDate'
})
export class FormatDatePipe implements PipeTransform {

    constructor(private datePipe: DatePipe) {}

    /**
     * Transform date such as [2019,6,23,12,0,0] in human-readable '23 June 2019 12:00:00'
     * @param dateArr
     */
    transform(dateArr: number[]): string {
        if (!dateArr) return;
        if (dateArr.length !== 6) {
            console.warn(`Unexpected value for ${dateArr}`);
            return dateArr.join();
        }
        const date = new Date(dateArr[0], dateArr[1] - 1, dateArr[2], dateArr[3], dateArr[4], dateArr[5]);
        return `${this.datePipe.transform(date, 'dd LLL y HH:mm:ss')}`;
    }

}
