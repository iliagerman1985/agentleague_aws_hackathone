import React, { useEffect, useState } from "react";
import { ConfettiBurst } from "./ConfettiBurst";

/**
 * Global one-shot overlay that shows confetti after a payment success redirect.
 * We set sessionStorage.purchaseCelebration = '1' on /billing/success, then
 * immediately navigate back to the previous page. This component checks that
 * flag and renders ConfettiBurst once, then clears the flag.
 */
export const PurchaseCelebrationOverlay: React.FC = () => {
  const [show, setShow] = useState(false);

  useEffect(() => {
    try {
      if (sessionStorage.getItem("purchaseCelebration") === "1") {
        setShow(true);
        // Clear the flag after a moment so it doesn't repeat on refresh
        sessionStorage.removeItem("purchaseCelebration");
        const t = window.setTimeout(() => setShow(false), 2800);
        return () => window.clearTimeout(t);
      }
    } catch {
      // ignore storage issues
    }
  }, []);

  if (!show) return null;
  return <ConfettiBurst />;
};

export default PurchaseCelebrationOverlay;

