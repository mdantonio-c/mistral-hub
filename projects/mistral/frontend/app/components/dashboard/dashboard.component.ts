import {Component, ViewChild} from '@angular/core';
import {RequestsComponent} from "../requests/requests.component";
import {SchedulesComponent} from "../schedules/schedules.component";

@Component({
    selector: 'app-dashboard',
    templateUrl: './dashboard.component.html',
    styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent {
    selectedTabId = 'requests';
    @ViewChild('rTab', {static: false}) requests: RequestsComponent;
    @ViewChild('sTab', {static: false}) schedules: SchedulesComponent;

    onTabChange($event) {
        this.selectedTabId = $event.nextId;
    }

    list() {
        if (this.selectedTabId == 'requests') {
            this.requests.list();
        } else {
            this.schedules.list();
        }
    }

}
