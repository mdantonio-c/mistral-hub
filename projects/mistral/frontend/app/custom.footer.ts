import { Component } from '@angular/core';
import * as moment from 'moment';
import { environment } from '@rapydo/../environments/environment'

@Component({
  selector: 'customfooter',
  templateUrl: './custom.footer.html',
})
export class CustomFooterComponent {

  public project: string;
  public version: string;
  public from_year: number = 2019;
  public to_year = moment().year();

  constructor() {
    var t = environment.projectDescription;
    t = t.replace(/^'/, "");
    t = t.replace(/'$/, "");
    this.project = t;
    this.version = environment.projectVersion;
  }

}
