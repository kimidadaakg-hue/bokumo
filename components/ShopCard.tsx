"use client";

import type { Shop } from "@/types/shop";

function Stars({ score }: { score: number }) {
  return (
    <span className="text-bokumo-accent tracking-tight" aria-label={`子連れ安心度 ${score}`}>
      {"★".repeat(score)}
      <span className="text-bokumo-line">{"★".repeat(5 - score)}</span>
    </span>
  );
}

const NEGATIVE_WORDS = [
  // 子連れ系ネガティブ
  "不向き", "遠慮", "お断り", "難しそう",
  // 設備・環境
  "狭い", "激狭", "窮屈", "汚い", "汚れ", "不衛生", "臭い", "暑い", "寒い",
  "うるさい", "騒がしい", "怖い",
  // サービス
  "気分が悪", "ひどく", "ひどい", "ぶっきらぼう", "無愛想", "態度が悪",
  "対応が悪", "接客が悪", "感じが悪", "不親切", "失礼",
  // 味・品質
  "まずい", "不味い", "しょっぱ", "しつこい", "冷たい", "ぬるい",
  // 総合評価
  "残念", "ガッカリ", "がっかり", "期待はずれ", "期待外れ",
  "おすすめできません", "オススメできません", "おすすめしない",
  "回転が悪", "待たされ", "遅い", "遅すぎ",
  "不十分", "不満", "最悪", "二度と", "行かない",
  "高い", "高すぎ", "コスパが悪", "割高", "ぼったくり",
];

function filterPositive(evs: string[]): string[] {
  return evs.filter((ev) => !NEGATIVE_WORDS.some((ng) => ev.includes(ng)));
}

export default function ShopCard({ shop }: { shop: Shop }) {
  const rawEvidence = (shop as any).evidence as string[] | undefined;
  const evidence = rawEvidence ? filterPositive(rawEvidence) : undefined;

  return (
    <article className="card-hover bg-white rounded-2xl overflow-hidden shadow-card border border-bokumo-line/50">
      {shop.image_url && (
        <div className="aspect-[4/3] bg-bokumo-pink-light overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={shop.image_url}
            alt={shop.name}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        </div>
      )}
      <div className="p-5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-bokumo-sub tracking-widest">
            {shop.area} ・ {shop.genre}
          </span>
          <Stars score={shop.score} />
        </div>
        <h3 className="mt-2 text-lg text-bokumo-ink leading-snug font-bold" style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}>
          {shop.name}
        </h3>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {shop.tags.slice(0, 3).map((t) => (
            <span
              key={t}
              className="text-[11px] px-2.5 py-0.5 rounded-full bg-bokumo-pink-light border border-bokumo-line text-bokumo-ink/70"
            >
              {t}
            </span>
          ))}
        </div>

        {evidence && evidence.length > 0 && (
          <div className="mt-3 bg-bokumo-pink-light/50 rounded-lg px-3 py-2">
            <p className="text-[11px] text-bokumo-accent font-bold mb-1" style={{ fontFamily: "'M PLUS Rounded 1c', sans-serif" }}>
              口コミ
            </p>
            {evidence.slice(0, 2).map((ev, i) => (
              <p key={i} className="text-xs text-bokumo-ink/70 leading-relaxed line-clamp-1">
                「{ev.length > 40 ? ev.slice(0, 40) + "…" : ev}」
              </p>
            ))}
          </div>
        )}

        {shop.description && !evidence?.length && (
          <p className="mt-3 text-sm text-bokumo-sub leading-relaxed line-clamp-2">
            {shop.description}
          </p>
        )}

        <a
          href={shop.tabelog_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-flex items-center justify-center w-full py-2.5 text-sm rounded-full bg-bokumo-accent text-white hover:opacity-90 transition"
        >
          Googleマップで見る →
        </a>
      </div>
    </article>
  );
}
