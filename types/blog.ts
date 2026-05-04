export interface BlogFilter {
  areas?: string[];
  genres?: string[];
  tags?: string[];
  limit?: number;
  sortBy?: "priority" | "rating" | "score";
}

export interface BlogPost {
  slug: string;
  title: string;
  description: string;
  intro: string;
  filter: BlogFilter;
  category: string;
  publishedAt: string;
}
