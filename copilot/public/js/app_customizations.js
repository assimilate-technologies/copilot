frappe.ui.keys.add_shortcut({
  shortcut: "shift+ctrl+d",
  action: function () {
    // navigate to ask CoPilot page
    frappe.set_route("copilot");
  },
  description: __("Ask CoPilot"),
});
