import {Component, OnInit, Output, EventEmitter} from '@angular/core';
import {FormBuilder, FormGroup, Validators} from '@angular/forms';
import {ObsFilter, ObsService} from '../services/obs.service';
import {NETWORKS, LICENSES, CodeDescPair} from "../services/data";
import {NgbDateStruct, NgbCalendar} from '@ng-bootstrap/ng-bootstrap';
import {NotificationService} from '@rapydo/services/notification';
import {environment} from '@rapydo/../environments/environment';

const LAST_DAYS = +environment.ALL['LASTDAYS'] || 10;

@Component({
    selector: 'app-obs-filter',
    templateUrl: './obs-filter.component.html',
    styleUrls: ['./obs-filter.component.css']
})
export class ObsFilterComponent implements OnInit {
    filterForm: FormGroup;
    allNetworks: CodeDescPair[];
    allLevels: CodeDescPair[];
    allProducts: CodeDescPair[];
    allTimeranges: CodeDescPair[];
    allLicenses: string[] = LICENSES;
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
        private notify: NotificationService
    ) {
        this.filterForm = this.fb.group({
            product: ['B12101', Validators.required],
            // reftime: [this.today, Validators.required],
            reftime: [new Date(2019, 11, 12), Validators.required],
            level: ['103,2000,0,0'],
            timerange: ['254,0,0'],
            boundingBox: [''],
            network: [''],
            license: ['CC-BY', Validators.required]
        });
    }

    ngOnInit() {
        // get fields enabling the form
        this.loadFilter();
        // subscribe form value changes
        this.onChanges();
    }

    private loadFilter() {
        this.obsService.getFields().subscribe(data => {
                // TODO manage filters
                let items = data.items;
                if (items.network) {
                    this.allNetworks = items.network;
                }
                if (items.level) {
                    this.allLevels = items.level;
                }
                if (items.timerange) {
                    this.allTimeranges = items.timerange;
                }
                if (items.product) {
                    this.allProducts = items.product;
                }
                // emit filter update
                if (!this.filterForm.invalid) {
                    this.update();
                }
            },
            error => {
                this.notify.showError(error);
            });
    }

    private onChanges(): void {
        this.filterForm.valueChanges.subscribe(val => {
            console.log('filter changed', val);
            console.log('is form invalid?', this.filterForm.invalid);
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
