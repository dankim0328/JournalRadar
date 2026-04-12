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

import Footer from "./components/Footer";
import CookieBanner from "./components/CookieBanner";

export default function RootLayout({ children }) {
  const gaId = process.env.NEXT_PUBLIC_GA_ID;

  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/JournalRadar/favicon.ico" />
        {gaId && (
          <>
            <Script id="google-analytics-consent" strategy="beforeInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                
                // Set default consent to 'denied'
                if (!localStorage.getItem('cookie-consent')) {
                  gtag('consent', 'default', {
                    'analytics_storage': 'denied',
                    'ad_storage': 'denied',
                    'wait_for_update': 500
                  });
                } else if (localStorage.getItem('cookie-consent') === 'granted') {
                  gtag('consent', 'default', {
                    'analytics_storage': 'granted',
                    'ad_storage': 'granted'
                  });
                }
              `}
            </Script>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${gaId}`}
              strategy="afterInteractive"
            />
            <Script id="google-analytics" strategy="afterInteractive">
              {`
                gtag('js', new Date());
                gtag('config', '${gaId}', {
                  'anonymize_ip': true
                });
              `}
            </Script>
          </>
        )}
      </head>
      <body>
        <LanguageProvider>
          <div className="bg-ambient" />
          <Header />
            <main>{children}</main>
          <Footer />
          <CookieBanner />
        </LanguageProvider>
      </body>
    </html>
  );
}
