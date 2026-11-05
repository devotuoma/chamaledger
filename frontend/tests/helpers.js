import { JSDOM } from "jsdom";

export function setup() {
  const dom = new JSDOM(`<p id="status" hidden></p><main id="view"></main>`, {
    url: "http://localhost/",
  });
  globalThis.FormData = dom.window.FormData;
  return {
    root: dom.window.document.getElementById("view"),
    statusEl: dom.window.document.getElementById("status"),
    window: dom.window,
  };
}

export function submit(window, form) {
  form.dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
}

/** Lets promise chains started by DOM event handlers finish. */
export const flush = () => new Promise((resolve) => setTimeout(resolve, 0));
