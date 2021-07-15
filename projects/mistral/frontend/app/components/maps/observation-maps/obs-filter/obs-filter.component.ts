import {
  Component,
  OnInit,
  Output,
  EventEmitter,
  Input,
  ChangeDetectorRef,
} from "@angular/core";
import { FormBuilder, FormGroup, Validators } from "@angular/forms";
import { ObsFilter, CodeDescPair, FieldsSummary } from "@app/types";
import { ObsService } from "../services/obs.service";
import { LICENSES } from "../services/data";
import { NgbDateStruct, NgbCalendar } from "@ng-bootstrap/ng-bootstrap";
import { NotificationService } from "@rapydo/services/notification";
import { environment } from "@rapydo/../environments/environment";
import { User } from "@rapydo/types";
import { AuthService } from "@rapydo/services/auth";
import { NgxSpinnerService } from "ngx-spinner";
import * as moment from "moment";
import { debounceTime, distinctUntilChanged } from "rxjs/operators";
import { Subject } from "rxjs";

const LAST_DAYS = +environment.CUSTOM.LASTDAYS || 10;

@Component({
  selector: "app-obs-filter",
  templateUrl: "./obs-filter.component.html",
  styleUrls: ["./obs-filter.component.css"],
})
export class ObsFilterComponent implements OnInit {
  readonly DEFAULT_PRODUCT = "B12101";
  readonly DEFAULT_LEVEL = "103,2000,0,0";
  readonly DEFAULT_TIMERANGE = "254,0,0";
  readonly DEFAULT_LICENSE = "CCBY_COMPLIANT";
  @Input() network: string;

  filterForm: FormGroup;
  allNetworks: CodeDescPair[];
  allLevels: CodeDescPair[];
  allProducts: CodeDescPair[];
  allTimeranges: CodeDescPair[];
  allLicenses: CodeDescPair[];
  today: Date = new Date();
  maxDate: NgbDateStruct = {
    year: this.today.getFullYear(),
    month: this.today.getMonth() + 1,
    day: this.today.getDate(),
  };
  minDate: NgbDateStruct | null;
  minTime: number = 0;
  maxTime: number = 23;
  rangeValue = [this.minTime, this.maxTime];
  timeChanged: Subject<number[]> = new Subject<number[]>();
  user: User;

  isUpdatable: boolean = false;

  @Output() filterChange: EventEmitter<ObsFilter> =
    new EventEmitter<ObsFilter>();
  @Output() filterUpdate: EventEmitter<ObsFilter> =
    new EventEmitter<ObsFilter>();
  @Output() filterDownload: EventEmitter<ObsFilter> =
    new EventEmitter<ObsFilter>();

  constructor(
    private fb: FormBuilder,
    private calendar: NgbCalendar,
    private obsService: ObsService,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private authService: AuthService,
    private ref: ChangeDetectorRef
  ) {
    this.filterForm = this.fb.group({
      product: [this.DEFAULT_PRODUCT, Validators.required],
      reftime: [this.today, Validators.required],
      time: [[this.minTime, this.maxTime]],
      level: [""],
      timerange: [""],
      boundingBox: [""],
      network: [""],
      license: [this.DEFAULT_LICENSE, Validators.required],
      reliabilityCheck: [true],
    });
    this.timeChanged
      .pipe(debounceTime(2000), distinctUntilChanged())
      .subscribe((model) => {
        this.filterForm.get("time").setValue(model);
      });
  }

  ngOnInit() {
    // get fields enabling the form
    let startFilter: ObsFilter = {
      product: this.DEFAULT_PRODUCT,
      reftime: this.today,
      license: this.DEFAULT_LICENSE,
    };
    if (this.network) {
      startFilter.network = this.network;
    }
    this.allProducts = [];
    this.loadFilter(startFilter, true);

    // subscribe form value changes
    this.onChanges();

    this.authService.isAuthenticated().subscribe((isAuth) => {
      this.user = isAuth ? this.authService.getUser() : null;
      if (!this.user) {
        this.applyMinDate();
      }
    });
    this.authService.userChanged.subscribe((user) => {
      if (user === this.authService.LOGGED_OUT) {
        this.user = null;
        this.ref.detectChanges();
        this.minDate = null;
      } else if (user === this.authService.LOGGED_IN) {
        this.user = this.authService.getUser();
      }
    });
  }

  private applyMinDate() {
    let d = moment.utc().subtract(LAST_DAYS, "days");
    this.minDate = {
      year: d.year(),
      month: d.month() + 1,
      day: d.date(),
    };
  }

  private loadFilter(f: ObsFilter, initialize = false) {
    setTimeout(() => this.spinner.show("filter-spinner"), 0);
    console.log("load filter", f);
    this.obsService
      .getFields(f)
      .subscribe(
        (data: FieldsSummary) => {
          // reset the form
          this.filterForm.reset(
            {
              reftime: f.reftime,
              time: f.time,
              product: f.product,
              network: f.network || "",
              level: "",
              timerange: "",
              boundingBox: "",
              license: f.license || "CCBY_COMPLIANT",
              reliabilityCheck: true,
            },
            { emitEvent: false }
          );

          let items = data.items;

          // I need all available products here, regardless of the filter
          this.allProducts = items.available_products;
          this.allLicenses = items.all_licenses;
          this.filterForm.controls.product.setValue(f.product, {
            emitEvent: false,
          });

          /*          if (items.all_licenses){
            this.allLicenses = items.all_licenses;
          }else{
            this.allLicenses = LICENSES
          }*/
          if (this.allLicenses == undefined) {
            this.filterForm.controls.license.setValue(this.DEFAULT_LICENSE, {
              emitEvent: false,
            });
          }

          if (items.network) {
            this.allNetworks = items.network;
            if (f.network) {
              this.filterForm.controls.network.setValue(f.network, {
                emitEvent: false,
              });
            }
          }
          if (items.level) {
            this.allLevels = items.level;
            if (this.allLevels.map((x) => x.code).includes(f.level)) {
              this.filterForm.controls.level.setValue(f.level, {
                emitEvent: false,
              });
            }
            if (this.allLevels.length === 1) {
              this.filterForm.controls.level.setValue(this.allLevels[0].code, {
                emitEvent: false,
              });
            }
          }
          if (items.timerange) {
            this.allTimeranges = items.timerange;
            if (this.allTimeranges.map((x) => x.code).includes(f.timerange)) {
              this.filterForm.controls.timerange.setValue(f.timerange, {
                emitEvent: false,
              });
            }
            if (this.allTimeranges.length === 1) {
              this.filterForm.controls.timerange.setValue(
                this.allTimeranges[0].code,
                { emitEvent: false }
              );
            }
          }
          if (initialize) {
            // set here default level and timerange
            this.filterForm.controls.level.setValue(this.DEFAULT_LEVEL, {
              emitEvent: false,
            });
            this.filterForm.controls.timerange.setValue(
              this.DEFAULT_TIMERANGE,
              { emitEvent: false }
            );
            // set default license
            this.filterForm.controls.license.setValue(this.DEFAULT_LICENSE, {
              emitEvent: false,
            });
            // emit filter update
            if (this.filterForm.invalid) {
              this.notify.showError(
                "Invalid filter: no data loaded on the map."
              );
              return;
            }
            // apply the default filter only if products are available
            if (this.allProducts && this.allProducts.length > 0) {
              this.update();
            }
          }

          if (!this.allProducts || this.allProducts.length === 0) {
            let extraMsg =
              f.network !== undefined && f.network !== ""
                ? " network or "
                : " ";
            this.notify.showWarning(
              `No data available. Try selecting a different${extraMsg}reference date.`
            );
            this.isUpdatable = false;
          }
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        setTimeout(() => this.spinner.hide("filter-spinner"), 0);
      });
  }

  private onChanges(): void {
    this.filterForm.valueChanges.subscribe((val) => {
      this.isUpdatable = true;
      // console.log('filter changed', val);
      // console.log('is form invalid?', this.filterForm.invalid);
      this.loadFilter(val);
      this.filterChange.emit(val);
    });
  }

  private toObsFilter(): ObsFilter {
    let form = this.filterForm.value;
    let filter: ObsFilter = {
      product: form.product,
      reftime: form.reftime,
      time: form.time,
      license: form.license,
    };
    if (form.network !== "") {
      filter.network = form.network;
    }
    if (form.timerange) {
      filter.timerange = form.timerange;
    }
    if (form.level) {
      filter.level = form.level;
    }
    if (form.reliabilityCheck) {
      filter.reliabilityCheck = true;
    }
    return filter;
  }
  toggleReliabilityCheck() {
    this.filterForm.value.reliabilityCheck =
      !this.filterForm.value.reliabilityCheck;
    if (this.allProducts && this.allProducts.length > 0) {
      this.isUpdatable = true;
    }
  }

  update() {
    let filter: ObsFilter = this.toObsFilter();
    console.log("emit update filter", filter);
    this.filterUpdate.emit(filter);
    this.isUpdatable = false;
  }

  download() {
    this.filterDownload.emit(this.toObsFilter());
  }

  updateTime($event) {
    this.timeChanged.next($event.newValue);
  }

  formatter = (val: number[]) =>
    `${String(val[0]).padStart(2, "0")}:00 - ${String(val[1]).padStart(
      2,
      "0"
    )}:59`;
}
