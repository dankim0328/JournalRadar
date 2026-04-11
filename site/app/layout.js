import "./globals.css";
import { LanguageProvider } from "./components/LanguageProvider";
import Header from "./components/Header";
import Script from "next/script";

export const metadata = {
  title: "Journal Radar — AI-Powered Academic Journal Analysis",
  description:
    "Weekly AI analysis of the world's top academic journals in Marketing, Finance, and Accounting. Stay ahead of cutting-edge research.",
  keywords: "academic journals, marketing research, finance research, accounting research, AI analysis, paper review",
  openGraph: {
    title: "Journal Radar",
    description: "AI-Powered Academic Journal Analysis Platform",
    type: "website",
  },
};

export default function RootLayout({ children }) {
  const gaId = process.env.NEXT_PUBLIC_GA_ID;

  return (
    <html lang="ko">
      <head>
        {gaId && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${gaId}`}
              strategy="afterInteractive"
            />
            <Script id="google-analytics" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${gaId}');
              `}
            </Script>
          </>
        )}
      </head>
      <body>
        <LanguageProvider>
          <div className="bg-ambient" />
          <Header />
          {children}
          <footer className="footer">
            <p>© {new Date().getFullYear()} Journal Radar — AI-Powered Academic Research</p>
          </footer>
        </LanguageProvider>
      </body>
    </html>
  );
}
