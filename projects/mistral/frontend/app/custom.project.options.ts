import { Injectable } from '@angular/core';

import { BytesPipe } from '@rapydo/pipes/pipes';

@Injectable()
export class ProjectOptions {

	constructor() {}

	public get_option(opt):any {
        if (opt == 'user_page') {
            return {
                "custom": [
                    {name: 'Disk Quota', prop: "disk_quota", flexGrow: 0.3, pipe: new BytesPipe()}
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
