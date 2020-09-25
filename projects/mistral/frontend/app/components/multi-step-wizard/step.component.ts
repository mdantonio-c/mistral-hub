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

  getConfirmation(name) {
    return {
      title: "Confirmation required",
      message:
        `<div class='card text-center'>
          <div class='card-body'>
          <h4 class='card-title'>Are you really sure you want to cancel this ` +
        name +
        `?</h4>
          <p class='card-text'>This operation cannot be undone.</p>
          </div>
          </div>`,
    };
  }
}
