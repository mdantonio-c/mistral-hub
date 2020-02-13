import {Component, Input, OnChanges, ViewChild, AfterViewInit} from '@angular/core';
import {DomSanitizer} from '@angular/platform-browser';
import {MeteoFilter, MeteoService} from "../services/meteo.service";
import {Areas, Fields, Resolutions} from "../services/data";
import {NgbCarousel, NgbSlideEvent} from '@ng-bootstrap/ng-bootstrap';
import * as moment from 'moment';
import {IonRangeSliderComponent} from "ng2-ion-range-slider";

@Component({
    selector: 'app-map-slider',
    templateUrl: './map-slider.component.html',
    styleUrls: ['./map-slider.component.css']
})
export class MapSliderComponent implements OnChanges, AfterViewInit {
    @Input() filter: MeteoFilter;
    @Input() offsets: string[];
    @Input() reftime: string;

    images: any[] = [];
    paused = true;
    maxHour: number = 48;
    legendToShow: any;
    isLegendLoading = false;
    grid_num = 6;
    utcTime = true;

    private lastRunAt: moment.Moment;
    timestamp: string;

    @ViewChild('carousel', {static: true}) carousel: NgbCarousel;
    @ViewChild('timeSlider', {static: false}) timeSliderEl: IonRangeSliderComponent;

    constructor(
        private sanitizer: DomSanitizer,
        private meteoService: MeteoService) {
    }

    ngOnChanges(): void {
        // parse reftime as utc date
        // console.log(`reference time ${this.reftime}`);
        this.lastRunAt = moment.utc(`${this.reftime}`, "YYYYMMDDHH");
        console.log(`last run at ${this.lastRunAt}`);
        this.timestamp = this.lastRunAt.format();

        this.grid_num = (this.filter.res === 'lm2.2') ? 4 : 6;

        this.images.length = 0;
        for (let i = 0; i < this.offsets.length; i++) {
            this.meteoService.getMapImage(this.filter, this.offsets[i]).subscribe(blob => {
                this.images[i] = this.sanitizer.bypassSecurityTrustUrl(URL.createObjectURL(blob));
            }, error => {
                console.log(error);
            });
        }
        this.maxHour = this.filter.res === 'lm2.2' ? 48 : 72;

        // get legend from service
        this.isLegendLoading = true;
        this.meteoService.getMapLegend(this.filter).subscribe(
            blob => {
                this.legendToShow = this.sanitizer.bypassSecurityTrustUrl(URL.createObjectURL(blob));
            }, error => {
                console.log(error);
            }
        ).add(() => {
            this.isLegendLoading = false;
        });
    }

    ngAfterViewInit() {
        this.setCurrentTime();
        this.carousel.pause();
    }

    /**
     * Stop and start map animation.
     */
    togglePaused() {
        if (this.paused) {
            this.carousel.cycle();
        } else {
            this.carousel.pause();
        }
        this.paused = !this.paused;
    }

    toggleUtcTime() {
        this.utcTime = !this.utcTime;
    }

    /**
     * Called every time the slide transition is completed.
     * @param slideEvent
     */
    onSlide(slideEvent: NgbSlideEvent) {
        // position the handle of the slider accordingly
        let idx = slideEvent.current.split("-").slice(-1)[0];
        this.setSliderTo(idx);
        this.updateTimestamp(parseInt(idx));
    }

    /**
     * Called whenever the cursor is dragged or repositioned at a point in the timeline.
     * @param $event
     */
    updateCarousel(index: number) {
        // load image slide into the carousel accordingly
        this.carousel.select(`slideId-${index}`);
        this.updateTimestamp(index);
    }

    private setSliderTo(from) {
        this.timeSliderEl.update({from: from});
    }

    getValue(param: string, key: string) {
        switch (param) {
            case 'field':
                return Fields.find(f => f.key === key).value;
            case 'res':
                return Resolutions.find(r => r.key === key).value;
            case 'area':
                return Areas.find(a => a.key === key).value;
        }
    }

    private updateTimestamp(amount: number) {
        let a = this.lastRunAt.clone().add(amount, 'hours');
        this.timestamp = a.format();
    }

    /**
     * Set timestamp to closest current hour
     */
    private setCurrentTime() {
        let today = moment.utc();
        // today.add(-7, 'days');  // for local test
        if (this.lastRunAt.isSame(today, 'day')) {
            this.setSliderTo(today.hours());
            setTimeout(() => {
                this.updateCarousel(today.hours());
            }, 500);
        }
    }

}
