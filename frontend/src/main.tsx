import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router";
import { AuthProvider } from "./auth";
import { App } from "./App";
import "./styles/tokens.css";
import "./styles.css";

// Auth pages live outside AppShell, so initialize the saved theme before any route renders.
if (typeof window !== "undefined") {
  document.documentElement.dataset.theme =
    window.localStorage.getItem("rk-theme") === "dark" ? "dark" : "light";
}

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  const baseUrl = import.meta.env.BASE_URL;
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register(`${baseUrl}sw.js`, { scope: baseUrl })
      .catch((error: unknown) => {
        console.warn("RuangKampus offline support could not be enabled.", error);
      });
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/+$/, "") || "/"}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);