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
      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs tracking-widest text-bokumo-sub mr-2">GENRE</span>
          {GENRES.map((g) => (
            <button
              key={g}
              onClick={() => setGenre(g)}
              className={`px-4 py-1.5 text-sm rounded-full border transition ${
                genre === g
                  ? "bg-bokumo-accent text-white border-bokumo-accent"
                  : "border-bokumo-line text-bokumo-ink hover:border-bokumo-accent"
              }`}
            >
              {g}
            </button>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-xs tracking-widest text-bokumo-sub mr-2">TAG</span>
          {ALL_TAGS.map((t) => {
            const on = selectedTags.includes(t);
            return (
              <button
                key={t}
                onClick={() => toggleTag(t)}
                className={`px-3 py-1 text-xs rounded-full border transition ${
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

        <div className="mt-4 text-xs text-bokumo-sub">{resultCount} 件のお店</div>
      </div>
    </section>
  );
}
