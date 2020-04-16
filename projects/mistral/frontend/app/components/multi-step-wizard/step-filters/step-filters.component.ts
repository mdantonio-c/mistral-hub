import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, FormArray, FormControl, Validators} from '@angular/forms';
import {NotificationService} from '@rapydo/services/notification';
import {FormDataService} from "@app/services/formData.service";
import {ArkimetService} from "@app/services/arkimet.service";
import {Filters} from "@app/services/data.service";
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';
import {NgxSpinnerService} from "ngx-spinner";
import * as moment from 'moment';
import * as _ from 'lodash';

@Component({
    selector: 'step-filters',
    templateUrl: './step-filters.component.html'
})
export class StepFiltersComponent implements OnInit {
    title = 'Filter your data';
    loading: boolean = false;
    summaryStats = {b: null, e: null, c: null, s: null};
    filterForm: FormGroup;
    filters: Filters;
    disabledDp = false;

    constructor(private fb: FormBuilder,
                private router: Router,
                private route: ActivatedRoute,
                private formDataService: FormDataService,
                private arkimetService: ArkimetService,
                private modalService: NgbModal,
                private notify: NotificationService,
                private spinner: NgxSpinnerService) {
        const refTime = this.formDataService.getReftime();
        this.filterForm = this.fb.group({
            filters: this.fb.array([]),
            fromDate: new FormControl({
                value: refTime ? refTime.from : this.formDataService.getDefaultRefTime().from,
                disabled: true
            }),
            fromTime: new FormControl({
                value: refTime ? moment(refTime.from).format('HH:mm') : '00:00',
                disabled: true
            }),
            toDate: new FormControl({
                value: refTime ? refTime.to : this.formDataService.getDefaultRefTime().to,
                disabled: true
            }),
            toTime: new FormControl({
                value: refTime ? moment(refTime.to).format('HH:mm') : '00:00',
                disabled: true
            }),
            fullDataset: [false],
            validRefTime: [false, Validators.requiredTrue]
        });
    }

    ngOnInit() {
        this.loadFilters();
        window.scroll(0, 0);
    }

    today() {
        const today = moment.utc();
        return {year: today.year(), month: today.month() + 1, day: today.date()};
    }

    private getFilterGroup(name: string, values: any): FormGroup {
        let filter = this.fb.group({
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

    onFilterChange() {
        this.spinner.show();
        let selectedFilters = this.getSelectedFilters();
        console.log('selected filter(s)', selectedFilters);
        let selectedFilterNames = selectedFilters.map(f => f.name);
        this.formDataService.getFilters(selectedFilters).subscribe(
            response => {
                let results = response.items;
                // console.log(results);
                // compare the current filters with the selection results
                // in order to disable the missing ones
                Object.entries(this.filters).forEach(f => {
                    // if (!selectedFilterNames.includes(f[0])) {
                    if (f[0] !== 'summarystats') {
                        // ["name", [{...},{...}]]
                        // console.log(f[0]);
                        // console.log('....OLD....', f[1]);
                        let m = Object.entries(results)
                            .filter(e => e[0] === f[0])[0];
                        if (selectedFilterNames.includes(m[0])) {
                            if (selectedFilterNames.length === 1) {
                                // active them all
                                for (const obj of <Array<any>>f[1]) {
                                    obj['active'] = true;
                                }
                            }
                        } else {
                            for (const obj of <Array<any>>f[1]) {
                                // equal by desc
                                obj['active'] = _.some(<Array<any>>m[1],
                                    (o, i) => o.desc === obj.desc);
                            }
                        }
                        // console.log('....NEW....', m[1]);
                    }
                });
                this.updateSummaryStats(response.items.summarystats);
            },
                error => {
                this.notify.showError(`Unable to get summary fields`);
            }).add(() => {
                this.spinner.hide();
        });
    }

    loadFilters() {
        this.loading = true;
        // reset filters
        (this.filterForm.controls.filters as FormArray).clear();
        this.formDataService.getFilters().subscribe(
            response => {
                this.filters = response.items;
                let toBeExcluded = ['summarystats', 'network'];
                Object.entries(this.filters).forEach(entry => {
                    if (!toBeExcluded.includes(entry[0])) {
                        (<Array<any>>entry[1]).forEach(function (obj) {
                          obj['active'] = true;
                        });
                        (this.filterForm.controls.filters as FormArray).push(this.getFilterGroup(entry[0], entry[1]));
                    }
                });
                //console.log(this.filterForm.get('filters'));
                //console.log(this.filters);

                this.updateSummaryStats(response.items.summarystats);
            },
            error => {
                this.notify.showError(`Unable to get summary fields`);
            }
        ).add(() => {
            this.loading = false;
            if (this.formDataService.getFormData().filters.length !== 0) {
                this.onFilterChange();
            }
        });
    }

    private updateSummaryStats(summaryStats) {
        this.summaryStats = summaryStats;
        if (!this.summaryStats.hasOwnProperty('b')) {
            let from = moment(this.formDataService.getReftime().from);
            this.summaryStats['b'] = [from.year(), from.month() + 1, from.date(), from.hour(), from.minute(), from.second()]
        }
        if (!this.summaryStats.hasOwnProperty('e')) {
            let to = moment(this.formDataService.getReftime().to);
            this.summaryStats['e'] = [to.year(), to.month() + 1, to.date(), to.hour(), to.minute(), to.second()]
        }
        if (this.summaryStats['c'] === 0) {
            (this.filterForm.controls.validRefTime as FormControl).setValue(false);
            this.notify.showWarning('The applied reference time does not produce any result. ' +
                'Please choose a different reference time range.');
        } else {
            (this.filterForm.controls.validRefTime as FormControl).setValue(true);
        }
    }

    resetFilters() {
        this.formDataService.setFilters([]);
        this.loadFilters();
    }

    toggleFullDataset() {
        this.disabledDp = !this.disabledDp;
        (this.filterForm.controls.fullDataset as FormControl).setValue(this.disabledDp);
        this.checkRefTimeControls();
    }

    private checkRefTimeControls() {
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
        let fullDataset = !this.formDataService.getReftime();
        setTimeout(() => {
            this.disabledDp = fullDataset;
            this.filterForm.get('fullDataset').setValue(fullDataset ? true : false);
            this.checkRefTimeControls();
        });
        modalRef.result.then((result) => {
            if (this.filterForm.controls.fullDataset.value) {
                this.formDataService.setReftime(null);
            } else {
                let fromDate: Date = this.filterForm.get('fromDate').value;
                const fromTime = this.filterForm.get('fromTime').value.split(':');
                fromDate.setHours(parseInt(fromTime[0]), parseInt(fromTime[1]));
                let toDate: Date = this.filterForm.get('toDate').value;
                const toTime = this.filterForm.get('toTime').value.split(':');
                toDate.setHours(parseInt(toTime[0]), parseInt(toTime[1]));
                this.formDataService.setReftime({
                    from: fromDate,
                    to: toDate
                });
            }
            this.loadFilters();
        }, (reason) => {
            // do nothing
        });
    }

    private save() {
        if (!this.filterForm.valid) {
            return false;
        }
        this.formDataService.setFilters(
            this.getSelectedFilters());
        return true;
    }

    private getSelectedFilters() {
        const selectedFilters = [];
        (this.filterForm.controls.filters as FormArray).controls.forEach((f: FormGroup) => {
            let res = {
                name: f.controls.name.value,
                values: (f.controls.values as FormArray).controls
                    .map((v, j) => v.value ? this.filters[f.controls.name.value][j] : null)
                    .filter(v => v !== null),
                query: ''
            };
            if (res.values.length) {
                res.query = this.arkimetService.getQuery(res);
                // dballe query
                if (res.query === '' || res.query.split(':')[1] === '') {
                    res.query += res.values.map(v => v.dballe_p).join(' or ')
                }
                selectedFilters.push(res);
            }
        });
        return selectedFilters;
    }

    goToPrevious() {
        // Navigate to the dataset page
        this.router.navigate(
            ['../', 'datasets'], {relativeTo: this.route});
    }

    goToNext() {
        if (this.save()) {
            // Navigate to the postprocess page
            this.router.navigate(
                ['../', 'postprocess'], {relativeTo: this.route});
        }
    }

    getFilterTooltip(key: string) {
        let desc = 'Add helpful info about this filter';
        switch (key) {
            case 'area':
                desc = 'Definition of the domain area of the model.';
                break;
            case 'level':
                desc = 'Levels of the atmosphere expressed in vertical coordinates (possibly layers). \n' +
                    'The parameters of the vertical coordinates define the edges of the atmospheric layers in terms ' +
                    'of surface pressure.';
                break;
            case 'origin':
                desc = 'Identifies the forecast model, the characteristic and its configuration. \n' +
                    'It is related to the selected dataset.';
                break;
            case 'proddef':
                desc = 'Product definition information.';
                break;
            case 'product':
                desc = 'Weather fields.';
                break;
            case 'run':
                desc = 'A forecasting model process. In the case of Cosmo they  are 2 per day.';
                break;
            case 'timerange':
                desc = 'Defines the time period of the forecast and any processing (eg instant data, hourly average, ' +
                    'etc.). It is composed of 3 attributes: a value code (eg instant value, average, accumulation), ' +
                    'difference between validity time and reference time, duration of statistical processing';
                break;
        }
        return desc;
    }
}
