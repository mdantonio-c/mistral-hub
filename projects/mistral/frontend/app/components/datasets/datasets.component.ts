import {
  Component,
  OnInit,
  ChangeDetectorRef,
  ViewChild,
  AfterViewInit,
} from "@angular/core";
import { Dataset } from "../../types";
import { NotificationService } from "@rapydo/services/notification";
import { AuthService } from "@rapydo/services/auth";
import { LocalStorageService } from "@rapydo/services/localstorage";
import { NgxSpinnerService } from "ngx-spinner";
import { NgbModal } from "@ng-bootstrap/ng-bootstrap";
import { DatasetDetailsComponent } from "../dataset-details/dataset-details.component";
import { FormBuilder, FormGroup, FormArray, FormControl } from "@angular/forms";
import { DataService } from "../../services/data.service";
import { User } from "@rapydo/types";
import { ObsMapComponent } from "../maps/observation-maps/obs-map/obs-map.component";
import { NgbAccordion } from "@ng-bootstrap/ng-bootstrap";

@Component({
  selector: "app-datasets",
  templateUrl: "./datasets.component.html",
  styleUrls: ["./datasets.component.scss"],
})
export class DatasetsComponent implements OnInit, AfterViewInit {
  readonly title = "Datasets";
  datasets: Dataset[] = [];
  filterForm: FormGroup;
  loading: boolean = false;
  multiSelection: boolean = false;
  //accordion: NgbdAccordionStatic;
  typesData: string[] = [];
  licensesData: string[] = [];
  attributionsData: string[] = [];

  private _datasets: Dataset[] = [];
  user: User;
  @ViewChild("acc") accordionComponent: NgbAccordion;

  constructor(
    private dataService: DataService,
    private local_storage: LocalStorageService,
    private authService: AuthService,
    private fb: FormBuilder,
    private notify: NotificationService,
    private spinner: NgxSpinnerService,
    private modalService: NgbModal,
    private ref: ChangeDetectorRef,
  ) {
    this.filterForm = this.fb.group({
      types: new FormArray([]),
      licenses: new FormArray([]),
      attributions: new FormArray([]),
    });
  }

  ngOnInit() {
    this.authService.isAuthenticated().subscribe((isAuth) => {
      this.user = isAuth ? this.authService.getUser() : null;
    });
    this.local_storage.userChanged.subscribe((user) => {
      if (user === this.local_storage.LOGGED_OUT) {
        this.user = null;
        this.ref.detectChanges();
      } else if (user === this.local_storage.LOGGED_IN) {
        this.user = this.authService.getUser();
      }
    });

    this.load();
  }

  ngAfterViewInit() {
    this.accordionComponent.expandAll();
  }

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
            this.typesFormArray.push(new FormControl(false)),
          );
          this.licensesData.forEach(() =>
            this.licensesFormArray.push(new FormControl(false)),
          );
          this.attributionsData.forEach(() =>
            this.attributionsFormArray.push(new FormControl(false)),
          );

          // copy datasets to display
          this.datasets = [...this._datasets];
        },
        (error) => {
          this.notify.showError(error);
        },
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
        selectedTypeIds.includes(ds.category),
      );
    }
    const selectedLicenseIds = this.filterForm.value.licenses
      .map((checked, i) => (checked ? this.licensesData[i] : null))
      .filter((v) => v !== null);
    // console.log(selectedLicenseIds);
    if (selectedLicenseIds.length) {
      // apply type filter
      this.datasets = this.datasets.filter((ds) =>
        selectedLicenseIds.includes(ds.license),
      );
    }
    const selectedAttributionIds = this.filterForm.value.attributions
      .map((checked, i) => (checked ? this.attributionsData[i] : null))
      .filter((v) => v !== null);
    // console.log(selectedAttributionIds);
    if (selectedAttributionIds.length) {
      // apply type filter
      this.datasets = this.datasets.filter((ds) =>
        selectedAttributionIds.includes(ds.attribution),
      );
    }
  }

  selectDataset($event) {
    // TODO
    console.log($event);
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

  get filteredDatasets() {
    if (!this.searchTerm.trim()) {
      return this.datasets;
    }

    return this.datasets.filter(
      (ds) =>
        ds.name.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        ds.description.toLowerCase().includes(this.searchTerm.toLowerCase()),
    );
  }
}
