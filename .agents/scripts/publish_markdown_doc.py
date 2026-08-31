"""Publish any local Markdown file to a Google Doc, in a named Drive folder.

Exists because the assessment/interview feedback skills author their report as
Markdown first (reviewable locally, diffable, and safe to iterate on before
anything reaches Drive) and then need exactly one thing: that same Markdown as a
real Doc, in the right lane folder, with headings/tables/bold intact. Before
this script the only Markdown-to-Docs bridge in the repo was
`publish_perf_report.py`, whose CLI is tied to a performance *session
directory*; every other caller had to hand-roll a one-off batchUpdate script,
which is the repeated one-off-approval friction `docs_editing.py` was added to
end for targeted edits.

Scope: whole-document publish (create, or replace an existing Doc's body).
For a targeted edit inside an existing Doc - append one section, replace one
paragraph - use `docs_editing.py` instead; it never rewrites the whole body.

The Markdown subset and the append-sequentially engine are `markdown_to_docs.py`.

Usage:
    python publish_markdown_doc.py report.md --folder-id <drive folder id> \
        --title "2026-08-28_assessment_feedback - <Person>"
    python publish_markdown_doc.py report.md --doc-id <existing doc id>
    python publish_markdown_doc.py report.md --dry-run

`--folder-id` may also be given as a Drive folder *path* under the workspace
root via `--folder-path` (resolved the way `resolve_drive_path.py` resolves a
mirror path), so a caller does not have to hardcode an id:

    python publish_markdown_doc.py report.md \
        --folder-path "60_Assessments_And_Interviews/internal_assessments/<Person>" \
        --title "..."

Images: a Markdown image embeds only if the file is uploaded to Drive and made
link-readable, which is a real sharing action. This script refuses to do that
silently - pass `--share-images` to allow it, otherwise an image block is a hard
error. Feedback reports are text; this is deliberately opt-in.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import markdown_to_docs as md2docs  # noqa: E402
import pipeline_common  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def resolve_folder_path(drive, relative_path: str) -> str:
    """Walk the workspace root folder tree by name and return the folder id."""
    from m2_workspace_layout import find_child_folder
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

    parent = ROOT_FOLDER_ID
    walked: list[str] = []
    for part in [p for p in relative_path.replace("\\", "/").split("/") if p]:
        found = find_child_folder(drive, parent, part)
        if not found:
            raise SystemExit(
                "no folder %r under %s - create it first (the owning lane's "
                "layout module has an ensure_* helper for this)"
                % (part, "/".join(walked) or "the workspace root")
            )
        walked.append(part)
        parent = found["id"]
    return parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("markdown", help="path to the Markdown file to publish")
    ap.add_argument("--title", default=None,
                    help="Doc name; defaults to the Markdown file's stem")
    ap.add_argument("--folder-id", default=None, help="destination Drive folder id")
    ap.add_argument("--folder-path", default=None,
                    help="destination folder as a path under the workspace root")
    ap.add_argument("--doc-id", default=None,
                    help="replace this Doc's body instead of creating a new Doc")
    ap.add_argument("--share-images", action="store_true",
                    help="allow uploading and link-sharing embedded images")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and report what would be written; touches no Google API")
    args = ap.parse_args()

    if args.folder_id and args.folder_path:
        sys.stderr.write("pass only one of --folder-id / --folder-path\n")
        return 2

    source = Path(args.markdown).resolve()
    if not source.is_file():
        sys.stderr.write("no Markdown file at %s\n" % source)
        return 2
    blocks = md2docs.parse(source.read_text(encoding="utf-8"))
    if not blocks:
        sys.stderr.write("%s parsed to zero blocks - nothing to publish\n" % source.name)
        return 2

    title = args.title or source.stem
    counts = md2docs.block_counts(blocks)
    print("source : %s" % source)
    print("title  : %s" % title)
    print("blocks : %s" % ", ".join("%s=%d" % kv for kv in sorted(counts.items())))

    images = [b["src"] for b in blocks if b["kind"] == "image"]
    if images and not args.share_images:
        sys.stderr.write(
            "refusing to publish: %d image(s) in %s can only embed if uploaded to "
            "Drive and made link-readable. Re-run with --share-images if that is "
            "intended, or remove the images.\n" % (len(images), source.name))
        return 2
    missing = [src for src in images if not (source.parent / src).is_file()]
    if missing:
        sys.stderr.write("missing image files: %s\n" % ", ".join(missing))
        return 2

    if args.dry_run:
        print("\ndry run - nothing was sent to Google. Outline:")
        md2docs.print_outline(blocks)
        return 0

    os.chdir(Path(__file__).resolve().parents[2])  # get_services uses relative paths
    services = pipeline_common.get_services()

    folder_id = args.folder_id
    if args.folder_path:
        folder_id = resolve_folder_path(services["drive"], args.folder_path)
        print("folder : %s -> %s" % (args.folder_path, folder_id))
    if not folder_id and not args.doc_id:
        sys.stderr.write(
            "no destination: pass --folder-id/--folder-path for a new Doc, or "
            "--doc-id to replace an existing one\n")
        return 2

    doc_id = md2docs.create_or_reset_doc(services, title, folder_id=folder_id,
                                        doc_id=args.doc_id)
    md2docs.render_blocks(services, doc_id, blocks, asset_root=source.parent,
                          share=args.share_images, folder_id=folder_id)

    print("\ndone: https://docs.google.com/document/d/%s/edit" % doc_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
