import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '赛博财神爷',
  description: '你的AI财务顾问',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        {children}
      </body>
    </html>
  );
}
