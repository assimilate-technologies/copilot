frappe.pages["copilot"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({
    parent: wrapper,
    single_column: true,
  });
};

frappe.pages["copilot"].on_page_show = function (wrapper) {
  load_copilot_ui(wrapper);
};

function load_copilot_ui(wrapper) {
  let $parent = $(wrapper).find(".layout-main-section");
  $parent.empty();

  frappe.require("copilot_ui.bundle.jsx").then(() => {
    new copilot.ui.CopilotUI({
      wrapper: $parent,
      page: wrapper.page,
    });
  });
}
