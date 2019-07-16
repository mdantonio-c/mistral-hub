import {Component} from '@angular/core';

import {ApiService} from '/rapydo/src/app/services/api';
import {AuthService} from '/rapydo/src/app/services/auth';
import {NotificationService} from '/rapydo/src/app/services/notification';

@Component({
    templateUrl: './data.component.html'
})
export class DataComponent {

    public data_id: string;

    constructor(
        protected api: ApiService,
        protected auth: AuthService,
        protected notify: NotificationService,
    ) { }


    private schedule() {
        this.api.put("data").subscribe(
            response => {

                this.notify.extractErrors(response, this.notify.ERROR);
            }, error => {
                this.notify.extractErrors(error, this.notify.ERROR);
            }
        );
    }
    private get_data() {
        let data = {};
        this.api.post("data", data).subscribe(
            response => {

                this.data_id = response['data'];

                this.notify.extractErrors(response, this.notify.ERROR);
            }, error => {
                this.notify.extractErrors(error, this.notify.ERROR);
            }
        );
    }

}
