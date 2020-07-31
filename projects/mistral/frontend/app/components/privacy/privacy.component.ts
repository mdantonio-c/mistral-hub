import { Component } from "@angular/core";
import { ProjectOptions } from "@app/custom.project.options";

@Component({
  selector: "privacy",
  templateUrl: "./privacy.component.html",
})
export class PrivacyComponent {
  public terms_of_use: string;

  constructor(private customization: ProjectOptions) {
    let tmp = this.customization.get_option("privacy_acceptance");
    this.terms_of_use = tmp[0]["text"];
  }
}
