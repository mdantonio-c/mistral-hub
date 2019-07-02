import {Component, OnInit} from '@angular/core';
import {Router} from '@angular/router';

import {FormDataService} from "../../../services/formData.service";
import {Dataset} from "../../../services/formData.model";

@Component({
    selector: 'step-datasets',
    templateUrl: './step-datasets.component.html'
})
export class StepDatasetsComponent implements OnInit {
    title = 'Please select one or more datasets';
    datasets: Dataset[];
    form: any;

    constructor(private router: Router, private formDataService: FormDataService) {
    }

    ngOnInit() {
        this.formDataService.getDatasets().subscribe(
            response => {
                this.datasets = response.data;
            }
        );
        console.log('Datsets loaded!');
    }
}
