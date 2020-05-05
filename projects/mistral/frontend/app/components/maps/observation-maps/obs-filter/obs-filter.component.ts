import {Component, OnInit, Output, EventEmitter} from '@angular/core';
import {FormBuilder, FormGroup, Validators, FormControl} from '@angular/forms';
import {Network, Product, ObsFilter, ObsService} from '../services/obs.service';
import {NETWORKS, LICENSES, CodeDescPair} from "../services/data";

@Component({
    selector: 'app-obs-filter',
    templateUrl: './obs-filter.component.html',
    styleUrls: ['./obs-filter.component.css']
})
export class ObsFilterComponent implements OnInit {
    filter: ObsFilter;
    filterForm: FormGroup;
    allNetworks: CodeDescPair[];
    allLevels: CodeDescPair[];
    allProducts: CodeDescPair[];
    allTimeranges: CodeDescPair[];
    allLicenses: string[] = LICENSES;

    @Output() onFilterChange: EventEmitter<ObsFilter> = new EventEmitter<ObsFilter>();
    @Output() onFilterUpdate: EventEmitter<ObsFilter> = new EventEmitter<ObsFilter>();

    constructor(private fb: FormBuilder, private obsService: ObsService) {
        this.filterForm = this.fb.group({
            product: ['B12101', Validators.required],
            level: ['', Validators.required],
            reftime: ['', Validators.required],
            timerange: [''],
            boundingBox: [''],
            network: ['agrmet'],
            license: ['CC-BY']
        });
    }

    ngOnInit() {
        // get fields enabling the form
        this.loadFilter();
        // subscribe for form value changes
        this.onChanges();
    }

    private loadFilter() {
        this.obsService.getFields().subscribe(data => {
                // TODO manage filters
                let items = data.items;
                if (items.network) { this.allNetworks = items.network; }
                if (items.level) { this.allLevels = items.level; }
                if (items.timerange) { this.allTimeranges = items.timerange; }
                if (items.product) { this.allProducts = items.product; }
                // apply filter
                this.applyFilter();
            },
            error => {
                // TODO
            });
    }

    private onChanges(): void {
        this.filterForm.valueChanges.subscribe(val => {
            // this.filter();
            console.log('filter changed', val);
        });
    }

    resetFiltersToDefault() {
        // TODO
    }

    applyFilter() {
        let filter = this.filterForm.value;
        console.log('apply filter', filter);
        this.onFilterUpdate.emit(filter);
    }
}
