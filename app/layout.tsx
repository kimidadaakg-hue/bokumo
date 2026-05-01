import type { Metadata, Viewport } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "BOKUMO（ボクモ / ぼくも）| 北海道の子連れ歓迎飲食店ガイド",
  description:
    "BOKUMO（ボクモ・ぼくも）は北海道の子連れ歓迎飲食店まとめサイト。札幌・旭川・函館など全道602店。ベビーカーOK・個室・座敷・キッズメニューで絞り込みできます。子供と楽しむ、おいしい時間。",
  keywords: ["BOKUMO", "ボクモ", "ぼくも", "北海道", "子連れ", "飲食店", "レストラン", "キッズ", "ベビーカー", "個室", "札幌", "子供"],
  openGraph: {
    title: "BOKUMO（ボクモ）| 北海道の子連れ歓迎飲食店ガイド",
    description: "北海道の子連れで行ける飲食店602店をまとめました。ベビーカーOK・個室・キッズメニューで検索できます。",
    url: "https://boku-mo.com",
    siteName: "BOKUMO（ボクモ）",
    locale: "ja_JP",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "BOKUMO（ボクモ）| 北海道の子連れ歓迎飲食店ガイド",
    description: "北海道の子連れで行ける飲食店602店をまとめました。",
  },
  alternates: {
    canonical: "https://boku-mo.com",
  },
  verification: {
    google: "8QfIyx_ySpadk-crZDjwnFaSb86ZEC7ecI6wMOEW61k",
    other: {
      "google-adsense-account": "ca-pub-6962959386359206",
    },
  },
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
      <head>
        <Script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6962959386359206"
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
        {/* Valuecommerce LinkSwitch (tabelog 等のリンクを自動アフィリエイト化) */}
        <Script id="vc-linkswitch" strategy="afterInteractive">
          {`var vc_pid = "892604880";`}
        </Script>
        <Script
          src="//aml.valuecommerce.com/vcdal.js"
          strategy="afterInteractive"
          async
        />
      </head>
      <body className="font-sans">{children}</body>
    </html>
  );
}
