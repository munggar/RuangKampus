import { describe, expect, it } from "vitest";
import { translateAppText } from "./i18n";

describe("global bilingual UI dictionary", () => {
  it("translates key room-management labels into English", () => {
    expect(translateAppText("Kelola ruangan", "en")).toBe("Manage rooms");
    expect(translateAppText("Pilih semua yang tampil", "en")).toBe("Select all visible");
    expect(translateAppText("Ketik HAPUS untuk mengonfirmasi", "en")).toBe("Type DELETE to confirm");
  });

  it("translates mixed count text while retaining the numeric value", () => {
    expect(translateAppText("19 ruangan dalam inventaris kampus.", "en")).toBe("19 rooms in the campus inventory.");
  });

  it("translates English interface labels back to Indonesian", () => {
    expect(translateAppText("Welcome back", "id")).toBe("Selamat datang kembali");
    expect(translateAppText("Search rooms", "id")).toBe("Cari ruangan");
  });

  it("preserves unrecognised room and user-provided content", () => {
    expect(translateAppText("Laboratorium Elektro & Robotika 1", "en")).toBe("Laboratorium Elektro & Robotika 1");
    expect(translateAppText("Jl. Tanah Merdeka No. 6, Jakarta Timur", "en")).toBe("Jl. Tanah Merdeka No. 6, Jakarta Timur");
  });
});
