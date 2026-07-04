import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/classnames";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md";

interface UiButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variants: Record<ButtonVariant, string> = {
  primary: "border-transparent bg-mint text-white shadow-sm hover:bg-emerald-700",
  secondary: "border-stone-300 bg-white text-ink shadow-sm hover:bg-stone-50",
  ghost: "border-stone-200 bg-white text-stone-600 hover:bg-stone-50",
  danger: "border-red-200 bg-white text-red-700 hover:bg-red-50"
};

const sizes: Record<ButtonSize, string> = {
  sm: "min-h-9 px-2.5 py-2 text-sm",
  md: "min-h-10 px-4 py-2 text-sm"
};

export const UiButton = forwardRef<HTMLButtonElement, UiButtonProps>(function UiButton({ children, className, icon, size = "md", type = "button", variant = "secondary", ...props }, ref) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex min-w-0 items-center justify-center gap-2 rounded-md border font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
        "whitespace-nowrap leading-none",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {icon ? <span className="flex h-4 w-4 shrink-0 items-center justify-center">{icon}</span> : null}
      {children ? <span className="min-w-0 truncate">{children}</span> : null}
    </button>
  );
});

export function IconButton({ className, icon, ...props }: Omit<UiButtonProps, "children">) {
  return <UiButton className={cn("h-9 w-9 px-0", className)} icon={icon} size="sm" {...props} />;
}
