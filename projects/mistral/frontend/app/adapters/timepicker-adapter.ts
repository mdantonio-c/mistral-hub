import {Injectable} from '@angular/core';
import {NgbTimeStruct, NgbTimeAdapter} from '@ng-bootstrap/ng-bootstrap';

/**
 * String Time adapter
 */
@Injectable()
export class NgbTimeStringAdapter extends NgbTimeAdapter<string> {

  fromModel(value: string): NgbTimeStruct {
    if (!value) {
      return null;
    }
    const split = value.toString().split(':');
    return {
      hour: parseInt(split[0], 10),
      minute: parseInt(split[1], 10),
      second: parseInt(split[2], 10)
    };
  }

  toModel(time: NgbTimeStruct): string {
    if (!time) {
      return null;
    }
    return `${this.pad(time.hour)}:${this.pad(time.minute)}`;
  }

  private pad(i: number): string {
    return i < 10 ? `0${i}` : `${i}`;
  }
}
