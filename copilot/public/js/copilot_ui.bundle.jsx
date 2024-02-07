import * as React from "react";
import { App } from "./App";
import { createRoot } from "react-dom/client";
import { ChakraProvider } from "@chakra-ui/react";
import { extendTheme } from "@chakra-ui/react";

const config = {
  initialColorMode: 'light',
  useSystemColorMode: false,
}
const theme = extendTheme({ config })
// DoppioBotUI
class CopilotUI {
  constructor({ wrapper, page }) {
    this.$wrapper = $(wrapper);
    this.page = page;
    this.init();
  }

  init() {
    const root = createRoot(this.$wrapper.get(0));
    root.render(
      <ChakraProvider theme={theme}>
        <App />
      </ChakraProvider>
    );
  }
}

frappe.provide("copilot.ui");
copilot.ui.CopilotUI = CopilotUI;
export default CopilotUI;
