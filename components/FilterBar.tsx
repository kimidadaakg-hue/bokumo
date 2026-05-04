"use client";

import { ALL_TAGS } from "@/types/shop";

const GENRES = [
  "すべて",
  "ラーメン",
  "寿司",
  "焼肉",
  "焼鳥",
  "居酒屋",
  "和食",
  "うどん・そば",
  "カレー",
  "中華",
  "韓国",
  "アジア",
  "イタリアン",
  "フレンチ",
  "洋食",
  "ステーキ",
  "ハンバーガー",
  "カフェ",
  "ベーカリー",
  "ファミレス",
  "その他",
] as const;

interface Props {
  genre: string;
  setGenre: (g: string) => void;
  selectedTags: string[];
  toggleTag: (t: string) => void;
  resultCount: number;
}

export default function FilterBar({
  genre,
  setGenre,
  selectedTags,
  toggleTag,
  resultCount
}: Props) {
  return (
    <section className="border-y border-bokumo-line bg-white">
      <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 md:py-6">
        <div className="flex flex-wrap items-center gap-1.5 md:gap-2">
          <span className="text-[10px] md:text-xs tracking-widest text-bokumo-sub mr-1 md:mr-2">GENRE</span>
          {GENRES.map((g) => (
            <button
              key={g}
              onClick={() => setGenre(g)}
              className={`px-2.5 md:px-4 py-1 md:py-1.5 text-xs md:text-sm rounded-full border transition ${
                genre === g
                  ? "bg-bokumo-accent text-white border-bokumo-accent"
                  : "border-bokumo-line text-bokumo-ink hover:border-bokumo-accent"
              }`}
            >
              {g}
            </button>
          ))}
        </div>

        <div className="mt-2 md:mt-4 flex flex-wrap items-center gap-1.5 md:gap-2">
          <span className="text-[10px] md:text-xs tracking-widest text-bokumo-sub mr-1 md:mr-2">TAG</span>
          {ALL_TAGS.map((t) => {
            const on = selectedTags.includes(t);
            return (
              <button
                key={t}
                onClick={() => toggleTag(t)}
                className={`px-2 md:px-3 py-0.5 md:py-1 text-[10px] md:text-xs rounded-full border transition ${
                  on
                    ? "bg-bokumo-accent text-white border-bokumo-accent"
                    : "border-bokumo-line text-bokumo-sub hover:border-bokumo-accent hover:text-bokumo-accent"
                }`}
              >
                {t}
              </button>
            );
          })}
        </div>

        <div className="mt-3 md:mt-4 text-[10px] md:text-xs text-bokumo-sub">{resultCount} 件のお店</div>
      </div>
    </section>
  );
}
