import { Info } from "lucide-react";
import { Link } from "react-router";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import type { AppRole } from "../auth/AuthContext";

interface PlaceholderPageProps {
  role: AppRole;
  title: string;
  description: string;
}

export function PlaceholderPage({ role, title, description }: PlaceholderPageProps) {
  const dashboardPath = role === "Student" ? "/student/dashboard" : "/admin/dashboard";

  return (
    <div className="dashboard-page">
      <PageHeader
        eyebrow={role === "Student" ? "STUDENT PORTAL" : "TU / ADMIN PORTAL"}
        title={title}
        description={description}
      />
      <section className="dashboard-panel placeholder-panel">
        <EmptyState
          eyebrow="FRONTEND SCAFFOLD"
          icon={<Info size={22} />}
          title="Halaman ini belum diimplementasikan"
          description="Struktur navigasi sudah disiapkan. Konten dan interaksi akan dibangun setelah spesifikasi desain serta kontrak API terkait tersedia."
          action={
            <Link className="button button--outline" to={dashboardPath}>
              Kembali ke dashboard
            </Link>
          }
        />
      </section>
    </div>
  );
}
