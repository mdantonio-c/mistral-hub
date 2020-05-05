import {Component, OnInit, ViewChild, ElementRef} from "@angular/core";
import {ObsFilter} from "./services/obs.service";

@Component({
    selector: 'app-observation-maps',
    templateUrl: './observation-maps.component.html',
    styleUrls: ['./observation-maps.component.css']
})
export class ObservationMapsComponent {
    filter: ObsFilter;
    totalItems: number = 0;

    applyFilter(filter: ObsFilter) {
        this.filter = filter;
    }

}
