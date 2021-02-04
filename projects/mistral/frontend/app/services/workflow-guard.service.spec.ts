import { TestBed, async, inject } from "@angular/core/testing";
import { RouterTestingModule } from "@angular/router/testing";
import { Router } from "@angular/router";

import { WorkflowGuard } from "@app/services/workflow-guard.service";
import { WorkflowService } from "@app/services/workflow.service";
import { WorkflowServiceStub } from "@app/services/workflow.service.stub";
import { FormDataService } from "@app/services/formData.service";
import { FormDataServiceStub } from "@app/services/formData.service.stub";
import { ArkimetService } from "@app/services/arkimet.service";

describe("WorkflowGuardServiceGuard", () => {
  let router: Router;
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [RouterTestingModule.withRoutes([])],
      providers: [
        WorkflowGuard,
        ArkimetService,
        { provide: WorkflowService, useClass: WorkflowServiceStub },
        { provide: FormDataService, useClass: FormDataServiceStub },
      ],
    });
    router = TestBed.inject(Router);
  });

  it("should ...", inject([WorkflowGuard], (guard: WorkflowGuard) => {
    expect(guard).toBeTruthy();
  }));
});
