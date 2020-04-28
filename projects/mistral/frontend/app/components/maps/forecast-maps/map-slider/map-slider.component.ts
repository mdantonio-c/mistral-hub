import {Component, Input, Output, OnChanges, ViewChild, AfterViewInit, EventEmitter, HostListener} from '@angular/core';
import {DomSanitizer} from '@angular/platform-browser';
import {MeteoFilter, MeteoService} from "../services/meteo.service";
import {Areas, Fields, Resolutions} from "../services/data";
import {NgbCarousel, NgbSlideEvent} from '@ng-bootstrap/ng-bootstrap';
import * as moment from 'moment';
import {NgxSpinnerService} from 'ngx-spinner';
import * as bootstrap_slider from 'bootstrap-slider/dist/bootstrap-slider.min.js'

const SLIDER_TICKS = [0, 12, 24, 36, 48, 60, 72];

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
    fromMin: number;
    maxHour = 48;
    sid: number;
    sliderTicks = SLIDER_TICKS;
    legendToShow: any;
    isImageLoading = false;
    grid_num = 6;
    utcTime = true;
    public readonly LEGEND_SPINNER = 'legendSpinner';
    public readonly IMAGE_SPINNER = 'imageSpinner';

    @Output() onCollapse: EventEmitter<null> = new EventEmitter<null>();

    private lastRunAt: moment.Moment;
    timestamp: string;

    @ViewChild('carousel', {static: true}) carousel: NgbCarousel;

    constructor(
        private sanitizer: DomSanitizer,
        private meteoService: MeteoService,
        private spinner: NgxSpinnerService) {
    }

    setInputSliderFormatter(value) {
        return `+${value}h`;
    }

    ngOnChanges(): void {
        // parse reftime as utc date
        // console.log(`reference time ${this.reftime}`);
        this.lastRunAt = moment.utc(`${this.reftime}`, "YYYYMMDDHH");
        // console.log(`last run at ${this.lastRunAt}`);
        this.timestamp = this.lastRunAt.format();

        this.grid_num = (this.filter.res === 'lm2.2') ? 4 : 6;

        this.images.length = 0;
        setTimeout(() => {
            this.spinner.show(this.IMAGE_SPINNER);
        }, 0);

        this.isImageLoading = true;
        this.meteoService.getAllMapImages(this.filter, this.offsets).subscribe(
            blobs => {
                for (let i = 0; i < this.offsets.length; i++) {
                    this.images[i] = this.sanitizer.bypassSecurityTrustUrl(URL.createObjectURL(blobs[i]));
                }
            }, error => {
                console.log(error);
            }
        ).add(() => {
            this.spinner.hide(this.IMAGE_SPINNER);
            this.isImageLoading = false;
            // once the maps have been loaded I can preset the carousel
            this.presetSlider();
        });

        if (this.filter.field === 'prec3' || this.filter.field === 'snow3') {
            this.fromMin = 3;
        } else if (this.filter.field === 'prec6' || this.filter.field === 'snow6') {
            this.fromMin = 6;
        } else if (this.filter.field === 'percentile' || this.filter.field === 'probability') {
            this.fromMin = 6;
        } else {
            this.fromMin = 0
        }
        this.sid = this.fromMin;
        this.maxHour = (this.filter.res === 'lm2.2') ? 48 : 72;
        if (this.maxHour === 48) {
            this.sliderTicks.slice(this.sliderTicks.length - 2);
        }

        // get legend from service
        this.spinner.show(this.LEGEND_SPINNER);
        this.meteoService.getMapLegend(this.filter).subscribe(
            blob => {
                this.legendToShow = this.sanitizer.bypassSecurityTrustUrl(URL.createObjectURL(blob));
            }, error => {
                console.log(error);
            }
        ).add(() => {
            this.spinner.hide(this.LEGEND_SPINNER)
        });
    }

    ngAfterViewInit() {
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

    collapse() {
        this.onCollapse.emit();
    }

    /**
     * Called every time the slide transition is completed.
     * @param slideEvent
     */
    onSlide(slideEvent: NgbSlideEvent) {
        // position the handle of the slider accordingly
        let idx = parseInt(slideEvent.current.split("-").slice(-1)[0]);
        // console.log(`onSlide ${idx}`);
        this.setSliderTo(idx);
        this.updateTimestamp(idx);
    }

    /**
     * Called whenever the cursor is dragged or repositioned at a point in the timeline.
     * @param $event
     */
    updateCarousel(index: number) {
        // load image slide into the carousel accordingly
        // console.log(`update carousel to slideId-${index}`);
        setTimeout(() => {
            this.carousel.select(`slideId-${index}`);
            this.updateTimestamp(index);
        });

    }

    private setSliderTo(from) {
        // console.log(`set slider to ${from}`);
        this.sid = from;
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
     * Preset the carousel and the slider on the nearest current hour.
     */
    private presetSlider() {
        // console.log('preset slider and update the carousel');
        let today = moment.utc();
        // let today = moment.utc("2020-01-31T18:30"); // for local test
        let from = 0;
        if (this.filter.field === 'prec3' || this.filter.field === 'snow3') {
            from += 3;
        }
        if (this.filter.field === 'prec6' || this.filter.field === 'snow6') {
            from += 6;
        }
        if (this.filter.field === 'percentile' || this.filter.field === 'probability') {
            from += 6;
	}
        if (this.lastRunAt.isSame(today, 'day')) {
            from = today.hours();
        }
        setTimeout(() => { this.updateCarousel(from); });
    }

    @HostListener('window:keydown', ['$event'])
    keyEvent(event: KeyboardEvent) {
        if (event.code === 'ArrowLeft') {
            this.carousel.prev();
        }
        if (event.code === 'ArrowRight') {
            this.carousel.next();
        }
    }

}
