import { TestBed, inject } from '@angular/core/testing';

import { WorkflowModelService } from './workflow.model.service';

describe('WorkflowModelService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [WorkflowModelService]
    });
  });

  it('should be created', inject([WorkflowModelService], (service: WorkflowModelService) => {
    expect(service).toBeTruthy();
  }));
});