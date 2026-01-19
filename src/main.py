import argparse
import sys
from src.crawler import DNSCrawler
from src.output import TextFormatter, GraphvizFormatter, MarkdownFormatter

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="oeuf-dns",
        description="OEUF DNS - Map the DNS environment of a domain"
    )
    parser.add_argument("domain", help="Domain to analyze")
    parser.add_argument("-d", "--depth", type=int, default=2, help="Recursion depth (default: 2)")
    parser.add_argument("-g", "--graph", action="store_true", help="Generate JPG graph image")
    parser.add_argument("-md", "--markdown", action="store_true", help="Generate Markdown report")
    parser.add_argument("-e", "--exclude", nargs="+", default=None, help="Extra patterns to exclude")
    parser.add_argument("-p", "--parallel", type=int, default=5, help="Workers (default: 5)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    parser.add_argument("--no-blacklist", action="store_true", help="Disable default blacklist")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    args = parser.parse_args()

    domain = args.domain.lower().strip()
    if not domain or "." not in domain:
        print(f"Error: Invalid domain '{domain}'", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"Analyzing {domain}...", file=sys.stderr)

    blacklist = [] if args.no_blacklist else None
    if args.exclude:
        from src.crawler import load_blacklist
        blacklist = ([] if args.no_blacklist else load_blacklist()) + [p.lower() for p in args.exclude]

    crawler = DNSCrawler(
        max_depth=args.depth,
        max_workers=args.parallel,
        blacklist=blacklist,
        verbose=args.verbose,
    )

    try:
        graph = crawler.crawl(domain)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    text_fmt = TextFormatter()
    print(text_fmt.format(graph))

    if args.graph:
        gv_fmt = GraphvizFormatter()
        dot = gv_fmt.format(graph)
        path = gv_fmt.to_image(dot, domain)
        if path:
            print(f"Graph saved: {path}", file=sys.stderr)

    if args.markdown:
        md_fmt = MarkdownFormatter()
        content = md_fmt.format(graph)
        out_file = f"{domain.replace('.', '_')}_dns_report.md"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Report saved: {out_file}", file=sys.stderr)

    return 0

if __name__ == "__main__":
    sys.exit(main())
