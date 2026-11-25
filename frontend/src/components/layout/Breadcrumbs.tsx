import { ChevronRight } from "lucide-react";
import { Link } from "react-router";

interface BreadcrumbsProps { homePath: string; current: string; }

export function Breadcrumbs({ homePath, current }: BreadcrumbsProps) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <Link to={homePath}>Beranda</Link>
      <ChevronRight size={14} aria-hidden="true" />
      <span aria-current="page">{current}</span>
    </nav>
  );
}
