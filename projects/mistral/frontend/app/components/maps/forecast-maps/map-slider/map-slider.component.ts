import {
  Component,
  Input,
  Output,
  OnChanges,
  OnInit,
  ViewChild,
  AfterViewInit,
  EventEmitter,
  HostListener,
} from "@angular/core";
import { DomSanitizer } from "@angular/platform-browser";
import { MeteoFilter, MeteoService } from "../services/meteo.service";
import {
  Areas,
  Fields,
  FlashFloodFFields,
  Resolutions,
  Runs,
  IffRuns,
  KeyValuePair,
} from "../services/data";
import { NgbCarousel, NgbSlideEvent } from "@ng-bootstrap/ng-bootstrap";
import * as moment from "moment";
import { NgxSpinnerService } from "ngx-spinner";

const SLIDER_TICKS = [0, 12, 24, 36, 48, 60, 72];

@Component({
  selector: "app-map-slider",
  templateUrl: "./map-slider.component.html",
  styleUrls: ["./map-slider.component.scss"],
})
export class MapSliderComponent implements OnChanges, AfterViewInit, OnInit {
  @Input() filter: MeteoFilter;
  @Input() offsets: string[];
  @Input() reftime: string;

  images: any[] = [];
  paused = true;
  // private fromMin: number;
  fromMinImage = 0;
  minHour = 0;
  maxHour = 48;
  /* slide id */
  sid: number;
  /* increment step of the slider */
  step: number;
  sliderTicks = SLIDER_TICKS;
  legendToShow: any;
  isImageLoading = false;
  grid_num = 6;
  utcTime = true;
  public readonly LEGEND_SPINNER = "legendSpinner";
  public readonly IMAGE_SPINNER = "imageSpinner";
  selectedRun: KeyValuePair;

  @Output() onCollapse: EventEmitter<null> = new EventEmitter<null>();

  private lastRunAt: moment.Moment;
  timestamp: string;
  timestampRun: string;

  @ViewChild("carousel", { static: true }) carousel: NgbCarousel;

  constructor(
    private sanitizer: DomSanitizer,
    private meteoService: MeteoService,
    private spinner: NgxSpinnerService
  ) {}

  ngOnInit() {
    this.selectedRun =
      this.filter.field == "percentile" || this.filter.field == "probability"
        ? IffRuns.find((x) => this.filter.run === x.key)
        : Runs.find((x) => this.filter.run === x.key);
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
    this.timestampRun = this.lastRunAt.format();

    this.grid_num = this.filter.res === "lm2.2" ? 4 : 6;

    this.images.length = 0;
    setTimeout(() => {
      this.spinner.show(this.IMAGE_SPINNER);
    }, 0);

    this.isImageLoading = true;

    //if(this.filter.field === 'percentile' || this.filter.field === 'probability'){
    //    // take only till 0048, the first 15 images
    //    this.offsets = this.offsets.slice(0,15);
    //}
    //console.log(`ngOnChanges: offsets=${this.offsets}`);

    this.meteoService
      .getAllMapImages(this.filter, this.offsets)
      .subscribe(
        (blobs) => {
          //console.log(`ngOnChanges: offsets length=${this.offsets.length}`);
          for (let i = 0; i < this.offsets.length; i++) {
            this.images[i] = this.sanitizer.bypassSecurityTrustUrl(
              URL.createObjectURL(blobs[i])
            );
            //console.log(`ngOnChanges: i=${i}`);
          }
        },
        (error) => {
          console.log(error);
        }
      )
      .add(() => {
        this.spinner.hide(this.IMAGE_SPINNER);
        this.isImageLoading = false;
        // once the maps have been loaded I can preset the carousel
        this.presetSlider();
      });

    this.step = 1;
    // parseInt at end of string to get the min hour (e.g prec6 -> 6)
    const matchedValue = this.filter.field.match(/(\d+)$/);
    if (matchedValue) {
      this.minHour = parseInt(matchedValue[0], 10);
      this.fromMinImage = this.minHour;
    }

    if (
      this.filter.field === "percentile" ||
      this.filter.field === "probability"
    ) {
      this.minHour = 6;
      this.maxHour = this.filter.run === "12" ? 216 : 240;
      this.step = 3;
    } else {
      this.maxHour = this.filter.res === "lm2.2" ? 48 : 72;
      if (this.maxHour === 48) {
        this.sliderTicks.slice(this.sliderTicks.length - 2);
      }
    }
    this.sid = this.minHour;

    // get legend from service
    this.spinner.show(this.LEGEND_SPINNER);
    this.meteoService
      .getMapLegend(this.filter)
      .subscribe(
        (blob) => {
          this.legendToShow = this.sanitizer.bypassSecurityTrustUrl(
            URL.createObjectURL(blob)
          );
        },
        (error) => {
          console.log(error);
        }
      )
      .add(() => {
        this.spinner.hide(this.LEGEND_SPINNER);
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
    // console.log(`onSlide: idx=${idx}`);

    const offset =
      this.filter.field === "percentile" || this.filter.field === "probability"
        ? this.minHour
        : 0;
    let idxSlider = offset + idx * this.step;
    // temporary patch
    // due to: flash flood step from 144h to 240h is 6h
    if (
      (this.filter.field === "percentile" ||
        this.filter.field === "probability") &&
      idx >= 47
    ) {
      idxSlider = idxSlider + (idx - 46) * 3;
    }
    // console.log(`onSlide: idxSlider=${idxSlider}`);

    this.setSliderTo(idxSlider);
    this.updateTimestamp(idxSlider);
  }

  /**
   * Load image slide into the carousel properly.
   * Called whenever the cursor is dragged or repositioned at a point in the timeline.
   * @param index
   */
  updateCarousel(index: number) {
    // console.log(`updateCarousel: index=${index}`);
    let indexImage = index;
    if (
      this.filter.field === "percentile" ||
      this.filter.field === "probability"
    ) {
      if (index < this.minHour) {
        index = this.minHour;
        //console.log(`updateCarousel: 2- index=${index}`);
        this.sid = index;
      }
      // temporary patch
      // due to: flash flood step from 144h to 240h is 6h
      if (index >= 150) {
        indexImage = (index - this.minHour) / this.step;
        indexImage = 46 + (index - 144) / 6;
      } else {
        indexImage = (index - this.minHour) / this.step;
      }
    }
    // console.log(`updateCarousel: indexImage=${indexImage}`);
    setTimeout(() => {
      this.carousel.select(`slideId-${indexImage}`);
      this.updateTimestamp(index);
    });
  }

  private setSliderTo(from) {
    // console.log(`set slider to ${from}`);
    this.sid = from;
  }

  getValue(param: string, key: string) {
    switch (param) {
      case "field":
        return Fields.concat(FlashFloodFFields).find((f) => f.key === key)
          .value;
      case "res":
        return Resolutions.find((r) => r.key === key).value;
      case "area":
        return Areas.find((a) => a.key === key).value;
    }
  }

  /**
   * Update the date and time to be displayed at the bottom center of the map.
   * @param amount the value to be added to the reference time
   * @private
   */
  private updateTimestamp(amount: number) {
    let a = this.lastRunAt.clone().add(amount, "hours");
    this.timestamp = a.format();
  }

  /**
   * Preset the carousel and the slider on the nearest current hour.
   */
  private presetSlider() {
    // console.log('preset slider and update the carousel');
    let today = moment.utc();
    let from = this.minHour;
    if (
      !(
        this.filter.field === "percentile" ||
        this.filter.field === "probability"
      ) &&
      this.lastRunAt.isSame(today, "day") &&
      today.hours() > this.minHour
    ) {
      from = today.hours();
    }
    setTimeout(() => {
      this.updateCarousel(from);
    });
  }

  @HostListener("window:keydown", ["$event"])
  keyEvent(event: KeyboardEvent) {
    if (event.code === "ArrowLeft") {
      this.carousel.prev();
    }
    if (event.code === "ArrowRight") {
      this.carousel.next();
    }
  }

  /**
   * backward
   */
  backward() {
    this.carousel.prev();
  }
  /**
   * forward
   */
  forward() {
    this.carousel.next();
  }
}
