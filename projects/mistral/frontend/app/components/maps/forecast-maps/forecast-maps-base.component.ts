import {Component, OnInit, HostListener} from "@angular/core";
import {MeteoFilter, MeteoService} from "./services/meteo.service";
import {NotificationService} from '@rapydo/services/notification';
import {NgxSpinnerService} from 'ngx-spinner';

@Component({
    selector: 'app-map-layout',
    template: ``
})
export class ForecastMapsBaseComponent implements OnInit {
    isFilterCollapsed = false;
    private collapsed = false;

    constructor(protected meteoService: MeteoService,
                protected notify: NotificationService,
                protected spinner: NgxSpinnerService) {
    }

    ngOnInit() {
        this.setCollapse(window.innerWidth);
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
