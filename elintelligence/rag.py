from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from bs4 import BeautifulSoup
from pypdf import PdfReader

from .paths import rag_file

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".markdown", ".html", ".htm", ".log", ".csv"}


@dataclass
class RagChunk:
    source: str
    text: str
    page: int | None = None
    path: str | None = None
    chunk: int | None = None
    embedding: list[float] | None = None
    mtime_ns: int | None = None
    size_bytes: int | None = None


@dataclass
class RagHit:
    source: str
    text: str
    score: float
    page: int | None = None
    path: str | None = None
    chunk: int | None = None
    lexical_score: float = 0.0
    semantic_score: float = 0.0

    @property
    def locator(self) -> str:
        if self.page:
            return f"{self.source} · pag. {self.page}"
        return self.source

    @property
    def excerpt(self) -> str:
        clean = re.sub(r"\s+", " ", self.text).strip()
        return clean[:420] + ("…" if len(clean) > 420 else "")


class RagStore:
    STOPWORDS = {
        "a", "ad", "al", "alla", "alle", "allo", "ai", "agli", "anche", "avere",
        "che", "chi", "ci", "come", "con", "cosa", "da", "dal", "dalla", "dalle",
        "dei", "del", "della", "delle", "di", "dove", "e", "ed", "è", "era", "essere",
        "fa", "fare", "fra", "gli", "ha", "hai", "hanno", "ho", "i", "il", "in", "io",
        "la", "le", "lo", "ma", "mi", "nei", "nel", "nella", "nelle", "non", "o", "per",
        "piu", "più", "puo", "può", "quale", "quali", "quando", "quanto", "questa", "queste",
        "questi", "questo", "se", "sei", "si", "sia", "sono", "su", "sul", "sulla", "tra",
        "tu", "un", "una", "uno", "va", "viene", "the", "and", "for", "from", "with", "that",
        "this", "what", "where", "when", "which", "how", "are", "was", "were", "have", "has",
    }

    def __init__(self) -> None:
        self.chunks: list[RagChunk] = []
        self._load()

    def _load(self) -> None:
        path = rag_file()
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            allowed = set(RagChunk.__dataclass_fields__)
            self.chunks = [
                RagChunk(**{k: v for k, v in item.items() if k in allowed})
                for item in raw if isinstance(item, dict)
            ]
        except Exception:
            self.chunks = []

    def _save(self) -> None:
        rag_file().write_text(
            json.dumps([asdict(x) for x in self.chunks], ensure_ascii=False),
            encoding="utf-8",
        )

    def clear(self) -> None:
        self.chunks = []
        try:
            rag_file().unlink(missing_ok=True)
        except Exception:
            pass

    def document_names(self) -> list[str]:
        return sorted({c.source for c in self.chunks})

    def embedded_count(self) -> int:
        return sum(1 for c in self.chunks if c.embedding)

    def embedding_coverage(self) -> tuple[int, int]:
        return self.embedded_count(), len(self.chunks)

    def import_file(
        self,
        path: Path,
        embedder: Callable[[list[str]], list[list[float]]] | None = None,
    ) -> int:
        path = path.resolve()
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError(f"Formato non supportato: {path.suffix}")
        stat = path.stat()
        imported: list[RagChunk] = []

        if path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))
            for page_no, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                for chunk_no, part in enumerate(self._chunk(page_text), start=1):
                    imported.append(
                        RagChunk(
                            source=path.name,
                            text=part,
                            page=page_no,
                            path=str(path),
                            chunk=chunk_no,
                            mtime_ns=stat.st_mtime_ns,
                            size_bytes=stat.st_size,
                        )
                    )
        else:
            text = self._extract_text(path)
            for chunk_no, part in enumerate(self._chunk(text), start=1):
                imported.append(
                    RagChunk(
                        source=path.name,
                        text=part,
                        page=None,
                        path=str(path),
                        chunk=chunk_no,
                        mtime_ns=stat.st_mtime_ns,
                        size_bytes=stat.st_size,
                    )
                )

        if not imported:
            raise ValueError("Nessun testo estraibile dal documento")

        if embedder is not None:
            vectors = embedder([c.text for c in imported])
            if len(vectors) != len(imported):
                raise RuntimeError("Numero embeddings non coerente con i chunk")
            for chunk, vector in zip(imported, vectors):
                chunk.embedding = vector

        self.chunks = [c for c in self.chunks if (c.path or c.source) != str(path)]
        self.chunks.extend(imported)
        self._save()
        return len(imported)

    def sync_folder(
        self,
        folder: Path,
        embedder: Callable[[list[str]], list[list[float]]] | None = None,
        status: Callable[[str], None] | None = None,
    ) -> tuple[int, int, int]:
        status = status or (lambda _x: None)
        folder = folder.resolve()
        if not folder.is_dir():
            raise NotADirectoryError(str(folder))
        files = sorted(
            p.resolve() for p in folder.rglob("*")
            if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
        )
        current_paths = {str(p) for p in files}
        existing_by_path: dict[str, RagChunk] = {}
        for chunk in self.chunks:
            if chunk.path:
                existing_by_path.setdefault(str(Path(chunk.path).resolve()), chunk)

        changed: list[Path] = []
        for path in files:
            old = existing_by_path.get(str(path))
            stat = path.stat()
            if old is None or old.mtime_ns != stat.st_mtime_ns or old.size_bytes != stat.st_size:
                changed.append(path)

        deleted_paths = {
            p for p in existing_by_path
            if self._is_inside(Path(p), folder) and p not in current_paths
        }
        if deleted_paths:
            self.chunks = [c for c in self.chunks if not c.path or str(Path(c.path).resolve()) not in deleted_paths]

        total_chunks = 0
        for idx, path in enumerate(changed, 1):
            status(f"Indicizzazione cartella {idx}/{len(changed)} · {path.name}")
            total_chunks += self.import_file(path, embedder=embedder)

        if deleted_paths and not changed:
            self._save()
        return len(changed), len(deleted_paths), total_chunks

    def reembed_all(
        self,
        embedder: Callable[[list[str]], list[list[float]]],
        status: Callable[[str], None] | None = None,
        batch_chunks: int = 24,
    ) -> int:
        status = status or (lambda _x: None)
        if not self.chunks:
            return 0
        done = 0
        for start in range(0, len(self.chunks), batch_chunks):
            batch = self.chunks[start:start + batch_chunks]
            status(f"RAG Pro: embeddings {min(start + len(batch), len(self.chunks))}/{len(self.chunks)}")
            vectors = embedder([c.text for c in batch])
            if len(vectors) != len(batch):
                raise RuntimeError("Numero embeddings non coerente")
            for chunk, vector in zip(batch, vectors):
                chunk.embedding = vector
                done += 1
        self._save()
        return done

    @staticmethod
    def _is_inside(path: Path, folder: Path) -> bool:
        try:
            path.resolve().relative_to(folder.resolve())
            return True
        except Exception:
            return False

    @staticmethod
    def _extract_text(path: Path) -> str:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix.lower() in {".html", ".htm"}:
            return BeautifulSoup(raw, "html.parser").get_text("\n", strip=True)
        return raw

    @staticmethod
    def _chunk(text: str, size: int = 1500, overlap: int = 220) -> list[str]:
        clean = re.sub(r"\s+", " ", text).strip()
        if not clean:
            return []
        chunks: list[str] = []
        start = 0
        while start < len(clean):
            end = min(len(clean), start + size)
            if end < len(clean):
                # Prefer breaking near sentence/paragraph boundaries to improve citation quality.
                cut = max(clean.rfind(". ", start + size // 2, end), clean.rfind("; ", start + size // 2, end))
                if cut > start:
                    end = cut + 1
            chunks.append(clean[start:end].strip())
            if end >= len(clean):
                break
            start = max(start + 1, end - overlap)
        return [c for c in chunks if c]

    @classmethod
    def _tokens(cls, text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9_\-]{3,}", text.lower())
        return [t for t in tokens if t not in cls.STOPWORDS]

    @staticmethod
    def _cosine(a: list[float] | None, b: list[float] | None) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na <= 0 or nb <= 0:
            return 0.0
        return dot / (na * nb)

    def search(
        self,
        query: str,
        limit: int = 4,
        query_embedding: list[float] | None = None,
    ) -> list[RagHit]:
        q_tokens = self._tokens(query)
        if not self.chunks:
            return []
        q_unique = set(q_tokens)
        chunk_tokens = [self._tokens(chunk.text) for chunk in self.chunks]
        nonempty_lengths = [len(tokens) for tokens in chunk_tokens if tokens]
        avgdl = (sum(nonempty_lengths) / len(nonempty_lengths)) if nonempty_lengths else 1.0
        n_docs = max(1, len(self.chunks))

        df: Counter[str] = Counter()
        for tokens in chunk_tokens:
            token_set = set(tokens)
            for term in q_unique:
                if term in token_set:
                    df[term] += 1

        raw: list[tuple[RagChunk, float, float, float]] = []
        k1, b = 1.45, 0.72
        query_phrase = " ".join(q_tokens)
        for chunk, tokens in zip(self.chunks, chunk_tokens):
            tf = Counter(tokens)
            common = q_unique & set(tokens)
            lexical = 0.0
            if q_unique and common:
                dl = max(1, len(tokens))
                for term in q_unique:
                    freq = tf.get(term, 0)
                    if not freq:
                        continue
                    freq_docs = df.get(term, 0)
                    idf = math.log(1.0 + (n_docs - freq_docs + 0.5) / (freq_docs + 0.5))
                    denom = freq + k1 * (1.0 - b + b * dl / max(1.0, avgdl))
                    lexical += idf * (freq * (k1 + 1.0) / denom)
                coverage = len(common) / max(1, len(q_unique))
                normalized_text = " ".join(tokens)
                if query_phrase and query_phrase in normalized_text:
                    lexical += 1.2
                lexical += coverage * 0.75
            semantic = max(0.0, self._cosine(query_embedding, chunk.embedding)) if query_embedding else 0.0
            if lexical > 0 or semantic > 0:
                raw.append((chunk, lexical, semantic, len(common) / max(1, len(q_unique)) if q_unique else 0.0))

        if not raw:
            return []
        max_lex = max((row[1] for row in raw), default=0.0) or 1.0
        hybrid = query_embedding is not None and any(row[2] > 0 for row in raw)
        candidates: list[RagHit] = []
        for chunk, lexical, semantic, coverage in raw:
            lexical_norm = lexical / max_lex
            if hybrid:
                # Dense semantic retrieval catches paraphrases; BM25 anchors exact technical terms.
                score = 0.58 * semantic + 0.34 * lexical_norm + 0.08 * coverage
            else:
                score = 0.88 * lexical_norm + 0.12 * coverage
            # Small locator/source bonus helps queries that explicitly name a manual/file.
            if q_unique and any(t in chunk.source.lower() for t in q_unique):
                score += 0.04
            candidates.append(
                RagHit(
                    source=chunk.source,
                    text=chunk.text,
                    score=score,
                    page=chunk.page,
                    path=chunk.path,
                    chunk=chunk.chunk,
                    lexical_score=lexical_norm,
                    semantic_score=semantic,
                )
            )

        candidates.sort(key=lambda hit: hit.score, reverse=True)
        top = candidates[0].score
        # Second-stage local rerank: strict relative cutoff + dedupe by page/file.
        cutoff = max(0.22 if hybrid else 0.28, top * (0.67 if hybrid else 0.62))
        selected: list[RagHit] = []
        seen_locations: set[tuple[str, int | None]] = set()
        for hit in candidates:
            if hit.score < cutoff:
                continue
            location = (hit.path or hit.source, hit.page)
            if location in seen_locations:
                continue
            # Reject dense-only weak matches unless semantic similarity is meaningful.
            if hybrid and hit.lexical_score < 0.05 and hit.semantic_score < 0.42:
                continue
            seen_locations.add(location)
            selected.append(hit)
            if len(selected) >= limit:
                break
        return selected
