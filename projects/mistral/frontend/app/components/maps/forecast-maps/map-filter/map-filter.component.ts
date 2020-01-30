import {Component, OnInit, Output, EventEmitter} from '@angular/core';
import {FormBuilder, FormGroup, Validators} from '@angular/forms';
import {KeyValuePair, Fields, Runs, Areas, Resolutions, Platforms, Envs} from '../services/data';
import {MeteoFilter} from "../services/meteo.service";
import {AuthService} from '@rapydo/services/auth';

@Component({
    selector: 'app-map-filter',
    templateUrl: './map-filter.component.html',
    styleUrls: ['./map-filter.component.css']
})
export class MapFilterComponent implements OnInit {
    filterForm: FormGroup;
    fields: KeyValuePair[] = Fields;
    runs: KeyValuePair[] = Runs;
    resolutions: KeyValuePair[] = Resolutions;
    platforms: KeyValuePair[] = Platforms;
    envs: KeyValuePair[] = Envs;
    areas: KeyValuePair[] = Areas;
    user;

    @Output() onFilterChange: EventEmitter<MeteoFilter> = new EventEmitter<MeteoFilter>();

    constructor(private fb: FormBuilder, private authService: AuthService) {
        this.filterForm = this.fb.group({
            field: ['prec3', Validators.required],
            run: ['00', Validators.required],
            resolution: ['lm2.2', Validators.required],
            platform: ['galileo_meteo_download/OPE/web', Validators.required],
            modality: ['PROD', Validators.required],
            area: ['Italia', Validators.required]
        });
    }

    ngOnInit() {
        this.user = this.authService.getUser();
        // subscribe for form value changes
        this.onChanges();
        // apply filter the first time
        this.filter();
    }

    onChanges(): void {
      this.filterForm.valueChanges.subscribe(val => {
        this.filter();
      });
    }

    private filter() {
        this.onFilterChange.emit(this.filterForm.value);
    }

}
