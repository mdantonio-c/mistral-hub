import { TestBed, inject } from "@angular/core/testing";

import { FormDataService } from "@app/services/formData.service";
import { WorkflowService } from "@app/services/workflow.service";
import { DataService } from "@app/services/data.service";
import { WorkflowServiceStub } from "@app/services/workflow.service.stub";
import { DataServiceStub } from "./data.service.stub";

describe("FormDataService", () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        FormDataService,
        { provide: WorkflowService, useClass: WorkflowServiceStub },
        { provide: DataService, useClass: DataServiceStub },
      ],
    });
  });

  it("should be created", inject(
    [FormDataService],
    (service: FormDataService) => {
      expect(service).toBeTruthy();
    },
  ));
});
