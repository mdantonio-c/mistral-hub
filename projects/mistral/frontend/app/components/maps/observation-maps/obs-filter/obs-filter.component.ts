import {Component, OnInit, Output, EventEmitter, ViewChild, AfterViewInit} from '@angular/core';
import {FormBuilder, FormGroup, Validators, FormControl} from '@angular/forms';
import {Network, Product, ObsFilter, ObsService} from '../services/obs.service';
import {NETWORKS, LICENSES, CodeDescPair} from "../services/data";
import {NgbDateStruct, NgbCalendar, NgbDateAdapter, NgbDateNativeAdapter, NgbInputDatepicker} from '@ng-bootstrap/ng-bootstrap';

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

    @Output() filterChange: EventEmitter<ObsFilter> = new EventEmitter<ObsFilter>();
    @Output() filterUpdate: EventEmitter<ObsFilter> = new EventEmitter<ObsFilter>();

    constructor(private fb: FormBuilder, private calendar: NgbCalendar, private obsService: ObsService) {
        this.filterForm = this.fb.group({
            product: ['B12101', Validators.required],
            level: ['', Validators.required],
            reftime: [this.today, Validators.required],
            timerange: [''],
            boundingBox: [''],
            network: [''],
            license: ['CC-BY']
        });
    }

    ngOnInit() {
        // get fields enabling the form
        this.loadFilter();
        // subscribe form value changes
        // this.onChanges();
    }

    private loadFilter() {
        this.obsService.getFields().subscribe(data => {
                // TODO manage filters
                let items = data.items;
                if (items.network) { this.allNetworks = items.network; }
                if (items.level) { this.allLevels = items.level; }
                if (items.timerange) { this.allTimeranges = items.timerange; }
                if (items.product) { this.allProducts = items.product; }
                // emit filter update
                this.update();
            },
            error => {
                // TODO
            });
    }
    /*
    private onChanges(): void {
        this.filterForm.valueChanges.subscribe(val => {
            // this.filter();
            // console.log('filter changed', val);
        });
    }
     */

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
        console.log('emit update filter', filter);
        this.filterUpdate.emit(filter);
    }
}
