import { Injectable } from "@angular/core";
import { User } from "@rapydo/types";
import { MockUser } from "@app/services/data.mock";
import { AuthService } from "@rapydo/services/auth";
import { NotificationService } from "@rapydo/services/notification";
import { ApiService } from "@rapydo/services/api";

@Injectable()
export class AuthServiceStub extends AuthService {
  constructor() {
    super({} as ApiService, {} as NotificationService);
  }

  getUser(): User {
    return MockUser;
  }
}
