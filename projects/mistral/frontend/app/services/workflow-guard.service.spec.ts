import { TestBed, async, inject } from '@angular/core/testing';

import { WorkflowGuardServiceGuard } from './workflow-guard.service.guard';

describe('WorkflowGuardServiceGuard', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [WorkflowGuardServiceGuard]
    });
  });

  it('should ...', inject([WorkflowGuardServiceGuard], (guard: WorkflowGuardServiceGuard) => {
    expect(guard).toBeTruthy();
  }));
});

