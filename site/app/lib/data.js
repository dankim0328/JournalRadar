import fs from "fs";
import path from "path";

const BASE_DATA_DIR = path.join(process.cwd(), "public", "data");

export function getCategoryIndex(category) {
  const filePath = path.join(BASE_DATA_DIR, category.toLowerCase(), "index.json");
  if (!fs.existsSync(filePath)) return { years: [] };
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export function getYearIndex(category, year) {
  const filePath = path.join(BASE_DATA_DIR, category.toLowerCase(), String(year), "index.json");
  if (!fs.existsSync(filePath)) return { weeks: [] };
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export function getWeekData(category, year, week) {
  const filePath = path.join(BASE_DATA_DIR, category.toLowerCase(), String(year), `${week}.json`);
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

export function getAllYears(category) {
  const idx = getCategoryIndex(category);
  return idx.years.map((y) => String(y.year));
}

export function getAllWeeks(category, year) {
  const idx = getYearIndex(category, year);
  return idx.weeks.map((w) => w.week);
}

export function getAllCategories() {
  return ["marketing", "finance", "accounting"];
}
