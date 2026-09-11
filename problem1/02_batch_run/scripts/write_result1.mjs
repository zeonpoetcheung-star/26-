import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const stage = path.resolve(scriptDir, "..");
const root = path.resolve(stage, "../../..");
const localRequire = createRequire(import.meta.url);
let artifactToolPath;
try {
  artifactToolPath = localRequire.resolve("@oai/artifact-tool");
} catch {
  const runtimeNodeModules = process.env.CODEX_NODE_MODULES
    ?? path.join(process.env.USERPROFILE ?? "", ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules");
  const runtimeRequire = createRequire(pathToFileURL(path.join(runtimeNodeModules, "resolver.cjs")));
  artifactToolPath = runtimeRequire.resolve("@oai/artifact-tool");
}
const { FileBlob, SpreadsheetFile } = await import(pathToFileURL(artifactToolPath).href);

const templatePath = path.join(root, "input/templates/result1.xlsx");
const schedulePath = path.join(stage, "results/p1_schedule_internal.csv");
const blockPath = path.join(stage, "tables/p1_storage_4h_summary.csv");
const outputPath = path.join(stage, "results/result1.xlsx");
const qaDir = path.join(stage, ".qa_work/result_renders");

function parseCsvLine(line) {
  const values = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"') {
      if (quoted && line[index + 1] === '"') {
        current += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === "," && !quoted) {
      values.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  values.push(current);
  return values;
}

async function readCsv(filePath) {
  const text = (await fs.readFile(filePath, "utf8")).replace(/^\uFEFF/, "").trimEnd();
  const lines = text.split(/\r?\n/);
  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const values = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index]]));
  });
}

const schedule = await readCsv(schedulePath);
const blocks = await readCsv(blockPath);
if (schedule.length !== 144 || blocks.length !== 6) {
  throw new Error(`导出载荷不完整：schedule=${schedule.length}, blocks=${blocks.length}`);
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(templatePath));
const purchaseSheet = workbook.worksheets.getItem("计划购电量");
const storageSheet = workbook.worksheets.getItem("充放电量");

const purchase = schedule.map((row) => Number(row.purchase_kwh));
const cyclicPurchase = [...purchase.slice(1), purchase[0]];
purchaseSheet.getRange("B2:B145").values = cyclicPurchase.map((value) => [value]);
storageSheet.getRange("B2:C7").values = blocks.map((row) => [Number(row["充电量_kWh"]), Number(row["放电量_kWh"])]);
storageSheet.getRange("E2:E3").values = [[6000], [6000]];

const beforeExport = await workbook.inspect({
  kind: "table",
  sheetId: "计划购电量",
  range: "A1:B145",
  maxChars: 4500,
  tableMaxRows: 6,
  tableMaxCols: 2,
});
console.log(beforeExport.ndjson);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const errors = await reopened.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "最终公式错误扫描",
});
console.log(errors.ndjson);

await fs.mkdir(qaDir, { recursive: true });
for (const sheetName of ["计划购电量", "充放电量"]) {
  const preview = await reopened.render({ sheetName, autoCrop: "all", scale: 1.5, format: "png" });
  await fs.writeFile(path.join(qaDir, `result1_${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}
console.log(`已生成：${outputPath}`);
