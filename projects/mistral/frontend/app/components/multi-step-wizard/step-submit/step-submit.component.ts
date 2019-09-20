import {Component, Input, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, Validators} from '@angular/forms';
import {additionalVariables, FormData, FormDataService} from "../../../services/formData.service";
import {
    DataService,
    ScheduleType,
    RepeatEvery,
    SummaryStats,
    TaskSchedule
} from "../../../services/data.service";
import {NotificationService} from '/rapydo/src/app/services/notification';
import {NgbModal} from '@ng-bootstrap/ng-bootstrap';

@Component({
    selector: 'step-submit',
    templateUrl: './step-submit.component.html'
})
export class StepSubmitComponent implements OnInit {
    title = 'Submit my request';
    summaryStats: SummaryStats = {c: 0, s: 0};
    @Input() formData: FormData;
    isFormValid = false;
    scheduleForm: FormGroup;
    schedule: TaskSchedule = null;
    vars = additionalVariables;

    constructor(
        private router: Router,
        private route: ActivatedRoute,
        private formBuilder: FormBuilder,
        private dataService: DataService,
        private formDataService: FormDataService,
        private modalService: NgbModal,
        private notify: NotificationService
    ) {
        this.scheduleForm = this.formBuilder.group({
            repeatType: [ScheduleType.CRONTAB, Validators.required],
            cPeriod: [RepeatEvery.DAY],
            time: ['00:00'],
            every: [1],
            period: [RepeatEvery.HOUR]
        });
    }

    ngOnInit() {
        this.formData = this.formDataService.getFormData();
        this.isFormValid = this.formDataService.isFormValid();
        this.formDataService.getSummaryStats().subscribe(response => {
            this.summaryStats = response.data;
            if (this.summaryStats.s === 0) {
                this.notify.showWarning('The applied filter do not produce any result. ' +
                    'Please choose different filters.');
            }
        });
        // default product name
        // this.formData.defaultName();
        window.scroll(0, 0);
    }

    emptyName() {
        return !this.formData.name || this.formData.name.trim().length === 0;
    }

    getVariableDescription(code): string {
        return this.vars.find(av => av.code === code).desc;
    }


    showSchedule(content) {
        const modalRef = this.modalService.open(content);
        if (this.schedule) {
            this.loadSchedule();
        }
        modalRef.result.then((result) => {
            switch (result) {
                case "save":
                    // add schedule
                    switch (this.scheduleForm.get('repeatType').value) {
                        case ScheduleType.CRONTAB:
                            this.schedule = {
                                type: ScheduleType.CRONTAB,
                                time: this.scheduleForm.get('time').value,
                                repeat: this.scheduleForm.get('cPeriod').value
                            };
                            break;
                        case ScheduleType.PERIOD:
                            this.schedule = {
                                type: ScheduleType.PERIOD,
                                every: this.scheduleForm.get('every').value,
                                repeat: this.scheduleForm.get('period').value
                            };
                            break;
                        case ScheduleType.DATA_READY:
                            this.schedule = {
                                type: ScheduleType.DATA_READY
                            };
                            break;
                    }
                    this.formData.setSchedule(this.schedule);
                    console.log('added schedule:', this.schedule);
                    break;
                case "remove":
                    this.formData.schedule = null;
                    this.schedule = null;
                    this.reset();
                    break;
            }
        }, (reason) => {
            // do nothing
        });
    }

    private loadSchedule() {
        this.scheduleForm.setValue({
            repeatType: this.schedule.type,
            cPeriod: (this.schedule.type === ScheduleType.CRONTAB) ? this.schedule.repeat : RepeatEvery.DAY,
            time: (this.schedule.type === ScheduleType.CRONTAB) ? this.schedule.time : '00:00',
            every: (this.schedule.type === ScheduleType.PERIOD) ? this.schedule.every : 1,
            period: (this.schedule.type === ScheduleType.PERIOD) ? this.schedule.repeat : RepeatEvery.HOUR
        });
    }

    private reset() {
        this.scheduleForm.reset({
            repeatType: ScheduleType.CRONTAB,
            cPeriod: RepeatEvery.DAY,
            time: '00:00',
            every: 1,
            period: RepeatEvery.HOUR
        });
    }

    goToPrevious() {
        // Navigate to the postprocess page
        this.router.navigate(
            ['../', 'postprocess'], {relativeTo: this.route});
    }

    submit(form: any) {
        console.log('submit request for data extraction');
        this.dataService.extractData(
            this.formData.name,
            this.formData.datasets,
            this.formData.filters,
            this.formData.schedule,
            this.formData.postprocessors).subscribe(
            resp => {
                this.schedule = null;
                this.formData = this.formDataService.resetFormData();
                this.isFormValid = false;
                // Navigate to the 'My Requests' page
                this.router.navigate(['app/requests']);
            },
            error => {
                this.notify.extractErrors(error.error.Response, this.notify.ERROR);
            }
        );
    }
}

