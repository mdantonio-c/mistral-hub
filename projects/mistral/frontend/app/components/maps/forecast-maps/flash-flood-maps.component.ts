import {Component, OnInit} from "@angular/core";
import {ForecastMapsBaseComponent} from "./forecast-maps-base.component";
import {MeteoFilter} from "./services/meteo.service";

@Component({
    selector: 'app-flash-flood-maps',
    templateUrl: './flash-flood-maps.component.html'
    // template: ``
})
export class FlashFloodMapsComponent extends ForecastMapsBaseComponent implements OnInit {

    ngOnInit() {
        super.ngOnInit();
    }

    applyFilter(filter: MeteoFilter) {
        console.log('apply filter');
    }

}
