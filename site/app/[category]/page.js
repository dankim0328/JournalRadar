import { getCategoryIndex, getAllCategories } from "../lib/data";
import CategoryPageClient from "./CategoryPageClient";

export async function generateStaticParams() {
  const categories = getAllCategories();
  return categories.map((category) => ({ category }));
}

export default async function CategoryPage({ params }) {
  const { category } = await params;
  const data = getCategoryIndex(category);

  return <CategoryPageClient category={category} data={data} />;
}
