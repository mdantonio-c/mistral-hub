import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, FormArray, FormControl, Validators} from '@angular/forms';
import {FormDataService} from "../../../services/formData.service";
import {Filters} from "../../../services/formData.model";
import {NotificationService} from '/rapydo/src/app/services/notification';

@Component({
    selector: 'step-filters',
    templateUrl: './step-filters.component.html'
})
export class StepFiltersComponent implements OnInit {
    title = 'Filter your data';
    summaryStats = {};
    filterForm: FormGroup;
    filters: Filters<string, any>;

    constructor(private formBuilder: FormBuilder,
                private router: Router,
                private route: ActivatedRoute,
                private formDataService: FormDataService,
                private notify: NotificationService) {
        this.filterForm = this.formBuilder.group({
            filters: this.formBuilder.array([])
        });
    }

    createFilter(name: string, values: any): FormGroup {
        let filter = this.formBuilder.group({
            name: [name, Validators.required],
            values: new FormArray([])
        });
        // init values
        values.map((o, i) => {
            // TODO pre-set actual values from formData
            const control = new FormControl(false);
            (filter.controls.values as FormArray).push(control);
        });
        return filter;
    }

    ngOnInit() {
        this.formDataService.getFilters().subscribe(response => {
            this.filters = response.data.items;
            this.summaryStats = response.data.items.summarystats;
            Object.entries(response.data.items).forEach(entry => {
                if (entry[0] !== 'summarystats') {
                    (this.filterForm.controls.filters as FormArray).push(this.createFilter(entry[0], entry[1]));
                }
            });
            //console.log(this.filterForm.get('filters'));
            //console.log(this.filters);
        });
    }


    private save() {
        if (!this.filterForm.valid) {
            return false;
        }
        const selectedFilters = [];
        this.filterForm.value.filters.forEach((f, i) => {
            let res = {
                name: f.name,
                values: f.values
                    .map((v, j) => v ? this.filters[f.name][j] : null)
                    .filter(v => v !== null)
            };
            if (res.values.length) {
                selectedFilters.push(res);
            }
        });
        // console.log(`selected filters: ${selectedFilters}`);
        this.formDataService.setFilters(selectedFilters);
        return true;
    }

    goToPrevious() {
        if (this.save()) {
            // Navigate to the dataset page
            this.router.navigate(
                ['../', 'datasets'], {relativeTo: this.route});
        }
    }

    goToNext(form: any) {
        if (this.save()) {
            // Navigate to the postprocess page
            this.router.navigate(
                ['../', 'postprocess'], {relativeTo: this.route});
        }
    }
}
