"use client";

import Masonry from "react-masonry-css";
import type { ReactNode } from "react";

const breakpointColumns = {
  default: 3,  // lg+
  1024: 2,     // sm–lg
  640: 1,      // mobile
};

interface MasonryGridProps {
  children: ReactNode;
}

export function MasonryGrid({ children }: MasonryGridProps) {
  return (
    <Masonry
      breakpointCols={breakpointColumns}
      className="masonry-grid"
      columnClassName="masonry-grid-column"
    >
      {children}
    </Masonry>
  );
}
