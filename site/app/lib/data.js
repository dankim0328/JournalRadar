import fs from "fs";
import path from "path";

const DATA_DIR = path.join(process.cwd(), "public", "data", "marketing");

export function getMarketingIndex() {
  const filePath = path.join(DATA_DIR, "index.json");
  if (!fs.existsSync(filePath)) return { years: [] };
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export function getYearIndex(year) {
  const filePath = path.join(DATA_DIR, String(year), "index.json");
  if (!fs.existsSync(filePath)) return { weeks: [] };
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export function getWeekData(year, week) {
  const filePath = path.join(DATA_DIR, String(year), `${week}.json`);
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export function getAllYears() {
  const idx = getMarketingIndex();
  return idx.years.map((y) => String(y.year));
}

export function getAllWeeks(year) {
  const idx = getYearIndex(year);
  return idx.weeks.map((w) => w.week);
}
