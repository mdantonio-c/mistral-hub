import {Component, Input, OnChanges, ViewChild, AfterViewInit} from '@angular/core';
import {MeteoFilter} from "../services/meteo.service";
import {Areas, Fields, Resolutions} from "../services/data";
import {NgbCarousel, NgbSlideEvent, NgbSlideEventSource} from '@ng-bootstrap/ng-bootstrap';
import * as moment from 'moment';
import {IonRangeSliderComponent} from "ng2-ion-range-slider";

const base_url = "https://meteo.cineca.it/media";

@Component({
    selector: 'app-map-slider',
    templateUrl: './map-slider.component.html',
    styleUrls: ['./map-slider.component.css']
})
export class MapSliderComponent implements OnChanges, AfterViewInit {
    @Input() filter: MeteoFilter;
    today: Date = new Date();
    images: any[] = [];
    paused = true;
    maxHour: number = 48;

    @ViewChild('carousel', {static: true}) carousel: NgbCarousel;
    @ViewChild('timeSlider', {static: false}) timeSliderEl: IonRangeSliderComponent;

    ngOnChanges(): void {
        let offsets = Array(24).fill(null).map((_, i) => '00' + i.toString().padStart(2, '0'));
        let arr2 = Array(24).fill(null).map((_, i) => '01' + i.toString().padStart(2, '0'));
        offsets.push(...arr2);
        if (this.filter.resolution === 'lm5') {
            let arr3 = Array(24).fill(null).map((_, i) => '02' + i.toString().padStart(2, '0'));
            offsets.push(...arr3);
            offsets.push(...['0300']);
        } else {
            offsets.push(...['0200']);
        }
        this.images.length = 0;
        this.images = offsets.map((offset, index) => ({
                'url': this.getImageUrl(offset),
                'datetime': index
            }));
        this.maxHour = this.filter.resolution === 'lm2.2' ? 48 : 72;
    }

    ngAfterViewInit() {
        this.carousel.pause();
    }

    togglePaused() {
        if (this.paused) {
            this.carousel.cycle();
        } else {
            this.carousel.pause();
        }
        this.paused = !this.paused;
    }

    /**
     * Called every time the slide transition is completed.
     * @param slideEvent
     */
    onSlide(slideEvent: NgbSlideEvent) {
        // position the handle of the slider accordingly
        this.setSliderTo(slideEvent.current.split("-").slice(-1)[0]);
    }

    /**
     * Called whenever the cursor is dragged or repositioned at a point in the timeline.
     * @param $event
     */
    updateSlider($event) {
        // load image slide into the carousel accordingly
        //console.log(`navigate to a slide identified by: ngb-slide-${$event.from}`);
        this.carousel.select(`slideId-${$event.from}`);
    }

    private setSliderTo(from) {
        this.timeSliderEl.update({from: from});
    }

    getLegendUrl() {
        return `${base_url}/${this.filter.platform}/${this.filter.modality}` +
            `/Magics-${this.filter.run}-${this.filter.resolution}.web` +
            `/legends/${this.filter.field}.png`
    }

    getValue(param: string, key: string) {
        switch (param) {
            case 'field':
                return Fields.find(f => f.key === key).value;
            case 'resolution':
                return Resolutions.find(r => r.key === key).value;
            case 'area':
                return Areas.find(a => a.key === key).value;
        }

    }

    /**
     * @param offset (00|01|02|03)[00-23]
     * @param date YYYYMMDD
     */
    getImageUrl(offset: string, date?: string) {
        if (!date) date = moment(this.today).format('YYYYMMDD');
        return `${base_url}/${this.filter.platform}/${this.filter.modality}` +
            `/Magics-${this.filter.run}-${this.filter.resolution}.web` +
            `/${this.filter.area}/${this.filter.field}/` +
            `${this.filter.field}.${date}${this.filter.run}.${offset}.png`;
    }

}
