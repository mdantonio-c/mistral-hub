import { Injectable } from "@angular/core";
import { User } from "@rapydo/types";
import { MockUser } from "@app/services/data.mock";
import { AuthService } from "@rapydo/services/auth";
import { ApiService } from "@rapydo/services/api";
import { LocalStorageService } from "@rapydo/services/localstorage";
import { NotificationService } from "@rapydo/services/notification";

@Injectable()
export class AuthServiceStub extends AuthService {
  constructor() {
    super(
      {} as LocalStorageService,
      {} as ApiService,
      {} as NotificationService
    );
  }

  getUser(): User {
    return MockUser;
  }
}
