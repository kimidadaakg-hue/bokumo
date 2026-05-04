"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import shopsData from "@/data/shops.json";
import postsData from "@/data/blog_posts.json";
import type { Shop } from "@/types/shop";
import type { BlogPost } from "@/types/blog";
import ShopCard from "@/components/ShopCard";
import FilterBar from "@/components/FilterBar";
import RegionSelector, { getAreasForRegion } from "@/components/RegionSelector";

const shops = shopsData as Shop[];
const posts = (postsData as BlogPost[])
  .slice()
  .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
const PAGE_SIZE = 30;

export default function HomePage() {
  const [region, setRegion] = useState("すべて");
  const [subRegion, setSubRegion] = useState("");
  const [microRegion, setMicroRegion] = useState("");
  const [genre, setGenre] = useState("すべて");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const toggleTag = (t: string) => {
    setSelectedTags((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
    setPage(1);
  };
  const handleGenre = (g: string) => { setGenre(g); setPage(1); };
  const handleRegion = (r: string) => { setRegion(r); setPage(1); };
  const handleSubRegion = (r: string) => { setSubRegion(r); setPage(1); };
  const handleMicroRegion = (r: string) => { setMicroRegion(r); setPage(1); };
  const handleQuery = (q: string) => { setQuery(q); setPage(1); };

  const filtered = useMemo(() => {
    const allowedAreas = getAreasForRegion(region, subRegion, microRegion);
    const q = query.trim().toLowerCase();

    return shops.filter((s) => {
      // 地域フィルタ
      if (allowedAreas && !allowedAreas.includes(s.area)) return false;
      // ジャンル
      if (genre !== "すべて" && s.genre !== genre) return false;
      // タグ
      if (selectedTags.length > 0 && !selectedTags.every((t) => s.tags.includes(t)))
        return false;
      // 店名検索 (大文字小文字無視・部分一致)
      if (q && !s.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [region, subRegion, microRegion, genre, selectedTags, query]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // 選択中エリアのラベル
  const areaLabel = microRegion
    ? microRegion
    : subRegion
    ? subRegion
    : region !== "すべて"
    ? region
    : "北海道";

  return (
    <main className="min-h-screen bg-bokumo-bg">
      {/* Hero */}
      <header className="max-w-6xl mx-auto px-6 pt-16 pb-8 text-center">
        <p className="text-xs tracking-[0.4em] text-bokumo-sub">HOKKAIDO</p>
        <h1 className="mt-3 text-5xl md:text-7xl text-bokumo-ink tracking-wide font-extrabold" style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}>
          BOKUMO
        </h1>
        <p className="mt-1 text-xs text-bokumo-sub/60">ボクモ / ぼくも</p>
        <p className="mt-2 text-sm text-bokumo-sub" style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}>
          子供と楽しむ、おいしい時間
        </p>
        <p className="mt-3 text-sm md:text-base text-bokumo-ink/60">
          北海道の、子連れでゆっくり過ごせる飲食店まとめ。
        </p>

        {/* 店名検索 (Hero内に大きく配置) */}
        <div className="mt-7 max-w-xl mx-auto">
          <div className="relative">
            <input
              type="search"
              inputMode="search"
              placeholder="店名で検索"
              value={query}
              onChange={(e) => handleQuery(e.target.value)}
              className="w-full pl-12 pr-12 py-3.5 text-sm md:text-base rounded-full bg-white border-2 border-bokumo-line focus:border-bokumo-accent focus:outline-none transition shadow-card"
              aria-label="店名で検索"
            />
            <svg
              className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-bokumo-sub"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4.3-4.3" />
            </svg>
            {query && (
              <button
                type="button"
                onClick={() => handleQuery("")}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-bokumo-sub hover:text-bokumo-accent transition text-lg"
                aria-label="クリア"
              >
                ×
              </button>
            )}
          </div>
        </div>
      </header>

      {/* 募集中バナー (コンパクト化) */}
      <section className="max-w-6xl mx-auto px-6 pb-8">
        <div className="bg-gradient-to-r from-bokumo-pink to-bokumo-pink-light rounded-2xl px-4 py-4 md:px-6 md:py-6 text-center shadow-card border border-bokumo-line/60">
          <p className="inline-block text-[10px] tracking-[0.25em] text-bokumo-accent font-bold mb-2 px-3 py-0.5 rounded-full bg-white">
            WANTED
          </p>
          <p className="text-sm md:text-lg text-bokumo-ink font-bold mb-1" style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}>
            子連れにおすすめのお店を募集中！
          </p>
          <p className="hidden md:block text-xs md:text-sm text-bokumo-ink/70 mb-4">
            あなたの知ってる素敵なお店を教えてください。確認後、サイトに掲載させていただきます。
          </p>
          <div className="flex flex-row items-center justify-center gap-2 md:gap-3 mt-3 md:mt-0">
            <a
              href="https://docs.google.com/forms/d/e/1FAIpQLSdG-VGN1WEj53rtg9OkX0ehH88nGK3ZKJPkOnfq174kyeUQOA/viewform"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 sm:flex-none px-4 md:px-6 py-2 md:py-2.5 text-xs md:text-sm rounded-full bg-bokumo-accent text-white hover:opacity-90 transition shadow-sm font-bold whitespace-nowrap"
            >
              お店を提案
            </a>
            <a
              href="https://docs.google.com/forms/d/e/1FAIpQLSfhF2zUpZVfjcUQu-NQaFqraAi7UwNQ8CMc_U8rD-CnDFVPnA/viewform"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 sm:flex-none px-4 md:px-6 py-2 md:py-2.5 text-xs md:text-sm rounded-full bg-white text-bokumo-ink hover:bg-bokumo-ink hover:text-white transition shadow-sm font-bold whitespace-nowrap"
            >
              口コミを送る
            </a>
          </div>
        </div>
      </section>

      {/* 特集記事 (コンパクト版) */}
      {posts.length > 0 && (
        <section className="max-w-6xl mx-auto px-6 pb-6">
          <div className="flex items-center justify-between mb-2">
            <h2
              className="text-sm font-bold text-bokumo-ink"
              style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}
            >
              <span className="text-bokumo-accent">★</span> 特集記事
            </h2>
            <Link
              href="/blog"
              className="text-xs text-bokumo-accent hover:underline font-bold"
            >
              一覧を見る →
            </Link>
          </div>
          <div className="flex flex-wrap gap-2">
            {posts.slice(0, 4).map((p) => (
              <Link
                key={p.slug}
                href={`/blog/${p.slug}`}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-xs rounded-full bg-white border border-bokumo-line hover:border-bokumo-accent hover:text-bokumo-accent transition"
              >
                <span className="text-[10px] text-bokumo-accent font-bold">{p.category}</span>
                <span className="text-bokumo-ink">{p.title}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* 地域セレクター (3階層) */}
      <RegionSelector
        shops={shops}
        region={region}
        subRegion={subRegion}
        microRegion={microRegion}
        setRegion={handleRegion}
        setSubRegion={handleSubRegion}
        setMicroRegion={handleMicroRegion}
      />

      {/* ジャンル・タグフィルター */}
      <FilterBar
        genre={genre}
        setGenre={handleGenre}
        selectedTags={selectedTags}
        toggleTag={toggleTag}
        resultCount={filtered.length}
      />

      {/* カード一覧 */}
      <section className="max-w-6xl mx-auto px-6 py-10">
        <div className="mb-6">
          <h2 className="font-serif text-2xl text-bokumo-ink">{areaLabel}</h2>
          <p className="text-xs text-bokumo-sub mt-1">{filtered.length} 件のお店</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          {paged.map((s) => (
            <ShopCard key={s.id} shop={s} />
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full text-center text-bokumo-sub py-20 text-sm">
              条件に合うお店が見つかりませんでした。
            </div>
          )}
        </div>

        {/* ページネーション */}
        {totalPages > 1 && (
          <div className="mt-10 flex items-center justify-center gap-2">
            <button
              onClick={() => { setPage((p) => Math.max(1, p - 1)); window.scrollTo({ top: 0, behavior: "smooth" }); }}
              disabled={page === 1}
              className="px-4 py-2 text-sm rounded-full border border-bokumo-line text-bokumo-ink disabled:opacity-30 hover:border-bokumo-accent hover:text-bokumo-accent transition"
            >
              ← 前
            </button>
            <span className="text-sm text-bokumo-sub px-4">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => { setPage((p) => Math.min(totalPages, p + 1)); window.scrollTo({ top: 0, behavior: "smooth" }); }}
              disabled={page === totalPages}
              className="px-4 py-2 text-sm rounded-full border border-bokumo-line text-bokumo-ink disabled:opacity-30 hover:border-bokumo-accent hover:text-bokumo-accent transition"
            >
              次 →
            </button>
          </div>
        )}
      </section>

      <footer className="bg-bokumo-pink mt-10">
        <div className="max-w-6xl mx-auto px-6 py-10 text-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="BOKUMO" className="mx-auto h-20 mb-5 object-contain" />
          <div className="mb-6">
            <p className="text-sm text-bokumo-ink mb-3">
              子連れにおすすめのお店を教えてください
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <a
                href="https://docs.google.com/forms/d/e/1FAIpQLSdG-VGN1WEj53rtg9OkX0ehH88nGK3ZKJPkOnfq174kyeUQOA/viewform"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-2.5 text-sm rounded-full bg-bokumo-accent text-white hover:opacity-90 transition shadow-sm"
              >
                お店を提案する
              </a>
              <a
                href="https://docs.google.com/forms/d/e/1FAIpQLSfhF2zUpZVfjcUQu-NQaFqraAi7UwNQ8CMc_U8rD-CnDFVPnA/viewform"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-2.5 text-sm rounded-full bg-white text-bokumo-ink hover:bg-bokumo-accent hover:text-white transition shadow-sm"
              >
                口コミ・写真を送る
              </a>
            </div>
          </div>

          {/* SNSリンク */}
          <div className="mb-6">
            <p className="text-xs text-bokumo-ink/70 mb-3">毎日3店舗を投稿中、フォローしてね！</p>
            <div className="flex items-center justify-center gap-3">
              <a
                href="https://www.instagram.com/bokumo2026/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-5 py-2.5 text-sm rounded-full bg-white border border-bokumo-line hover:border-bokumo-accent hover:text-bokumo-accent transition shadow-sm"
                aria-label="Instagram @bokumo2026"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 2.16c3.2 0 3.58.01 4.85.07 1.17.05 1.81.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.25 1.81-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-1.17-.05-1.81-.25-2.23-.41a3.81 3.81 0 0 1-1.38-.9 3.81 3.81 0 0 1-.9-1.38c-.16-.42-.36-1.06-.41-2.23C2.17 15.58 2.16 15.2 2.16 12s.01-3.58.07-4.85c.05-1.17.25-1.81.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.42 2.17 8.8 2.16 12 2.16M12 0C8.74 0 8.33.01 7.05.07 5.78.13 4.9.33 4.14.63A5.97 5.97 0 0 0 1.97 1.97 5.97 5.97 0 0 0 .63 4.14C.33 4.9.13 5.78.07 7.05.01 8.33 0 8.74 0 12s.01 3.67.07 4.95c.06 1.27.26 2.15.56 2.91.31.79.73 1.46 1.34 2.07.61.61 1.28 1.03 2.07 1.34.76.3 1.64.5 2.91.56C8.33 23.99 8.74 24 12 24s3.67-.01 4.95-.07c1.27-.06 2.15-.26 2.91-.56a5.97 5.97 0 0 0 2.07-1.34 5.97 5.97 0 0 0 1.34-2.07c.3-.76.5-1.64.56-2.91.06-1.28.07-1.69.07-4.95s-.01-3.67-.07-4.95c-.06-1.27-.26-2.15-.56-2.91a5.97 5.97 0 0 0-1.34-2.07A5.97 5.97 0 0 0 19.86.63C19.1.33 18.22.13 16.95.07 15.67.01 15.26 0 12 0Zm0 5.84a6.16 6.16 0 1 0 0 12.32 6.16 6.16 0 0 0 0-12.32ZM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm6.4-11.84a1.44 1.44 0 1 0 0 2.88 1.44 1.44 0 0 0 0-2.88Z"/>
                </svg>
                <span className="font-bold">Instagram</span>
              </a>
              <a
                href="https://www.tiktok.com/@bokumo"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-5 py-2.5 text-sm rounded-full bg-white border border-bokumo-line hover:border-bokumo-accent hover:text-bokumo-accent transition shadow-sm"
                aria-label="TikTok @bokumo"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5.8 20.1a6.34 6.34 0 0 0 10.86-4.43V8.91a8.16 8.16 0 0 0 4.77 1.52V7a4.85 4.85 0 0 1-1.84-.31Z"/>
                </svg>
                <span className="font-bold">TikTok</span>
              </a>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-bokumo-ink/50 mb-3">
            <a href="/blog" className="hover:text-bokumo-accent transition">特集記事</a>
            <span>|</span>
            <a href="/about" className="hover:text-bokumo-accent transition">BOKUMOについて</a>
            <span>|</span>
            <a href="/contact" className="hover:text-bokumo-accent transition">お問い合わせ</a>
            <span>|</span>
            <a href="/privacy" className="hover:text-bokumo-accent transition">プライバシーポリシー</a>
          </div>
          <p className="text-xs text-bokumo-ink/50 mb-2">
            当サイトは Google AdSense および Valuecommerce 等のアフィリエイトプログラムを利用しています
          </p>
          <p className="text-xs text-bokumo-ink/50">
            © BOKUMO ・ 北海道の子連れ歓迎店ガイド
          </p>
        </div>
      </footer>
    </main>
  );
}
