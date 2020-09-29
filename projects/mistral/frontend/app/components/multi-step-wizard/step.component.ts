import { Component } from "@angular/core";
import { FormDataService } from "@app/services/formData.service";
import { Router, ActivatedRoute } from "@angular/router";

@Component({
  selector: "mst-step",
  template: "",
})
export class StepComponent {
  title: string;

  constructor(
    protected formDataService: FormDataService,
    protected router: Router,
    protected route: ActivatedRoute
  ) {}

  cancel() {
    this.formDataService.resetFormData();
    console.log("request canceled");
    this.router.navigate(["../", "datasets"], { relativeTo: this.route });
  }
}
