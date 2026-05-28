/**
 * Hook for drag-to-resize panels.
 * Returns the current size and props to spread on the resize handle element.
 */

import { useCallback, useEffect, useRef, useState } from "react";

type Direction = "horizontal" | "vertical";

interface UseResizeOptions {
  direction: Direction;
  initialSize: number;
  minSize: number;
  maxSize: number;
  /** If true, dragging right/down *decreases* the size (used for right panel). */
  reverse?: boolean;
}

export function useResize({
  direction,
  initialSize,
  minSize,
  maxSize,
  reverse = false,
}: UseResizeOptions) {
  const [size, setSize] = useState(initialSize);
  const dragging = useRef(false);
  const startPos = useRef(0);
  const startSize = useRef(0);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      startPos.current = direction === "horizontal" ? e.clientX : e.clientY;
      startSize.current = size;
      document.body.style.cursor = direction === "horizontal" ? "col-resize" : "row-resize";
      document.body.style.userSelect = "none";
    },
    [direction, size],
  );

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const pos = direction === "horizontal" ? e.clientX : e.clientY;
      const delta = pos - startPos.current;
      const newSize = reverse
        ? startSize.current - delta
        : startSize.current + delta;
      setSize(Math.min(maxSize, Math.max(minSize, newSize)));
    };

    const onMouseUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [direction, minSize, maxSize, reverse]);

  return { size, onMouseDown };
}
