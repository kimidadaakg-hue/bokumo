import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BOKUMO | 子供と楽しむ、おいしい時間",
  description:
    "北海道の子連れ歓迎飲食店まとめサイト。ベビーカーOK・個室・キッズメニューで絞り込みできます。",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#FCD5CE",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="font-sans">{children}</body>
    </html>
  );
}
