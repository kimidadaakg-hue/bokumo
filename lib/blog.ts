import shopsData from "@/data/shops.json";
import postsData from "@/data/blog_posts.json";
import type { Shop } from "@/types/shop";
import type { BlogPost, BlogFilter } from "@/types/blog";

const shops = shopsData as Shop[];
const posts = postsData as BlogPost[];

function priority(s: Shop): number {
  return (s.tags?.length ?? 0) * 3 + (s.score ?? 0);
}

export function getAllPosts(): BlogPost[] {
  return [...posts].sort((a, b) =>
    b.publishedAt.localeCompare(a.publishedAt)
  );
}

export function getPostBySlug(slug: string): BlogPost | undefined {
  return posts.find((p) => p.slug === slug);
}

export function getShopsForPost(filter: BlogFilter): Shop[] {
  let list = shops.filter((s) => {
    if (filter.areas && filter.areas.length > 0 && !filter.areas.includes(s.area)) return false;
    if (filter.genres && filter.genres.length > 0 && !filter.genres.includes(s.genre)) return false;
    if (filter.tags && filter.tags.length > 0) {
      if (!filter.tags.every((t) => s.tags.includes(t))) return false;
    }
    return true;
  });

  const sortBy = filter.sortBy ?? "priority";
  if (sortBy === "rating") {
    list.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
  } else if (sortBy === "score") {
    list.sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  } else {
    list.sort((a, b) => priority(b) - priority(a));
  }

  return list.slice(0, filter.limit ?? 10);
}
