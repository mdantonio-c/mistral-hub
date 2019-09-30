import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, FormArray, FormControl, Validators} from '@angular/forms';
import {FormDataService} from "../../../services/formData.service";
import {NotificationService} from '/rapydo/src/app/services/notification';
import {ArkimetService} from "../../../services/arkimet.service";
import {Filters} from "../../../services/data.service";
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import * as moment from 'moment';

@Component({
    selector: 'step-filters',
    templateUrl: './step-filters.component.html'
})
export class StepFiltersComponent implements OnInit {
    title = 'Filter your data';
    loading: boolean = false;
    summaryStats = {};
    filterForm: FormGroup;
    filters: Filters;

    today = moment();
    maxDate = {year: this.today.year(), month: this.today.month(), day: this.today.day()};
    disabledDp = false;

    constructor(private formBuilder: FormBuilder,
                private router: Router,
                private route: ActivatedRoute,
                private formDataService: FormDataService,
                private arkimetService: ArkimetService,
                private modalService: NgbModal,
                private notify: NotificationService) {
        const reftime = this.formDataService.getReftime();
        this.filterForm = this.formBuilder.group({
            filters: this.formBuilder.array([]),
            fromDate: new FormControl({value: reftime.from, disabled: true}),
            fromTime: new FormControl({value: '00:00', disabled: true}),
            toDate: new FormControl({value: reftime.to, disabled: true}),
            toTime: new FormControl({value: '00:00', disabled: true}),
            fullDataset: [false]
        });
    }

    createFilter(name: string, values: any): FormGroup {
        let filter = this.formBuilder.group({
            name: [name, Validators.required],
            values: new FormArray([])
        });
        // init values
        values.map(o => {
            // pre-set actual values from formData
            const control = new FormControl(this.formDataService.isFilterSelected(o));
            (filter.controls.values as FormArray).push(control);
        });
        return filter;
    }

    ngOnInit() {
        this.loading = true;
        this.formDataService.getFilters().subscribe(
            response => {
                this.filters = response.data.items;
                this.summaryStats = response.data.items.summarystats;
                Object.entries(response.data.items).forEach(entry => {
                    if (entry[0] !== 'summarystats') {
                        (this.filterForm.controls.filters as FormArray).push(this.createFilter(entry[0], entry[1]));
                    }
                });
                //console.log(this.filterForm.get('filters'));
                //console.log(this.filters);
                this.loading = false;
            },
            error => {
                this.notify.extractErrors(error.error.Response, this.notify.ERROR);
                this.loading = false;
            });
        window.scroll(0, 0);
    }

    toggleFullDataset() {
        this.disabledDp = !this.disabledDp;
        (this.filterForm.controls.fullDataset as FormControl).setValue(this.disabledDp);
        this.checkControls();
        console.log(this.filterForm.value);
    }

    private checkControls() {
        if (this.disabledDp) {
            (this.filterForm.controls.fromDate as FormControl).disable();
            (this.filterForm.controls.fromTime as FormControl).disable();
            (this.filterForm.controls.toDate as FormControl).disable();
            (this.filterForm.controls.toTime as FormControl).disable();
        } else {
            (this.filterForm.controls.fromDate as FormControl).enable();
            (this.filterForm.controls.fromTime as FormControl).enable();
            (this.filterForm.controls.toDate as FormControl).enable();
            (this.filterForm.controls.toTime as FormControl).enable();
        }
    }

    editReftime(content) {
        const modalRef = this.modalService.open(content);
        setTimeout(() => {
          this.checkControls();
        });
        modalRef.result.then((result) => {

        }, (reason) => {
            // do nothing
        });
    }

    private save() {
        if (!this.filterForm.valid) {
            return false;
        }
        const selectedFilters = [];
        this.filterForm.value.filters.forEach(f => {
            let res = {
                name: f.name,
                values: f.values
                    .map((v, j) => v ? this.filters[f.name][j] : null)
                    .filter(v => v !== null),
                query: ''
            };
            if (res.values.length) {
                res.query = this.arkimetService.getQuery(res);
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
