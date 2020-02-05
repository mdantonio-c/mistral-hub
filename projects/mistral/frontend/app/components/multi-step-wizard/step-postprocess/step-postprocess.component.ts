import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { FormDataService } from "@app/services/formData.service";
import { DataService } from "@app/services/data.service";
import { NotificationService } from '@rapydo/services/notification';

@Component({
    selector: 'step-postprocess',
    templateUrl: './step-postprocess.component.html'
})
export class StepPostprocessComponent implements OnInit {
    title = 'Choose a post-processing';
    form: FormGroup;
    vars = [];
    space_crop_boundings = [
        {
            code: 'ilon',
            desc: 'Initial Lon',
            validators: [
                Validators.min(-180),
                Validators.max(180)
            ]
        },
        {
            code: 'ilat',
            desc: 'Initial Lat',
            validators: [
                Validators.min(-90),
                Validators.max(90)
            ]
        },
        {
            code: 'flon',
            desc: 'Final Lon',
            validators: [
                Validators.min(-180),
                Validators.max(180)
            ]
        },
        {
            code: 'flat',
            desc: 'Final Lat',
            validators: [
                Validators.min(-90),
                Validators.max(90)
            ]
        },
    ]

    constructor(private formBuilder: FormBuilder,
        private router: Router,
        private route: ActivatedRoute,
        private formDataService: FormDataService,
        private dataService: DataService,
        private notify: NotificationService) {
        this.form = this.formBuilder.group({
            derived_variables: new FormArray([]),
            space_type: ['crop'],
            space_crop: new FormArray([])
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

    private buildSpaceCrop() {
        this.space_crop_boundings.map(bound => {
            const control = this.formBuilder.control(0, bound.validators);
            (this.form.controls.space_crop as FormArray).push(control);
        })
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
        this.buildSpaceCrop();
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
        // push space processor object in selectedProcessors
        // TODO: space pp type <==> radio buttons binding
        const selectedSpaceProcessor = this.form.value.space_type;
        if (selectedSpaceProcessor && selectedSpaceProcessor.length) {
            switch (selectedSpaceProcessor) {
                case 'crop': {
                    selectedProcessors.push(this.calculateSpaceCrop());
                    break;
                }

                case 'grid': {
                    // selectedProcessors.push(this.calculateSpaceGrid());
                    break;
                }

                case 'points': {
                    // selectedProcessors.push(this.calculateSpacePoints());
                    break;
                }
            }

        }

        this.formDataService.setPostProcessor(selectedProcessors);
        return true;
    }


    calculateSpaceCrop() {
        const boundings = {}
        this.form.value.space_crop.map((value, i) => {
            boundings[this.space_crop_boundings[i].code] = value;
        })
        return {
            type: 'grid_cropping',
            sub_type: 'coord',
            boundings: boundings,
        }
    }

    goToPrevious() {
        // Navigate to the dataset page
        this.router.navigate(
            ['../', 'filters'], { relativeTo: this.route });
    }

    goToNext() {
        if (this.save()) {
            // Navigate to the postprocess page
            this.router.navigate(
                ['../', 'submit'], { relativeTo: this.route });
        }
    }

}
