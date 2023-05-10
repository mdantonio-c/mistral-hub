import { Injectable } from "@angular/core";
import { CanActivate, Router, ActivatedRouteSnapshot } from "@angular/router";

import { WorkflowService } from "@app/services/workflow.service";
import { FormDataService } from "@app/services/formData.service";
import { ArkimetService } from "@app/services/arkimet.service";
import * as moment from "moment";
import { Filters } from "@app/types";

@Injectable({
  providedIn: "root",
})
export class WorkflowGuard implements CanActivate {
  constructor(
    private router: Router,
    private workflowService: WorkflowService,
    private formDataService: FormDataService,
    private arkimetService: ArkimetService,
  ) {}

  canActivate(route: ActivatedRouteSnapshot): boolean {
    let path: string = route.routeConfig.path;
    return this.verifyWorkFlow(path);
  }

  verifyWorkFlow(path): boolean {
    // console.log(`Entered '${path}' path.`);
    let presetForm = this.router.getCurrentNavigation().extras.state;
    if (presetForm) {
      // STEP: DATASETS (arg: Dataset[])
      this.formDataService.setDatasets(presetForm.datasets);
      // STEP: FILTERS  (arg: Filters[])
      this.formDataService.setReftime({
        from: moment.utc(presetForm.reftime.from).toDate(),
        to: moment.utc(presetForm.reftime.to).toDate(),
      });
      let filters: Filters[] = [];
      if (presetForm.filters) {
        for (const [key, value] of Object.entries(presetForm.filters)) {
          let res = {
            name: `${key}`,
            values: value as any[],
            query: "",
          };
          if (res.values.length) {
            res.query = this.arkimetService.getQuery(res);
            // dballe query
            if (res.query === "" || res.query.split(":")[1] === "") {
              res.query += res.values.map((v) => v.code).join(" or ");
            }
            filters.push(res);
          }
        }
      }
      this.formDataService.setFilters(filters);
      // STEP: POST-PROCESS
      this.formDataService.setPostProcessor(presetForm.postprocessors || []);
      if (presetForm.hasOwnProperty("output_format")) {
        this.formDataService.setOutputFormat(presetForm.output_format);
      }
      if (presetForm.hasOwnProperty("only_reliable")) {
        this.formDataService.setQCFilter(presetForm.only_reliable);
      }
    }

    // If any of the previous steps is invalid, go back to the first invalid step
    let firstPath = this.workflowService.getFirstInvalidStep(path);
    if (!presetForm && firstPath.length > 0) {
      console.log(
        `Redirected to '${firstPath}' path which is the first invalid step.`,
      );
      let url = `/app/data/${firstPath}`;
      this.router.navigate([url]);
      return false;
    }
    return true;
  }
}
