import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "BOKUMOについて | BOKUMO",
  description: "BOKUMO（ボクモ）は北海道の子連れ歓迎飲食店ガイドです。サイトの運営方針と掲載基準について。",
};

export default function AboutPage() {
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
          {/* ロゴ */}
          <div className="text-center mb-8">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/logo.png"
              alt="BOKUMO"
              className="mx-auto h-20 mb-4 object-contain"
            />
            <h1
              className="text-2xl md:text-3xl text-bokumo-ink font-bold"
              style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
            >
              BOKUMOについて
            </h1>
            <p className="mt-2 text-sm text-bokumo-sub">
              ボクモ ・ 子供と楽しむ、おいしい時間
            </p>
          </div>

          <div className="space-y-8 text-sm text-bokumo-ink/80 leading-relaxed">
            {/* コンセプト */}
            <section>
              <h2
                className="text-base font-bold text-bokumo-ink mb-3"
                style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
              >
                BOKUMOとは
              </h2>
              <p>
                BOKUMO（ボクモ）は、北海道の「子連れで行ける飲食店」をまとめたガイドサイトです。
              </p>
              <p className="mt-2">
                小さなお子様がいると「このお店、子供連れて行っても大丈夫かな？」と不安になることがありますよね。座敷はある？ベビーカーは入れる？子供用のメニューはある？——そんな疑問に応えるために、BOKUMOは生まれました。
              </p>
              <p className="mt-2">
                サイト名の由来は、お子様の「ぼくも連れてって！」という声。家族みんなで、おいしい時間を過ごせるお店を見つけるお手伝いをします。
              </p>
            </section>

            {/* 掲載基準 */}
            <section>
              <h2
                className="text-base font-bold text-bokumo-ink mb-3"
                style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
              >
                掲載基準
              </h2>
              <p>
                BOKUMOに掲載するお店は、以下の基準で選定しています。
              </p>
              <ul className="mt-3 space-y-2 pl-4">
                <li className="flex items-start gap-2">
                  <span className="text-bokumo-accent mt-0.5">●</span>
                  <span>実際の口コミで「子連れで利用した」という実績があること</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-bokumo-accent mt-0.5">●</span>
                  <span>座敷・個室・キッズチェアなど、子連れ向けの設備情報が確認できること</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-bokumo-accent mt-0.5">●</span>
                  <span>公式サイトやSNSで子連れ歓迎の姿勢が確認できること</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-bokumo-accent mt-0.5">●</span>
                  <span>「子連れお断り」など、明確にお断りしている店舗は掲載しません</span>
                </li>
              </ul>
            </section>

            {/* タグの説明 */}
            <section>
              <h2
                className="text-base font-bold text-bokumo-ink mb-3"
                style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
              >
                タグについて
              </h2>
              <p className="mb-3">
                各お店には、確認できた情報に基づいてタグを付けています。
              </p>
              <div className="bg-bokumo-bg rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-bokumo-pink-light border border-bokumo-line text-bokumo-ink/70">子連れOK</span>
                  <span className="text-xs text-bokumo-ink/60">口コミやサイトで子連れ利用の実績が確認できるお店</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-bokumo-pink-light border border-bokumo-line text-bokumo-ink/70">個室あり</span>
                  <span className="text-xs text-bokumo-ink/60">個室または半個室があるお店</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-bokumo-pink-light border border-bokumo-line text-bokumo-ink/70">座敷/小上がりあり</span>
                  <span className="text-xs text-bokumo-ink/60">座敷・小上がり・掘りごたつがあるお店</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-bokumo-pink-light border border-bokumo-line text-bokumo-ink/70">キッズチェアあり</span>
                  <span className="text-xs text-bokumo-ink/60">子供用の椅子があるお店</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-bokumo-pink-light border border-bokumo-line text-bokumo-ink/70">子供メニューあり</span>
                  <span className="text-xs text-bokumo-ink/60">お子様メニューやキッズメニューがあるお店</span>
                </div>
              </div>
            </section>

            {/* 情報提供のお願い */}
            <section className="bg-bokumo-pink-light/50 rounded-xl p-6">
              <h2
                className="text-base font-bold text-bokumo-ink mb-2"
                style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
              >
                情報提供のお願い
              </h2>
              <p>
                BOKUMOでは、子連れにおすすめのお店の情報を募集しています。「このお店が子連れで良かった！」という情報があれば、ぜひ教えてください。
              </p>
              <p className="mt-2">
                また、掲載情報に誤りがある場合も、お気軽にご連絡ください。
              </p>
              <div className="mt-4 flex flex-col sm:flex-row gap-3">
                <a
                  href="https://docs.google.com/forms/d/e/1FAIpQLSdG-VGN1WEj53rtg9OkX0ehH88nGK3ZKJPkOnfq174kyeUQOA/viewform"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center justify-center px-6 py-2.5 text-sm rounded-full bg-bokumo-accent text-white hover:opacity-90 transition font-bold"
                >
                  お店を提案する →
                </a>
                <Link
                  href="/contact"
                  className="inline-flex items-center justify-center px-6 py-2.5 text-sm rounded-full bg-white text-bokumo-ink border border-bokumo-line hover:border-bokumo-accent hover:text-bokumo-accent transition font-bold"
                >
                  お問い合わせ →
                </Link>
              </div>
            </section>

            {/* 運営者情報 */}
            <section>
              <h2
                className="text-base font-bold text-bokumo-ink mb-3"
                style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
              >
                運営者情報
              </h2>
              <div className="bg-bokumo-bg rounded-lg p-4">
                <dl className="space-y-2 text-sm">
                  <div className="flex gap-4">
                    <dt className="text-bokumo-sub w-24 shrink-0">サイト名</dt>
                    <dd className="text-bokumo-ink">BOKUMO（ボクモ）</dd>
                  </div>
                  <div className="flex gap-4">
                    <dt className="text-bokumo-sub w-24 shrink-0">URL</dt>
                    <dd className="text-bokumo-ink">https://boku-mo.com</dd>
                  </div>
                  <div className="flex gap-4">
                    <dt className="text-bokumo-sub w-24 shrink-0">お問い合わせ</dt>
                    <dd>
                      <Link href="/contact" className="text-bokumo-accent hover:underline">
                        お問い合わせページ
                      </Link>
                    </dd>
                  </div>
                </dl>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
