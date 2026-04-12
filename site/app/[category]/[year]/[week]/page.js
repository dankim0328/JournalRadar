import { getAllCategories, getAllYears, getAllWeeks, getWeekData } from "../../../lib/data";
import WeekPageClient from "./WeekPageClient";
import { Suspense } from "react";

export async function generateStaticParams() {
  const categories = getAllCategories();
  const params = [];

  for (const cat of categories) {
    const years = getAllYears(cat);
    for (const year of years) {
      const weeks = getAllWeeks(cat, year);
      for (const week of weeks) {
        params.push({ category: cat, year, week });
      }
    }
  }

  return params;
}

export default async function WeekPage({ params }) {
  const { category, year, week } = await params;
  const data = getWeekData(category, year, week);
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <WeekPageClient category={category} year={year} week={week} data={data} />
    </Suspense>
  );
}
