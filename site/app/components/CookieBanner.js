"use client";
import { useState, useEffect } from "react";
import { useLanguage } from "./LanguageProvider";

export default function CookieBanner() {
  const [showBanner, setShowBanner] = useState(false);
  const { lang, t } = useLanguage();

  useEffect(() => {
    // Check v2 consent
    const consent = localStorage.getItem("cookie-consent-v2");
    if (!consent) {
      const timer = setTimeout(() => setShowBanner(true), 1200);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAll = () => {
    localStorage.setItem("cookie-consent-v2", "all");
    
    if (typeof window !== "undefined" && window.gtag) {
      window.gtag('consent', 'update', {
        'analytics_storage': 'granted',
        'ad_storage': 'granted'
      });
    }
    setShowBanner(false);
  };

  const handleEssential = () => {
    localStorage.setItem("cookie-consent-v2", "essential");
    
    if (typeof window !== "undefined" && window.gtag) {
      window.gtag('consent', 'update', {
        'analytics_storage': 'denied',
        'ad_storage': 'denied'
      });
    }
    setShowBanner(false);
  };

  if (!showBanner) return null;

  return (
    <div className="cookie-banner-container">
      <div className="cookie-banner-content">
        <div className="cookie-banner-icon">🍪</div>
        <div className="cookie-banner-text">
          <p className="cookie-title">
            {lang === 'ko' ? '개인정보 보호 설정' : 'Privacy Settings'}
          </p>
          <p className="cookie-desc">
            {lang === 'ko' 
              ? '더 나은 연구 데이터 제공을 위해 쿠키를 사용합니다. 선택해 주세요.' 
              : 'We use cookies to improve your research experience. Please choose your preference.'}
          </p>
        </div>
        <div className="cookie-banner-actions">
          <button onClick={handleEssential} className="cookie-btn btn-secondary">
            {lang === 'ko' ? '필수 항목만' : 'Essential Only'}
          </button>
          <button onClick={handleAll} className="cookie-btn btn-primary">
            {lang === 'ko' ? '전체 수락' : 'Accept All'}
          </button>
        </div>
      </div>
      
      <style jsx>{`
        .cookie-banner-container {
          position: fixed;
          bottom: 24px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 1000;
          width: calc(100% - 48px);
          max-width: 500px;
          animation: slideUp 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }

        .cookie-banner-content {
          background: rgba(18, 18, 26, 0.85);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 20px;
          padding: 20px;
          display: flex;
          align-items: center;
          gap: 16px;
          box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), 
                      0 0 20px rgba(167, 139, 250, 0.1);
        }

        .cookie-banner-icon {
          font-size: 24px;
          background: rgba(255, 255, 255, 0.05);
          width: 48px;
          height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 14px;
        }

        .cookie-banner-text {
          flex: 1;
        }

        .cookie-title {
          font-size: 14px;
          font-weight: 700;
          color: #f0f0f5;
          margin-bottom: 2px;
        }

        .cookie-desc {
          font-size: 13px;
          color: #a0a0b8;
          line-height: 1.4;
        }

        .cookie-banner-actions {
          display: flex;
          gap: 8px;
        }

        .cookie-btn {
          padding: 8px 16px;
          border-radius: 10px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          border: 1px solid transparent;
        }

        .btn-primary {
          background: #ffffff;
          color: #000000;
        }

        .btn-primary:hover {
          transform: scale(1.05);
          box-shadow: 0 0 15px rgba(255, 255, 255, 0.3);
        }

        .btn-secondary {
          background: rgba(255, 255, 255, 0.05);
          color: #a0a0b8;
          border-color: rgba(255, 255, 255, 0.1);
        }

        .btn-secondary:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #f0f0f5;
        }

        @keyframes slideUp {
          from {
            transform: translate(-50%, 100%) scale(0.9);
            opacity: 0;
          }
          to {
            transform: translate(-50%, 0) scale(1);
            opacity: 1;
          }
        }

        @media (max-width: 480px) {
          .cookie-banner-content {
            flex-direction: column;
            text-align: center;
            padding: 24px;
          }
          .cookie-banner-actions {
            width: 100%;
            margin-top: 12px;
          }
          .cookie-btn {
            flex: 1;
          }
        }
      `}</style>
    </div>
  );
}
