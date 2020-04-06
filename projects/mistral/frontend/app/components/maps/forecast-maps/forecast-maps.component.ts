import {Component, OnInit, ViewChild, ElementRef, HostListener} from "@angular/core";
import {MeteoFilter, MeteoService} from "./services/meteo.service";
import {NotificationService} from '@rapydo/services/notification';

@Component({
    selector: 'app-forecast-maps',
    templateUrl: './forecast-maps.component.html'
})
export class ForecastMapsComponent implements OnInit {
    loading = false;
    filter: MeteoFilter;
    offsets: string[] = [];
    reftime: string; // YYYYMMDD
    isFilterCollapsed = false;
    private collapsed = false;

    constructor(private meteoService: MeteoService, private notify: NotificationService) {
    }

    ngOnInit() {
        this.setCollapse(window.innerWidth);
    }

    applyFilter(filter: MeteoFilter) {
        this.loading = true;
        this.filter = filter;
        this.offsets.length = 0;
        console.log(filter);

        // get data
        this.meteoService.getMapset(filter).subscribe(
            response => {
                this.offsets = response.offsets;
                this.reftime = response.reftime;
                // always apply platform value from this response
                // this means request maps from that platform
                this.filter.platform = response.platform;
                if (!this.filter.env) {
                    this.filter.env = 'PROD';
                }
            },
            error => {
                this.notify.showError(error);
            }
        ).add(() => {
            this.loading = false;
        });
    }

    toggleCollapse() {
        this.isFilterCollapsed = !this.isFilterCollapsed;
    }

    private setCollapse(width: number) {
        if (width < 991.98) {
            if (!this.collapsed) {
                this.isFilterCollapsed = true;
                this.collapsed = true;
            }
        } else {
            this.isFilterCollapsed = false;
            this.collapsed = false;
        }
    }

    @HostListener('window:resize', ['$event'])
    onResize(event) {
        this.setCollapse(event.target.innerWidth);
    }
}
