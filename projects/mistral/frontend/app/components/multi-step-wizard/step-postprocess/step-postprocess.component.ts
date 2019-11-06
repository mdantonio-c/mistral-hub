import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup} from '@angular/forms';
import {FormDataService} from "../../../services/formData.service";
import {additionalVariables} from "../../../services/data.service";

@Component({
    selector: 'step-postprocess',
    templateUrl: './step-postprocess.component.html'
})
export class StepPostprocessComponent implements OnInit {
    title = 'Choose a post-processing';
    form: FormGroup;
    vars = additionalVariables;

    constructor(private formBuilder: FormBuilder,
                private router: Router,
                private route: ActivatedRoute,
                private formDataService: FormDataService) {
        this.form = this.formBuilder.group({
            additional_variables: this.buildAdditionaVariables()
        });
    }

    private buildAdditionaVariables() {
        const av = this.formDataService.getFormData().postprocessors.filter(p => p.type === 'additional_variables');
        let presetVariables = [];
        if (av && av.length) {
            presetVariables = av[0].variables;
        }
        const arr = this.vars.map(v => {
            return this.formBuilder.control(presetVariables.includes(v.code));
        });
        return this.formBuilder.array(arr);
    }

    ngOnInit() {
        window.scroll(0, 0);
    }

    private save() {
        if (!this.form.valid) {
            return false;
        }
        const selectedProcessors = [];
        // additional variables
        const selectedAdditionalVariables = this.form.value.additional_variables
            .map((v, i) => v ? this.vars[i].code : null)
            .filter(v => v !== null);
        if (selectedAdditionalVariables && selectedAdditionalVariables.length) {
            selectedProcessors.push({
                type: 'additional_variables',
                variables: selectedAdditionalVariables
            });
        }
        this.formDataService.setPostProcessor(selectedProcessors);
        return true;
    }

    goToPrevious() {
        if (this.save()) {
            // Navigate to the dataset page
            this.router.navigate(
                ['../', 'filters'], {relativeTo: this.route});
        }
    }

    goToNext() {
        if (this.save()) {
            // Navigate to the postprocess page
            this.router.navigate(
                ['../', 'submit'], {relativeTo: this.route});
        }
    }

}
