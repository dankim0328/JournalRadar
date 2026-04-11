import { getAllYears, getAllWeeks, getWeekData } from "../../../lib/data";
import WeekPageClient from "./WeekPageClient";

export function generateStaticParams() {
  const years = getAllYears();
  const params = [];
  for (const year of years) {
    const weeks = getAllWeeks(year);
    for (const week of weeks) {
      params.push({ year, week });
    }
  }
  return params;
}

export default async function WeekPage({ params }) {
  const { year, week } = await params;
  const data = getWeekData(year, week);
  return <WeekPageClient year={year} week={week} data={data} />;
}
