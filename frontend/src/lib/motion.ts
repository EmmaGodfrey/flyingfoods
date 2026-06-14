/**
 * Shared motion primitives so every feature animates with one vocabulary.
 *
 * Curves mirror the CSS custom easings in styles.css. Order cards use a spring
 * (they should feel alive and survive interruption when the list reorders);
 * page and overlay transitions use tuned ease-out durations under 320ms.
 */

import type { Transition, Variants } from "motion/react";

export const easeOut = [0.23, 1, 0.32, 1] as const;
export const easeInOut = [0.77, 0, 0.175, 1] as const;

/** Apple-style spring: easy to reason about, subtle bounce. */
export const cardSpring: Transition = { type: "spring", duration: 0.45, bounce: 0.18 };

/** List item enter/exit — used with AnimatePresence + layout for reordering. */
export const ticketVariants: Variants = {
  initial: { opacity: 0, scale: 0.95, y: 12 },
  animate: { opacity: 1, scale: 1, y: 0, transition: cardSpring },
  exit: { opacity: 0, scale: 0.96, transition: { duration: 0.18, ease: easeOut } },
};

/** Route / page content fade-up. */
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.24, ease: easeOut } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.16, ease: easeOut } },
};

/** Stagger container for lists that appear together. */
export const staggerParent: Variants = {
  animate: { transition: { staggerChildren: 0.045 } },
};
