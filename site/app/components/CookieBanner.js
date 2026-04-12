"use client";
import { useState, useEffect } from "react";
import { useLanguage } from "./LanguageProvider";

export default function CookieBanner() {
  const [showBanner, setShowBanner] = useState(false);
  const { lang, t } = useLanguage();

  useEffect(() => {
    // Check if user has already made a choice
    const consent = localStorage.getItem("cookie-consent");
    if (!consent) {
      // Small delay for entrance animation
      const timer = setTimeout(() => setShowBanner(true), 1200);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem("cookie-consent", "granted");
    
    // Update GA4 consent state
    if (typeof window !== "undefined" && window.gtag) {
      window.gtag('consent', 'update', {
        'analytics_storage': 'granted',
        'ad_storage': 'granted'
      });
    }
    
    setShowBanner(false);
  };

  const handleDecline = () => {
    localStorage.setItem("cookie-consent", "denied");
    setShowBanner(false);
  };

  if (!showBanner) return null;

  return (
    <div className="cookie-banner-container">
      <div className="cookie-banner-content">
        <div className="cookie-banner-icon">🍪</div>
        <div className="cookie-banner-text">
          <p className="cookie-title">
            {lang === 'ko' ? '쿠키 사용 안내' : 'Cookie Policy'}
          </p>
          <p className="cookie-desc">
            {lang === 'ko' 
              ? '더 나은 연구 분석을 위해 익명의 사용자 데이터를 수집합니다. 동의하시나요?' 
              : 'We use cookies to analyze site traffic and improve your research experience.'}
          </p>
        </div>
        <div className="cookie-banner-actions">
          <button onClick={handleDecline} className="cookie-btn btn-secondary">
            {lang === 'ko' ? '거절' : 'Decline'}
          </button>
          <button onClick={handleAccept} className="cookie-btn btn-primary">
            {lang === 'ko' ? '수락' : 'Accept'}
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
