export type Area = string;

export type Genre = string;

export const ALL_TAGS = [
  "子連れOK",
  "座敷/小上がりあり",
  "キッズチェアあり",
  "個室あり",
  "子供メニューあり"
] as const;

export type Tag = (typeof ALL_TAGS)[number];

export interface Shop {
  id: number;
  name: string;
  area: string;
  genre: Genre;
  tags: string[];
  description: string;
  score: number;
  lat: number;
  lng: number;
  tabelog_url: string;
  image_url: string;
  is_chain: boolean;
  evidence: string[];
  source: string;
  hotpepper_url: string;
}
