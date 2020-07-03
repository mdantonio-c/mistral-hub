import {Component, Output, EventEmitter, Injector} from '@angular/core';

import {DataService} from "@app/services/data.service";
import {environment} from '@rapydo/../environments/environment';

@Component({
    selector: 'app-license',
    templateUrl: './license.component.html'
})
export class LicenseComponent {
    expanded: any = {};
    @Output() onLoad: EventEmitter<null> = new EventEmitter<null>();
    loading = false;
    data;

    constructor(protected injector: Injector, public dataService: DataService) {
        //this.endpoint = 'license';
        //this.get(this.endpoint);


//export const MockLicenseResponse: any = [
//    {	
//	"name": "cosmo-2i",
//	"descr": "COSMO 2km on Italy area",
//	"license": [{"name": "CCBY", "descr": "Creative Common BY"}],
//	"attribution": [{"name": "ARPAE", "descr": "Arpa Emilia-Romagna"]
//    }
//];

	this.data = new Array();
	var dataset1 = {
		"name":"COSMO-2I", 
		"description":"COSMO 2.2 km on Italy area",
		"license": [],
		"attribution": []
	};
	var dataset2 = {
		"name":"COSMO-5M", 
		"description":"COSMO 5 km on Mediterranean area",
		"license": [],
		"attribution": []
	};
	this.data.push(dataset1);
	this.data.push(dataset2);
	console.log(`data=`,this.data);
    }

    ngOnInit() {
        // init
        console.log(`ngOnInit`);
    }
}
