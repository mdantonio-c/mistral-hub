import { Component, OnInit, Output, EventEmitter } from "@angular/core";
import { FormBuilder, FormGroup, Validators } from "@angular/forms";
import {
  KeyValuePair,
  FlashFloodFFields,
  IffRuns,
  Levels_pe,
  Levels_pr,
} from "../services/data";
import { MeteoFilter } from "../services/meteo.service";
import { AuthService } from "@rapydo/services/auth";

@Component({
  selector: "app-map-flash-flood-filter",
  templateUrl: "./map-flash-flood-filter.component.html",
  styleUrls: ["./map-filter.component.css"],
})
export class MapFlashFloodFilterComponent implements OnInit {
  filterForm: FormGroup;
  fields: KeyValuePair[] = FlashFloodFFields;
  levels_pe: KeyValuePair[] = Levels_pe;
  levels_pr: KeyValuePair[] = Levels_pr;
  runs: KeyValuePair[] = IffRuns;

  resolutions: KeyValuePair[] = [{ key: "lm2.2", value: "2.2" }];
  areas: KeyValuePair[] = [
    { key: "Italia", value: "Italy" },
    { key: "Nord_Italia", value: "Northern Italy" },
    { key: "Centro_Italia", value: "Central Italy" },
    { key: "Sud_Italia", value: "Southern Italy" },
  ];
  user;

  @Output() onFilterChange: EventEmitter<MeteoFilter> =
    new EventEmitter<MeteoFilter>();

  constructor(private fb: FormBuilder, private authService: AuthService) {
    this.filterForm = this.fb.group({
      field: ["percentile", Validators.required],
      level_pe: ["25"],
      level_pr: ["20"],
      run: ["00", Validators.required],

      res: ["lm2.2", Validators.required],
      area: ["Italia", Validators.required],
    });
  }

  ngOnInit() {
    this.user = this.authService.getUser();
    // subscribe for form value changes
    this.onChanges();
    // apply filter the first time
    this.filter();
  }

  private onChanges(): void {
    this.filterForm.valueChanges.subscribe((val) => {
      this.filter();
    });
  }

  private filter() {
    let filter: MeteoFilter = this.filterForm.value;
    this.onFilterChange.emit(filter);
  }
}
