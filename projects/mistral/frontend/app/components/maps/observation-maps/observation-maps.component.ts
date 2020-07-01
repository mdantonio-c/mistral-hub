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
    currentView: string = 'Data';
    filter: ObsFilter;

    @ViewChild(ObsMapComponent) map: ObsMapComponent;

    applyFilter(filter?: ObsFilter) {
        if (filter) {
            this.filter = filter;
        }
        this.filter.onlyStations = (this.currentView === 'Stations');
        setTimeout(() => {
             this.map.updateMap(this.filter);
        }, 0);
    }

    changeFilter(filter: ObsFilter) {
        console.log('devo fare qualcosa qui????');
    }

    changeView(view) {
		this.currentView = view;
        this.applyFilter();
	}

}
