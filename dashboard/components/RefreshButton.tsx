"use client";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { useState } from "react";

export function RefreshButton() {
  const router = useRouter();
  const [spinning, setSpinning] = useState(false);

  const handleRefresh = () => {
    setSpinning(true);
    router.refresh();
    setTimeout(() => setSpinning(false), 1000);
  };

  return (
    <button
      onClick={handleRefresh}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-subtle text-xs hover:text-text hover:border-accent/50 transition-colors"
    >
      <RefreshCw
        size={12}
        className={spinning ? "animate-spin" : ""}
      />
      Refresh
    </button>
  );
}
