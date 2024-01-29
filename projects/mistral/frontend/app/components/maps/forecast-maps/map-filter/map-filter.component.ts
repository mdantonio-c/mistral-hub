import { Component, OnInit, Output, EventEmitter, Input } from "@angular/core";
import {
  FormBuilder,
  FormGroup,
  Validators,
  FormControl,
} from "@angular/forms";
import {
  KeyValuePair,
  Fields_cosmo,
  Fields_wrf,
  Levels_pe,
  Levels_pr,
  Runs,
  Areas,
  Resolutions,
  Platforms,
  Envs,
} from "../services/data";
import { MeteoFilter } from "../services/meteo.service";
import { AuthService } from "@rapydo/services/auth";
import { environment } from "@rapydo/../environments/environment";

@Component({
  selector: "app-map-filter",
  templateUrl: "./map-filter.component.html",
  styleUrls: ["./map-filter.component.css"],
})
export class MapFilterComponent implements OnInit {
  readonly DEFAULT_PLATFORM = environment.CUSTOM.PLATFORM || "G100";
  readonly DEFAULT_ENV = "PROD";

  filterForm: FormGroup;
  fields: KeyValuePair[] = [{ key: "lm2.2", value: "2.2" }]; // = []; //Fields;
  fields_cosmo: KeyValuePair[] = Fields_cosmo;
  fields_wrf: KeyValuePair[] = Fields_wrf;
  levels_pe: KeyValuePair[] = Levels_pe;
  levels_pr: KeyValuePair[] = Levels_pr;
  runs: KeyValuePair[] = Runs;
  resolutions: KeyValuePair[] = Resolutions;
  platforms: KeyValuePair[] = Platforms;
  envs: KeyValuePair[] = Envs;
  areas: KeyValuePair[] = Areas;
  user;

  @Output()
  onFilterChange: EventEmitter<MeteoFilter> = new EventEmitter<MeteoFilter>();
  // @Input()
  // weekday : string;

  constructor(private fb: FormBuilder, private authService: AuthService) {
    this.filterForm = this.fb.group({
      field: ["t2m", Validators.required],
      level_pe: ["25"],
      level_pr: ["20"],
      run: ["00", Validators.required],
      res: ["lm2.2", Validators.required],
      platform: [""],
      env: [""],
      area: ["Italia", Validators.required],
      weekday: [""],
    });
  }

  ngOnInit() {
    this.user = this.authService.getUser();
    this.fields = this.fields_cosmo;
    if (this.user && this.user.isAdmin) {
      (this.filterForm.controls.platform as FormControl).setValue(
        this.DEFAULT_PLATFORM,
      );
      (this.filterForm.controls.env as FormControl).setValue(this.DEFAULT_ENV);
    }
    // subscribe for form value changes
    this.onChanges();
    // apply filter the first time
    this.firstFilter();
  }

  _weekday: string;
  get weekday(): string {
    return this._weekday;
  }
  @Input() set weekday(value: string) {
    this._weekday = value;
    this.filterForm.get("weekday").setValue(this.weekday);
  }

  private onChanges(): void {
    this.filterForm.get("area").valueChanges.subscribe((val) => {
      if (val === "Area_Mediterranea") {
        this.filterForm.get("resolution").setValue("lm5", { emitEvent: false });
      }
    });
    this.filterForm.valueChanges.subscribe((val) => {
      this.filter();
    });
    this.filterForm.get("res").valueChanges.subscribe((val) => {
      if (val === "WRF_OL" || val === "WRF_DA_ITA") {
        this.fields = this.fields_wrf;
      } else this.fields = this.fields_cosmo;
    });
    //console.log(this.filterForm.value);
    //this.filterForm.get("weekday").setValue(this.weekday)
    // this.filterForm.valueChanges.subscribe((val) => {
    //   this.filter();
    //   });
  }

  private filter() {
    let filter: MeteoFilter = this.filterForm.value;
    if (!filter.weekday || filter.weekday === "") {
      delete filter["weekday"];
    }
    if (filter.env === "") {
      delete filter["env"];
    }
    if (filter.platform === "") {
      delete filter["platform"];
    }

    //this.onFilterChange.emit(filter);
  }
  pushBotton() {
    let filter: MeteoFilter = this.filterForm.value;
    this.onFilterChange.emit(filter);
  }
  private firstFilter() {
    let filter: MeteoFilter = this.filterForm.value;
    if (!filter.weekday || filter.weekday === "") {
      delete filter["weekday"];
    }
    if (filter.env === "") {
      delete filter["env"];
    }
    if (filter.platform === "") {
      delete filter["platform"];
    }

    this.onFilterChange.emit(filter);
  }
}
