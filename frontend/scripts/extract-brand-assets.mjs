import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { inflateRawSync } from "node:zlib";

const archiveUrl =
  "https://raw.githubusercontent.com/munggar/RuangKampus/main/RuangKampus-Brand-Assets%20(1).zip";
const outputRoot = path.resolve("public/brand");

const requiredHashes = new Map([
  ["public/brand/logo-primary.png", "8157481bd7d6d8f87c805cff47dd27fd11bbbc781a481f6363c0eb667e503bcd"],
  ["public/brand/logo-primary-white-bg.png", "3d94fa78467ee1bfdf169bdebb1b70d48cefc73203e8cd20f92d89425c050606"],
  ["public/brand/favicon/favicon.ico", "2786bb3130485ea1361f4d01d3480920540704dc5d40ad9ba82d4d31aac766cb"],
  ["public/brand/favicon/favicon-32x32.png", "606b22a2a2598cb67c0ec0efcc7b3d0b4fb401e1a4e2f96f203e67872dc5541d"],
  ["public/brand/favicon/favicon-16x16.png", "c44f48d4b2391919356e5d308261d2c238f663aff4e00e10b05fb6e3adfcdb6b"],
  ["public/brand/favicon/apple-touch-icon.png", "269ee4c7e6695dcab913ba430b90afc4c4a1ab37f0ae5871602709221f58c1ea"],
  ["public/brand/favicon/site.webmanifest", "89aea36bfa6672353cd32d5b443399357512852c4027e6c1f6361c6952d76ea5"],
]);

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

const response = await fetch(archiveUrl, {
  headers: { "User-Agent": "RuangKampus-brand-assets-build" },
  redirect: "follow",
});
if (!response.ok) {
  throw new Error(`Unable to download official brand archive: HTTP ${response.status}`);
}
const archive = Buffer.from(await response.arrayBuffer());
if (archive.length !== 760176) throw new Error(`Unexpected brand archive size: ${archive.length}`);
const archiveSha256 = createHash("sha256").update(archive).digest("hex");
if (archiveSha256 !== "567cc38d1b6725d1797173cbdd6429ced2b6570170778acd26f213abc2205fa3") {
  throw new Error("Official brand archive checksum does not match the repository source.");
}
if (archive.length < 22) throw new Error("Brand archive is empty or truncated.");

const eocdSignature = Buffer.from([0x50, 0x4b, 0x05, 0x06]);
const eocdOffset = archive.lastIndexOf(eocdSignature);
if (eocdOffset < 0) throw new Error("Brand archive ZIP directory is missing.");

const entryCount = archive.readUInt16LE(eocdOffset + 10);
let directoryOffset = archive.readUInt32LE(eocdOffset + 16);
const extracted = new Set();

for (let index = 0; index < entryCount; index += 1) {
  if (archive.readUInt32LE(directoryOffset) !== 0x02014b50) {
    throw new Error("Invalid entry in official brand archive.");
  }

  const method = archive.readUInt16LE(directoryOffset + 10);
  const expectedCrc = archive.readUInt32LE(directoryOffset + 16);
  const compressedSize = archive.readUInt32LE(directoryOffset + 20);
  const uncompressedSize = archive.readUInt32LE(directoryOffset + 24);
  const nameLength = archive.readUInt16LE(directoryOffset + 28);
  const extraLength = archive.readUInt16LE(directoryOffset + 30);
  const commentLength = archive.readUInt16LE(directoryOffset + 32);
  const localOffset = archive.readUInt32LE(directoryOffset + 42);
  const entryName = archive.toString(
    "utf8",
    directoryOffset + 46,
    directoryOffset + 46 + nameLength,
  );
  directoryOffset += 46 + nameLength + extraLength + commentLength;

  if (!entryName.startsWith("public/brand/") || entryName.endsWith("/")) continue;
  if (archive.readUInt32LE(localOffset) !== 0x04034b50) {
    throw new Error(`Invalid ZIP local header for ${entryName}`);
  }

  const localNameLength = archive.readUInt16LE(localOffset + 26);
  const localExtraLength = archive.readUInt16LE(localOffset + 28);
  const dataOffset = localOffset + 30 + localNameLength + localExtraLength;
  const compressed = archive.subarray(dataOffset, dataOffset + compressedSize);

  let fileBytes;
  if (method === 0) fileBytes = Buffer.from(compressed);
  else if (method === 8) fileBytes = inflateRawSync(compressed);
  else throw new Error(`Unsupported ZIP compression method ${method}: ${entryName}`);

  if (fileBytes.length !== uncompressedSize || crc32(fileBytes) !== expectedCrc) {
    throw new Error(`Integrity check failed for ${entryName}`);
  }

  const relativePath = entryName.slice("public/brand/".length);
  const destination = path.resolve(outputRoot, relativePath);
  if (!destination.startsWith(outputRoot + path.sep)) {
    throw new Error(`Unsafe path in brand archive: ${entryName}`);
  }
  await mkdir(path.dirname(destination), { recursive: true });
  await writeFile(destination, fileBytes);
  extracted.add(entryName);
}

for (const [archivePath, expectedHash] of requiredHashes) {
  if (!extracted.has(archivePath)) throw new Error(`Required official asset missing: ${archivePath}`);
  const relativePath = archivePath.slice("public/brand/".length);
  const bytes = await readFile(path.resolve(outputRoot, relativePath));
  const actualHash = createHash("sha256").update(bytes).digest("hex");
  if (actualHash !== expectedHash) {
    throw new Error(`Official asset checksum mismatch: ${archivePath}`);
  }
}

console.log(`Verified and extracted ${extracted.size} original files into frontend/public/brand.`);
