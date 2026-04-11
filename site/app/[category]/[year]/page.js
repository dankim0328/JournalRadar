import { getAllCategories, getAllYears, getYearIndex } from "../../lib/data";
import YearPageClient from "./YearPageClient";

export async function generateStaticParams() {
  const categories = getAllCategories();
  const params = [];

  for (const cat of categories) {
    const years = getAllYears(cat);
    years.forEach((year) => params.push({ category: cat, year }));
  }

  return params;
}

export default async function YearPage({ params }) {
  const { category, year } = await params;
  const data = getYearIndex(category, year);
  return <YearPageClient year={year} data={data} />;
}
