import {Component, Input, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, Validators} from '@angular/forms';
import {FormData, FormDataService} from "../../../services/formData.service";
import {
    DataService,
    RepeatSchedule,
    RepeatScheduleOptions,
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
    title = 'Submit your request';
    summaryStats: SummaryStats = {c: 0, s: 0};
    @Input() formData: FormData;
    isFormValid = false;
    scheduleForm: FormGroup;
    curDate = new Date();
    schedule: TaskSchedule;
    scheduleRepeatOptions = RepeatScheduleOptions;

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
            date: [''],
            time: [''],
            repeat: [RepeatSchedule.NO, Validators.required]
        });
    }

    ngOnInit() {
        // this.cleanUpSchedule();
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
        this.formData.defaultName();
        window.scroll(0, 0);
    }

    emptyName() {
        return !this.formData.name || this.formData.name.trim().length === 0;
    }

    showSchedule(content) {
        const modalRef = this.modalService.open(content, {ariaLabelledBy: 'modal-basic-title'});
        modalRef.result.then((result) => {
            switch (result) {
                case "save":
                    // add schedule
                    this.formData.setSchedule(this.schedule);
                    console.log('added schedule', this.schedule);
                    break;
                case "remove":
                    this.formData.schedule = null;
                    this.cleanUpSchedule();
                    break;
            }
        }, (reason) => {
            // clean up schedule
            this.cleanUpSchedule();
        });
    }

    private cleanUpSchedule() {
        this.schedule = {
            date: null,
            time: {hour: 0, minute: 0},
            repeat: RepeatSchedule.NO
        };
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
            this.formData.filters).subscribe(
            resp => {
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

