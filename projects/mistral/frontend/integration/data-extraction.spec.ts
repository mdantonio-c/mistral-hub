// This is to silence ESLint about undefined cy
/*global cy*/

describe("Data-extraction test", () => {
  before(() => {
    cy.login();
  });

  // beforeEach(() => {
  // });

  it("should visit dataset page", () => {
    // now that we're logged in, we can visit
    // any kind of restricted route!
    cy.visit("app/data");
    cy.location().should((location) => {
      expect(location.pathname).to.eq("/app/data/datasets");
    });
  });
});
