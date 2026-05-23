from pathlib import Path
import importlib.util
import shutil
import sys

RENDER = Path(r"C:\Users\Clark\.codex\plugins\cache\openai-primary-runtime\documents\26.426.12240\skills\documents\render_docx.py")
DOCX = Path(r"C:\dev\gradution\.codex_tmp\第3章草稿_edited.docx")
OUT = Path(r"C:\dev\gradution\.codex_tmp\rendered")
TMP_ROOT = Path(r"C:\dev\gradution\.codex_tmp\manual_render_tmp")


def load_render_module():
    spec = importlib.util.spec_from_file_location("docx_render_skill", RENDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main():
    module = load_render_module()
    OUT.mkdir(parents=True, exist_ok=True)
    if TMP_ROOT.exists():
        shutil.rmtree(TMP_ROOT, ignore_errors=True)
    profile = TMP_ROOT / "profile"
    convert = TMP_ROOT / "convert"
    profile.mkdir(parents=True, exist_ok=True)
    convert.mkdir(parents=True, exist_ok=True)

    stem = DOCX.stem
    pdf_path, debug = module.convert_to_pdf(
        str(DOCX.resolve()), str(profile.resolve()), str(convert.resolve()), stem, verbose=True
    )
    if not pdf_path or not Path(pdf_path).exists():
        print(debug)
        raise RuntimeError("Failed to produce PDF")

    dst_pdf = OUT / f"{stem}.pdf"
    shutil.copy2(pdf_path, dst_pdf)
    paths_raw = module.convert_from_path(
        pdf_path,
        dpi=150,
        fmt="png",
        thread_count=4,
        output_folder=str(OUT),
        paths_only=True,
        output_file="page",
    )
    pages = []
    for src in paths_raw:
        base = Path(src).stem
        page_num = int(base.split("-")[-1])
        dst = OUT / f"page-{page_num}.png"
        if dst.exists():
            dst.unlink()
        Path(src).replace(dst)
        pages.append(dst)
    print(f"pdf={dst_pdf}")
    print(f"pages={len(pages)}")
    for page in sorted(pages):
        print(page)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
