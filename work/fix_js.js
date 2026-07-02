var fs = require("fs");
var path = "C:\\Users\\arenn\\Documents\\Codex\\2026-06-30\\opencall-token\\outputs\\opencall-token\\app.js";
var code = fs.readFileSync(path, "utf8");

// Fix the broken querySelector: use single quotes to avoid quote clash
code = code.replace(
  'querySelector(".nav-btn[data-view="local"]")',
  "querySelector('.nav-btn[data-view=\"local\"]')"
);

fs.writeFileSync(path, code, "utf8");
console.log("Fixed");
