import { Component, OnInit, ViewChild, ElementRef } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  FormArray,
  FormControl,
  Validators,
} from "@angular/forms";
import { User } from "@rapydo/types";
import { GenericItems, RefTime } from "@app/types";
import { NotificationService } from "@rapydo/services/notification";
import { FormDataService } from "@app/services/formData.service";
import { ArkimetService } from "@app/services/arkimet.service";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { NgxSpinnerService } from "ngx-spinner";
import * as moment from "moment";
import * as _ from "lodash";
import { StepComponent } from "../step.component";
import { ReftimeModalContent, ReftimeModel } from "./reftime-modal.component";
import { AuthService } from "@rapydo/services/auth";
import { LEVELTYPES } from "./level-descriptions";

@Component({
  selector: "step-filters",
  templateUrl: "./step-filters.component.html",
})
export class StepFiltersComponent extends StepComponent implements OnInit {
  @ViewChild("leveltypediv ", { static: false })
  public leveltypediv: ElementRef;
  title = "Filter your data";
  summaryStats = { b: null, e: null, c: null, s: null };
  filterForm: FormGroup;
  filters: GenericItems;
  user: User;
  public isCollapsed = true;
  levelTypes: string[] = [];
  levelTypesDescriptions: string[] = [];
  selectedLevelTypes: boolean[] = [];
  isLevelsSelected: boolean = false;

  constructor(
    private fb: FormBuilder,
    protected router: Router,
    protected route: ActivatedRoute,
    protected formDataService: FormDataService,
    private arkimetService: ArkimetService,
    private modalService: NgbModal,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private authService: AuthService
  ) {
    super(formDataService, router, route);
    const refTime: RefTime = this.formDataService.getReftime();
    this.filterForm = this.fb.group({
      filters: this.fb.array([]),
      reftime: ReftimeModel.getReftime({
        fromDate: refTime
          ? refTime.from
          : this.formDataService.getDefaultRefTime().from,
        fromTime: refTime ? moment.utc(refTime.from).format("HH:mm") : "00:00",
        toDate: refTime
          ? refTime.to
          : this.formDataService.getDefaultRefTime().to,
        toTime: refTime ? moment.utc(refTime.to).format("HH:mm") : "00:00",
        fullDataset: false,
      }),
      validRefTime: new FormControl(false, [Validators.requiredTrue]),
    });
  }

  ngOnInit() {
    this.user = this.authService.getUser();
    this.loadFilters();
    window.scroll(0, 0);
  }

  private getFilterGroup(name: string, values: any): FormGroup {
    let filter = this.fb.group({
      name: [name, Validators.required],
      values: new FormArray([]),
    });
    // init values
    values.map((o) => {
      // pre-set actual values from formData
      const control = new FormControl(
        this.formDataService.isFilterSelected(o, name)
      );
      (filter.controls.values as FormArray).push(control);
    });
    return filter;
  }

  onFilterChange() {
    this.spinner.show("sp2");
    let selectedFilters = this.getSelectedFilters();
    // console.log('selected filter(s)', selectedFilters);
    let selectedFilterNames = selectedFilters.map((f) => f.name);
    this.formDataService
      .getFilters(selectedFilters)
      .subscribe(
        (response) => {
          let results = response.items;
          // console.log(results);
          // compare the current filters with the selection results
          // in order to disable the missing ones
          Object.entries(this.filters).forEach((f) => {
            // if (!selectedFilterNames.includes(f[0])) {
            if (f[0] !== "summarystats") {
              // ["name", [{...},{...}]]
              // console.log(f[0]);
              // console.log('....OLD....', f[1]);
              let m = Object.entries(results).filter((e) => e[0] === f[0])[0];
              if (selectedFilterNames.includes(m[0])) {
                if (selectedFilterNames.length === 1) {
                  // active them all
                  for (const obj of <Array<any>>f[1]) {
                    obj["active"] = true;
                  }
                }
              } else {
                for (const obj of <Array<any>>f[1]) {
                  // equal by desc
                  obj["active"] = _.some(
                    <Array<any>>m[1],
                    (o, i) => o.desc === obj.desc
                  );
                }
              }
              //console.log('....NEW....', m[1]);
            }
          });
          if (this.levelTypes.length !== 0) {
            // disable the leveltypes
            this.updateLevelType();
          }
          this.updateSummaryStats(response.items.summarystats);
        },
        (error) => {
          this.notify.showError(`Unable to get summary fields`);
        }
      )
      .add(() => {
        this.spinner.hide("sp2");
      });
  }

  loadFilters() {
    this.spinner.show("sp1");
    // reset filters
    (this.filterForm.controls.filters as FormArray).clear();
    this.formDataService
      .getFilters()
      .subscribe(
        (response) => {
          this.filters = response.items as GenericItems;
          let toBeExcluded = ["summarystats", "network"];
          Object.entries(this.filters).forEach((entry) => {
            if (!toBeExcluded.includes(entry[0])) {
              (<Array<any>>entry[1]).forEach(function (obj) {
                obj["active"] = true;
              });
              (this.filterForm.controls.filters as FormArray).push(
                this.getFilterGroup(entry[0], entry[1])
              );
              // group filter values
              if (entry[0] === "level") {
                let arr: string[] = [];
                (<Array<any>>entry[1]).forEach(function (obj) {
                  if (obj.style == "GRIB1" || obj.style == "GRIB2S") {
                    arr.push(obj.level_type);
                  } else if (obj.style == "GRIB2D") {
                    arr.push(obj.l1 + "," + obj.l2);
                  }
                });
                // @ts-ignore
                this.levelTypes = [...new Set(arr)];
                // get descriptions for leveltypes
                this.getLevelTypeDesc();
                //initialize leveltypes
                this.levelTypesInit();
              }
            }
          });
          //console.log(this.filterForm.get('filters'));
          //console.log(this.filters);

          this.updateSummaryStats(response.items.summarystats);
        },
        (error) => {
          this.notify.showError(`Unable to get summary fields`);
        }
      )
      .add(() => {
        this.spinner.hide("sp1");
        if (this.formDataService.getFormData().filters.length !== 0) {
          this.onFilterChange();
        }
      });
  }

  private updateSummaryStats(summaryStats) {
    // console.log(summaryStats);
    this.summaryStats = summaryStats;
    let from = null;
    if (!this.summaryStats.hasOwnProperty("b")) {
      from = moment(this.formDataService.getReftime().from).utc();
      this.summaryStats["b"] = [
        from.year(),
        from.month() + 1,
        from.date(),
        from.hour(),
        from.minute(),
        0,
      ];
    } else {
      from = moment.utc({
        year: this.summaryStats.b[0],
        month: this.summaryStats.b[1] - 1,
        day: this.summaryStats.b[2],
        hour: this.summaryStats.b[3],
        minute: this.summaryStats.b[4],
      });
    }
    (this.filterForm.controls.reftime as FormGroup).controls.fromDate.setValue(
      from.toDate()
    );
    (this.filterForm.controls.reftime as FormGroup).controls.fromTime.setValue(
      from.format("HH:mm")
    );
    let to = null;
    if (!this.summaryStats.hasOwnProperty("e")) {
      to = moment(this.formDataService.getReftime().to).utc();
      this.summaryStats["e"] = [
        to.year(),
        to.month() + 1,
        to.date(),
        to.hour(),
        to.minute(),
        0,
      ];
    } else {
      to = moment.utc({
        year: this.summaryStats.e[0],
        month: this.summaryStats.e[1] - 1,
        day: this.summaryStats.e[2],
        hour: this.summaryStats.e[3],
        minute: this.summaryStats.e[4],
      });
    }
    (this.filterForm.controls.reftime as FormGroup).controls.toDate.setValue(
      to.toDate()
    );
    (this.filterForm.controls.reftime as FormGroup).controls.toTime.setValue(
      to.format("HH:mm")
    );
    this.formDataService.setReftime({
      from: from.toDate(),
      to: to.toDate(),
    });

    if (this.summaryStats["c"] === 0) {
      this.filterForm.controls.validRefTime.setValue(false);
      this.notify.showWarning(
        "The applied reference time does not produce any result. " +
          "Please choose a different reference time range."
      );
    } else {
      this.filterForm.controls.validRefTime.setValue(true);
    }
  }
  updateLevelType() {
    Object.entries(this.filters).forEach((f) => {
      if (f[0] == "level") {
        for (const obj of <Array<any>>f[1]) {
          let levelType = null;
          if (obj.style == "GRIB1" || obj.style == "GRIB2S") {
            levelType = "#lt-" + obj.level_type;
          } else if (obj.style == "GRIB2D") {
            levelType = "#lt-" + obj.l1 + "," + obj.l2;
          }
          let levelTypeInput =
            this.leveltypediv.nativeElement.querySelector(levelType);
          levelTypeInput["disabled"] = !obj.active;
        }
      }
    });
  }

  resetFilters() {
    this.formDataService.setFilters([]);
    this.loadFilters();
  }

  editReftime() {
    const modalRef = this.modalService.open(ReftimeModalContent);
    modalRef.componentInstance.data = this.filterForm.value.reftime;
    modalRef.result.then(
      (result) => {
        this.filterForm.get("reftime").patchValue(result);
        if (
          (this.filterForm.controls.reftime as FormGroup).controls.fullDataset
            .value
        ) {
          this.formDataService.setReftime(null);
        } else {
          let fromDate: Date = (
            this.filterForm.controls.reftime as FormGroup
          ).get("fromDate").value;
          const fromTime = (this.filterForm.controls.reftime as FormGroup)
            .get("fromTime")
            .value.split(":");
          fromDate = moment(fromDate)
            .utc()
            .hours(parseInt(fromTime[0]))
            .minutes(parseInt(fromTime[1]))
            .toDate();
          let toDate: Date = (
            this.filterForm.controls.reftime as FormGroup
          ).get("toDate").value;
          const toTime = (this.filterForm.controls.reftime as FormGroup)
            .get("toTime")
            .value.split(":");
          toDate = moment(toDate)
            .utc()
            .hours(parseInt(toTime[0]))
            .minutes(parseInt(toTime[1]))
            .toDate();
          this.formDataService.setReftime({
            from: fromDate,
            to: toDate,
          });
        }
        this.loadFilters();
      },
      (reason) => {
        // do nothing
      }
    );
  }

  private save() {
    if (!this.filterForm.valid) {
      return false;
    }
    this.formDataService.setFilters(this.getSelectedFilters());
    return true;
  }

  private getSelectedFilters() {
    const selectedFilters = [];
    (this.filterForm.controls.filters as FormArray).controls.forEach(
      (f: AbstractControl) => {
        let res = {
          name: (f as FormGroup).controls.name.value,
          values: ((f as FormGroup).controls.values as FormArray).controls
            .map((v, j) =>
              v.value
                ? this.filters[(f as FormGroup).controls.name.value][j]
                : null
            )
            .filter((v) => v !== null),
          query: "",
        };
        if (res.values.length) {
          res.query = this.arkimetService.getQuery(res);
          // dballe query
          if (res.query === "" || res.query.split(":")[1] === "") {
            res.query += res.values.map((v) => v.code).join(" or ");
          }
          selectedFilters.push(res);
        }
      }
    );
    // check if there is any level that is selected
    if (selectedFilters.length) {
      let selectedLevels = selectedFilters.find((x) => x.name === "level");
      if (selectedLevels) {
        this.isLevelsSelected = true;
      } else {
        this.isLevelsSelected = false;
      }
      //console.log("is any level selected? "+ this.isLevelsSelected)
    } else {
      this.isLevelsSelected = false;
    }

    return selectedFilters;
  }

  goToPrevious() {
    // Navigate to the dataset page
    this.router.navigate(["../", "datasets"], { relativeTo: this.route });
  }

  goToNext() {
    if (this.save()) {
      // Navigate to the postprocess page
      this.router.navigate(["../", "postprocess"], { relativeTo: this.route });
    }
  }

  getFilterTooltip(key: string) {
    let desc = "Add helpful info about this filter";
    switch (key) {
      case "area":
        desc = "Definition of the domain area of the model.";
        break;
      case "level":
        desc =
          "Levels of the atmosphere expressed in vertical coordinates (possibly layers). \n" +
          "The parameters of the vertical coordinates define the edges of the atmospheric layers in terms " +
          "of surface pressure.";
        break;
      case "origin":
        desc =
          "Identifies the forecast model, the characteristic and its configuration. \n" +
          "It is related to the selected dataset.";
        break;
      case "proddef":
        desc = "Product definition information.";
        break;
      case "product":
        desc = "Weather fields.";
        break;
      case "run":
        desc =
          "A forecasting model process. In the case of Cosmo they  are 2 per day.";
        break;
      case "timerange":
        desc =
          "Defines the time period of the forecast and any processing (eg instant data, hourly average, " +
          "etc.). It is composed of 3 attributes: a value code (eg instant value, average, accumulation), " +
          "difference between validity time and reference time, duration of statistical processing";
        break;
    }
    return desc;
  }

  getLevelTypeDesc() {
    this.levelTypesDescriptions = [];
    for (let el = 0; el < this.levelTypes.length; el++) {
      const leveltype = LEVELTYPES.find(
        (x) => x.code === this.levelTypes[el].toString()
      );
      if (leveltype) {
        this.levelTypesDescriptions.push(leveltype.desc);
      } else {
        this.levelTypesDescriptions.push(this.levelTypes[el]);
      }
    }
  }

  levelTypesInit() {
    this.selectedLevelTypes = [];
    for (let el = 0; el < this.levelTypes.length; el++) {
      this.selectedLevelTypes.push(false);
    }
  }

  toggleAllLevels(cIndex, action: string) {
    // @ts-ignore
    const level: FormGroup = (
      this.filterForm.controls.filters as FormArray
    ).controls.at(cIndex);

    this.filters["level"].forEach((l, i) => {
      if (
        action === "select" &&
        (level.controls.values as FormArray).controls.at(i).disabled == false
      ) {
        (level.controls.values as FormArray).controls.at(i).setValue(true);
      }
      if (action !== "select") {
        (level.controls.values as FormArray).controls.at(i).setValue(false);
      }
    });
    this.onFilterChange();
  }

  onLevelTypeChange(cIndex) {
    //console.log(this.selectedLevelTypes)
    // @ts-ignore
    const level: FormGroup = (
      this.filterForm.controls.filters as FormArray
    ).controls.at(cIndex);
    this.filters["level"].forEach((l, i) => {
      if (l["style"] == "GRIB1" || l["style"] == "GRIB2S") {
        if (this.selectedLevelTypes[this.levelTypes.indexOf(l["level_type"])]) {
          (level.controls.values as FormArray).controls.at(i).setValue(true);
        }
      } else if (l["style"] == "GRIB2D") {
        if (
          this.selectedLevelTypes[
            this.levelTypes.indexOf(l["l1"] + "," + l["l2"])
          ]
        ) {
          (level.controls.values as FormArray).controls.at(i).setValue(true);
        }
      }
    });
    this.onFilterChange();
    // clean the leveltype selection array
    this.levelTypesInit();
  }
}
