import {Component, Input, OnInit} from '@angular/core';
import {FormDataService} from "../../services/formData.service";

@Component({
    selector: 'multi-step-wizard',
    templateUrl: './multi-step-wizard.component.html'
})
export class MultiStepWizardComponent implements OnInit {
    title = 'Multi-Step Wizard';
    @Input() formData;

    constructor(private formDataService: FormDataService) {
    }

    ngOnInit(): void {
        this.formData = this.formDataService.getFormData();
        console.log(this.title + ' loaded!');
    }

}
