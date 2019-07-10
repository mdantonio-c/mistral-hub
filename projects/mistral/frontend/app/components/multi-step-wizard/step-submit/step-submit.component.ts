import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, FormArray, FormControl, ValidatorFn} from '@angular/forms';
import {FormDataService} from "../../../services/formData.service";

@Component({
    selector: 'step-submit',
    templateUrl: './step-submit.component.html'
})
export class StepSubmitComponent  implements OnInit {
    title = 'Submit your request';
    form: FormGroup;

    constructor(private formBuilder: FormBuilder,
              private router: Router,
              private route: ActivatedRoute,
              private formDataService: FormDataService) {
        this.form = this.formBuilder.group({
            // TODO
        });
    }

    ngOnInit() {

    }

    goToPrevious() {
        // Navigate to the postprocess page
        this.router.navigate(
            ['../', 'postprocess'], { relativeTo: this.route });
    }

    submit(form: any) {
        console.log('submit request for data extraction');
        // Navigate to the 'My Requests' page
        this.router.navigate(['app/requests']);
    }

}

