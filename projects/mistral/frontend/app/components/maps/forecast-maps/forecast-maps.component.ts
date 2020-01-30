import {Component, OnInit, ViewChild, ElementRef} from "@angular/core";
import {MeteoFilter} from "./services/meteo.service";

@Component({
    selector: 'app-forecast-maps',
    templateUrl: './forecast-maps.component.html'
})
export class ForecastMapsComponent {
    loading = false;
    filter: MeteoFilter;

    applyFilter(filter: MeteoFilter) {
        this.loading = true;
        this.filter = filter;
        console.log(filter);

        // get data
        // setTimeout( () => { /*Your Code*/ }, 3000 );

        this.loading = false;
    }
}
