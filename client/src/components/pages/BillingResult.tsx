import React, { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { ConfettiBurst } from "@/components/common/utility/ConfettiBurst";
import { api } from "@/lib/api";

export const BillingResult: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  const isSuccess = location.pathname.includes("/billing/success");

  useEffect(() => {
    const confirmAndBounce = async () => {
      try {
        const params = new URLSearchParams(location.search);
        const sessionId = params.get("session_id");
        if (sessionId) {
          try {
            await api.billing.confirmSession(sessionId);
          } catch (e) {
            // Non-fatal: webhook may still process it; continue
          }
        }
        await refreshUser();
        sessionStorage.setItem("purchaseCelebration", "1");
        const prev = sessionStorage.getItem("preCheckoutPath") || "/games-management";
        navigate(prev, { replace: true });
      } catch {
        navigate("/games-management", { replace: true });
      }
    };
    void confirmAndBounce();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="w-full h-full flex items-center justify-center p-6 relative">
      {isSuccess && <ConfettiBurst />}
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>{isSuccess ? "Payment Successful" : "Payment Canceled"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isSuccess ? (
            <p>Your purchase was completed. Your coin balance has been updated. Enjoy!</p>
          ) : (
            <p>Your purchase was canceled. No charges were made.</p>
          )}
          <div className="flex gap-2">
            <Button onClick={() => navigate("/games-management")}>Back to Play</Button>
            <Button variant="outline" onClick={() => navigate("/settings")}>Go to Settings</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default BillingResult;

