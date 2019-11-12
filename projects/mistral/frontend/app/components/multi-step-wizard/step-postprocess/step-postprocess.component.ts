import {Component, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {FormBuilder, FormGroup, FormArray} from '@angular/forms';
import {FormDataService} from "@app/services/formData.service";
import {DataService} from "@app/services/data.service";
import {NotificationService} from '@rapydo/services/notification';

@Component({
    selector: 'step-postprocess',
    templateUrl: './step-postprocess.component.html'
})
export class StepPostprocessComponent implements OnInit {
    title = 'Choose a post-processing';
    form: FormGroup;
    vars = [];

    constructor(private formBuilder: FormBuilder,
                private router: Router,
                private route: ActivatedRoute,
                private formDataService: FormDataService,
                private dataService: DataService,
                private notify: NotificationService) {
        this.form = this.formBuilder.group({
            derived_variables: new FormArray([])
        });
    }

    private buildDerivedVariables() {
        const av = this.formDataService.getFormData().postprocessors.filter(p => p.type === 'derived_variables');
        let presetVariables = [];
        if (av && av.length) {
            presetVariables = av[0].variables;
        }
        this.vars.map(v => {
            const control = this.formBuilder.control(presetVariables.includes(v.code));
            (this.form.controls.derived_variables as FormArray).push(control);
        });
    }

    ngOnInit() {
        window.scroll(0, 0);
        this.dataService.getDerivedVariables().subscribe(
            data => {
                this.vars = data;
                this.buildDerivedVariables();
            },
            error => {
                this.notify.showError('Unable to load derived variables configuration');
            }
        )
    }

    private save() {
        if (!this.form.valid) {
            return false;
        }
        const selectedProcessors = [];
        // derived variables
        const selectedDerivedVariables = this.form.value.derived_variables
            .map((v, i) => v ? this.vars[i].code : null)
            .filter(v => v !== null);
        if (selectedDerivedVariables && selectedDerivedVariables.length) {
            selectedProcessors.push({
                type: 'derived_variables',
                variables: selectedDerivedVariables
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
