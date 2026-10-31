import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import test from "node:test";
import vm from "node:vm";

const testDirectory = dirname(fileURLToPath(import.meta.url));
const packageDirectory = resolve(testDirectory, "../..");
const scriptPath = resolve(
  packageDirectory,
  "static/LogiBoard/js/scripts.js",
);
const templatePath = resolve(packageDirectory, "templates/log_iboard.html");
const script = readFileSync(scriptPath, "utf8");
const template = readFileSync(templatePath, "utf8");

class FakeElement {
  constructor(tagName = "div") {
    this.tagName = tagName;
    this.children = [];
    this.listeners = new Map();
    this.attributes = new Map();
    this.classList = { add() {}, remove() {} };
    this.style = { display: "", setProperty() {} };
    this.value = "";
    this.src = "";
    this.className = "";
  }

  addEventListener(name, callback) {
    this.listeners.set(name, callback);
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  setAttribute(name, value) {
    this.attributes.set(name, value);
  }

  getAttribute(name) {
    return this.attributes.get(name) ?? `/static/${name}`;
  }

  set innerHTML(value) {
    this._innerHTML = value;
    this.children = [];
  }

  get innerHTML() {
    return this._innerHTML ?? "";
  }
}

function createContext() {
  const elements = new Map();
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, new FakeElement(id));
      return elements.get(id);
    },
    querySelector() {
      return new FakeElement();
    },
    querySelectorAll() {
      return [];
    },
    createElement(tagName) {
      return new FakeElement(tagName);
    },
    createTextNode(text) {
      return { nodeType: 3, textContent: String(text) };
    },
  };

  const context = vm.createContext({
    document,
    alert() {},
    setInterval() { return 1; },
    clearInterval() {},
    FileReader: class {},
    JSZip: {},
  });
  vm.runInContext(script, context, { filename: scriptPath });
  return { context, document };
}

test("archive filenames are inserted as text, never parsed as HTML", () => {
  const { context, document } = createContext();
  const maliciousName = '<img src=x onerror="globalThis.compromised=true">';
  const container = new FakeElement();

  vm.runInContext(
    `displayFolderContents({${JSON.stringify(maliciousName)}: null}, container, {}, [])`,
    vm.createContext({
      displayFolderContents: context.displayFolderContents,
      container,
      document,
    }),
  );

  const fileElement = container.children[0];
  assert.equal(fileElement.children[1].textContent, maliciousName);
  assert.equal(fileElement.innerHTML, "");
  assert.equal(fileElement.children[0].tagName, "img");
});

test("archive folder trees use null-prototype objects for untrusted names", () => {
  const { context } = createContext();
  const tree = vm.runInContext(
    `buildFolderTree(["__proto__/constructor/payload.txt", "constructor/prototype/file.log"])`,
    context,
  );

  assert.equal(Object.getPrototypeOf(tree), null);
  assert.equal(Object.getPrototypeOf(tree.__proto__), null);
  assert.equal(Object.getPrototypeOf(tree.__proto__.constructor), null);
  assert.equal(tree.__proto__.constructor["payload.txt"], null);
  assert.equal(Object.prototype.polluted, undefined);
});

test("LogiBoard pins the ZIP parser with Subresource Integrity", () => {
  assert.match(template, /jszip\/3\.10\.1\/jszip\.min\.js/);
  assert.match(template, /integrity="sha512-XMVd28F1oH\/O71fzwBnV7HucLxVwtxf26XV8P4wPk26EDxuGZ91N8bsOttmnomcCD3CS5ZMRL50H0GgOHvegtg=="/);
  assert.match(template, /crossorigin="anonymous"/);
});
