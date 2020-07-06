import {Component, OnInit, Output, EventEmitter} from '@angular/core';
import {FormBuilder, FormGroup, Validators} from '@angular/forms';
import {FieldsSummary, ObsFilter, ObsService} from '../services/obs.service';
import {NETWORKS, LICENSES, CodeDescPair} from "../services/data";
import {NgbDateStruct, NgbCalendar} from '@ng-bootstrap/ng-bootstrap';
import {NotificationService} from '@rapydo/services/notification';
import {environment} from '@rapydo/../environments/environment';
import {NgxSpinnerService} from 'ngx-spinner';

const LAST_DAYS = +environment.ALL['LASTDAYS'] || 10;

@Component({
    selector: 'app-obs-filter',
    templateUrl: './obs-filter.component.html',
    styleUrls: ['./obs-filter.component.css']
})
export class ObsFilterComponent implements OnInit {
    readonly DEFAULT_PRODUCT = 'B12101';
    readonly DEFAULT_LEVEL = '103,2000,0,0';
    readonly DEFAULT_TIMERANGE = '254,0,0';

    filterForm: FormGroup;
    allNetworks: CodeDescPair[];
    allLevels: CodeDescPair[];
    allProducts: CodeDescPair[];
    allTimeranges: CodeDescPair[];
    allLicenses: CodeDescPair[] = LICENSES;
    today: Date = new Date();
    maxDate: NgbDateStruct = {
        year: this.today.getFullYear(),
        month: this.today.getMonth() + 1,
        day: this.today.getDate()
    }

    @Output() filterChange: EventEmitter<ObsFilter> = new EventEmitter<ObsFilter>();
    @Output() filterUpdate: EventEmitter<ObsFilter> = new EventEmitter<ObsFilter>();

    constructor(
        private fb: FormBuilder,
        private calendar: NgbCalendar,
        private obsService: ObsService,
        private notify: NotificationService,
        private spinner: NgxSpinnerService
    ) {
        this.filterForm = this.fb.group({
            product: [this.DEFAULT_PRODUCT, Validators.required],
            reftime: [this.today, Validators.required],
            level: [this.DEFAULT_LEVEL],
            timerange: [this.DEFAULT_TIMERANGE],
            boundingBox: [''],
            network: [''],
            license: ['CC-BY', Validators.required]
        });
    }

    ngOnInit() {

        // get fields enabling the form
        let startFilter: ObsFilter = {
            product: this.DEFAULT_PRODUCT,
            reftime: this.today
        }
        this.loadFilter(startFilter, true);

        // subscribe form value changes
        this.onChanges();
    }

    private loadFilter(f: ObsFilter, initialize = false) {
        setTimeout(() => this.spinner.show('filter-spinner'), 0);
        this.obsService.getFields(f).subscribe(
            (data: FieldsSummary) => {
                let items = data.items;
                // I need all available products here, regardless of the filter
                this.allProducts = items.available_products;
                // set product
                this.filterForm.controls.product.patchValue(f.product, {emitEvent:false})
                if (items.network) {
                    // console.log('networks', items.network);
                    this.allNetworks = items.network;
                }
                if (items.level) {
                    // console.log('levels', items.level);
                    this.allLevels = items.level;
                }
                if (items.timerange) {
                    this.allTimeranges = items.timerange;
                }
                if (initialize) {
                    // emit filter update
                    if (!this.filterForm.invalid) {
                        this.update();
                    } else {
                        this.notify.showError('Invalid filter: no data loaded on the map');
                    }
                }
            },
            error => {
                this.notify.showError(error);
            }
        ).add(() => {
            this.spinner.hide('filter-spinner');
        });
    }

    private onChanges(): void {
        this.filterForm.valueChanges.subscribe(val => {
            console.log('filter changed', val);
            console.log('is form invalid?', this.filterForm.invalid);
            this.loadFilter(val);
            this.filterChange.emit(val);
        });
    }

    resetFiltersToDefault() {
        // TODO
    }

    update() {
        let form = this.filterForm.value;
        let filter: ObsFilter = {
            product: form.product,
            reftime: form.reftime
        }
        if (form.network !== '') {
            filter.network = form.network;
        }
        if (form.timerange) {
            filter.timerange = form.timerange;
        }
        if (form.level) {
            filter.level = form.level;
        }
        console.log('emit update filter', filter);
        this.filterUpdate.emit(filter);
    }
}
