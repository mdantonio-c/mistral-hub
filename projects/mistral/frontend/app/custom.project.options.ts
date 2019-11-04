import { Injectable } from '@angular/core';

@Injectable()
export class ProjectOptions {

	constructor() {}

	public get_option(opt):any {
        if (opt == 'user_page') {
            return {
                "custom": [
                    {name: 'Disk Quota', prop: "disk_quota", flexGrow: 0.3}
                ]
            }
        }
		return null;
	}

/*	
	private registration_options() {
		return {}
	}
*/
}
