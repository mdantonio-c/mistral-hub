import {FormatDatePipe} from './format-date.pipe';
import {DatePipe} from '@angular/common';

describe('FormatDatePipe', () => {
    const datePipe = new DatePipe('it-IT');
    const pipe = new FormatDatePipe(datePipe);
    const dateArray = [2019, 6, 23, 12, 0, 0];

    it('create an instance', () => {
        expect(pipe).toBeTruthy();
    });

    it('should transform a date array value', () => {
      // TODO
      //expect(pipe.transform(dateArray)).toEqual(`?????`);
    });
});
