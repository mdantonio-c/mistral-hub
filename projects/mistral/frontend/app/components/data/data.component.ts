import {Component} from '@angular/core';

import {ApiService} from '@rapydo/services/api';
import {AuthService} from '@rapydo/services/auth';
import {NotificationService} from '@rapydo/services/notification';

@Component({
    templateUrl: './data.component.html'
})
export class DataComponent {

    public data_id: string;
    public loading: boolean = false;

    constructor(
        protected api: ApiService,
        protected auth: AuthService,
        protected notify: NotificationService,
    ) { }

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
