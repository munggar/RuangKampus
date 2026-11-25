import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  description: string;
  icon: LucideIcon;
}

export function StatCard({ label, description, icon: Icon }: StatCardProps) {
  return (
    <article className="stat-card">
      <div className="stat-card__top">
        <span className="stat-card__icon"><Icon size={19} aria-hidden="true" /></span>
        <span className="stat-card__status">API belum terhubung</span>
      </div>
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value" aria-label={`${label}: belum tersedia`}>—</p>
      <p className="stat-card__description">{description}</p>
    </article>
  );
}
