"use client";

import { useMemo, useState } from "react";
import shopsData from "@/data/shops.json";
import type { Shop } from "@/types/shop";
import ShopCard from "@/components/ShopCard";
import FilterBar from "@/components/FilterBar";
import RegionSelector, { getAreasForRegion } from "@/components/RegionSelector";

const shops = shopsData as Shop[];
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

      {/* 募集中バナー */}
      <section className="max-w-6xl mx-auto px-6 pb-8">
        <div className="bg-gradient-to-r from-bokumo-pink to-bokumo-pink-light rounded-2xl px-6 py-5 md:py-6 text-center shadow-card border border-bokumo-line/60">
          <p className="inline-block text-[10px] tracking-[0.25em] text-bokumo-accent font-bold mb-2 px-3 py-0.5 rounded-full bg-white">
            WANTED
          </p>
          <p className="text-base md:text-lg text-bokumo-ink font-bold mb-1" style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}>
            子連れにおすすめのお店を募集中！
          </p>
          <p className="text-xs md:text-sm text-bokumo-ink/70 mb-4">
            あなたの知ってる素敵なお店を教えてください。確認後、サイトに掲載させていただきます。
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="https://docs.google.com/forms/d/e/1FAIpQLSdG-VGN1WEj53rtg9OkX0ehH88nGK3ZKJPkOnfq174kyeUQOA/viewform"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto px-6 py-2.5 text-sm rounded-full bg-bokumo-accent text-white hover:opacity-90 transition shadow-sm font-bold"
            >
              お店を提案する →
            </a>
            <a
              href="https://docs.google.com/forms/d/e/1FAIpQLSfhF2zUpZVfjcUQu-NQaFqraAi7UwNQ8CMc_U8rD-CnDFVPnA/viewform"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto px-6 py-2.5 text-sm rounded-full bg-white text-bokumo-ink hover:bg-bokumo-ink hover:text-white transition shadow-sm font-bold"
            >
              口コミを送る →
            </a>
          </div>
        </div>
      </section>

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
