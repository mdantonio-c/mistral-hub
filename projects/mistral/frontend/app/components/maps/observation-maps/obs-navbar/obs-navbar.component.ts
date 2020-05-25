import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
	selector: 'app-obs-navbar',
	templateUrl: './obs-navbar.component.html',
	styleUrls: ['./obs-navbar.component.css']
})
export class ObsNavbarComponent {
	@Input() totalItems: number;
	@Input() loading: boolean;
	displayMode: string = 'Stations';
	@Output() viewChange: EventEmitter<string> = new EventEmitter<string>();

	ngOnChanges() {}

	changeView(choice) {
		this.displayMode = choice;
		this.viewChange.emit(choice);
	}
}
