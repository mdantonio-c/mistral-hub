import {Injectable} from '@angular/core';
import {
    CanActivate, Router,
    ActivatedRouteSnapshot,
} from '@angular/router';

import {WorkflowService} from '@app/services/workflow.service';

@Injectable({
  providedIn: 'root',
})
export class WorkflowGuard implements CanActivate {
    constructor(private router: Router, private workflowService: WorkflowService) {
    }

    canActivate(route: ActivatedRouteSnapshot): boolean {
        let path: string = route.routeConfig.path;
        return this.verifyWorkFlow(path);
    }

    verifyWorkFlow(path): boolean {
        console.log(`Entered '${path}' path.`);

        // If any of the previous steps is invalid, go back to the first invalid step
        let firstPath = this.workflowService.getFirstInvalidStep(path);
        if (firstPath.length > 0) {
            console.log(`Redirected to '${firstPath}' path which is the first invalid step.`);
            let url = `/app/data/${firstPath}`;
            this.router.navigate([url])
            return false;
        }
        return true;
    }
}
