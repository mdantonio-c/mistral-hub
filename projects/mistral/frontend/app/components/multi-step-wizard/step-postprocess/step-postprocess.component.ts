import { Component, OnInit, EventEmitter, Output } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import {
  FormBuilder,
  FormGroup,
  FormArray,
  FormControl,
  Validators,
} from "@angular/forms";
import { FormDataService } from "@app/services/formData.service";
import { PP_TIME_RANGES } from "@app/services/data";
import { SummaryStats, DataService } from "@app/services/data.service";
import { NotificationService } from "@rapydo/services/notification";

@Component({
  selector: "step-postprocess",
  templateUrl: "./step-postprocess.component.html",
})
export class StepPostprocessComponent implements OnInit {
  title = "Choose a post-processing";
  form: FormGroup;
  vars = [];
  gridInterpolationTemplates = [];
  sparePointsTemplates = [];
  validationResults = [];
  summaryStats: SummaryStats = { c: 0, s: 0 };
  uploadedFileName;
  space_crop_boundings = [
    {
      code: "ilon",
      desc: "Initial Lon",
      validators: [Validators.min(-180), Validators.max(180)],
    },
    {
      code: "ilat",
      desc: "Initial Lat",
      validators: [Validators.min(-90), Validators.max(90)],
    },
    {
      code: "flon",
      desc: "Final Lon",
      validators: [Validators.min(-180), Validators.max(180)],
    },
    {
      code: "flat",
      desc: "Final Lat",
      validators: [Validators.min(-90), Validators.max(90)],
    },
  ];

  space_grid_boundings = [
    {
      code: "x-min",
      desc: "Initial Lon",
      validators: [Validators.min(-180), Validators.max(180)],
    },
    {
      code: "y-min",
      desc: "Initial Lat",
      validators: [Validators.min(-90), Validators.max(90)],
    },
    {
      code: "x-max",
      desc: "Final Lon",
      validators: [Validators.min(-180), Validators.max(180)],
    },
    {
      code: "y-max",
      desc: "Final Lat",
      validators: [Validators.min(-90), Validators.max(90)],
    },
  ];

  interpolation_nodes = [
    {
      code: "nx",
      desc: "nx",
      validators: [Validators.min(0)],
    },
    {
      code: "ny",
      desc: "ny",
      validators: [Validators.min(0)],
    },
  ];

  timeRanges = PP_TIME_RANGES;
  stepIntervals = ["-", "hours", "days", "months", "years"];
  interpolationTypes = ["-", "near", "bilin", "average", "min", "max"];

  cropTypes = [
    {
      code: 0,
      desc: "coord",
    },
    {
      code: 1,
      desc: "bbox",
    },
  ];

  formatTypes = ["-", "json"];

  selectedInputTimeRange;
  selectedOutputTimeRange;
  selectedStepInterval;
  selectedInterpolationType;
  selectedConversionFormat;
  selectedCropType;

  constructor(
    private formBuilder: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private formDataService: FormDataService,
    private dataService: DataService,
    private notify: NotificationService
  ) {
    this.form = this.formBuilder.group({
      derived_variables: new FormArray([]),
      space_type: [],
      space_crop: new FormArray([], [Validators.required]),
      space_grid: new FormArray([]),
      gridInterpolationType: ["template"],
      gridTemplateFile: new FormControl(""),
      interpolationNodes: new FormArray([]),
      conversionFormat: ["json"],
      timeStep: new FormControl(),
      selectedGITemplate: new FormControl(),
      selectedSPTemplate: new FormControl(),
      selectedTimePP: new FormControl(),
      selectedSpacePP: new FormControl(),
      hasGribDataset: false,
      hasBufrDataset: false,
    });
  }

  private buildDerivedVariables() {
    const av = this.formDataService
      .getFormData()
      .postprocessors.filter((p) => p.processor_type === "derived_variables");
    let presetVariables = [];
    if (av && av.length) {
      presetVariables = av[0].variables;
    }
    this.vars.map((v) => {
      const control = this.formBuilder.control(
        presetVariables.includes(v.code)
      );
      (this.form.controls.derived_variables as FormArray).push(control);
    });
  }

  private buildTimePostProcess() {
    const pt = this.formDataService
      .getFormData()
      .postprocessors.filter(
        (p) => p.processor_type === "statistic_elaboration"
      );
    if (pt && pt.length) {
      this.form.controls["selectedTimePP"].setValue(true);
      this.selectedStepInterval = pt[0].interval; //'interval': this.selectedStepInterval,
      this.form.controls["timeStep"].setValue(pt[0].step); //'step': this.form.value.timeStep
      this.selectedInputTimeRange = this.timeRanges.filter(
        (t) => t.code == pt[0]["input_timerange"]
      )[0];
      this.selectedOutputTimeRange = this.timeRanges.filter(
        (t) => t.code == pt[0]["output_timerange"]
      )[0];
    } else {
      this.selectedStepInterval = "-";
      this.selectedInputTimeRange = {
        code: -1,
        desc: "-",
      };

      this.selectedOutputTimeRange = {
        code: -1,
        desc: "-",
      };
    }
  }

  private buildSpaceCrop() {
    const pt = this.formDataService
      .getFormData()
      .postprocessors.filter((p) => p.processor_type === "grid_cropping");
    if (pt && pt.length) {
      this.form.controls["selectedSpacePP"].setValue(true);
      this.form.controls["space_type"].setValue("crop");
      this.selectedCropType = this.cropTypes.filter(
        (c) => c.desc === pt[0]["sub_type"]
      )[0];
      const boundings = pt[0].boundings;
      this.space_crop_boundings.map((bound) => {
        const control = this.formBuilder.control(
          boundings[bound.code],
          bound.validators
        );
        (this.form.controls.space_crop as FormArray).push(control);
      });
    } else {
      this.selectedCropType = {
        code: 0,
        desc: "coord",
      };
      this.space_crop_boundings.map((bound) => {
        const control = this.formBuilder.control(0, bound.validators);
        (this.form.controls.space_crop as FormArray).push(control);
      });
    }
  }

  private buildSpaceGrid() {
    const pt = this.formDataService
      .getFormData()
      .postprocessors.filter((p) => p.processor_type === "grid_interpolation");
    if (pt && pt.length) {
      this.form.controls["selectedSpacePP"].setValue(true);
      this.form.controls["space_type"].setValue("grid");
      this.selectedInterpolationType = this.interpolationTypes.filter(
        (i) => i === pt[0]["sub_type"]
      )[0];
      const boundings = pt[0].boundings;
      if (boundings) {
        this.form.controls["gridInterpolationType"].setValue("area");
        this.space_grid_boundings.map((bound) => {
          const control = this.formBuilder.control(
            boundings[bound.code],
            bound.validators
          );
          (this.form.controls.space_grid as FormArray).push(control);
        });
        const nodes = pt[0].nodes;
        this.interpolation_nodes.map((node) => {
          const control = this.formBuilder.control(
            nodes[node.code],
            node.validators
          );
          (this.form.controls.interpolationNodes as FormArray).push(control);
        });
      } else {
        this.form.controls["gridInterpolationType"].setValue("template");
        const selectedTemplate = this.gridInterpolationTemplates.filter(
          (t) => t.filepath === pt[0].template
        )[0];
        this.form.controls["selectedGITemplate"].setValue(
          selectedTemplate.filepath
        );
        this.space_grid_boundings.map((bound) => {
          const control = this.formBuilder.control(0, bound.validators);
          (this.form.controls.space_grid as FormArray).push(control);
        });
        this.interpolation_nodes.map((node) => {
          const control = this.formBuilder.control(0, node.validators);
          (this.form.controls.interpolationNodes as FormArray).push(control);
        });
      }
    } else {
      this.selectedInterpolationType = "-";
      this.space_grid_boundings.map((bound) => {
        const control = this.formBuilder.control(0, bound.validators);
        (this.form.controls.space_grid as FormArray).push(control);
      });
      this.interpolation_nodes.map((node) => {
        const control = this.formBuilder.control(0, node.validators);
        (this.form.controls.interpolationNodes as FormArray).push(control);
      });
    }
  }

  private buildSparePoint() {
    const pt = this.formDataService
      .getFormData()
      .postprocessors.filter(
        (p) => p.processor_type === "spare_point_interpolation"
      );
    if (pt && pt.length) {
      this.form.controls["selectedSpacePP"].setValue(true);
      this.form.controls["space_type"].setValue("points");
      this.selectedInterpolationType = this.interpolationTypes.filter(
        (i) => i === pt[0]["sub_type"]
      )[0];
      const selectedTemplate = this.sparePointsTemplates.filter(
        (t) => t.filepath === pt[0]["coord_filepath"]
      )[0];
      this.form.controls["selectedSPTemplate"].setValue(
        selectedTemplate.filepath
      );
    } else {
      this.selectedInterpolationType = "-";
    }
  }

  private buildTemplates() {
    this.gridInterpolationTemplates = [];
    // grid interpolation templates
    this.dataService.getTemplates("grib").subscribe(
      (data) => {
        for (let type of data) {
          for (let file of type.files) {
            let filepath = file.split("/");
            let label = filepath[filepath.length - 1];
            this.gridInterpolationTemplates.push({
              label: label,
              filepath: file,
              format: type.type,
            });
            if (this.uploadedFileName && label === this.uploadedFileName) {
              this.form.controls["selectedGITemplate"].setValue(file);
            }
          }
        }
        this.buildSpaceGrid();
      },
      (error) => {
        this.notify.showError("Unable to load templates");
      }
    );

    // spare points templates
    this.sparePointsTemplates = [];
    this.dataService.getTemplates("shp").subscribe(
      (data) => {
        for (let type of data) {
          for (let file of type.files) {
            let filepath = file.split("/");
            let label = filepath[filepath.length - 1];
            this.sparePointsTemplates.push({
              label: label,
              filepath: file,
              format: type.type,
            });
            if (this.uploadedFileName) {
              let extractExtensionRegex = new RegExp("(?:.([^.]+))?$");
              let fileExtension = extractExtensionRegex.exec(
                this.uploadedFileName
              )[1];
              if (fileExtension === "geojson") {
                this.uploadedFileName = this.uploadedFileName.replace(
                  "geojson",
                  "shp"
                );
              } else if (fileExtension === "zip") {
                this.uploadedFileName = this.uploadedFileName.replace(
                  "zip",
                  "shp"
                );
              }
              if (label === this.uploadedFileName)
                this.form.controls["selectedSPTemplate"].setValue(file);
            }
          }
        }
        this.buildSparePoint();
      },
      (error) => {
        this.notify.showError("Unable to load templates");
      }
    );
  }

  private buildOutputFormat() {
    if (this.formDataService.getFormData().output_format) {
      this.selectedConversionFormat = this.formDataService.getFormData().output_format;
    } else {
      this.selectedConversionFormat = "-";
    }
  }

  private checkDatasetFormat() {
    const selectedDataset = this.formDataService.getFormData().datasets;
    this.form.controls["hasBufrDataset"].setValue(
      selectedDataset.some((d) => d.format === "bufr")
    );
    this.form.controls["hasGribDataset"].setValue(
      selectedDataset.some((d) => d.format === "grib")
    );
  }

  ngOnInit() {
    window.scroll(0, 0);

    this.formDataService.getSummaryStats().subscribe((response) => {
      this.summaryStats = response;
      //console.log('ngOnInit: this.summaryStats=', this.summaryStats);
    });

    this.checkDatasetFormat();
    this.dataService.getDerivedVariables().subscribe(
      (data) => {
        this.vars = data;
        this.buildDerivedVariables();
      },
      (error) => {
        this.notify.showError("Unable to load derived variables configuration");
      }
    );
    this.buildTemplates();
    this.buildTimePostProcess();
    this.buildSpaceCrop();
    this.buildOutputFormat();
  }

  loadFile(files: FileList) {
    if (files.length == 1) {
      let file: File = files[0];
      this.uploadedFileName = file.name;
      this.uploadFile(file);
    }
  }

  uploadFile(file: File) {
    this.dataService.uploadTemplate(file).subscribe(
      (data) => {
        this.buildTemplates();
      },
      (error) => {
        this.notify.showError(error.error);
      }
    );
  }

  private save() {
    if (!this.form.valid) {
      return false;
    }
    const selectedProcessors = [];
    // derived variables
    const selectedDerivedVariables = this.form.value.derived_variables
      .map((v, i) => (v ? this.vars[i].code : null))
      .filter((v) => v !== null);
    if (selectedDerivedVariables && selectedDerivedVariables.length) {
      selectedProcessors.push({
        processor_type: "derived_variables",
        variables: selectedDerivedVariables,
      });
    }

    // Time post processing
    if (this.form.value.selectedTimePP) {
      this.validateTimePostProcessor();
      let timeValidationItem = this.validationResults.filter(
        (v) => v.type == "time"
      )[0];
      if (!timeValidationItem) {
        selectedProcessors.push(this.calculateTimePostProcessor());
      }
    }

    // push space processor object in selectedProcessors
    const selectedSpaceProcessor = this.form.value.space_type;
    if (
      this.form.value.selectedSpacePP &&
      selectedSpaceProcessor &&
      selectedSpaceProcessor.length
    ) {
      switch (selectedSpaceProcessor) {
        case "crop": {
          this.validateAreaCrop();
          let areaValidationItem = this.validationResults.filter(
            (v) => v.type == "area"
          )[0];
          if (!areaValidationItem) {
            selectedProcessors.push(this.calculateSpaceCrop());
          }
          break;
        }
        case "grid": {
          this.validateGridInterpolation();
          let gridAreaValidationItem = this.validationResults.filter(
            (v) => v.type == "grid"
          )[0];
          if (!gridAreaValidationItem) {
            selectedProcessors.push(this.calculateSpaceGridCoord());
          }
          break;
        }

        case "points": {
          this.validateSparePoints();
          let sparePointsValidationItem = this.validationResults.filter(
            (v) => v.type == "spare_points"
          )[0];
          if (!sparePointsValidationItem) {
            selectedProcessors.push(this.calculateSparePoints());
          }
          break;
        }
      }
    }

    this.formDataService.setPostProcessor(selectedProcessors);
    if (
      this.selectedConversionFormat != null &&
      this.selectedConversionFormat != "-" &&
      (this.form.value.hasBufrDataset ||
        (this.form.value.hasGribDataset &&
          this.form.value.selectedSpacePP &&
          this.form.value.space_type === "points"))
    ) {
      this.formDataService.setOutputFormat(this.selectedConversionFormat);
    } else {
      this.formDataService.setOutputFormat("");
    }

    if (this.validationResults.length) {
      this.validationResults.forEach((r) => {
        if (r.messages.length) {
          let errorMessage = "";
          r.messages.forEach((m) => {
            errorMessage = errorMessage + m;
          });
          this.notify.showError(errorMessage, r.title);
        }
      });
      this.validationResults = [];
      return false;
    } else {
      return true;
    }
  }

  calculateSpaceCrop() {
    const boundings = {};
    this.form.value.space_crop.map((value, i) => {
      boundings[this.space_crop_boundings[i].code] = value;
    });

    return {
      processor_type: "grid_cropping",
      sub_type: this.selectedCropType.desc,
      boundings: boundings,
    };
  }

  calculateSpaceGridCoord() {
    const boundings = {};
    const nodes = {};

    if (this.form.value.gridInterpolationType == "area") {
      this.form.value.space_grid.map((value, i) => {
        boundings[this.space_grid_boundings[i].code] = value;
      });
      this.form.value.interpolationNodes.map((value, i) => {
        nodes[this.interpolation_nodes[i].code] = value;
      });

      return {
        processor_type: "grid_interpolation",
        sub_type: this.selectedInterpolationType,
        boundings: boundings,
        nodes: nodes,
      };
    }
    if (this.form.value.gridInterpolationType == "template") {
      return {
        processor_type: "grid_interpolation",
        template: this.form.value.selectedGITemplate,
        sub_type: this.selectedInterpolationType,
      };
    }
  }

  calculateSparePoints() {
    return {
      processor_type: "spare_point_interpolation",
      coord_filepath: this.form.value.selectedSPTemplate,
      format: this.sparePointsTemplates.find(
        (t) => t.filepath == this.form.value.selectedSPTemplate
      ).format,
      sub_type: this.selectedInterpolationType,
    };
  }

  calculateTimePostProcessor() {
    return {
      processor_type: "statistic_elaboration",
      input_timerange: this.selectedInputTimeRange.code,
      output_timerange: this.selectedOutputTimeRange.code,
      interval: this.selectedStepInterval,
      step: this.form.value.timeStep,
    };
  }

  validateTimePostProcessor() {
    let validationItem = {
      type: "time",
      title: "Time Post Processing",
      messages: [],
    };

    if (
      this.selectedInputTimeRange.code == null ||
      this.selectedInputTimeRange.code == -1 ||
      this.selectedOutputTimeRange.code == null ||
      this.selectedOutputTimeRange.code == -1 ||
      this.form.value.timeStep == null ||
      this.selectedStepInterval == null ||
      this.selectedStepInterval == "-"
    ) {
      validationItem.messages.push(" - Missing mandatory fields<br/>");
    }

    if (this.selectedInputTimeRange.code != this.selectedOutputTimeRange.code) {
      if (
        (this.selectedInputTimeRange.code == 254 &&
          (this.selectedOutputTimeRange.code == 1 ||
            this.selectedOutputTimeRange.code == 254)) ||
        (this.selectedInputTimeRange.code == 0 &&
          this.selectedOutputTimeRange.code != 254)
      ) {
        validationItem.messages.push(" - Inconsistent values<br/>");
      }
    }

    let timeStepRegex = new RegExp("^-?[0-9]+$");
    if (
      this.form.value.timeStep != null &&
      (this.form.value.timeStep <= 0 ||
        !timeStepRegex.test(this.form.value.timeStep))
    ) {
      validationItem.messages.push(
        " - Step value must be a positive integer<br/>"
      );
    }

    if (validationItem.messages.length) {
      this.validationResults.push(validationItem);
    }
  }

  validateAreaCrop() {
    let validationItem = {
      type: "area",
      title: "Area crop",
      messages: [],
    };

    if (
      this.form.value.space_crop.filter((s) => {
        let regex = new RegExp("-?[1-9]{1,2}.?[d]{0,6}$");
        return !regex.test(s);
      }).length
    ) {
      validationItem.messages.push(" - Lat/Lon values must be nonzero<br/>");
      this.validationResults.push(validationItem);
    }
  }

  validateGridInterpolation() {
    let validationItem = {
      type: "grid",
      title: "Grid interpolation",
      messages: [],
    };

    if (
      this.selectedInterpolationType == null ||
      this.selectedInterpolationType == "-"
    ) {
      validationItem.messages.push(" - interpolation type required<br/>");
    }

    if (this.form.value.gridInterpolationType == "area") {
      if (
        this.form.value.space_grid.filter((s) => {
          let regex = new RegExp("-?[1-9]{1,2}.?[d]{0,6}$");
          return !regex.test(s);
        }).length
      ) {
        validationItem.messages.push(" - Lat/Lon values must be nonzero<br/>");
      }

      if (
        this.form.value.interpolationNodes.filter((n) => {
          let regex = new RegExp("^-?[0-9]+$");
          return !regex.test(n);
        }).length
      ) {
        validationItem.messages.push(" - nx/ny values must be nonzero<br/>");
      }
    } else {
      if (!this.form.value.selectedGITemplate) {
        validationItem.messages.push(
          " - at least one template must be selected<br/>"
        );
      }
    }

    if (validationItem.messages.length) {
      this.validationResults.push(validationItem);
    }
  }

  validateSparePoints() {
    let validationItem = {
      type: "spare_points",
      title: "Spare points",
      messages: [],
    };

    if (
      this.selectedInterpolationType == null ||
      this.selectedInterpolationType == "-"
    ) {
      validationItem.messages.push(" - interpolation type required<br/>");
    }

    if (!this.form.value.selectedSPTemplate) {
      validationItem.messages.push(
        " - at least one template must be selected<br/>"
      );
    }

    if (validationItem.messages.length) {
      this.validationResults.push(validationItem);
    }
  }

  goToPrevious() {
    // Navigate to the dataset page
    this.router.navigate(["../", "filters"], { relativeTo: this.route });
  }

  goToNext() {
    if (this.save()) {
      // Navigate to the postprocess page
      this.router.navigate(["../", "submit"], { relativeTo: this.route });
    }
  }

  setInputRange(inRange) {
    this.selectedInputTimeRange = inRange;
  }

  setOutputRange(outRange) {
    this.selectedOutputTimeRange = outRange;
  }

  setStepInterval(interval) {
    this.selectedStepInterval = interval;
  }

  setCropType(cropType) {
    this.selectedCropType = cropType;
  }

  setInterpolationType(interpolationType) {
    this.selectedInterpolationType = interpolationType;
  }

  setConversionFormat(format) {
    this.selectedConversionFormat = format;
  }
}
