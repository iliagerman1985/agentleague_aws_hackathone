/**
 * Chess-themed background art component
 * Displays subtle chess piece silhouettes and checkered patterns
 */

import React from "react";
import { cn } from "@/lib/utils";

interface ChessBackgroundProps {
  className?: string;
  opacity?: number;
}

export const ChessBackground: React.FC<ChessBackgroundProps> = ({
  className,
  opacity = 0.03
}) => {
  return (
    <div
      className={cn("absolute inset-0 overflow-hidden pointer-events-none min-h-full", className)}
      style={{ opacity }}
    >
      {/* Rich gradient overlay with warm amber and golden tones (toned down) */}
      <div className="absolute inset-0 bg-gradient-to-br from-amber-600/18 via-orange-700/14 to-amber-900/18" />

      {/* Secondary gradient for depth */}
      <div className="absolute inset-0 bg-gradient-to-tr from-yellow-600/10 via-transparent to-amber-800/10" />

      {/* Chess pieces scattered across the background */}
      <svg
        className="absolute inset-0 w-full h-full"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          {/* Define chess piece symbols with board-like palette (dark silhouettes) */}
          <text id="king" fontSize="48" fill="#111827" opacity="0.18">♚</text>
          <text id="queen" fontSize="48" fill="#111827" opacity="0.18">♛</text>
          <text id="rook" fontSize="40" fill="#111827" opacity="0.16">♜</text>
          <text id="bishop" fontSize="40" fill="#111827" opacity="0.16">♝</text>
          <text id="knight" fontSize="40" fill="#111827" opacity="0.16">♞</text>
          <text id="pawn" fontSize="32" fill="#111827" opacity="0.14">♟</text>
        </defs>

        {/* Scatter pieces across the canvas - more pieces, varied positions */}
        {/* Top section */}
        <use href="#king" x="5%" y="8%" />
        <use href="#queen" x="15%" y="12%" />
        <use href="#knight" x="25%" y="6%" />
        <use href="#bishop" x="35%" y="10%" />
        <use href="#rook" x="45%" y="8%" />
        <use href="#pawn" x="55%" y="12%" />
        <use href="#knight" x="65%" y="7%" />
        <use href="#queen" x="75%" y="11%" />
        <use href="#bishop" x="85%" y="9%" />
        <use href="#king" x="95%" y="13%" />

        {/* Upper-middle section */}
        <use href="#pawn" x="8%" y="22%" />
        <use href="#rook" x="18%" y="25%" />
        <use href="#bishop" x="28%" y="20%" />
        <use href="#pawn" x="38%" y="24%" />
        <use href="#knight" x="48%" y="21%" />
        <use href="#queen" x="58%" y="26%" />
        <use href="#pawn" x="68%" y="23%" />
        <use href="#rook" x="78%" y="27%" />
        <use href="#bishop" x="88%" y="22%" />

        {/* Middle section */}
        <use href="#knight" x="3%" y="38%" />
        <use href="#pawn" x="13%" y="42%" />
        <use href="#queen" x="23%" y="36%" />
        <use href="#rook" x="33%" y="40%" />
        <use href="#bishop" x="43%" y="37%" />
        <use href="#pawn" x="53%" y="41%" />
        <use href="#knight" x="63%" y="39%" />
        <use href="#king" x="73%" y="43%" />
        <use href="#rook" x="83%" y="38%" />
        <use href="#pawn" x="93%" y="42%" />

        {/* Lower-middle section */}
        <use href="#bishop" x="10%" y="55%" />
        <use href="#pawn" x="20%" y="58%" />
        <use href="#knight" x="30%" y="53%" />
        <use href="#queen" x="40%" y="57%" />
        <use href="#pawn" x="50%" y="54%" />
        <use href="#rook" x="60%" y="59%" />
        <use href="#bishop" x="70%" y="56%" />
        <use href="#pawn" x="80%" y="52%" />
        <use href="#knight" x="90%" y="58%" />

        {/* Bottom section */}
        <use href="#rook" x="7%" y="70%" />
        <use href="#pawn" x="17%" y="73%" />
        <use href="#bishop" x="27%" y="68%" />
        <use href="#knight" x="37%" y="72%" />
        <use href="#queen" x="47%" y="69%" />
        <use href="#king" x="57%" y="74%" />
        <use href="#pawn" x="67%" y="71%" />
        <use href="#rook" x="77%" y="75%" />
        <use href="#bishop" x="87%" y="70%" />

        {/* Very bottom section */}
        <use href="#pawn" x="12%" y="85%" />
        <use href="#knight" x="22%" y="88%" />
        <use href="#pawn" x="32%" y="83%" />
        <use href="#bishop" x="42%" y="87%" />
        <use href="#rook" x="52%" y="84%" />
        <use href="#pawn" x="62%" y="89%" />
        <use href="#knight" x="72%" y="86%" />
        <use href="#queen" x="82%" y="90%" />
        <use href="#pawn" x="92%" y="85%" />
      </svg>

      {/* Knight piece silhouette - rich amber */}
      <svg
        className="absolute bottom-10 left-10 w-32 h-32 md:w-48 md:h-48 opacity-35"
        viewBox="0 0 45 45"
        fill="#D97706"
      >
        <g fillRule="evenodd" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
          <path d="M22 10c10.5 1 16.5 8 16 29H15c0-9 10-6.5 8-21" fill="#D97706" stroke="#D97706" />
          <path d="M24 18c.38 2.91-5.55 7.37-8 9-3 2-2.82 4.34-5 4-1.042-.94 1.41-3.04 0-3-1 0 .19 1.23-1 2-1 0-4.003 1-4-4 0-2 6-12 6-12s1.89-1.9 2-3.5c-.73-.994-.5-2-.5-3 1-1 3 2.5 3 2.5h2s.78-1.992 2.5-3c1 0 1 3 1 3" fill="#D97706" stroke="#D97706" />
          <path d="M9.5 25.5a.5.5 0 1 1-1 0 .5.5 0 1 1 1 0z" fill="none" stroke="#D97706" />
          <path d="M14.933 15.75a.5 1.5 30 1 1-.866-.5.5 1.5 30 1 1 .866.5z" fill="none" stroke="#D97706" strokeWidth="1.49997" />
        </g>
      </svg>

      {/* Rook piece silhouette - deep brown */}
      <svg
        className="absolute top-20 right-20 w-24 h-24 md:w-36 md:h-36 opacity-28"
        viewBox="0 0 45 45"
        fill="#92400E"
      >
        <g fillRule="evenodd" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
          <path d="M9 39h27v-3H9v3zm3-3v-4h21v4H12zm-1-22V9h4v2h5V9h5v2h5V9h4v5" stroke="#92400E" fill="#92400E" />
          <path d="M34 14l-3 3H14l-3-3" fill="#92400E" stroke="#92400E" />
          <path d="M31 17v12.5H14V17" stroke="#92400E" fill="#92400E" />
          <path d="M31 29.5l1.5 2.5h-20l1.5-2.5" fill="#92400E" stroke="#92400E" />
          <path d="M11 14h23" fill="none" stroke="#92400E" strokeLinejoin="miter" />
        </g>
      </svg>

      {/* Bishop piece silhouette - golden amber */}
      <svg
        className="absolute top-1/2 left-1/4 w-20 h-20 md:w-32 md:h-32 opacity-24"
        viewBox="0 0 45 45"
        fill="#F59E0B"
      >
        <g fillRule="evenodd" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
          <path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2z" fill="#F59E0B" stroke="#F59E0B" />
          <path d="M15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2z" fill="#F59E0B" stroke="#F59E0B" />
          <path d="M25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z" fill="#F59E0B" stroke="#F59E0B" />
        </g>
      </svg>

      {/* Queen piece silhouette - warm amber */}
      <svg
        className="absolute top-1/4 right-1/3 w-24 h-24 md:w-40 md:h-40 opacity-26"
        viewBox="0 0 45 45"
        fill="#F59E0B"
      >
        <g fillRule="evenodd" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
          <path d="M9 26c8.5-1.5 21-1.5 27 0l2.5-12.5L31 25l-.3-14.1-5.2 13.6-3-14.5-3 14.5-5.2-13.6L14 25 6.5 13.5 9 26z" stroke="#F59E0B" fill="#F59E0B" />
          <path d="M9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1 2.5-1 2.5-1.5 1.5 0 2.5 0 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke="#F59E0B" fill="#F59E0B" />
          <path d="M11.5 30c3.5-1 18.5-1 22 0M12 33.5c6-1 15-1 21 0" fill="none" stroke="#F59E0B" />
          <circle cx="6" cy="12" r="2" fill="#F59E0B" stroke="#F59E0B" />
          <circle cx="14" cy="9" r="2" fill="#F59E0B" stroke="#F59E0B" />
          <circle cx="22.5" cy="8" r="2" fill="#F59E0B" stroke="#F59E0B" />
          <circle cx="31" cy="9" r="2" fill="#F59E0B" stroke="#F59E0B" />
          <circle cx="39" cy="12" r="2" fill="#F59E0B" stroke="#F59E0B" />
        </g>
      </svg>

      {/* King piece silhouette - rich brown */}
      <svg
        className="absolute bottom-1/3 right-10 w-22 h-22 md:w-36 md:h-36 opacity-30"
        viewBox="0 0 45 45"
        fill="#B45309"
      >
        <g fillRule="evenodd" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
          <path d="M22.5 11.63V6M20 8h5" stroke="#B45309" fill="none" strokeLinejoin="miter" />
          <path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#B45309" stroke="#B45309" strokeLinecap="butt" strokeLinejoin="miter" />
          <path d="M12.5 37c5.5 3.5 14.5 3.5 20 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-2.5-7.5-12-10.5-16-4-3 6 6 10.5 6 10.5v7" fill="#B45309" stroke="#B45309" />
          <path d="M12.5 30c5.5-3 14.5-3 20 0m-20 3.5c5.5-3 14.5-3 20 0m-20 3.5c5.5-3 14.5-3 20 0" fill="none" stroke="#B45309" />
        </g>
      </svg>

      {/* Pawn piece silhouette - golden */}
      <svg
        className="absolute top-2/3 left-1/3 w-16 h-16 md:w-24 md:h-24 opacity-22"
        viewBox="0 0 45 45"
        fill="#FBBF24"
      >
        <g fillRule="evenodd" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5">
          <path d="M22.5 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38C17.33 16.5 16 18.59 16 21c0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#FBBF24" stroke="#FBBF24" />
        </g>
      </svg>
    </div>
  );
};

