const fs = require('fs');
const html = fs.readFileSync('/Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/templates/category/view.html', 'utf8');

// Extract all <script> contents
const scripts = [];
const regex = /<script.*?>([\s\S]*?)<\/script>/gi;
let match;
while ((match = regex.exec(html)) !== null) {
  scripts.push(match[1]);
}

const jsCode = scripts.join('\n');
// Replace jinja tags to prevent syntax errors
const safeJs = jsCode.replace(/\{\{[\s\S]*?\}\}/g, '"TEMPLATED"').replace(/\{%[\s\S]*?%\}/g, '');

try {
  new Function(safeJs);
  console.log("Syntax is OK!");
} catch (e) {
  console.log("Syntax Error:");
  console.log(e);
}
