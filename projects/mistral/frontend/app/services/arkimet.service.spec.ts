import { TestBed, inject } from '@angular/core/testing';

import { ArkimetService } from './arkimet.service';

describe('ArkimetService', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ArkimetService]
    });
  });

  it('should be created', inject([ArkimetService], (service: ArkimetService) => {
    expect(service).toBeTruthy();
  }));
});