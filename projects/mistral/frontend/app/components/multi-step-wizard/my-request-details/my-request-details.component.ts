import {Component, Input, OnInit} from '@angular/core';
import {FormDataService, FormData} from "@app/services/formData.service";
import {DataService} from "@app/services/data.service";

@Component({
    selector: 'mst-my-request-details',
    templateUrl: './my-request-details.component.html',
    styleUrls: ['./my-request-details.component.css']
})
export class MyRequestDetailsComponent implements OnInit {
    myRequest: FormData;

    constructor(private formDataService: FormDataService,
                public dataService: DataService) {
    }

    ngOnInit(): void {
        this.myRequest = this.formDataService.getFormData();
    }
}
