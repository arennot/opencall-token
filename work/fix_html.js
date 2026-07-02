var fs = require("fs");
var path = "C:\\Users\\arenn\\Documents\\Codex\\2026-06-30\\opencall-token\\outputs\\opencall-token\\index.html";
var html = fs.readFileSync(path, "utf8");

// Replace the nav section - remove duplicate grant button, add grant and local
// The current nav has: all, opencall, residency, local (grant was removed by bug)
// We need to change it to: all, opencall, residency, grant, local

// Find the nav section and fix it
html = html.replace(
  /<button class="nav-btn" data-view="residency">[^<]+<\/button>\s*<button class="nav-btn" data-view="local">[^<]+<\/button>/,
  "<button class=\"nav-btn\" data-view=\"residency\">驻留</button>\n      <button class=\"nav-btn\" data-view=\"grant\">资助</button>\n      <button class=\"nav-btn\" data-view=\"local\">社区</button>"
);

// Also remove any duplicate grant buttons
html = html.replace(
  /(<button class="nav-btn" data-view="grant">[^<]+<\/button>)(?:\s*<button class="nav-btn" data-view="grant">[^<]+<\/button>)+/g,
  "$1"
);

fs.writeFileSync(path, html, "utf8");
console.log("Fixed index.html");
