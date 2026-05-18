import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number): string {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    minimumFractionDigits: 0,
  }).format(price);
}

export function getBudgetStatusColor(status: string): string {
  switch (status) {
    case "healthy": return "text-green-600";
    case "warning": return "text-yellow-600";
    case "critical": return "text-red-600";
    default: return "text-gray-600";
  }
}

export function getSpendingTypeLabel(type: string): string {
  switch (type) {
    case "dengeli": return "Dengeli Harcayıcı";
    case "savruk": return "Savruk Harcayıcı";
    case "tutumlu": return "Tutumlu Harcayıcı";
    default: return type;
  }
}
