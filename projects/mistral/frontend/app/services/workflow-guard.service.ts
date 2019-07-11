import {Injectable} from '@angular/core';
import {
    CanActivate, Router,
    ActivatedRouteSnapshot,
} from '@angular/router';

import {WorkflowService} from './workflow.service';

@Injectable()
export class WorkflowGuard implements CanActivate {
    constructor(private router: Router, private workflowService: WorkflowService) {
    }

    canActivate(route: ActivatedRouteSnapshot): boolean {
        let path: string = route.routeConfig.path;
        return this.verifyWorkFlow(path);
    }

    verifyWorkFlow(path): boolean {
        console.log(`Entered ${path} path.`);

        // If any of the previous steps is invalid, go back to the first invalid step
        let firstPath = this.workflowService.getFirstInvalidStep(path);
        if (firstPath.length > 0) {
            console.log(`Redirected to ${firstPath} path which it is the first invalid step.`);
            let url = `/app/data/(step:${firstPath})`;
            this.router.navigate([path]);
            return false;
        }
        return true;
    }
}
