"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/classnames";

interface NavigatingLinkProps {
  children: React.ReactNode;
  className?: string;
  href: string;
}

export function NavigatingLink({ children, className, href }: NavigatingLinkProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  return (
    <button
      className={cn(className, loading ? "pointer-events-none opacity-70" : "")}
      disabled={loading}
      onClick={() => {
        setLoading(true);
        router.push(href);
      }}
      type="button"
    >
      {loading ? <Loader2 className="h-4 w-4 shrink-0 animate-spin" /> : null}
      <span>{loading ? "Carregando..." : children}</span>
    </button>
  );
}
