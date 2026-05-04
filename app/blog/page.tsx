import type { Metadata } from "next";
import Link from "next/link";
import { getAllPosts } from "@/lib/blog";

export const metadata: Metadata = {
  title: "BOKUMOブログ - 北海道の子連れ飲食店まとめ記事一覧",
  description: "札幌・旭川・函館など、北海道の子連れOKな飲食店をテーマ別に紹介する特集記事一覧。座敷あり、キッズメニュー対応店など、シーン別に厳選しています。",
  alternates: {
    canonical: "https://boku-mo.com/blog",
  },
};

export default function BlogIndexPage() {
  const posts = getAllPosts();
  const categories = Array.from(new Set(posts.map((p) => p.category)));

  return (
    <main className="min-h-screen bg-bokumo-bg">
      <div className="max-w-4xl mx-auto px-6 py-10">
        <Link
          href="/"
          className="inline-flex items-center text-sm text-bokumo-sub hover:text-bokumo-accent transition mb-8"
        >
          ← トップに戻る
        </Link>

        <header className="text-center mb-10">
          <p className="text-xs tracking-[0.4em] text-bokumo-sub">BOKUMO BLOG</p>
          <h1 className="mt-3 text-3xl md:text-4xl text-bokumo-ink font-bold" style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}>
            北海道の子連れ飲食店まとめ記事
          </h1>
          <p className="mt-3 text-sm text-bokumo-sub">
            エリア別・設備別の特集記事
          </p>
        </header>

        {categories.map((cat) => {
          const inCat = posts.filter((p) => p.category === cat);
          return (
            <section key={cat} className="mb-10">
              <h2 className="text-base font-bold text-bokumo-accent mb-4 pb-2 border-b border-bokumo-line">
                {cat}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {inCat.map((p) => (
                  <Link
                    key={p.slug}
                    href={`/blog/${p.slug}`}
                    className="block bg-white rounded-2xl shadow-card border border-bokumo-line/50 p-5 hover:border-bokumo-accent transition"
                  >
                    <h3 className="text-base font-bold text-bokumo-ink mb-2 line-clamp-2" style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}>
                      {p.title}
                    </h3>
                    <p className="text-xs text-bokumo-ink/70 line-clamp-3 leading-relaxed">
                      {p.description}
                    </p>
                    <p className="text-xs text-bokumo-sub mt-3">
                      {p.publishedAt}
                    </p>
                  </Link>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </main>
  );
}
