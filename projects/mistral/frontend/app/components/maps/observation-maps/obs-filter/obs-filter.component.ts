import {Component, OnInit, Output, EventEmitter} from '@angular/core';
import {FormBuilder, FormGroup, Validators, FormControl} from '@angular/forms';
import {Network, ObsFilter, ObsService} from '../services/obs.service';
import {NETWORKS, LICENSES} from "../services/data";

@Component({
    selector: 'app-obs-filter',
    templateUrl: './obs-filter.component.html',
    styleUrls: ['./obs-filter.component.css']
})
export class ObsFilterComponent implements OnInit {
    filterForm: FormGroup;
    allNetworks: Network[] = NETWORKS;
    allLicenses: string[] = LICENSES;

    @Output() onFilterChange: EventEmitter<ObsFilter> = new EventEmitter<ObsFilter>();

    constructor(private fb: FormBuilder) {
        this.filterForm = this.fb.group({
            product: ['B11001', Validators.required],
            level: ['', Validators.required],
            reftime: ['', Validators.required],
            timerange: [''],
            boundingBox: [''],
            network: [''],
            license: ['CC-BY']
        });
    }

    ngOnInit() {
        // subscribe for form value changes
        this.onChanges();
        // apply filter the first time
        this.filter();
    }

    private onChanges(): void {
        this.filterForm.valueChanges.subscribe(val => {
            this.filter();
        });
    }

    private filter() {
        let filter: ObsFilter = this.filterForm.value;
        this.onFilterChange.emit(filter);
    }
}
