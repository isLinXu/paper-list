import hashlib
import base64
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


WAYBACK_PREFIX = "https://web.archive.org/web/"

ARCHITECTURE_RULES = {
    "vision transformer": "Vision Transformer",
    "vit": "Vision Transformer",
    "swin": "Swin Transformer",
    "transformer": "Transformer",
    "diffusion": "Diffusion",
    "multi-view": "Multi-view Network",
    "multiview": "Multi-view Network",
    "memory mechanism": "Memory Mechanism",
    "unet": "U-Net",
    "u-net": "U-Net",
    "cnn": "CNN",
    "resnet": "ResNet",
    "clip": "CLIP",
    "llm": "LLM",
    "mamba": "Mamba",
    "moe": "Mixture-of-Experts",
    "gnn": "Graph Neural Network",
    "graph neural": "Graph Neural Network",
}

FRAMEWORK_RULES = {
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "jax": "JAX",
    "flax": "Flax",
    "mindspore": "MindSpore",
    "cuda": "CUDA",
}

DATASET_RULES = {
    "ade20k": "ADE20K",
    "imagenet": "ImageNet",
    "coco": "COCO",
    "kitti": "KITTI",
    "scannet": "ScanNet",
    "nyuv2": "NYUv2",
    "pascal voc": "PASCAL VOC",
    "nuscenes": "nuScenes",
    "waymo": "Waymo Open Dataset",
    "laion": "LAION",
    "msr-vtt": "MSR-VTT",
}

BENCHMARK_RULES = {
    "imagenet-1k": "ImageNet-1K",
    "imagenet 1k": "ImageNet-1K",
    "coco val2017": "COCO val2017",
    "coco test-dev": "COCO test-dev",
    "ade20k val": "ADE20K validation",
    "kitti 2015": "KITTI 2015",
    "scannet v2": "ScanNet v2",
    "nuscenes val": "nuScenes validation",
    "vqa v2": "VQA v2",
    "textvqa": "TextVQA",
    "gqa": "GQA",
}

LOW_SIGNAL_LABELS = {
    "artificial intelligence",
    "computer science",
    "computer vision",
    "computer graphics (images)",
    "machine learning",
    "deep learning",
    "image processing",
    "pattern recognition",
}


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text or "unknown"


def stable_id(*parts: str) -> str:
    joined = "||".join(str(part).strip() for part in parts if str(part).strip())
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def manifest_row_filename(row: dict[str, Any], suffix: str = ".html") -> str:
    entity_type = slugify(row.get("entity_type") or "unknown")
    identifier = row.get("id") or stable_id(row.get("archive_url", ""), row.get("original_url", ""))
    return f"{entity_type}--{identifier}{suffix}"


def extract_text_blocks(html: str) -> list[str]:
    blocks = re.findall(r">([^<>]+)<", html or "")
    return [re.sub(r"\s+", " ", block).strip() for block in blocks if block.strip()]


def extract_links(html: str, base_url: str | None = None) -> list[str]:
    links = re.findall(r'href=["\']([^"\']+)["\']', html or "", flags=re.IGNORECASE)
    cleaned = []
    for link in links:
        if link.startswith("#") or link.startswith("javascript:"):
            continue
        if base_url and link.startswith("/"):
            origin = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(base_url))
            cleaned.append(origin + link)
        else:
            cleaned.append(link)
    return cleaned


def extract_wayback_target(archive_url: str) -> str:
    if "/http" in archive_url:
        return "http" + archive_url.split("/http", 1)[1]
    return archive_url


def resolve_archive_link(base_archive_url: str, link: str) -> str:
    if link.startswith("http://") or link.startswith("https://"):
        return link

    target = extract_wayback_target(base_archive_url)
    target_uri = urlparse(target)
    if not link.startswith("/"):
        link = "/" + link

    if "/web/" in base_archive_url:
        prefix = base_archive_url.split("/http", 1)[0]
        return f"{prefix}/https://{target_uri.netloc}{link}"

    return f"{target_uri.scheme}://{target_uri.netloc}{link}"


def normalize_repo_url(repo_url: str | None) -> str | None:
    if not repo_url:
        return None
    match = re.search(r"https://github\.com/[^/\s]+/[^/\s#?]+", repo_url)
    if match:
        return match.group(0).rstrip("/")
    return repo_url.rstrip("/")


def decode_github_readme(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""
    content = payload.get("content")
    if not content:
        return ""
    if payload.get("encoding") == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", errors="ignore")
        except (ValueError, TypeError):
            return ""
    return str(content)


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    cleaned = str(doi).strip()
    cleaned = re.sub(r"^https?://(dx\.)?doi\.org/", "", cleaned, flags=re.IGNORECASE)
    return cleaned.lower()


def extract_repo_slug(repo_url: str | None) -> str | None:
    repo = normalize_repo_url(repo_url)
    if not repo:
        return None
    parsed = urlparse(repo)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return None


def infer_labels(*texts: str, rules: dict[str, str]) -> list[str]:
    haystack = " ".join(texts).lower()
    labels = {label for needle, label in rules.items() if needle in haystack}
    return sorted(labels)


def titlecase_slug(slug: str) -> str:
    cleaned = str(slug).strip("/").split("/")[-1]
    cleaned = cleaned.replace("-", " ").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in cleaned.split())


def extract_entity_labels_from_links(links: list[str], entity: str) -> list[str]:
    labels = []
    needle = f"/{entity}/"
    for link in links:
        if needle not in link:
            continue
        labels.append(titlecase_slug(link.split(needle, 1)[1]))
    return merge_unique_strings(labels)


def infer_tasks_methods_datasets(title: str, abstract: str, links: list[str]) -> tuple[list[str], list[str], list[str], list[str]]:
    task_labels = extract_entity_labels_from_links(links, "task")
    method_labels = extract_entity_labels_from_links(links, "method")
    dataset_labels = extract_entity_labels_from_links(links, "dataset")
    benchmark_labels = extract_entity_labels_from_links(links, "benchmark")

    text = f"{title} {abstract}".lower()
    keyword_tasks = []
    if "segmentation" in text:
        keyword_tasks.append("Semantic Segmentation")
    if "depth" in text:
        keyword_tasks.append("Depth Estimation")
    if "reconstruction" in text:
        keyword_tasks.append("3D Reconstruction")
    if "visual odometry" in text:
        keyword_tasks.append("Visual Odometry")
    if "camera pose" in text or "pose estimation" in text:
        keyword_tasks.append("Camera Pose Estimation")
    if "slam" in text:
        keyword_tasks.append("Visual SLAM")
    if "sfm" in text or "structure from motion" in text:
        keyword_tasks.append("Structure from Motion")
    if "question answering" in text or "vqa" in text:
        keyword_tasks.append("Visual Question Answering")
    if "instance segmentation" in text or "instance-segmentation" in text:
        keyword_tasks.append("Instance Segmentation")
    if "object detection" in text or "detection" in text:
        keyword_tasks.append("Object Detection")
    if "multimodal" in text or "vision-language" in text or "vision language" in text:
        keyword_tasks.append("Multimodal Learning")
    if "large language model" in text or "language model" in text or "llm" in text:
        keyword_tasks.append("Large Language Models")
    if "image generation" in text or "text-to-image" in text or "text to image" in text:
        keyword_tasks.append("Image Generation")

    keyword_methods = infer_labels(title, abstract, rules=ARCHITECTURE_RULES)
    keyword_datasets = infer_labels(title, abstract, rules=DATASET_RULES)
    keyword_benchmarks = infer_labels(title, abstract, rules=BENCHMARK_RULES)
    return (
        merge_unique_strings(task_labels, keyword_tasks),
        merge_unique_strings(method_labels, keyword_methods),
        merge_unique_strings(dataset_labels, keyword_datasets),
        merge_unique_strings(benchmark_labels, keyword_benchmarks),
    )


def merge_unique_strings(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group or []:
            text = str(item).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            merged.append(text)
    return merged


def filter_low_signal_labels(values: list[str]) -> list[str]:
    filtered = []
    seen = set()
    for value in values or []:
        text = str(value).strip()
        if not text:
            continue
        if text.lower() in LOW_SIGNAL_LABELS:
            continue
        if text in seen:
            continue
        seen.add(text)
        filtered.append(text)
    return filtered


def merge_provenance(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for item in group or []:
            source = str(item.get("source", "")).strip()
            url = str(item.get("url", "")).strip()
            key = (source, url)
            if key in seen:
                continue
            seen.add(key)
            merged.append({"source": source, "url": url})
    return merged


def merge_confidence(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in (extra or {}).items():
        if value is None:
            continue
        if key not in merged or merged[key] in (None, "", 0):
            merged[key] = value
            continue
        try:
            merged[key] = max(float(merged[key]), float(value))
        except (TypeError, ValueError):
            merged[key] = value
    return merged


def record_path_iter(input_path: str | Path) -> list[Path]:
    path = Path(input_path)
    if path.is_dir():
        return sorted(path.glob("*.json"))
    return [path]


def normalize_paper_record(raw: dict[str, Any]) -> dict[str, Any]:
    title = str(raw.get("title", "")).strip()
    paper_url = raw.get("paper_url")
    repo_url = normalize_repo_url(raw.get("repo_url"))
    repo_topics = [str(topic).strip() for topic in raw.get("repo_topics", []) if str(topic).strip()]
    repo_homepage = raw.get("repo_homepage")
    archive_page_url = raw.get("archive_page_url")
    capture_timestamp = raw.get("capture_timestamp")
    authors = raw.get("authors") or []
    if isinstance(authors, str):
        authors = [part.strip() for part in authors.split(",") if part.strip()]
    abstract = str(raw.get("abstract", "")).strip()
    inferred_tasks, inferred_methods, inferred_datasets, inferred_benchmarks = infer_tasks_methods_datasets(title, abstract, [])
    tasks = filter_low_signal_labels(
        sorted({task.strip() for task in merge_unique_strings(raw.get("tasks", []), inferred_tasks) if str(task).strip()})
    )
    methods = filter_low_signal_labels(
        sorted({method.strip() for method in merge_unique_strings(raw.get("methods", []), inferred_methods) if str(method).strip()})
    )
    datasets = filter_low_signal_labels(
        sorted({dataset.strip() for dataset in merge_unique_strings(raw.get("datasets", []), inferred_datasets) if str(dataset).strip()})
    )
    benchmarks = filter_low_signal_labels(
        sorted(
            {
                benchmark.strip()
                for benchmark in merge_unique_strings(raw.get("benchmarks", []), inferred_benchmarks)
                if str(benchmark).strip()
            }
        )
    )
    frameworks = sorted(
        set(raw.get("frameworks", []))
        | set(infer_labels(title, abstract, repo_url or "", repo_homepage or "", " ".join(repo_topics), rules=FRAMEWORK_RULES))
    )
    architecture = sorted(
        set(raw.get("architecture", []))
        | set(infer_labels(title, abstract, repo_url or "", repo_homepage or "", " ".join(repo_topics), rules=ARCHITECTURE_RULES))
    )
    repo_slug = extract_repo_slug(repo_url)
    paper_id = raw.get("paper_id")
    if not paper_id:
        paper_id = raw.get("arxiv_id") or raw.get("doi") or stable_id(title, paper_url or "", repo_url or "")
    if repo_topics:
        inferred_topic_tasks, _, inferred_topic_datasets, inferred_topic_benchmarks = infer_tasks_methods_datasets(
            title,
            " ".join(repo_topics),
            [],
        )
        tasks = filter_low_signal_labels(sorted(set(tasks) | set(inferred_topic_tasks)))
        datasets = filter_low_signal_labels(sorted(set(datasets) | set(inferred_topic_datasets)))
        benchmarks = filter_low_signal_labels(sorted(set(benchmarks) | set(inferred_topic_benchmarks)))
    return {
        "paper_id": paper_id,
        "title": title,
        "authors": authors,
        "publication_year": raw.get("publication_year"),
        "venue": raw.get("venue"),
        "paper_url": paper_url,
        "doi": normalize_doi(raw.get("doi")),
        "abstract": abstract,
        "tasks": tasks,
        "methods": methods,
        "datasets": datasets,
        "benchmarks": benchmarks,
        "repo_url": repo_url,
        "repo_host": "github" if repo_slug else raw.get("repo_host"),
        "repo_owner": repo_slug.split("/")[0] if repo_slug else raw.get("repo_owner"),
        "repo_name": repo_slug.split("/")[1] if repo_slug else raw.get("repo_name"),
        "repo_languages": raw.get("repo_languages", {}),
        "repo_topics": repo_topics,
        "repo_homepage": repo_homepage,
        "frameworks": frameworks,
        "architecture": architecture,
        "license": raw.get("license"),
        "stars_at_capture": raw.get("stars_at_capture"),
        "capture_timestamp": capture_timestamp,
        "archive_page_url": archive_page_url,
        "source_provenance": raw.get("source_provenance", []),
        "confidence": raw.get("confidence", {}),
    }


def enrich_with_openalex(record: dict[str, Any], work: dict[str, Any], request_url: str) -> dict[str, Any]:
    title = record.get("title") or work.get("display_name")
    authorships = work.get("authorships") or []
    authors = [item.get("author", {}).get("display_name") for item in authorships if item.get("author")]
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    biblio = work.get("biblio") or {}
    concepts = work.get("concepts") or []
    keywords = [item.get("display_name") for item in concepts[:8] if item.get("display_name")]
    extra = {
        "title": title,
        "authors": authors or record.get("authors") or [],
        "publication_year": work.get("publication_year") or record.get("publication_year"),
        "venue": source.get("display_name") or record.get("venue"),
        "paper_url": record.get("paper_url") or work.get("primary_location", {}).get("landing_page_url"),
        "doi": record.get("doi") or work.get("doi"),
        "abstract": record.get("abstract") or reconstruct_openalex_abstract(work.get("abstract_inverted_index")),
        "methods": merge_unique_strings(record.get("methods", []), keywords),
        "datasets": merge_unique_strings(record.get("datasets", []), infer_labels(title or "", record.get("abstract", "") or "", rules=DATASET_RULES)),
        "source_provenance": merge_provenance(
            record.get("source_provenance", []),
            [{"source": "openalex", "url": request_url}],
        ),
        "confidence": merge_confidence(record.get("confidence", {}), {"paper_match": 0.92}),
    }
    return normalize_paper_record({**record, **extra})


def enrich_with_github(
    record: dict[str, Any],
    repo_payload: dict[str, Any],
    languages_payload: dict[str, Any],
    request_url: str,
    readme_text: str = "",
) -> dict[str, Any]:
    total = sum(languages_payload.values()) or 0
    language_mix = {}
    if total:
        language_mix = {
            language: round(size / total, 4)
            for language, size in sorted(languages_payload.items(), key=lambda item: item[1], reverse=True)
        }
    text_hints = " ".join(
        str(value)
        for value in [
            repo_payload.get("name", ""),
            repo_payload.get("description", ""),
            repo_payload.get("homepage", ""),
            " ".join(repo_payload.get("topics") or []),
            " ".join(language_mix.keys()),
            readme_text,
        ]
    )
    extra = {
        "license": (repo_payload.get("license") or {}).get("spdx_id") or record.get("license"),
        "stars_at_capture": repo_payload.get("stargazers_count") or record.get("stars_at_capture"),
        "repo_languages": language_mix or record.get("repo_languages", {}),
        "repo_topics": merge_unique_strings(record.get("repo_topics", []), repo_payload.get("topics", [])),
        "repo_homepage": repo_payload.get("homepage") or record.get("repo_homepage"),
        "frameworks": merge_unique_strings(
            record.get("frameworks", []),
            infer_labels(text_hints, rules=FRAMEWORK_RULES),
        ),
        "architecture": merge_unique_strings(
            record.get("architecture", []),
            infer_labels(text_hints, rules=ARCHITECTURE_RULES),
        ),
        "datasets": merge_unique_strings(
            record.get("datasets", []),
            infer_labels(text_hints, rules=DATASET_RULES),
        ),
        "benchmarks": merge_unique_strings(
            record.get("benchmarks", []),
            infer_labels(text_hints, rules=BENCHMARK_RULES),
        ),
        "source_provenance": merge_provenance(
            record.get("source_provenance", []),
            [{"source": "github", "url": request_url}],
        ),
        "confidence": merge_confidence(record.get("confidence", {}), {"repo_match": 0.95}),
    }
    return normalize_paper_record({**record, **extra})


def reconstruct_openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positions = {}
    for word, indexes in inverted_index.items():
        for idx in indexes:
            positions[idx] = word
    return " ".join(word for _, word in sorted(positions.items()))


def parse_paper_page(html: str, archive_url: str) -> dict[str, Any]:
    blocks = extract_text_blocks(html)
    title = ""
    authors: list[str] = []
    abstract = ""
    year = None

    for block in blocks:
        if not title and len(block) > 20 and block.lower() not in {"paper", "code"}:
            title = block
            continue
        if not year:
            match = re.search(r"\b(19|20)\d{2}\b", block)
            if match:
                year = int(match.group(0))
        if not abstract and len(block) > 140:
            abstract = block

    links = extract_links(html, base_url=archive_url)
    repo_url = next((normalize_repo_url(link) for link in links if "github.com/" in link), None)
    paper_url = next((link for link in links if "arxiv.org/abs/" in link or "doi.org/" in link), None)
    tasks, methods, datasets, benchmarks = infer_tasks_methods_datasets(title, abstract, links)

    author_match = re.search(r"authors?[:\s]+([^<\n]+)", html, flags=re.IGNORECASE)
    if author_match:
        authors = [part.strip() for part in re.split(r",| and ", author_match.group(1)) if part.strip()]

    return normalize_paper_record(
        {
            "title": title,
            "authors": authors,
            "publication_year": year,
            "paper_url": paper_url,
            "repo_url": repo_url,
            "abstract": abstract,
            "tasks": tasks,
            "methods": methods,
            "datasets": datasets,
            "benchmarks": benchmarks,
            "archive_page_url": archive_url,
            "capture_timestamp": extract_capture_timestamp(archive_url),
            "source_provenance": [{"source": "paperswithcode-archive", "url": archive_url}],
            "confidence": {"paper_match": 0.6, "repo_match": 0.7, "architecture_inference": 0.5},
        }
    )


def extract_capture_timestamp(archive_url: str) -> str | None:
    match = re.search(r"/web/(\d{14})/", archive_url)
    if not match:
        return None
    stamp = match.group(1)
    return f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[8:10]}:{stamp[10:12]}:{stamp[12:14]}Z"


def load_json(path: str | Path, default: Any) -> Any:
    file_path = Path(path)
    if not file_path.exists():
        return default
    content = file_path.read_text(encoding="utf-8").strip()
    if not content:
        return default
    return json.loads(content)


def dump_json(path: str | Path, payload: Any) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def dump_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def classify_entity_type(link: str) -> str:
    """Classify a PapersWithCode archive URL into an entity type.

    Moved from scripts.pwc_discover to break the circular import
    between pwc_merge_seed_sources and pwc_discover.
    """
    for kind in ("paper", "task", "method", "dataset"):
        if f"/{kind}/" in link:
            return kind
    return "unknown"
