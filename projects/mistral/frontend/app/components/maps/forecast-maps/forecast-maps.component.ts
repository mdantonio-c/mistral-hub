import {Component, OnInit, ViewChild, ElementRef} from "@angular/core";
import {MeteoFilter, MeteoService} from "./services/meteo.service";
import {NotificationService} from '@rapydo/services/notification';

@Component({
    selector: 'app-forecast-maps',
    templateUrl: './forecast-maps.component.html'
})
export class ForecastMapsComponent {
    loading = false;
    filter: MeteoFilter;
    offsets: string[] = [];
    reftime: string; // YYYYMMDD

    constructor(private meteoService: MeteoService, private notify: NotificationService) {
    }

    applyFilter(filter: MeteoFilter) {
        this.loading = true;
        this.filter = filter;
        this.offsets.length = 0;
        console.log(filter);

        // get data
        this.meteoService.getMapset(filter).subscribe(
            response => {
                this.offsets = response.data.offsets;
                this.reftime = response.data.reftime;
                // always apply platform value from this response
                // this means request maps from that platform
                this.filter.platform = response.data.platform;
                if (!this.filter.env) {
                    this.filter.env = 'PROD';
                }
            },
            error => {
                this.notify.extractErrors(error, this.notify.ERROR);
            }
        ).add(() => {
            this.loading = false;
        });
    }
}
