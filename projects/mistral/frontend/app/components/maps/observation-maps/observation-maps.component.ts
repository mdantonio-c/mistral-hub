import {Component, OnInit, ViewChild, ElementRef} from "@angular/core";
import {ObsFilter} from "./services/obs.service";
import {ObsMapComponent} from "./obs-map/obs-map.component";

@Component({
    selector: 'app-observation-maps',
    templateUrl: './observation-maps.component.html',
    styleUrls: ['./observation-maps.component.css']
})
export class ObservationMapsComponent {
    totalItems: number = 0;

    @ViewChild(ObsMapComponent) map: ObsMapComponent;

    applyFilter(filter: ObsFilter) {
        setTimeout(() => {
             this.map.updateMap(filter);
        }, 0);

    }

}
