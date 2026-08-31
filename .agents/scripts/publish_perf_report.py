"""Publish a cbs-devops performance session report to Google Docs.

The report is authored as Markdown in the session directory that holds the data
and charts, because it belongs next to the runs and CI can write it there. This
script is the one-way bridge from that Markdown to the client-facing Doc, and it
lives here because this is where the Google credentials and the Docs conventions
already are.

The Markdown subset, block parser, Docs append primitives, and the
append-sequentially publisher all live in `markdown_to_docs.py` - shared with
`publish_markdown_doc.py`. What stays here is only what is actually
performance-report-specific: the session-directory layout (`<session>/report.md`
plus its chart PNGs), the default title, and the missing-chart precheck.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import markdown_to_docs as md2docs  # noqa: E402
import pipeline_common  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("session", help="path to the session directory (may be absolute)")
    ap.add_argument("--report", default="report.md")
    ap.add_argument("--title", default=None)
    ap.add_argument("--folder-id", default=None, help="Drive folder for the Doc and charts")
    ap.add_argument("--doc-id", default=None, help="update this Doc instead of creating one")
    ap.add_argument("--no-share", action="store_true",
                    help="refuse to make chart images link-readable (images then cannot embed)")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and report what would be written; touches no Google API")
    args = ap.parse_args()

    session = Path(args.session).resolve()
    report_path = session / args.report
    if not report_path.is_file():
        sys.stderr.write("no report at %s\n" % report_path)
        return 2
    blocks = md2docs.parse(report_path.read_text(encoding="utf-8"))

    title = args.title or "CBS Performance Test Report - %s" % session.name
    counts = md2docs.block_counts(blocks)

    print("session : %s" % session)
    print("title   : %s" % title)
    print("blocks  : %s" % ", ".join("%s=%d" % kv for kv in sorted(counts.items())))

    missing = [b["src"] for b in blocks
               if b["kind"] == "image" and not (session / b["src"]).is_file()]
    if missing:
        sys.stderr.write("missing chart files: %s\n" % ", ".join(missing))
        return 2

    if args.dry_run:
        print("\ndry run - nothing was sent to Google. Outline:")
        md2docs.print_outline(blocks)
        return 0

    os.chdir(Path(__file__).resolve().parents[2])  # get_services uses relative paths
    services = pipeline_common.get_services()

    doc_id = md2docs.create_or_reset_doc(services, title, folder_id=args.folder_id,
                                         doc_id=args.doc_id)
    md2docs.render_blocks(services, doc_id, blocks, asset_root=session,
                          share=not args.no_share, folder_id=args.folder_id)

    print("\ndone: https://docs.google.com/document/d/%s/edit" % doc_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
