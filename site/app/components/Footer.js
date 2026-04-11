"use client";
import { useLanguage } from "./LanguageProvider";

export default function Footer() {
  const { lang } = useLanguage();

  const disclaimer_ko = (
    <div className="footer-disclaimer">
      <strong>AI 생성 콘텐츠 안내</strong>
      이 사이트의 모든 논문 분석 요약은 Google Gemini 2.0 AI 모델을 사용하여 자동 생성되었습니다. 
      AI 분석은 일반적인 정보 제공만을 목적으로 하며, 학술적 정확성이나 저자의 의도를 100% 완벽하게 반영하지 못할 수 있습니다. 
      정확한 내용은 반드시 원문 논문을 참조하시기 바랍니다.
    </div>
  );

  const disclaimer_en = (
    <div className="footer-disclaimer">
      <strong>AI-Generated Content Disclaimer</strong>
      All research analysis summaries on this site are automatically generated using the Google Gemini 2.0 AI model. 
      These analyses are for informational purposes only and may not perfectly reflect academic accuracy or the authors' original intent. 
      Please always refer to the original papers for definitive information.
    </div>
  );

  return (
    <footer className="footer">
      <div className="footer-content">
        <p>© 2026 Journal Radar. All rights reserved.</p>
        {lang === "ko" ? disclaimer_ko : disclaimer_en}
      </div>
    </footer>
  );
}
