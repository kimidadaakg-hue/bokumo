import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "お問い合わせ | BOKUMO",
  description: "BOKUMO（ボクモ）へのお問い合わせ。お店の提案や口コミの投稿もこちらから。",
};

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-bokumo-bg">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <Link
          href="/"
          className="inline-flex items-center text-sm text-bokumo-sub hover:text-bokumo-accent transition mb-8"
        >
          ← トップに戻る
        </Link>

        <div className="bg-white rounded-2xl shadow-card border border-bokumo-line/50 p-6 md:p-10">
          <h1
            className="text-2xl md:text-3xl text-bokumo-ink font-bold mb-4"
            style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
          >
            お問い合わせ
          </h1>
          <p className="text-sm text-bokumo-ink/70 mb-8">
            BOKUMOに関するお問い合わせは、以下のフォームよりお気軽にご連絡ください。
          </p>

          <div className="space-y-6">
            {/* お問い合わせ */}
            <div className="bg-bokumo-bg rounded-xl p-6">
              <h2
                className="text-base font-bold text-bokumo-ink mb-2"
                style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
              >
                一般的なお問い合わせ
              </h2>
              <p className="text-sm text-bokumo-ink/70 mb-4">
                サイトに関するご質問、掲載情報の修正依頼、その他ご意見など。
              </p>
              <a
                href="https://docs.google.com/forms/d/e/1FAIpQLSdG-VGN1WEj53rtg9OkX0ehH88nGK3ZKJPkOnfq174kyeUQOA/viewform"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-6 py-2.5 text-sm rounded-full bg-bokumo-accent text-white hover:opacity-90 transition font-bold"
              >
                お問い合わせフォームへ →
              </a>
            </div>

            {/* お店の提案 */}
            <div className="bg-bokumo-pink-light/50 rounded-xl p-6">
              <h2
                className="text-base font-bold text-bokumo-ink mb-2"
                style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
              >
                子連れにおすすめのお店を教える
              </h2>
              <p className="text-sm text-bokumo-ink/70 mb-4">
                あなたの知っている子連れに優しいお店を教えてください。確認後、サイトに掲載させていただきます。
              </p>
              <a
                href="https://docs.google.com/forms/d/e/1FAIpQLSdG-VGN1WEj53rtg9OkX0ehH88nGK3ZKJPkOnfq174kyeUQOA/viewform"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-6 py-2.5 text-sm rounded-full bg-bokumo-accent text-white hover:opacity-90 transition font-bold"
              >
                お店を提案する →
              </a>
            </div>

            {/* 口コミ */}
            <div className="bg-bokumo-pink-light/50 rounded-xl p-6">
              <h2
                className="text-base font-bold text-bokumo-ink mb-2"
                style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
              >
                口コミ・写真を送る
              </h2>
              <p className="text-sm text-bokumo-ink/70 mb-4">
                掲載中のお店について、実際に行った感想や写真を送ってください。
              </p>
              <a
                href="https://docs.google.com/forms/d/e/1FAIpQLSfhF2zUpZVfjcUQu-NQaFqraAi7UwNQ8CMc_U8rD-CnDFVPnA/viewform"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-6 py-2.5 text-sm rounded-full bg-white text-bokumo-ink border border-bokumo-line hover:border-bokumo-accent hover:text-bokumo-accent transition font-bold"
              >
                口コミを送る →
              </a>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
