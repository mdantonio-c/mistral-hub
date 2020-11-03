import { Component, OnInit } from "@angular/core";
// import {of} from "rxjs";
import { Dataset } from "../../types";
// import {MockDatasetsResponse} from "./data.mock";
import { NotificationService } from "@rapydo/services/notification";
import { NgxSpinnerService } from "ngx-spinner";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { DatasetDetailsComponent } from "../dataset-details/dataset-details.component";
import { FormBuilder, FormGroup, FormArray, FormControl } from "@angular/forms";
import { DataService } from "../../services/data.service";

interface DatasetFilter {
  productType: string;
  productLicense: string;
  attribution: string;
}

@Component({
  selector: "app-datasets",
  templateUrl: "./datasets.component.html",
  styleUrls: ["./datasets.component.css"],
})
export class DatasetsComponent implements OnInit {
  readonly title = "Datasets";
  // filter: DatasetFilter;
  datasets: Dataset[] = [];
  filterForm: FormGroup;
  loading: boolean = false;

  typesData: string[] = [];
  licensesData: string[] = [];
  attributionsData: string[] = [];

  private _datasets: Dataset[] = [];

  constructor(
    private dataService: DataService,
    private fb: FormBuilder,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private modalService: NgbModal
  ) {
    this.filterForm = this.fb.group({
      types: new FormArray([]),
      licenses: new FormArray([]),
      attributions: new FormArray([]),
    });
  }

  ngOnInit() {
    this.load();
  }

  // changeFilter(newFilter: DatasetFilter) {
  //   this.filter = newFilter;
  //   this.load();
  // }

  private load() {
    this.loading = true;
    this.spinner.show();
    this.dataService
      .getDatasets(true)
      .subscribe(
        (data) => {
          this._datasets = data;
          // once the data is available the filter can be create
          this.typesData = [
            ...new Set(this._datasets.map((ds) => ds.category)),
          ];
          this.licensesData = [
            ...new Set(this._datasets.map((ds) => ds.license)),
          ];
          this.attributionsData = [
            ...new Set(this._datasets.map((ds) => ds.attribution)),
          ];
          // init form data with empty checkboxes
          this.typesData.forEach(() =>
            this.typesFormArray.push(new FormControl(false))
          );
          this.licensesData.forEach(() =>
            this.licensesFormArray.push(new FormControl(false))
          );
          this.attributionsData.forEach(() =>
            this.attributionsFormArray.push(new FormControl(false))
          );

          // copy datasets to display
          this.datasets = [...this._datasets];
        },
        (error) => {
          this.notify.showError(error);
        }
      )
      .add(() => {
        this.loading = false;
        this.spinner.hide();
      });
  }

  openDataset(ds: Dataset) {
    const modalRef = this.modalService.open(DatasetDetailsComponent, {
      size: "lg",
      centered: true,
    });
    modalRef.componentInstance.dataset = ds;
  }

  onFilterChange() {
    this.datasets = [...this._datasets];
    const selectedTypeIds = this.filterForm.value.types
      .map((checked, i) => (checked ? this.typesData[i] : null))
      .filter((v) => v !== null);
    // console.log(selectedTypeIds);
    if (selectedTypeIds.length) {
      // apply type filter
      this.datasets = this.datasets.filter((ds) =>
        selectedTypeIds.includes(ds.category)
      );
    }
    const selectedLicenseIds = this.filterForm.value.licenses
      .map((checked, i) => (checked ? this.licensesData[i] : null))
      .filter((v) => v !== null);
    // console.log(selectedLicenseIds);
    if (selectedLicenseIds.length) {
      // apply type filter
      this.datasets = this.datasets.filter((ds) =>
        selectedLicenseIds.includes(ds.license)
      );
    }
    const selectedAttributionIds = this.filterForm.value.attributions
      .map((checked, i) => (checked ? this.attributionsData[i] : null))
      .filter((v) => v !== null);
    // console.log(selectedAttributionIds);
    if (selectedAttributionIds.length) {
      // apply type filter
      this.datasets = this.datasets.filter((ds) =>
        selectedAttributionIds.includes(ds.attribution)
      );
    }
  }

  // @ts-ignore
  get typesFormArray() {
    return this.filterForm.controls.types as FormArray;
  }

  // @ts-ignore
  get licensesFormArray() {
    return this.filterForm.controls.licenses as FormArray;
  }

  // @ts-ignore
  get attributionsFormArray() {
    return this.filterForm.controls.attributions as FormArray;
  }
}
