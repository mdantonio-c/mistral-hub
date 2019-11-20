import { TestBed, async, inject } from '@angular/core/testing';

import { WorkflowGuard } from '@app/services/workflow-guard.service';

describe('WorkflowGuardServiceGuard', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [WorkflowGuard]
    });
  });

  it('should ...', inject([WorkflowGuard], (guard: WorkflowGuard) => {
    expect(guard).toBeTruthy();
  }));
});

