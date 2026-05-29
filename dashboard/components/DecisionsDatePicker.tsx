"use client";
import { useRouter, usePathname } from "next/navigation";

interface Props {
  selectedDate: string;
}

export function DecisionsDatePicker({ selectedDate }: Props) {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <input
      type="date"
      defaultValue={selectedDate}
      max={new Date().toISOString().split("T")[0]}
      className="bg-surface border border-border rounded-lg px-3 py-1.5 text-sm text-text focus:outline-none focus:border-accent/60 transition-colors"
      onChange={(e) => {
        const d = e.target.value;
        if (d) router.push(`${pathname}?date=${d}`);
      }}
    />
  );
}
