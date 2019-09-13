import {Component} from '@angular/core';

@Component({
    selector: 'app-dashboard',
    templateUrl: './dashboard.component.html',
    styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent {
    selectedTabId = 'requests';

    onTabChange($event) {
        this.selectedTabId = $event.nextId;
    }

}
