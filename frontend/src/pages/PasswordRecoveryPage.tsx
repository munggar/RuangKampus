import { ArrowLeft, LockKeyhole } from "lucide-react";
import { Link } from "react-router";
import { BrandWordmark } from "../components/BrandWordmark";

export function PasswordRecoveryPage() {
  return (
    <main className="simple-page">
      <section className="simple-page__card" aria-labelledby="recovery-heading">
        <BrandWordmark />
        <div className="simple-page__icon"><LockKeyhole size={24} aria-hidden="true" /></div>
        <p className="eyebrow">PEMULIHAN AKUN</p>
        <h1 id="recovery-heading">Lupa kata sandi?</h1>
        <p>
          Tampilan pemulihan akun tersedia dalam rancangan. Endpoint permintaan
          reset kata sandi belum tercantum pada API Contract, sehingga pengiriman
          permintaan belum diaktifkan.
        </p>
        <Link className="button button--primary" to="/login">
          <ArrowLeft size={18} aria-hidden="true" />
          Kembali ke login
        </Link>
      </section>
    </main>
  );
}
