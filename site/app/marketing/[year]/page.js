import { getAllYears, getYearIndex } from "../../lib/data";
import YearPageClient from "./YearPageClient";

export function generateStaticParams() {
  const years = getAllYears();
  return years.map((year) => ({ year }));
}

export default async function YearPage({ params }) {
  const { year } = await params;
  const data = getYearIndex(year);
  return <YearPageClient year={year} data={data} />;
}
