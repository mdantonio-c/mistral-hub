import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, FormArray, FormControl, ValidatorFn} from '@angular/forms';
import {FormDataService} from "../../../services/formData.service";

@Component({
    selector: 'step-postprocess',
    templateUrl: './step-postprocess.component.html'
})
export class StepPostprocessComponent implements OnInit {
    title = 'Choose a post-processing';
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
        window.scroll(0,0);
    }

    private save() {
        if (!this.form.valid) {
            return false;
        }
        // TODO
        this.formDataService.setPostProcessor([]);
        return true;
    }

    goToPrevious() {
        if (this.save()) {
            // Navigate to the dataset page
            this.router.navigate(
                ['../', 'filters'], { relativeTo: this.route });
        }
    }

    goToNext(form: any) {
        if (this.save()) {
            // Navigate to the postprocess page
            this.router.navigate(
                ['../', 'submit'], { relativeTo: this.route });
        }
    }

}
