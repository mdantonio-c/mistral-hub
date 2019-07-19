import {Component, OnInit, Input} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
// import {FormBuilder, FormGroup, FormArray, FormControl, ValidatorFn} from '@angular/forms';
import {FormDataService} from "../../../services/formData.service";
import {FormData} from "../../../services/formData.model";

@Component({
    selector: 'step-submit',
    templateUrl: './step-submit.component.html'
})
export class StepSubmitComponent implements OnInit {
    title = 'Submit your request';
    @Input() formData: FormData;
    isFormValid: boolean = false;

    constructor(private router: Router,
                private route: ActivatedRoute,
                private formDataService: FormDataService) {
    }

    ngOnInit() {
        this.formData = this.formDataService.getFormData();
        this.isFormValid = this.formDataService.isFormValid();
        console.log('Result feature loaded!');
    }

    goToPrevious() {
        // Navigate to the postprocess page
        this.router.navigate(
            ['../', 'postprocess'], {relativeTo: this.route});
    }

    submit(form: any) {
        console.log('submit request for data extraction');
        this.formData = this.formDataService.resetFormData();
        this.isFormValid = false;
        // Navigate to the 'My Requests' page
        this.router.navigate(['app/requests']);
    }

}

