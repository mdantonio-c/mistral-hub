import {Component, OnInit, Output, EventEmitter} from '@angular/core';
import {FormBuilder, FormGroup, Validators, FormControl} from '@angular/forms';
import {KeyValuePair, Fields, Levels_pe, Levels_pr, Runs, Areas, Resolutions, Platforms, Envs} from '../services/data';
import {MeteoFilter} from "../services/meteo.service";
import {AuthService} from '@rapydo/services/auth';
import {environment} from '@rapydo/../environments/environment';

@Component({
    selector: 'app-map-filter',
    templateUrl: './map-filter.component.html',
    styleUrls: ['./map-filter.component.css']
})
export class MapFilterComponent implements OnInit {

    readonly DEFAULT_PLATFORM = environment.ALL['PLATFORM'] || 'GALILEO';
    readonly DEFAULT_ENV = 'PROD';

    filterForm: FormGroup;
    fields: KeyValuePair[] = Fields;
    levels_pe: KeyValuePair[] = Levels_pe;
    levels_pr: KeyValuePair[] = Levels_pr;
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
            level_pe: ['25'],
            level_pr: ['20'],
            run: ['00', Validators.required],
            res: ['lm5', Validators.required],
            platform: [''],
            env: [''],
            area: ['Area_Mediterranea', Validators.required]
        });
    }

    ngOnInit() {
        this.user = this.authService.getUser();
        if (this.user && this.user.isAdmin) {
            (this.filterForm.controls.platform as FormControl).setValue(this.DEFAULT_PLATFORM);
            (this.filterForm.controls.env as FormControl).setValue(this.DEFAULT_ENV);
        }
        // subscribe for form value changes
        this.onChanges();
        // apply filter the first time
        this.filter();
    }

    private onChanges(): void {
        this.filterForm.get('area').valueChanges.subscribe(val => {
           if (val === 'Area_Mediterranea') {
               this.filterForm.get('resolution').setValue('lm5', {emitEvent: false});
           }
        });
        this.filterForm.valueChanges.subscribe(val => {
            this.filter();
        });
    }

    private filter() {
        let filter: MeteoFilter = this.filterForm.value;
        if (filter.env === '') {delete filter['env']}
        if (filter.platform === '') {delete filter['platform']}
        this.onFilterChange.emit(filter);
    }

}
