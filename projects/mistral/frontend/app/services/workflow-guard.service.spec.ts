import {TestBed, async, inject} from '@angular/core/testing';
import {RouterTestingModule} from '@angular/router/testing';
import {Router} from '@angular/router';

import {WorkflowGuard} from '@app/services/workflow-guard.service';
import {WorkflowService} from '@app/services/workflow.service';
import {WorkflowServiceStub} from '@app/services/workflow.service.stub';

describe('WorkflowGuardServiceGuard', () => {
    let router: Router;
    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [RouterTestingModule.withRoutes([])],
            providers: [
                WorkflowGuard,
                {provide: WorkflowService, useClass: WorkflowServiceStub}
            ]
        });
        router = TestBed.get(Router);
    });

    it('should ...', inject([WorkflowGuard], (guard: WorkflowGuard) => {
        expect(guard).toBeTruthy();
    }));
});

