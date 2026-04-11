/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true, // GitHub Pages에서 폴더 구조를 위해 필수
  basePath: '/JournalRadar',
  assetPrefix: '/JournalRadar', // 더 명시적인 에셋 경로
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
