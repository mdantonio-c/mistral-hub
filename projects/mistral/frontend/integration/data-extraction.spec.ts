import "cypress-localstorage-commands";

describe("Data-extraction test", () => {

    before(() => {
        cy.clearLocalStorageSnapshot();
        let credentials = {
            username: Cypress.env('AUTH_DEFAULT_USERNAME'),
            password: Cypress.env('AUTH_DEFAULT_PASSWORD')
        }
        cy.request('POST',  Cypress.env('API_URL') + 'auth/login', credentials)
            .its('body')
            .then(identity => {
                cy.log('token', identity);
                cy.setLocalStorage('token', identity);
            });

        cy.log('Login successful')
        cy.getLocalStorage('token').then(
          token => {
            const options = {
              method: 'GET',
              url: Cypress.env('API_URL') + 'auth/profile',
              'headers': {
                'Authorization': `Bearer ${token}`
              }
            }

            cy.request(options).then(response => {
                cy.log('currentUser', response.body)
                cy.setLocalStorage("currentUser", response.body);
            });

          }
        );

        cy.saveLocalStorage();
    });

    beforeEach(() => {
      cy.restoreLocalStorage();
    });

    it("should exist identity in localStorage", () => {
        cy.log(`${cy.getLocalStorage("token")}`);
        cy.getLocalStorage("token").should("exist");
        cy.getLocalStorage("token").then(token => {
          cy.log("Identity token", token);
        });
    });

    it("should exist currentUser in localStorage", () => {
        cy.getLocalStorage("currentUser").should("exist");
        cy.getLocalStorage("currentUser").then(profile => {
          cy.log("currentUser", profile);
        });
    });

    it('should visit dataset page', () => {
        // now that we're logged in, we can visit
        // any kind of restricted route!
        cy.visit('app/data')
        cy.location().should((location) => {
            expect(location.pathname).to.eq("/app/data/datasets");
        });
        // cy.wait(2000)
    });
});
