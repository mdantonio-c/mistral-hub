import {Component, OnInit, Output, EventEmitter} from '@angular/core';
import {FormBuilder, FormGroup, Validators, FormControl} from '@angular/forms';
import {ObsFilter} from '../services/obs.service';
import {AuthService} from '@rapydo/services/auth';
import {NgbDateStruct, NgbPanelChangeEvent} from '@ng-bootstrap/ng-bootstrap';

@Component({
    selector: 'app-obs-filter',
    templateUrl: './obs-filter.component.html',
    styleUrls: ['./obs-filter.component.css']
})
export class ObsFilterComponent implements OnInit {
    filterForm: FormGroup;
    user: any;
    model: NgbDateStruct;

    @Output() onFilterChange: EventEmitter<ObsFilter> = new EventEmitter<ObsFilter>();

    constructor(private fb: FormBuilder, private authService: AuthService) {
        this.filterForm = this.fb.group({
            product: ['B11001', Validators.required],
            level: ['', Validators.required],
            reftime: ['lm5', Validators.required],
            timerange: [''],
            boundingBox: [''],
            license: ['CC-BY', Validators.required]
        });
    }

    ngOnInit() {
        this.user = this.authService.getUser();
    }
}
